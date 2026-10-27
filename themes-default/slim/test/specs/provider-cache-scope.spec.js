import Vuex, { Store } from 'vuex';
import { createLocalVue } from '@vue/test-utils';
import providerModule from '../../src/store/modules/provider';

const deferred = () => {
    let resolve;
    const promise = new Promise(done => {
        resolve = done;
    });
    return { promise, resolve };
};
const resultRow = (identifier, scope = {}) => ({
    identifier, showSlug: 'tvdb123', season: 1, episodes: [1], size: 1000,
    provider: { id: 'provider', name: 'Provider' }, ...scope
});
const request = { showSlug: 'tvdb123', season: 1, episode: 1 };

describe('Provider cache search scopes', () => {
    let store;
    let get;

    beforeEach(() => {
        const localVue = createLocalVue();
        localVue.use(Vuex);
        get = jest.fn();
        store = new Store({
            state: { auth: { client: { api: { get } } } },
            modules: {
                provider: {
                    ...providerModule,
                    state: { providers: [{ id: 'provider', name: 'Provider', config: { enabled: true }, cache: [] }] }
                }
            }
        });
    });

    const cache = () => store.state.provider.providers[0].cache;

    it.each([
        ['show', { showSlug: 'tvdb456' }, { showSlug: 'tvdb456' }],
        ['season', { season: 2 }, { season: 2 }],
        ['episode', { episode: 2 }, { episodes: [2] }]
    ])('keeps both %s searches when an earlier request finishes last', async (_label, scope, rowScope) => {
        const first = deferred();
        get.mockReturnValueOnce(first.promise).mockResolvedValueOnce({ data: [resultRow('second', rowScope)] });
        const firstRequest = store.dispatch('getProviderCacheResults', request);
        await store.dispatch('getProviderCacheResults', { ...request, ...scope });
        first.resolve({ data: [resultRow('first')] });
        await firstRequest;

        expect(cache().map(row => row.identifier).sort()).toEqual(['first', 'second']);
    });

    it('discards a superseded response for the same search even after the newer request finishes', async () => {
        const first = deferred();
        get.mockReturnValueOnce(first.promise).mockResolvedValueOnce({ data: [resultRow('latest')] });
        const firstRequest = store.dispatch('getProviderCacheResults', request);
        await store.dispatch('getProviderCacheResults', request);
        first.resolve({ data: [resultRow('obsolete')] });

        expect((await firstRequest).cancelled).toBe(true);
        expect(cache().map(row => row.identifier)).toEqual(['latest']);
    });

    it('does not start a cache search whose owner is already inactive', async () => {
        const response = await store.dispatch('getProviderCacheResults', { ...request, isCurrent: () => false });

        expect(response).toMatchObject({ cancelled: true, providersSearched: 0, totalSearchResults: [] });
        expect(get).not.toHaveBeenCalled();
    });

    it('stops cancelled searches before committing or requesting another page or provider', async () => {
        const pending = deferred();
        let active = true;
        store.state.provider.providers.push({ id: 'other', config: { enabled: true }, cache: [] });
        get.mockReturnValueOnce(pending.promise).mockResolvedValue({ data: [] });
        const search = store.dispatch('getProviderCacheResults', { ...request, isCurrent: () => active });
        active = false;
        pending.resolve({ data: Array.from({ length: 1000 }, (_, id) => resultRow(String(id))) });

        expect((await search).cancelled).toBe(true);
        expect(get).toHaveBeenCalledTimes(1);
        expect(cache()).toEqual([]);
    });

    it('keeps every API page and websocket additions or updates received during the fetch', async () => {
        const pageTwo = deferred();
        const pageTwoStarted = deferred();
        const otherShow = resultRow('other-show', { showSlug: 'tvdb456' });
        store.state.provider.providers[0].cache = [resultRow('0'), otherShow];
        get.mockResolvedValueOnce({ data: Array.from({ length: 1000 }, (_, id) => resultRow(String(id))) })
            .mockImplementationOnce(() => {
                pageTwoStarted.resolve();
                return pageTwo.promise;
            });
        const search = store.dispatch('getProviderCacheResults', request);
        await pageTwoStarted.promise;
        await store.dispatch('addManualSearchResult', resultRow('0', { size: 9000 }));
        await store.dispatch('addManualSearchResult', resultRow('live', { size: 5000 }));
        pageTwo.resolve({ data: [resultRow('last')] });
        const response = await search;

        expect(get).toHaveBeenCalledTimes(2);
        expect(response.totalSearchResults).toHaveLength(1001);
        expect(cache().length).toBe(1003);
        expect(cache().find(row => row.identifier === '0').size).toBe(9000);
        expect(cache()).toContainEqual(resultRow('live', { size: 5000 }));
        expect(cache()).toContainEqual(otherShow);
    });

    it('replaces only matching single-episode rows and retains multi-episode and season-pack results', async () => {
        const retained = [resultRow('multi', { episodes: [1, 2] }), resultRow('pack', { episodes: [] }), resultRow('second', { episodes: [2] })];
        store.state.provider.providers[0].cache = [resultRow('obsolete'), ...retained];
        get.mockResolvedValue({ data: [resultRow('fresh')] });

        await store.dispatch('getProviderCacheResults', request);

        expect(cache().map(row => row.identifier).sort()).toEqual(['fresh', 'multi', 'pack', 'second']);
    });

    it('treats season searches as all results in that season, including specials season zero', async () => {
        store.state.provider.providers[0].cache = [
            resultRow('single', { season: 0 }),
            resultRow('multi', { season: 0, episodes: [1, 2] }),
            resultRow('pack', { season: 0, episodes: [] }),
            resultRow('other-season')
        ];
        get.mockResolvedValue({ data: [] });

        await store.dispatch('getProviderCacheResults', { showSlug: request.showSlug, season: 0 });

        expect(cache().map(row => row.identifier)).toEqual(['other-season']);
    });

    it('clears only the requested scope when the backend reports an empty cache with 404', async () => {
        store.state.provider.providers[0].cache = [resultRow('obsolete'), resultRow('other', { episodes: [2] })];
        get.mockRejectedValue({ response: { status: 404 } });

        await store.dispatch('getProviderCacheResults', request);

        expect(cache().map(row => row.identifier)).toEqual(['other']);
    });

    it('keeps cached results when a provider request fails', async () => {
        store.state.provider.providers[0].cache = [resultRow('existing')];
        get.mockRejectedValue(new Error('Network unavailable'));

        await store.dispatch('getProviderCacheResults', request);

        expect(cache()).toEqual([resultRow('existing')]);
    });

    it('preserves result caches while updating provider configuration and metadata', async () => {
        store.state.provider.providers[0].cache = [resultRow('cached')];
        const previousCache = cache();
        get.mockResolvedValue({ data: [{ id: 'provider', name: 'Renamed provider', config: { enabled: false } }] });

        await store.dispatch('getProviders');

        expect(cache()).toBe(previousCache);
        expect(store.state.provider.providers[0]).toMatchObject({ name: 'Renamed provider', config: { enabled: false } });
    });

    it('does not overwrite a completed episode refresh with an overlapping older season response', async () => {
        const seasonResponse = deferred();
        const pack = resultRow('pack', { episodes: [1, 2] });
        store.state.provider.providers[0].cache = [resultRow('episode'), pack];
        get.mockReturnValueOnce(seasonResponse.promise)
            .mockResolvedValueOnce({ data: [resultRow('episode', { size: 9000 })] });
        const seasonRequest = store.dispatch('getProviderCacheResults', { showSlug: request.showSlug, season: 1 });
        await store.dispatch('getProviderCacheResults', request);
        seasonResponse.resolve({ data: [resultRow('episode'), pack] });
        await seasonRequest;

        expect(cache().find(row => row.identifier === 'episode').size).toBe(9000);
        expect(cache()).toContainEqual(pack);
    });

    it('retains live results arriving before their provider summary loads', async () => {
        store.state.provider.providers = [];
        await store.dispatch('addManualSearchResult', resultRow('live'));
        get.mockResolvedValue({ data: [{ id: 'provider', name: 'Provider', config: { enabled: true } }] });

        await store.dispatch('getProviders');

        expect(cache()).toEqual([resultRow('live')]);
        expect(store.state.provider.providers).toHaveLength(1);
    });

    it('does not resurrect results removed by a newer overlapping episode refresh', async () => {
        const seasonResponse = deferred();
        store.state.provider.providers[0].cache = [resultRow('expired')];
        get.mockReturnValueOnce(seasonResponse.promise).mockResolvedValueOnce({ data: [] });
        const seasonRequest = store.dispatch('getProviderCacheResults', { showSlug: request.showSlug, season: 1 });
        await store.dispatch('getProviderCacheResults', request);
        seasonResponse.resolve({ data: [resultRow('expired')] });
        await seasonRequest;

        expect(cache()).toEqual([]);
    });
});
