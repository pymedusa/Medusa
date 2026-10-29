import Vuex, { Store } from 'vuex';
import { createLocalVue } from '@vue/test-utils';
import historyModule from '../../src/store/modules/history';
import showsModule from '../../src/store/modules/shows';

describe('Downloaded History show-file refresh', () => {
    const cloneHistoryState = () => JSON.parse(JSON.stringify(historyModule.state));
    const deferred = () => {
        let resolve;
        const promise = new Promise(nextResolve => {
            resolve = nextResolve;
        });
        return { promise, resolve };
    };

    let localVue;

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
    });

    it.each([
        ['compact', true, true],
        ['compact', false, false],
        ['detailed', true, true],
        ['detailed', false, false]
    ])('refreshes files and preserves %s History behavior (active: %s)', async (layout, active, refetch) => {
        const api = { get: jest.fn(() => Promise.resolve({ data: [{ id: 'filtered-row' }], headers: { 'x-pagination-count': '100' } })) };
        const refreshShowFiles = jest.fn().mockResolvedValue(undefined);
        const state = cloneHistoryState();
        state.historyActive = active;
        state.remote.page = 2;
        state.remote.filter = { columnFilters: { resource: 'filtered' } };
        state.remoteCompact.page = 3;
        state.remoteCompact.filter = { columnFilters: { resource: 'compact-filter' } };
        const store = new Store({
            state: {
                auth: { client: { api } },
                config: { layout: { history: layout } }
            },
            actions: { refreshShowFiles },
            modules: {
                history: { ...historyModule, state }
            }
        });
        const event = { id: 'download', statusName: 'Downloaded', series: 'tvdb123', season: 1, episode: 2 };

        await store.dispatch('updateHistory', event);

        expect(refreshShowFiles).toHaveBeenCalledTimes(1);
        expect(refreshShowFiles).toHaveBeenCalledWith(expect.any(Object), {
            showSlug: 'tvdb123', episodes: true, season: 1
        });
        const historyLayout = layout === 'compact' ? 'remoteCompact' : 'remote';
        const otherLayout = layout === 'compact' ? 'remote' : 'remoteCompact';
        const expectedHistoryParams = {
            page: layout === 'compact' ? 3 : 2,
            limit: 25,
            sort: JSON.stringify(state[historyLayout].sort),
            filter: JSON.stringify(state[historyLayout].filter)
        };
        if (layout === 'compact') {
            expectedHistoryParams.compact = true;
        }
        const expectedApiCalls = refetch ? [['/history', { params: expectedHistoryParams }]] : [];
        const expectedRows = refetch ? [{ id: 'filtered-row' }] : (layout === 'detailed' ? [event] : []);
        expect(api.get.mock.calls).toEqual(expectedApiCalls);
        expect(store.state.history[historyLayout].rows).toEqual(expectedRows);
        expect(store.state.history[otherLayout].rows).toEqual([]);
    });

    it.each(['history', 'files'])('waits for both operations when %s resolves first', async first => {
        const historyRequest = deferred();
        const fileRefresh = deferred();
        const api = { get: jest.fn(() => historyRequest.promise) };
        const refreshShowFiles = jest.fn(() => fileRefresh.promise);
        const state = cloneHistoryState();
        state.historyActive = true;
        const store = new Store({
            state: {
                auth: { client: { api } },
                config: { layout: { history: 'detailed' } }
            },
            actions: { refreshShowFiles },
            modules: { history: { ...historyModule, state } }
        });
        const historyUpdated = new Promise(resolve => {
            store.watch(current => current.history.remote.rows, resolve);
        });
        let actionSettled = false;
        const action = store.dispatch('updateHistory', {
            statusName: 'Downloaded', series: 'tvdb123', season: 1
        }).then(() => {
            actionSettled = true;
        });

        if (first === 'history') {
            historyRequest.resolve({ data: [{ id: 'history-row' }], headers: { 'x-pagination-count': '1' } });
            await historyUpdated;
        } else {
            fileRefresh.resolve();
            await fileRefresh.promise;
        }
        await new Promise(resolve => setImmediate(resolve));
        expect(actionSettled).toBe(false);

        if (first === 'history') {
            fileRefresh.resolve();
        } else {
            historyRequest.resolve({ data: [{ id: 'history-row' }], headers: { 'x-pagination-count': '1' } });
            await historyUpdated;
        }
        await action;
        expect(actionSettled).toBe(true);
    });

    it('refreshes cached show files through the real History and shows actions', async () => {
        const historyRows = [{ id: 'matching-row', resource: 'Target.Show.S01E02', season: 1, episode: 2 }];
        const episodeRequests = [];
        const refreshedEpisode = {
            showSlug: 'tvdb123', season: 1, episode: 2, slug: 's01e02', file: { size: 200 }
        };
        const api = {
            get: jest.fn((url, { params }) => {
                if (url === '/history') {
                    return Promise.resolve({ data: historyRows, headers: { 'x-pagination-count': '100' } });
                }
                if (url === '/series/tvdb123') {
                    return Promise.resolve({ data: { id: { slug: 'tvdb123', tvdb: 123 }, indexer: 'tvdb', config: { searchTemplates: [] }, size: 2000 } });
                }
                if (url === '/series/tvdb123/episodes') {
                    episodeRequests.push({ url, params });
                    return Promise.resolve({ data: [refreshedEpisode] });
                }
                throw new Error(`Unexpected API request: ${url}`);
            })
        };
        const state = cloneHistoryState();
        state.historyActive = true;
        state.remote.page = 2;
        state.remote.perPage = 10;
        state.remote.sort = [{ field: 'actionDate', type: 'asc' }];
        state.remote.filter = { columnFilters: { resource: 'Target.Show' } };
        const show = {
            id: { slug: 'tvdb123', tvdb: 123 },
            indexer: 'tvdb',
            config: { searchTemplates: [] },
            size: 1000,
            seasonCount: [{ season: 1, episodeCount: 2 }],
            seasons: [{ season: 1, children: [
                { ...refreshedEpisode, file: { size: 100 } }
            ] }]
        };
        const store = new Store({
            state: {
                auth: { client: { api } },
                config: {
                    layout: { history: 'detailed' },
                    system: { webRoot: '' },
                    general: { recentShows: [] }
                }
            },
            modules: {
                history: { ...historyModule, state },
                shows: {
                    ...showsModule,
                    state: {
                        ...JSON.parse(JSON.stringify(showsModule.state)),
                        shows: [show],
                        currentShow: { showSlug: 'tvdb123' }
                    }
                }
            }
        });
        const event = { statusName: 'Downloaded', series: 'tvdb123', season: 1, episode: 2 };

        await store.dispatch('updateHistory', event);

        expect(api.get).toHaveBeenCalledWith('/history', { params: {
            page: 2,
            limit: 10,
            sort: JSON.stringify(state.remote.sort),
            filter: JSON.stringify(state.remote.filter)
        } });
        expect(store.state.history.remote.rows).toEqual(historyRows);
        expect(episodeRequests).toEqual([{ url: '/series/tvdb123/episodes', params: { limit: 1000, season: 1 } }]);
        expect(store.state.shows.shows[0].size).toBe(2000);
        expect(store.state.shows.shows[0].seasons[0].children[0].file.size).toBe(200);
        expect(store.state.shows.staleEpisodeShows.tvdb123.seasons).toEqual([]);
    });
});
