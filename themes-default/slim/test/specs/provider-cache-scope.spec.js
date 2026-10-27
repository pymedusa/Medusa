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

describe('Active provider result cache', () => {
    let store;
    let get;
    let owner;

    const cache = () => store.state.provider.providers[0].cache;
    const claim = (scope = {}, nextOwner = owner) => store.commit('claimProviderCache', { ...request, ...scope, owner: nextOwner });
    const search = (scope = {}) => store.dispatch('getProviderCacheResults', { ...request, owner, ...scope });

    beforeEach(() => {
        const localVue = createLocalVue();
        localVue.use(Vuex);
        owner = {};
        get = jest.fn().mockResolvedValue({ data: [] });
        store = new Store({
            state: { auth: { client: { api: { get } } } },
            modules: {
                provider: {
                    ...providerModule,
                    state: { providers: [{ id: 'provider', name: 'Provider', config: { enabled: true }, cache: [] }] }
                }
            }
        });
        claim();
    });

    it.each([
        ['show', { showSlug: 'tvdb456' }, { showSlug: 'tvdb456' }],
        ['season', { season: 2 }, { season: 2 }],
        ['episode', { episode: 2 }, { episodes: [2] }]
    ])('evicts the previous %s search and ignores its late response', async (_label, scope, rowScope) => {
        const first = deferred();
        store.state.provider.providers[0].cache = [resultRow('old')];
        get.mockReturnValueOnce(first.promise).mockResolvedValueOnce({ data: [resultRow('second', rowScope)] });
        const firstRequest = search();
        const nextOwner = {};
        claim(scope, nextOwner);
        expect(cache()).toEqual([]);
        await search({ ...scope, owner: nextOwner });
        first.resolve({ data: [resultRow('first')] });

        expect((await firstRequest).cancelled).toBe(true);
        expect(cache().map(row => row.identifier)).toEqual(['second']);
    });

    it('does not let a departed owner release the new owner\'s cache', async () => {
        claim({}, {});
        await store.dispatch('addManualSearchResult', resultRow('live'));
        store.commit('releaseProviderCache', owner);

        expect(cache().map(row => row.identifier)).toEqual(['live']);
    });

    it('clears results on release and ignores websocket results without an owner', async () => {
        await store.dispatch('addManualSearchResult', resultRow('live'));
        store.commit('releaseProviderCache', owner);
        await store.dispatch('addManualSearchResult', resultRow('late'));
        await store.dispatch('addManualSearchResult', resultRow('unknown', { provider: { id: 'unknown' } }));

        expect(cache()).toEqual([]);
        expect(store.state.provider.providers).toHaveLength(1);
    });

    it('rejects requests with no matching owner even when their scope matches', async () => {
        const response = await search({ owner: undefined });

        expect(response.cancelled).toBe(true);
        expect(get).not.toHaveBeenCalled();
    });

    it('keeps a repeated claim by the same owner and scope without cancelling its request', async () => {
        const pending = deferred();
        get.mockReturnValue(pending.promise);
        const loading = search();
        await store.dispatch('addManualSearchResult', resultRow('live'));
        const currentCache = cache();
        claim();
        expect(cache()).toBe(currentCache);
        pending.resolve({ data: [] });

        expect((await loading).cancelled).not.toBe(true);
        expect(cache().map(row => row.identifier)).toEqual(['live']);
    });

    it('invalidates the old request when the same owner changes scope', async () => {
        const pending = deferred();
        get.mockReturnValue(pending.promise);
        const loading = search();
        claim({ episode: 2 });
        await store.dispatch('addManualSearchResult', resultRow('new-scope', { episodes: [2] }));
        pending.resolve({ data: [resultRow('old-scope')] });

        expect((await loading).cancelled).toBe(true);
        expect(cache().map(row => row.identifier)).toEqual(['new-scope']);
    });

    it('discards superseded responses for the same active search', async () => {
        const first = deferred();
        get.mockReturnValueOnce(first.promise).mockResolvedValueOnce({ data: [resultRow('latest')] });
        const firstRequest = search();
        await search();
        first.resolve({ data: [resultRow('obsolete')] });

        expect((await firstRequest).cancelled).toBe(true);
        expect(cache().map(row => row.identifier)).toEqual(['latest']);
    });

    it('stops released searches before committing or fetching another page or provider', async () => {
        const pending = deferred();
        store.state.provider.providers.push({ id: 'other', config: { enabled: true }, cache: [] });
        get.mockReturnValueOnce(pending.promise).mockResolvedValue({ data: [] });
        const loading = search();
        store.commit('releaseProviderCache', owner);
        pending.resolve({ data: Array.from({ length: 1000 }, (_, id) => resultRow(String(id))) });

        expect((await loading).cancelled).toBe(true);
        expect(get).toHaveBeenCalledTimes(1);
        expect(cache()).toEqual([]);
    });

    it('continues to honor the request lifecycle callback', async () => {
        const response = await search({ isCurrent: () => false });

        expect(response.cancelled).toBe(true);
        expect(get).not.toHaveBeenCalled();
    });

    it('retains all API pages and newer matching websocket rows without retaining other searches', async () => {
        const pageTwo = deferred();
        const pageTwoStarted = deferred();
        store.state.provider.providers[0].cache = [resultRow('0')];
        get.mockResolvedValueOnce({ data: Array.from({ length: 1000 }, (_, id) => resultRow(String(id))) })
            .mockImplementationOnce(() => {
                pageTwoStarted.resolve();
                return pageTwo.promise;
            });
        const loading = search();
        await pageTwoStarted.promise;
        await store.dispatch('addManualSearchResult', resultRow('0', { size: 9000 }));
        await store.dispatch('addManualSearchResult', resultRow('live', { episodes: [1, 2] }));
        await store.dispatch('addManualSearchResult', resultRow('other-show', { showSlug: 'tvdb456' }));
        await store.dispatch('addManualSearchResult', resultRow('other-season', { season: 2 }));
        await store.dispatch('addManualSearchResult', resultRow('other-episode', { episodes: [11] }));
        pageTwo.resolve({ data: [resultRow('last', { episodes: [1, 2] })] });
        const response = await loading;

        expect(response.totalSearchResults).toHaveLength(1001);
        expect(cache().length).toBe(1002);
        expect(cache().find(row => row.identifier === '0').size).toBe(9000);
        expect(cache().filter(row => row.episodes.length > 1).map(row => row.identifier).sort()).toEqual(['last', 'live']);
    });

    it('reloads single and multi-episode results on revisit without retaining the previous visit', async () => {
        await store.dispatch('addManualSearchResult', resultRow('old-live'));
        store.commit('releaseProviderCache', owner);
        const nextOwner = {};
        claim({}, nextOwner);
        const results = [resultRow('single'), resultRow('multi', { episodes: [1, 2] })];
        get.mockResolvedValue({ data: results });

        await search({ owner: nextOwner });

        expect(cache()).toEqual(results);
    });

    it('matches season zero and episode zero without treating either as unspecified', async () => {
        claim({ season: 0, episode: 0 });
        await store.dispatch('addManualSearchResult', resultRow('zero', { season: 0, episodes: [0, 1] }));
        await store.dispatch('addManualSearchResult', resultRow('wrong', { season: 0, episodes: [1] }));
        get.mockResolvedValue({ data: [resultRow('zero', { season: 0, episodes: [0, 1] })] });

        await search({ season: 0, episode: 0 });

        expect(get).toHaveBeenCalledWith('/providers/provider/results', { params: { limit: 1000, showslug: request.showSlug, season: 0, episode: 0, page: 1 } });
        expect(cache().map(row => row.identifier)).toEqual(['zero']);
    });

    it('keeps all release types for an active season search', async () => {
        claim({ season: 0, episode: undefined });
        const results = [
            resultRow('single', { season: 0 }),
            resultRow('multi', { season: 0, episodes: [1, 2] }),
            resultRow('pack', { season: 0, episodes: [] })
        ];
        get.mockResolvedValue({ data: results });

        await search({ season: 0, episode: undefined });

        expect(cache()).toEqual(results);
    });

    it('clears expired active results on 404 but preserves them on a failed request', async () => {
        store.state.provider.providers[0].cache = [resultRow('existing')];
        get.mockRejectedValueOnce(new Error('Network unavailable')).mockRejectedValueOnce({ response: { status: 404 } });
        await search();
        expect(cache()).toEqual([resultRow('existing')]);
        await search();
        expect(cache()).toEqual([]);
    });

    it('preserves live results before their provider summary loads but cannot restore them after release', async () => {
        const pending = deferred();
        store.state.provider.providers = [];
        await store.dispatch('addManualSearchResult', resultRow('live'));
        const currentCache = cache();
        const providers = [{ id: 'provider', name: 'Renamed', config: { enabled: true } }];
        get.mockResolvedValueOnce({ data: providers }).mockReturnValueOnce(pending.promise);
        await store.dispatch('getProviders');
        expect(cache()).toBe(currentCache);
        const summary = store.dispatch('getProviders');
        store.commit('releaseProviderCache', owner);
        pending.resolve({ data: providers });
        await summary;

        expect(cache()).toEqual([]);
        expect(store.state.provider.providers[0].name).toBe('Renamed');
    });
});
