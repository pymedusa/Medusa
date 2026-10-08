import Vue from 'vue';
import Vuex from 'vuex';
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

describe('history store', () => {
    it.each(['Snatched', 'Downloaded', 'Failed'])(
        'reapplies every active filter before showing a new %s websocket row',
        async statusName => {
            const apiRows = [{ id: 'filtered-api-row' }];
            const websocketRow = {
                id: `websocket-${statusName.toLowerCase()}`,
                statusName,
                resource: 'Unrelated.Show.S01E01.720p',
                quality: '720p',
                provider: {
                    name: 'Other Provider'
                },
                size: 512,
                clientStatus: 1
            };
            const mismatchingAction = statusName === 'Downloaded' ? 2 : 4;
            const sort = [{ field: 'date', type: 'asc' }];
            const filter = {
                scope: 'all',
                columnFilters: {
                    resource: 'caramelise',
                    statusName: mismatchingAction,
                    quality: '1080p',
                    providerId: 'Nyaa.si',
                    size: '> 1024',
                    clientStatus: 3
                }
            };
            const { api, history, store } = createHistoryStore({
                remote: {
                    rows: [{ id: 'old-row' }],
                    totalRows: 1,
                    page: 1,
                    perPage: 50,
                    sort,
                    filter
                }
            });
            api.get.mockImplementation((_url, { params }) => {
                const activeFilters = JSON.parse(params.filter).columnFilters;
                const filtersRemain = Object.keys(activeFilters).length > 0;
                const data = filtersRemain ? apiRows : [websocketRow];
                return Promise.resolve({
                    data,
                    headers: {
                        'x-pagination-count': String(data.length)
                    }
                });
            });

            await store.dispatch('setHistoryActive', true);
            await store.dispatch('updateHistory', websocketRow);

            expect(api.get).toHaveBeenLastCalledWith('/history', {
                params: {
                    page: 1,
                    limit: 50,
                    sort: JSON.stringify(sort),
                    filter: JSON.stringify(filter)
                }
            });
            expect(history.remote.rows).toEqual(apiRows);
            expect(history.remote.rows).not.toContain(websocketRow);
            expect(history.remote.totalRows).toBe(1);

            const observedRows = [];
            const relaxations = ['clientStatus', 'size', 'providerId', 'quality', 'statusName', 'resource'];
            await relaxations.reduce((previous, field) => previous.then(async () => {
                const relaxedFilters = Object.assign({}, history.remote.filter.columnFilters);
                delete relaxedFilters[field];
                history.remote.filter = Object.assign({}, history.remote.filter, {
                    columnFilters: relaxedFilters
                });

                await store.dispatch('updateHistory', websocketRow);
                observedRows.push(history.remote.rows.slice());
            }), Promise.resolve());

            expect(api.get).toHaveBeenCalledTimes(7);
            expect(JSON.parse(api.get.mock.calls[6][1].params.filter).columnFilters).toEqual({});
            expect(observedRows).toEqual([
                apiRows,
                apiRows,
                apiRows,
                apiRows,
                apiRows,
                [websocketRow]
            ]);
        }
    );

    it('keeps the newer active Detailed response when requests resolve out of order', async () => {
        const olderResponse = deferred();
        const newerResponse = deferred();
        const { api, history, store } = createHistoryStore({
            remote: {
                rows: [{ id: 'before-refresh' }],
                totalRows: 1,
                page: 1,
                perPage: 25,
                sort: [{ field: 'date', type: 'desc' }],
                filter: {
                    columnFilters: {
                        resource: 'stacked episode',
                        statusName: 'Downloaded'
                    }
                }
            }
        });
        api.get
            .mockImplementationOnce(() => olderResponse.promise)
            .mockImplementationOnce(() => newerResponse.promise);

        await store.dispatch('setHistoryActive', true);
        const olderRequest = store.dispatch('updateHistory', { id: 'older-websocket-row' });
        const newerRequest = store.dispatch('updateHistory', { id: 'newer-websocket-row' });

        newerResponse.resolve({
            data: [{ id: 'newer-api-row' }],
            headers: {
                'x-pagination-count': '9'
            }
        });
        await newerRequest;
        expect(history.remote.rows).toEqual([{ id: 'newer-api-row' }]);
        expect(history.remote.totalRows).toBe(9);

        olderResponse.resolve({
            data: [{ id: 'older-api-row' }],
            headers: {
                'x-pagination-count': '2'
            }
        });
        await olderRequest;
        expect(history.remote.rows).toEqual([{ id: 'newer-api-row' }]);
        expect(history.remote.totalRows).toBe(9);
        expect(history.historyRequestIds.detailed).toBe(2);
    });

    it('keeps a valid carried Detailed page and commits it with one request', async () => {
        const sort = [{ field: 'actionDate', type: 'asc' }];
        const filter = {
            columnFilters: {
                resource: 'carried episode'
            }
        };
        const { api, history, store } = createHistoryStore({
            remote: {
                page: 2,
                perPage: 50,
                sort,
                filter
            },
            response: {
                data: [{ id: 'valid-page-row' }],
                headers: {
                    'x-pagination-count': '51'
                }
            }
        });

        await store.dispatch('getHistory', {
            page: 2,
            perPage: 50,
            sort,
            filter
        });

        expect(api.get).toHaveBeenCalledTimes(1);
        expect(api.get).toHaveBeenCalledWith('/history', {
            params: {
                page: 2,
                limit: 50,
                sort: JSON.stringify(sort),
                filter: JSON.stringify(filter)
            }
        });
        expect(history.remote.page).toBe(2);
        expect(history.remote.totalRows).toBe(51);
        expect(history.remote.rows).toEqual([{ id: 'valid-page-row' }]);
    });

    it('clamps an out-of-range Detailed page and refetches without committing stale rows', async () => {
        const sort = [{ field: 'date', type: 'desc' }];
        const filter = {
            columnFilters: {
                resource: 'detailed episode',
                statusName: 'Downloaded'
            }
        };
        const firstResponse = {
            data: [{ id: 'out-of-range-row' }],
            headers: {
                'x-pagination-count': '101'
            }
        };
        const finalResponse = {
            data: [{ id: 'clamped-detailed-row' }],
            headers: {
                'x-pagination-count': '101'
            }
        };
        const { api, history, store } = createHistoryStore({
            remote: {
                rows: [{ id: 'before-clamp' }],
                totalRows: 200,
                page: 5,
                perPage: 50,
                sort,
                filter
            }
        });
        api.get
            .mockImplementationOnce(() => Promise.resolve(firstResponse))
            .mockImplementationOnce(() => Promise.resolve(finalResponse));

        await store.dispatch('getHistory', {
            page: 5,
            perPage: 50,
            sort,
            filter
        });

        expect(api.get).toHaveBeenCalledTimes(2);
        expect(api.get.mock.calls[0][1].params.page).toBe(5);
        expect(api.get.mock.calls[1][1].params).toEqual({
            page: 3,
            limit: 50,
            sort: JSON.stringify(sort),
            filter: JSON.stringify(filter)
        });
        expect(history.remote.page).toBe(3);
        expect(history.remote.totalRows).toBe(101);
        expect(history.remote.rows).toEqual([{ id: 'clamped-detailed-row' }]);
    });

    it('clamps an out-of-range Compact page using its grouped total', async () => {
        const sort = [{ field: 'quality', type: 'asc' }];
        const filter = {
            columnFilters: {
                resource: 'compact episode'
            }
        };
        const { api, history, store } = createHistoryStore({
            layout: 'compact',
            remote: {
                page: 2,
                rows: [{ id: 'detailed-row' }]
            },
            remoteCompact: {
                rows: [{ id: 'before-compact-clamp' }],
                totalRows: 100,
                page: 4,
                perPage: 25,
                sort,
                filter
            }
        });
        api.get
            .mockImplementationOnce(() => Promise.resolve({
                data: [{ id: 'out-of-range-group' }],
                headers: {
                    'x-pagination-count': '26'
                }
            }))
            .mockImplementationOnce(() => Promise.resolve({
                data: [{ id: 'clamped-compact-group' }],
                headers: {
                    'x-pagination-count': '26'
                }
            }));

        await store.dispatch('getHistory', {
            page: 4,
            perPage: 25,
            sort,
            filter,
            compact: true
        });

        expect(api.get).toHaveBeenCalledTimes(2);
        expect(api.get.mock.calls[1][1].params).toEqual({
            page: 2,
            limit: 25,
            sort: JSON.stringify(sort),
            filter: JSON.stringify(filter),
            compact: true
        });
        expect(history.remote.page).toBe(2);
        expect(history.remoteCompact.page).toBe(2);
        expect(history.remoteCompact.totalRows).toBe(26);
        expect(history.remoteCompact.rows).toEqual([{ id: 'clamped-compact-group' }]);
    });

    it('clamps an empty Detailed result to page 1 and refetches once', async () => {
        const sort = [{ field: 'actionDate', type: 'desc' }];
        const filter = {
            columnFilters: {
                resource: 'empty episode'
            }
        };
        const { api, history, store } = createHistoryStore({
            remote: {
                rows: [{ id: 'before-empty-clamp' }],
                page: 4,
                perPage: 25,
                sort,
                filter
            }
        });
        api.get
            .mockImplementationOnce(() => Promise.resolve({
                data: [{ id: 'stale-empty-page-row' }],
                headers: {
                    'x-pagination-count': '0'
                }
            }))
            .mockImplementationOnce(() => Promise.resolve({
                data: [],
                headers: {
                    'x-pagination-count': '0'
                }
            }));

        await store.dispatch('getHistory', {
            page: 4,
            perPage: 25,
            sort,
            filter
        });

        expect(api.get).toHaveBeenCalledTimes(2);
        expect(api.get.mock.calls[1][1].params.page).toBe(1);
        expect(history.remote.page).toBe(1);
        expect(history.remote.totalRows).toBe(0);
        expect(history.remote.rows).toEqual([]);
    });

    it.each([
        ['page', history => {
            history.remote.page = 4;
        }],
        ['sort', history => {
            history.remote.sort = [{ field: 'actionDate', type: 'asc' }];
        }],
        ['filter', history => {
            history.remote.filter = {
                columnFilters: {
                    resource: 'changed episode'
                }
            };
        }]
    ])('discards a Detailed response when the live %s query changes without a newer request', async (_field, changeQuery) => {
        const response = deferred();
        const existingRows = [{ id: 'before-live-query-change' }];
        const { api, history, store } = createHistoryStore({
            remote: {
                rows: existingRows,
                totalRows: 7,
                page: 3,
                perPage: 50,
                sort: [{ field: 'date', type: 'desc' }],
                filter: {
                    columnFilters: {
                        resource: 'original episode',
                        statusName: 'Downloaded'
                    }
                }
            }
        });
        api.get.mockImplementation(() => response.promise);

        await store.dispatch('setHistoryActive', true);
        const request = store.dispatch('updateHistory', { id: 'websocket-row' });
        changeQuery(history);

        response.resolve({
            data: [{ id: 'stale-api-row' }],
            headers: {
                'x-pagination-count': '99'
            }
        });
        await request;

        expect(api.get).toHaveBeenCalledTimes(1);
        expect(history.remote.rows).toEqual(existingRows);
        expect(history.remote.totalRows).toBe(7);
    });

    it('discards an active Detailed response after compact transition invalidation', async () => {
        const response = deferred();
        const existingRows = [{ id: 'existing-detailed-row' }];
        const { api, history, store } = createHistoryStore({
            remote: {
                rows: existingRows,
                totalRows: 6,
                page: 1,
                perPage: 50,
                sort: [{ field: 'date', type: 'asc' }],
                filter: {
                    columnFilters: {
                        resource: 'episode to clear'
                    }
                }
            },
            remoteCompact: {
                filter: {
                    columnFilters: {
                        resource: 'compact episode',
                        statusName: 'Failed'
                    }
                }
            }
        });
        api.get.mockImplementation(() => response.promise);

        await store.dispatch('setHistoryActive', true);
        const request = store.dispatch('updateHistory', { id: 'websocket-row' });
        await store.dispatch('prepareHistoryLayoutTransition', { layout: 'compact' });

        response.resolve({
            data: [{ id: 'stale-api-row' }],
            headers: {
                'x-pagination-count': '99'
            }
        });
        await request;

        expect(history.remote.rows).toEqual(existingRows);
        expect(history.remote.totalRows).toBe(6);
        expect(history.remote.page).toBe(1);
        expect(history.remote.filter.columnFilters).toEqual({
            resource: 'episode to clear'
        });
        expect(history.historyRequestIds.detailed).toBe(2);
    });

    it('does not clamp or refetch an out-of-range stale Detailed response', async () => {
        const response = deferred();
        const existingRows = [{ id: 'before-stale-clamp' }];
        const { api, history, store } = createHistoryStore({
            remote: {
                rows: existingRows,
                totalRows: 200,
                page: 5,
                perPage: 50,
                sort: [{ field: 'date', type: 'desc' }],
                filter: {
                    columnFilters: {
                        resource: 'stale episode'
                    }
                }
            }
        });
        api.get.mockImplementation(() => response.promise);

        const request = store.dispatch('getHistory', {
            page: 5,
            perPage: 50,
            sort: history.remote.sort,
            filter: history.remote.filter
        });
        history.remote.filter = {
            columnFilters: {
                resource: 'changed before response'
            }
        };
        response.resolve({
            data: [{ id: 'stale-out-of-range-row' }],
            headers: {
                'x-pagination-count': '1'
            }
        });
        await request;

        expect(api.get).toHaveBeenCalledTimes(1);
        expect(history.remote.page).toBe(5);
        expect(history.remote.totalRows).toBe(200);
        expect(history.remote.rows).toEqual(existingRows);
    });

    it('prepends inactive detailed websocket history without fetching', async () => {
        const existingRow = { id: 'old-row' };
        const websocketRow = { id: 'websocket-row' };
        const { api, history, store } = createHistoryStore({
            remote: {
                rows: [existingRow],
                totalRows: 1
            }
        });

        await store.dispatch('updateHistory', websocketRow);

        expect(api.get).not.toHaveBeenCalled();
        expect(history.remote.rows).toEqual([websocketRow, existingRow]);
        expect(history.remote.totalRows).toBe(1);
    });

    it('refetches active compact history without inserting the raw websocket row', async () => {
        const existingRow = { id: 'compact-old-row' };
        const websocketRow = { id: 'websocket-row' };
        const { api, history, store } = createHistoryStore({
            layout: 'compact',
            remoteCompact: {
                rows: [existingRow],
                totalRows: 1
            }
        });

        await store.dispatch('setHistoryActive', true);
        await store.dispatch('updateHistory', websocketRow);

        expect(api.get).toHaveBeenCalledTimes(1);
        expect(api.get).toHaveBeenCalledWith('/history', {
            params: {
                page: 1,
                limit: 25,
                sort: JSON.stringify([{ field: 'date', type: 'desc' }]),
                filter: JSON.stringify({}),
                compact: true
            }
        });
        expect(history.remoteCompact.rows).toEqual([{ id: 'api-row' }]);
        expect(history.remoteCompact.rows).not.toContain(websocketRow);
        expect(history.remoteCompact.totalRows).toBe(4);
    });

    it('keeps bare getHistory untracked and commits rows without clamping', async () => {
        const existingRows = [{ id: 'before-bare-load' }];
        const { api, history, store } = createHistoryStore({
            remote: {
                page: 4,
                rows: existingRows,
                totalRows: 1
            },
            response: {
                data: [{ id: 'bare-api-row' }],
                headers: {
                    'x-pagination-count': '4'
                }
            }
        });

        await store.dispatch('getHistory');

        expect(api.get).toHaveBeenCalledTimes(1);
        expect(api.get).toHaveBeenCalledWith('/history', {
            params: {
                page: 1,
                limit: 1000,
                sort: JSON.stringify([{ field: 'date', type: 'desc' }]),
                filter: JSON.stringify({})
            }
        });
        expect(history.remote.rows).toEqual([{ id: 'bare-api-row' }]);
        expect(history.remote.totalRows).toBe(4);
        expect(history.remote.page).toBe(4);
        expect(history.historyRequestIds).toEqual({ detailed: 0, compact: 0 });
    });

    it('keeps show-specific getHistory untracked and commits show data without clamping', async () => {
        const showRow = {
            id: 'show-api-row',
            season: 1,
            episode: 2,
            resource: 'Show.Release.S01E02'
        };
        const { api, history, store } = createHistoryStore({
            remote: {
                page: 9,
                rows: [{ id: 'before-show-load' }],
                totalRows: 3
            },
            response: {
                data: [showRow],
                headers: {
                    'x-pagination-count': '1'
                }
            }
        });

        await store.dispatch('getHistory', { showSlug: 'show-slug' });

        expect(api.get).toHaveBeenCalledTimes(1);
        expect(api.get).toHaveBeenCalledWith('/history/show-slug', {
            params: {
                page: 1,
                limit: 1000,
                sort: JSON.stringify([{ field: 'date', type: 'desc' }]),
                filter: JSON.stringify({})
            }
        });
        expect(history.episodeHistory['show-slug'].s01e02).toEqual([showRow]);
        expect(history.remote.rows).toEqual([{ id: 'before-show-load' }]);
        expect(history.remote.page).toBe(9);
        expect(history.remote.totalRows).toBe(1);
        expect(history.historyRequestIds).toEqual({ detailed: 0, compact: 0 });
    });

    it('initializes the shared Episode filter once from the mounted layout without resetting either page', async () => {
        const { history, store } = createHistoryStore({
            layout: 'detailed',
            remote: {
                page: 4,
                filter: {
                    saved: true,
                    columnFilters: {
                        resource: 'stored episode',
                        quality: '1080p'
                    }
                }
            },
            remoteCompact: {
                page: 8,
                filter: {
                    saved: 'compact',
                    columnFilters: {
                        resource: 'compact episode',
                        statusName: 'Downloaded'
                    }
                }
            }
        });

        await store.dispatch('initializeEpisodeFilter', { layout: 'detailed' });

        expect(history.episodeFilter).toEqual({
            inputValue: 'stored episode',
            filterValue: 'stored episode',
            malformed: false,
            initialized: true
        });
        expect(history.remote.page).toBe(4);
        expect(history.remoteCompact.page).toBe(8);
        expect(history.remote.filter.columnFilters).toEqual({
            resource: 'stored episode',
            quality: '1080p'
        });
        expect(history.remoteCompact.filter.columnFilters).toEqual({
            resource: 'stored episode',
            statusName: 'Downloaded'
        });

        history.remote.filter.columnFilters.resource = 'changed after init';
        await store.dispatch('initializeEpisodeFilter', { layout: 'compact' });
        expect(history.episodeFilter.filterValue).toBe('stored episode');
        expect(history.remote.page).toBe(4);
        expect(history.remoteCompact.page).toBe(8);
    });

    it('updates raw and normalized Episode state across both layouts while preserving filter fields', async () => {
        const { history, store } = createHistoryStore({
            remote: {
                page: 6,
                filter: {
                    saved: 'detailed',
                    columnFilters: {
                        resource: 'old detailed',
                        quality: '1080p'
                    }
                }
            },
            remoteCompact: {
                page: 9,
                filter: {
                    saved: 'compact',
                    columnFilters: {
                        resource: 'old compact',
                        statusName: 'Downloaded'
                    }
                }
            }
        });

        await store.dispatch('updateEpisodeFilter', {
            inputValue: "'  typed episode",
            filterValue: 'typed episode',
            malformed: true
        });

        expect(history.episodeFilter).toEqual({
            inputValue: "'  typed episode",
            filterValue: 'typed episode',
            malformed: true,
            initialized: true
        });
        expect(history.remote.page).toBe(1);
        expect(history.remoteCompact.page).toBe(1);
        expect(history.remote.filter).toEqual({
            saved: 'detailed',
            columnFilters: {
                resource: 'typed episode',
                quality: '1080p'
            }
        });
        expect(history.remoteCompact.filter).toEqual({
            saved: 'compact',
            columnFilters: {
                resource: 'typed episode',
                statusName: 'Downloaded'
            }
        });
    });

    it('prepares compact transitions by retaining only the shared Episode filter', async () => {
        const { history, store } = createHistoryStore({
            remote: {
                page: 5,
                filter: {
                    saved: 'detailed',
                    columnFilters: {
                        resource: 'old detailed',
                        providerId: 'provider',
                        quality: '1080p'
                    }
                }
            },
            remoteCompact: {
                page: 7,
                filter: {
                    saved: 'compact',
                    columnFilters: {
                        resource: 'old compact',
                        statusName: 'Downloaded',
                        clientStatus: 3
                    }
                }
            }
        });

        await store.dispatch('updateEpisodeFilter', {
            inputValue: 'shared episode',
            filterValue: 'shared episode',
            malformed: false
        });
        history.remote.page = 5;
        history.remoteCompact.page = 7;
        await store.dispatch('prepareHistoryLayoutTransition', { layout: 'compact' });

        expect(history.remote.page).toBe(5);
        expect(history.remoteCompact.page).toBe(5);
        expect(history.remote.filter).toEqual({
            saved: 'detailed',
            columnFilters: {
                resource: 'shared episode'
            }
        });
        expect(history.remoteCompact.filter).toEqual({
            saved: 'compact',
            columnFilters: {
                resource: 'shared episode'
            }
        });

        const filtersAfterCompact = JSON.parse(JSON.stringify({
            remote: history.remote,
            remoteCompact: history.remoteCompact
        }));
        await store.dispatch('prepareHistoryLayoutTransition', { layout: 'detailed' });
        expect({
            remote: history.remote,
            remoteCompact: history.remoteCompact
        }).toEqual(filtersAfterCompact);

        await store.dispatch('updateEpisodeFilter', {
            inputValue: '',
            filterValue: '',
            malformed: false
        });
        await store.dispatch('prepareHistoryLayoutTransition', { layout: 'compact' });
        expect(history.remote.filter.columnFilters).toEqual({});
        expect(history.remoteCompact.filter.columnFilters).toEqual({});
    });

    it.each([
        ['Detailed Date asc to Compact Time', { sourceLayout: 'detailed', targetLayout: 'compact', sourceField: 'date', type: 'asc' }],
        ['Detailed Date desc to Compact Time', { sourceLayout: 'detailed', targetLayout: 'compact', sourceField: 'date', type: 'desc' }],
        ['Compact Time asc to Detailed Date', { sourceLayout: 'compact', targetLayout: 'detailed', sourceField: 'actionDate', type: 'asc' }],
        ['Compact Time desc to Detailed Date', { sourceLayout: 'compact', targetLayout: 'detailed', sourceField: 'actionDate', type: 'desc' }]
    ])('maps %s to actionDate while preserving direction', async (_name, sortCase) => {
        const { sourceLayout, targetLayout, sourceField, type } = sortCase;
        const sourceSort = [{ field: sourceField, type }];
        const { history, store } = createHistoryStore({
            layout: sourceLayout,
            remote: sourceLayout === 'detailed' ? { page: 4, perPage: 50, sort: sourceSort } : {},
            remoteCompact: sourceLayout === 'compact' ? { page: 6, perPage: 100, sort: sourceSort } : {}
        });

        await store.dispatch('prepareHistoryLayoutTransition', { layout: targetLayout });

        const target = targetLayout === 'compact' ? history.remoteCompact : history.remote;
        const source = sourceLayout === 'compact' ? history.remoteCompact : history.remote;
        expect(target.sort).toEqual([{ field: 'actionDate', type }]);
        expect(history.remote.page).toBe(source.page);
        expect(history.remoteCompact.page).toBe(source.page);
        expect(history.remote.perPage).toBe(source.perPage);
        expect(history.remoteCompact.perPage).toBe(source.perPage);
    });

    it.each([
        ['Detailed Quality asc to Compact Quality', 'detailed', 'compact', 'asc'],
        ['Detailed Quality desc to Compact Quality', 'detailed', 'compact', 'desc'],
        ['Compact Quality asc to Detailed Quality', 'compact', 'detailed', 'asc'],
        ['Compact Quality desc to Detailed Quality', 'compact', 'detailed', 'desc']
    ])('maps %s while preserving direction', async (_name, sourceLayout, targetLayout, type) => {
        const sourceSort = [{ field: 'quality', type }];
        const { history, store } = createHistoryStore({
            layout: sourceLayout,
            remote: sourceLayout === 'detailed' ? { sort: sourceSort } : {},
            remoteCompact: sourceLayout === 'compact' ? { sort: sourceSort } : {}
        });

        await store.dispatch('prepareHistoryLayoutTransition', { layout: targetLayout });

        const target = targetLayout === 'compact' ? history.remoteCompact : history.remote;
        expect(target.sort).toEqual([{ field: 'quality', type }]);
    });

    it.each([
        ['Detailed statusName sort', 'detailed', 'compact', { field: 'statusName', type: 'asc' }],
        ['Detailed provider sort', 'detailed', 'compact', { field: 'providerId', type: 'asc' }],
        ['Detailed size sort', 'detailed', 'compact', { field: 'size', type: 'desc' }],
        ['Detailed clientStatus sort', 'detailed', 'compact', { field: 'clientStatus', type: 'asc' }],
        ['Compact subtitled sort', 'compact', 'detailed', { field: 'subtitled', type: 'desc' }],
        ['empty sort', 'detailed', 'compact', null],
        ['none sort', 'compact', 'detailed', { field: 'date', type: 'none' }],
        ['invalid sort', 'detailed', 'compact', { field: 'episodeTitle', type: 'asc' }]
    ])('falls back for %s', async (_name, sourceLayout, targetLayout, sourceSort) => {
        const source = sourceLayout === 'compact' ? { sort: sourceSort ? [sourceSort] : [] } : { sort: sourceSort ? [sourceSort] : [] };
        const { history, store } = createHistoryStore({
            layout: sourceLayout,
            remote: sourceLayout === 'detailed' ? source : {},
            remoteCompact: sourceLayout === 'compact' ? source : {}
        });

        await store.dispatch('prepareHistoryLayoutTransition', { layout: targetLayout });

        const target = targetLayout === 'compact' ? history.remoteCompact : history.remote;
        expect(target.sort).toEqual([{ field: 'actionDate', type: 'desc' }]);
    });

    it('initializes History sort once from the first mounted layout and preserves its sort entries', async () => {
        const { history, store } = createHistoryStore({
            layout: 'detailed',
            remote: {
                sort: [{ field: 'date', type: 'asc' }]
            },
            remoteCompact: {
                sort: [{ field: 'quality', type: 'desc' }]
            }
        });

        await store.dispatch('initializeHistorySort', {
            layout: 'detailed',
            sort: [
                { field: 'date', type: 'asc' },
                { field: 'providerId', type: 'desc' }
            ]
        });

        expect(history.historySortInitialized).toBe(true);
        expect(history.remote.sort).toEqual([
            { field: 'actionDate', type: 'asc' },
            { field: 'providerId', type: 'desc' }
        ]);
        expect(history.remoteCompact.sort).toEqual([{ field: 'quality', type: 'desc' }]);

        await store.dispatch('initializeHistorySort', {
            layout: 'compact',
            sort: [{ field: 'quality', type: 'asc' }]
        });
        expect(history.remote.sort).toEqual([
            { field: 'actionDate', type: 'asc' },
            { field: 'providerId', type: 'desc' }
        ]);
        expect(history.remoteCompact.sort).toEqual([{ field: 'quality', type: 'desc' }]);
    });

    it('initializes shared pagination from the first Detailed layout', async () => {
        const { history, store } = createHistoryStore({
            remote: {
                perPage: 25
            },
            remoteCompact: {
                perPage: 50
            }
        });

        await store.dispatch('initializeHistoryPagination', {
            layout: 'detailed',
            perPage: 100
        });

        expect(history.historyPaginationInitialized).toBe(true);
        expect(history.remote.perPage).toBe(100);
        expect(history.remoteCompact.perPage).toBe(100);
    });

    it('initializes shared pagination from Compact with a numeric cookie string', async () => {
        const { history, store } = createHistoryStore({
            layout: 'compact',
            remote: {
                perPage: 25
            },
            remoteCompact: {
                perPage: 50
            }
        });

        await store.dispatch('initializeHistoryPagination', {
            layout: 'compact',
            perPage: '250'
        });

        expect(history.remote.perPage).toBe(250);
        expect(history.remoteCompact.perPage).toBe(250);
    });

    it.each([
        ['missing', undefined],
        ['blank', ''],
        ['zero', 0],
        ['negative', -25],
        ['non-numeric', 'invalid']
    ])('uses the active layout perPage for %s initialization values', async (_name, perPage) => {
        const { history, store } = createHistoryStore({
            layout: 'compact',
            remote: {
                perPage: 40
            },
            remoteCompact: {
                perPage: 60
            }
        });

        await store.dispatch('initializeHistoryPagination', {
            layout: 'compact',
            perPage
        });

        expect(history.historyPaginationInitialized).toBe(true);
        expect(history.remote.perPage).toBe(60);
        expect(history.remoteCompact.perPage).toBe(60);
    });

    it('initializes shared pagination only once and preserves carried state', async () => {
        const { history, store } = createHistoryStore();

        await store.dispatch('initializeHistoryPagination', {
            layout: 'detailed',
            perPage: 50
        });
        await store.dispatch('initializeHistoryPagination', {
            layout: 'compact',
            perPage: 100
        });

        expect(history.remote.perPage).toBe(50);
        expect(history.remoteCompact.perPage).toBe(50);
    });
});
