import Vue from 'vue';
import Vuex from 'vuex';
import HistoryPage from '../../src/components/history.vue';
import historyModule from '../../src/store/modules/history';

Vue.use(Vuex);

const cloneHistoryState = () => JSON.parse(JSON.stringify(historyModule.state));

const deferred = () => {
    let resolve;
    const promise = new Promise(nextResolve => {
        resolve = nextResolve;
    });
    return { promise, resolve };
};

const createHistoryStore = ({ layout = 'detailed', remote = {}, remoteCompact = {}, response } = {}) => {
    const apiResponse = response || {
        data: [{ id: 'api-row' }],
        headers: {
            'x-pagination-count': '4'
        }
    };
    const api = {
        get: jest.fn(() => Promise.resolve(apiResponse))
    };
    const moduleState = cloneHistoryState();
    moduleState.remote = {
        ...moduleState.remote,
        ...remote
    };
    moduleState.remoteCompact = {
        ...moduleState.remoteCompact,
        ...remoteCompact
    };

    const store = new Vuex.Store({
        modules: {
            auth: {
                state: {
                    client: {
                        api
                    }
                }
            },
            config: {
                state: {
                    layout: {
                        history: layout
                    }
                }
            },
            history: {
                ...historyModule,
                state: moduleState
            }
        }
    });

    return {
        api,
        history: store.state.history,
        store
    };
};

const compactQuery = (history, overrides = {}) => ({
    page: history.remoteCompact.page,
    perPage: history.remoteCompact.perPage,
    sort: history.remoteCompact.sort,
    filter: history.remoteCompact.filter,
    compact: true,
    ...overrides
});

