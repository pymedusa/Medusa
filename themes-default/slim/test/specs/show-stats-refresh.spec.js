import Vuex, { Store } from 'vuex';
import { createLocalVue } from '@vue/test-utils';
import statsModule from '../../src/store/modules/stats';

describe('Live show statistics', () => {
    const showSlug = 'tvdb123';
    let store;
    let get;
    let warn;
    let first;
    let second;

    const response = (...stats) => ({ data: { stats, maxDownloadCount: 100000 } });
    const deferred = () => {
        let resolve;
        const promise = new Promise(fulfill => {
            resolve = fulfill;
        });
        return { promise, resolve };
    };

    beforeEach(() => {
        const localVue = createLocalVue();
        localVue.use(Vuex);
        warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
        first = { indexerId: 1, seriesId: 123, epDownloaded: 1, epSnatched: 0, epTotal: 5, seriesSize: 1000 };
        second = { ...first, seriesId: 456, epTotal: 2000 };
        get = jest.fn().mockResolvedValue(response({ ...first, epDownloaded: 2, seriesSize: 2000 }));
        store = new Store({
            state: {
                auth: { client: { api: { get } } },
                shows: {
                    shows: [123, 456].map(id => ({ indexer: 'tvdb', id: { slug: `tvdb${id}`, tvdb: id } }))
                }
            },
            getters: { indexerNameToId: () => () => 1 },
            modules: {
                stats: {
                    ...statsModule,
                    state: { overall: {}, show: { stats: [first, second], maxDownloadCount: 200000 } }
                }
            }
        });
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    it('refreshes only the affected row while preserving other shows and the library maximum', async () => {
        await store.dispatch('refreshShowStats', showSlug);

        expect(get).toHaveBeenCalledTimes(1);
        expect(get).toHaveBeenCalledWith('/stats/show', { params: { showslug: showSlug } });
        expect(store.state.stats.show.stats).toEqual([{ ...first, epDownloaded: 2, seriesSize: 2000 }, second]);
        expect(store.state.stats.show.stats[1]).toBe(second);
        expect(store.state.stats.show.maxDownloadCount).toBe(200000);
    });

    it('adds a missing row without loading the entire library', async () => {
        store.state.stats.show.stats = [second];

        await store.dispatch('refreshShowStats', showSlug);

        expect(store.state.stats.show.stats).toEqual([second, { ...first, epDownloaded: 2, seriesSize: 2000 }]);
        expect(get).toHaveBeenCalledTimes(1);
    });

    it('coalesces a synchronous burst for the same show into one request', async () => {
        await Promise.all(Array.from({ length: 12 }, () => store.dispatch('refreshShowStats', showSlug)));

        expect(get).toHaveBeenCalledTimes(1);
    });

    it('reads again after a change arrives during the request', async () => {
        const initial = deferred();
        get.mockReturnValueOnce(initial.promise)
            .mockResolvedValueOnce(response({ ...first, epDownloaded: 3 }));
        const refresh = store.dispatch('refreshShowStats', showSlug);
        await Promise.resolve();
        const updates = Array.from({ length: 3 }, () => store.dispatch('refreshShowStats', showSlug));
        expect(get).toHaveBeenCalledTimes(1);

        initial.resolve(response({ ...first, epDownloaded: 2 }));
        await Promise.all([refresh, ...updates]);

        expect(get).toHaveBeenCalledTimes(2);
        expect(store.state.stats.show.stats[0].epDownloaded).toBe(3);
    });

    it('coalesces different shows separately', async () => {
        get.mockImplementation((url, { params }) => Promise.resolve(response(
            { ...(params.showslug === showSlug ? first : second), epDownloaded: 4 }
        )));

        await Promise.all([showSlug, 'tvdb456', showSlug, 'tvdb456'].map(slug => store.dispatch('refreshShowStats', slug)));

        expect(get).toHaveBeenCalledTimes(2);
        expect(store.state.stats.show.stats.map(row => row.epDownloaded)).toEqual([4, 4]);
    });

    it('finishes an older full request before applying a newer targeted refresh', async () => {
        const full = deferred();
        get.mockReturnValueOnce(full.promise);
        const loading = store.dispatch('getStats', 'show');
        await Promise.resolve();
        const updating = store.dispatch('refreshShowStats', showSlug);
        expect(get).toHaveBeenCalledTimes(1);

        full.resolve(response(first, second));
        await Promise.all([loading, updating]);

        expect(get).toHaveBeenNthCalledWith(1, '/stats/show');
        expect(get).toHaveBeenNthCalledWith(2, '/stats/show', { params: { showslug: showSlug } });
        expect(store.state.stats.show.stats[0].epDownloaded).toBe(2);
    });

    it('serializes a full refresh requested during a targeted refresh', async () => {
        const targeted = deferred();
        get.mockReturnValueOnce(targeted.promise)
            .mockResolvedValueOnce(response({ ...first, epDownloaded: 3 }, second));
        const updating = store.dispatch('refreshShowStats', showSlug);
        await Promise.resolve();
        const loading = store.dispatch('getStats', 'show');
        expect(get).toHaveBeenCalledTimes(1);

        targeted.resolve(response({ ...first, epDownloaded: 2 }));
        await Promise.all([updating, loading]);

        expect(get).toHaveBeenNthCalledWith(2, '/stats/show');
        expect(store.state.stats.show.stats[0].epDownloaded).toBe(3);
    });

    it('lets a queued full refresh cover pending targeted updates', async () => {
        get.mockResolvedValue(response({ ...first, epDownloaded: 2 }, second));

        await Promise.all([
            store.dispatch('refreshShowStats', showSlug),
            store.dispatch('getStats', 'show'),
            store.dispatch('refreshShowStats', 'tvdb456')
        ]);

        expect(get).toHaveBeenCalledTimes(1);
        expect(get).toHaveBeenCalledWith('/stats/show');
        expect(store.state.stats.show.stats[0].epDownloaded).toBe(2);
    });

    it('ignores a show which is no longer tracked', async () => {
        await store.dispatch('refreshShowStats', 'tvdb999');

        expect(get).not.toHaveBeenCalled();
        expect(store.state.stats.show.stats).toEqual([first, second]);
    });

    it('still refreshes pending shows if the full request covering them fails', async () => {
        get.mockRejectedValueOnce(new Error('Offline'));

        await Promise.all([
            store.dispatch('refreshShowStats', showSlug),
            store.dispatch('getStats', 'show')
        ]);

        expect(get).toHaveBeenCalledTimes(2);
        expect(get).toHaveBeenNthCalledWith(2, '/stats/show', { params: { showslug: showSlug } });
        expect(store.state.stats.show.stats[0].epDownloaded).toBe(2);
    });

    it('ignores a response when the show was deleted while loading', async () => {
        const pending = deferred();
        get.mockReturnValueOnce(pending.promise);
        const refresh = store.dispatch('refreshShowStats', showSlug);
        await Promise.resolve();
        store.state.shows.shows.splice(0, 1);

        pending.resolve(response({ ...first, epDownloaded: 2 }));
        await refresh;

        expect(store.state.stats.show.stats).toEqual([first, second]);
    });

    it('removes the old row when the tracked show has no episode statistics left', async () => {
        get.mockResolvedValue(response());

        await store.dispatch('refreshShowStats', showSlug);

        expect(store.state.stats.show.stats).toEqual([second]);
        expect(store.state.stats.show.maxDownloadCount).toBe(200000);
    });

    it('preserves existing rows on failure and allows a later update to retry', async () => {
        get.mockRejectedValueOnce(new Error('Offline'));

        await store.dispatch('refreshShowStats', showSlug);

        expect(store.state.stats.show.stats).toEqual([first, second]);
        expect(warn).toHaveBeenCalledTimes(1);

        await store.dispatch('refreshShowStats', showSlug);

        expect(get).toHaveBeenCalledTimes(2);
        expect(store.state.stats.show.stats[0].epDownloaded).toBe(2);
    });

    it('keeps an invalidation queued while a failed request is settling', async () => {
        const pending = deferred();
        get.mockImplementationOnce(() => pending.promise.then(() => {
            throw new Error('Offline');
        }));
        const firstRefresh = store.dispatch('refreshShowStats', showSlug);
        await Promise.resolve();
        const retry = store.dispatch('refreshShowStats', showSlug);

        pending.resolve();
        await Promise.all([firstRefresh, retry]);

        expect(get).toHaveBeenCalledTimes(2);
        expect(store.state.stats.show.stats[0].epDownloaded).toBe(2);
    });

    it('keeps overall statistics on their existing request path', async () => {
        const overall = { episodes: { downloaded: 5, total: 10 } };
        get.mockResolvedValue({ data: overall });

        await store.dispatch('getStats');

        expect(get).toHaveBeenCalledWith('/stats/');
        expect(store.state.stats.overall).toEqual(overall);
    });
});