describe('history store request freshness and page correction', () => {
    it('toggles the active state from the History page lifecycle hooks', () => {
        const setHistoryActive = jest.fn();

        HistoryPage.mounted.call({ setHistoryActive });
        HistoryPage.beforeDestroy.call({ setHistoryActive });

        expect(setHistoryActive.mock.calls).toEqual([[true], [false]]);
    });

    it('ignores inactive Compact events without inserting or fetching', async () => {
        const existingRows = [{ id: 'existing-compact-row' }];
        const { api, history, store } = createHistoryStore({
            layout: 'compact',
            remoteCompact: {
                rows: existingRows
            }
        });

        await store.dispatch('updateHistory', { id: 'websocket-row' });

        expect(api.get).not.toHaveBeenCalled();
        expect(history.remoteCompact.rows).toEqual(existingRows);
    });

    it('refreshes active Compact history with the current query and only server rows', async () => {
        const sort = [{ field: 'quality', type: 'asc' }];
        const filter = { columnFilters: { resource: 'compact-event' } };
        const { api, history, store } = createHistoryStore({
            layout: 'compact',
            remoteCompact: {
                page: 2,
                perPage: 50,
                sort,
                filter,
                rows: [{ id: 'before-event' }]
            },
            response: {
                data: [{ id: 'server-row' }],
                headers: { 'x-pagination-count': '51' }
            }
        });
        await store.dispatch('setHistoryActive', true);
        await store.dispatch('updateHistory', { id: 'websocket-row' });

        expect(api.get).toHaveBeenCalledTimes(1);
        expect(api.get).toHaveBeenCalledWith('/history', {
            params: {
                page: 2,
                limit: 50,
                sort: JSON.stringify(sort),
                filter: JSON.stringify(filter),
                compact: true
            }
        });
        expect(history.remoteCompact.rows).toEqual([{ id: 'server-row' }]);
        expect(history.remoteCompact.rows).not.toContainEqual({ id: 'websocket-row' });
    });

    it('keeps the newest active Compact event response when requests resolve out of order', async () => {
        const olderResponse = deferred();
        const newerResponse = deferred();
        const { api, history, store } = createHistoryStore({
            layout: 'compact',
            remoteCompact: {
                sort: [{ field: 'date', type: 'desc' }],
                filter: { columnFilters: { resource: 'out-of-order' } }
            }
        });
        api.get
            .mockImplementationOnce(() => olderResponse.promise)
            .mockImplementationOnce(() => newerResponse.promise);
        await store.dispatch('setHistoryActive', true);

        const olderRequest = store.dispatch('updateHistory', { id: 'older-event' });
        const newerRequest = store.dispatch('updateHistory', { id: 'newer-event' });
        newerResponse.resolve({
            data: [{ id: 'newer-server-row' }],
            headers: { 'x-pagination-count': '9' }
        });
        await newerRequest;
        olderResponse.resolve({
            data: [{ id: 'older-server-row' }],
            headers: { 'x-pagination-count': '2' }
        });
        await olderRequest;

        expect(history.remoteCompact.rows).toEqual([{ id: 'newer-server-row' }]);
        expect(history.remoteCompact.totalRows).toBe(9);
    });

    it('clamps active Compact event refreshes without committing obsolete rows', async () => {
        const sort = [{ field: 'quality', type: 'asc' }];
        const filter = { columnFilters: { resource: 'compact-clamp-event' } };
        const { api, history, store } = createHistoryStore({
            layout: 'compact',
            remoteCompact: {
                rows: [{ id: 'before-event-clamp' }],
                page: 4,
                perPage: 25,
                sort,
                filter
            }
        });
        api.get
            .mockImplementationOnce(() => Promise.resolve({
                data: [{ id: 'obsolete-event-page-row' }],
                headers: { 'x-pagination-count': '26' }
            }))
            .mockImplementationOnce(() => Promise.resolve({
                data: [{ id: 'clamped-event-row' }],
                headers: { 'x-pagination-count': '26' }
            }));
        await store.dispatch('setHistoryActive', true);
        await store.dispatch('updateHistory', { id: 'websocket-event' });

        expect(api.get).toHaveBeenCalledTimes(2);
        expect(api.get.mock.calls[1][1].params).toEqual({
            page: 2,
            limit: 25,
            sort: JSON.stringify(sort),
            filter: JSON.stringify(filter),
            compact: true
        });
        expect(history.remoteCompact.page).toBe(2);
        expect(history.remoteCompact.rows).toEqual([{ id: 'clamped-event-row' }]);
        expect(history.remoteCompact.rows).not.toContainEqual({ id: 'obsolete-event-page-row' });
    });

    it('preserves Detailed websocket events as raw prepends', async () => {
        const existingRows = [{ id: 'existing-detailed-row' }];
        const { api, history, store } = createHistoryStore({
            remote: {
                rows: existingRows
            }
        });
        await store.dispatch('updateHistory', { id: 'detailed-event' });

        expect(api.get).not.toHaveBeenCalled();
        expect(history.remote.rows).toEqual([{ id: 'detailed-event' }, { id: 'existing-detailed-row' }]);
    });

    it('keeps the newer Compact response and loading state after out-of-order completion', async () => {
        const olderResponse = deferred();
        const newerResponse = deferred();
        const { api, history, store } = createHistoryStore({
            remoteCompact: {
                rows: [{ id: 'before-refresh' }],
                totalRows: 1,
                page: 1,
                perPage: 25,
                sort: [{ field: 'date', type: 'desc' }],
                filter: { columnFilters: { resource: 'same-query' } }
            }
        });
        api.get
            .mockImplementationOnce(() => olderResponse.promise)
            .mockImplementationOnce(() => newerResponse.promise);

        const query = compactQuery(history);
        const olderRequest = store.dispatch('getHistory', query);
        const newerRequest = store.dispatch('getHistory', query);
        expect(history.loading).toBe(true);

        newerResponse.resolve({
            data: [{ id: 'newer-row' }],
            headers: { 'x-pagination-count': '9' }
        });
        await newerRequest;
        expect(history.remoteCompact.rows).toEqual([{ id: 'newer-row' }]);
        expect(history.remoteCompact.totalRows).toBe(9);
        expect(history.loading).toBe(false);

        olderResponse.resolve({
            data: [{ id: 'older-row' }],
            headers: { 'x-pagination-count': '2' }
        });
        await olderRequest;
        expect(history.remoteCompact.rows).toEqual([{ id: 'newer-row' }]);
        expect(history.remoteCompact.totalRows).toBe(9);
        expect(history.loading).toBe(false);
    });

    it('keeps loading while an older Compact response completes before the latest request', async () => {
        const olderResponse = deferred();
        const newerResponse = deferred();
        const existingRows = [{ id: 'before-refresh' }];
        const { api, history, store } = createHistoryStore({
            remoteCompact: {
                rows: existingRows,
                totalRows: 1,
                page: 1,
                perPage: 25,
                sort: [{ field: 'date', type: 'desc' }],
                filter: { columnFilters: { resource: 'same-query' } }
            }
        });
        api.get
            .mockImplementationOnce(() => olderResponse.promise)
            .mockImplementationOnce(() => newerResponse.promise);

        const query = compactQuery(history);
        const olderRequest = store.dispatch('getHistory', query);
        const newerRequest = store.dispatch('getHistory', query);

        olderResponse.resolve({
            data: [{ id: 'older-row' }],
            headers: { 'x-pagination-count': '2' }
        });
        await olderRequest;
        expect(history.remoteCompact.rows).toEqual(existingRows);
        expect(history.remoteCompact.totalRows).toBe(1);
        expect(history.loading).toBe(true);

        newerResponse.resolve({
            data: [{ id: 'newer-row' }],
            headers: { 'x-pagination-count': '9' }
        });
        await newerRequest;
        expect(history.remoteCompact.rows).toEqual([{ id: 'newer-row' }]);
        expect(history.remoteCompact.totalRows).toBe(9);
        expect(history.loading).toBe(false);
    });

    it('discards a Compact response when its live query changes', async () => {
        const response = deferred();
        const existingRows = [{ id: 'before-query-change' }];
        const { api, history, store } = createHistoryStore({
            remoteCompact: {
                rows: existingRows,
                totalRows: 7,
                page: 1,
                perPage: 25,
                sort: [{ field: 'date', type: 'desc' }],
                filter: { columnFilters: { resource: 'before-query-change' } }
            }
        });
        api.get.mockImplementation(() => response.promise);

        const request = store.dispatch('getHistory', compactQuery(history));
        history.remoteCompact.filter = { columnFilters: { resource: 'after-query-change' } };
        response.resolve({
            data: [{ id: 'stale-row' }],
            headers: { 'x-pagination-count': '99' }
        });
        await request;

        expect(api.get).toHaveBeenCalledTimes(1);
        expect(history.remoteCompact.rows).toEqual(existingRows);
        expect(history.remoteCompact.totalRows).toBe(7);
        expect(history.loading).toBe(false);
    });

    it('clamps a Compact page and refetches exact params without committing the stale page', async () => {
        const finalResponse = deferred();
        const sort = [{ field: 'quality', type: 'asc' }];
        const filter = { columnFilters: { resource: 'compact episode' } };
        const { api, history, store } = createHistoryStore({
            remoteCompact: {
                rows: [{ id: 'before-clamp' }],
                totalRows: 100,
                page: 4,
                perPage: 25,
                sort,
                filter
            }
        });
        api.get
            .mockImplementationOnce(() => Promise.resolve({
                data: [{ id: 'stale-page-row' }],
                headers: { 'x-pagination-count': '26' }
            }))
            .mockImplementationOnce(() => finalResponse.promise);

        const request = store.dispatch('getHistory', compactQuery(history, { page: 4 }));
        await Promise.resolve();
        await Promise.resolve();

        expect(api.get).toHaveBeenCalledTimes(2);
        expect(api.get.mock.calls[0][1].params).toEqual({
            page: 4,
            limit: 25,
            sort: JSON.stringify(sort),
            filter: JSON.stringify(filter),
            compact: true
        });
        expect(api.get.mock.calls[1][1].params).toEqual({
            page: 2,
            limit: 25,
            sort: JSON.stringify(sort),
            filter: JSON.stringify(filter),
            compact: true
        });
        expect(history.remoteCompact.page).toBe(2);
        expect(history.remoteCompact.totalRows).toBe(26);
        expect(history.remoteCompact.rows).toEqual([{ id: 'before-clamp' }]);

        finalResponse.resolve({
            data: [{ id: 'clamped-page-row' }],
            headers: { 'x-pagination-count': '26' }
        });
        await request;
        expect(history.remoteCompact.rows).toEqual([{ id: 'clamped-page-row' }]);
    });

    it('uses one request for a valid Compact page', async () => {
        const { api, history, store } = createHistoryStore({
            remoteCompact: {
                page: 2,
                perPage: 50,
                sort: [{ field: 'date', type: 'desc' }],
                filter: { columnFilters: { resource: 'valid-page' } }
            },
            response: {
                data: [{ id: 'valid-page-row' }],
                headers: { 'x-pagination-count': '51' }
            }
        });

        await store.dispatch('getHistory', compactQuery(history));

        expect(api.get).toHaveBeenCalledTimes(1);
        expect(history.remoteCompact.page).toBe(2);
        expect(history.remoteCompact.totalRows).toBe(51);
        expect(history.remoteCompact.rows).toEqual([{ id: 'valid-page-row' }]);
    });
});
