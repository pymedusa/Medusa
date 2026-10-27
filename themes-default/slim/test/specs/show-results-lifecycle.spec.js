import Vuex, { Store } from 'vuex';
import { createLocalVue, mount } from '@vue/test-utils';
import ShowResults from '../../src/components/show-results.vue';

const deferred = () => {
    let resolve;
    const promise = new Promise(done => {
        resolve = done;
    });
    return { promise, resolve };
};
const emptyResults = { providersSearched: 1, totalSearchResults: [] };
const cachedResults = { providersSearched: 1, totalSearchResults: [{ identifier: 'result' }] };
const props = { show: { id: { slug: 'tvdb123' } }, season: 1, episode: 2 };
const Results = { ...ShowResults, render: h => h('div') };

describe('Manual search page request ownership', () => {
    let localVue;
    let store;
    let wrappers;
    let getProviders;
    let getProviderCacheResults;
    let getShowEpisodeHistory;
    let apiPut;

    const flush = async () => {
        for (let i = 0; i < 6; i++) {
            // Resolve the Vuex action and lifecycle promise chains.
            await localVue.nextTick(); // eslint-disable-line no-await-in-loop
        }
    };
    const render = (component = Results, options = {}) => {
        const wrapper = mount(component, { localVue, store, propsData: props,
            mocks: { $cookies: { get: () => null, set: jest.fn() } }, ...options });
        wrappers.push(wrapper);
        return wrapper;
    };
    const cachedHost = () => ({
        data: () => ({ visible: true }),
        render(h) {
            return h('keep-alive', [this.visible ? h(Results, { props }) : h('div')]);
        }
    });

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        wrappers = [];
        getProviders = jest.fn().mockResolvedValue(undefined);
        getProviderCacheResults = jest.fn().mockResolvedValue(cachedResults);
        getShowEpisodeHistory = jest.fn().mockResolvedValue(undefined);
        apiPut = jest.fn().mockResolvedValue({});
        store = new Store({
            state: {
                provider: { providers: [] }, history: { episodeHistory: {} },
                config: { general: {}, layout: {}, search: {} }, queue: { queueitems: [] },
                auth: { client: { api: { put: apiPut } } }
            },
            mutations: {
                setQueue(state, queue) {
                    state.queue.queueitems = queue;
                },
                setProviders(state, providers) {
                    state.provider.providers = providers;
                }
            },
            actions: { getProviders, getProviderCacheResults, getShowEpisodeHistory },
            getters: {
                fuzzyParseDateTime: () => value => value,
                effectiveIgnored: () => () => [], effectiveRequired: () => () => []
            }
        });
    });

    afterEach(() => {
        wrappers.forEach(wrapper => wrapper.destroy());
        jest.useRealTimers();
        jest.restoreAllMocks();
    });

    it('does not start a cache request after destruction while providers are loading', async () => {
        const providers = deferred();
        getProviders.mockReturnValueOnce(providers.promise);
        const wrapper = render();
        wrapper.destroy();
        providers.resolve();
        await flush();
        expect(getProviderCacheResults).not.toHaveBeenCalled();
        expect(apiPut).not.toHaveBeenCalled();
    });

    it('does not launch a search after a destroyed page receives an empty cache', async () => {
        const results = deferred();
        getProviderCacheResults.mockReturnValueOnce(results.promise);
        const wrapper = render();
        await flush();
        wrapper.destroy();
        results.resolve(emptyResults);
        await flush();
        expect(apiPut).not.toHaveBeenCalled();
    });

    it('invalidates cached pages and starts one fresh request when they return', async () => {
        const oldResults = deferred();
        getProviderCacheResults.mockReturnValueOnce(oldResults.promise);
        const wrapper = render(cachedHost());
        await flush();
        expect(getProviders).toHaveBeenCalledTimes(1);
        await wrapper.setData({ visible: false });
        await wrapper.setData({ visible: true });
        await flush();
        oldResults.resolve(emptyResults);
        await flush();
        expect(getProviders).toHaveBeenCalledTimes(2);
        expect(getProviderCacheResults).toHaveBeenCalledTimes(2);
        expect(apiPut).not.toHaveBeenCalled();
    });

    it('does not start requests for a child created under an inactive cached page', async () => {
        const Page = {
            data: () => ({ reveal: false }),
            render(h) {
                return h('div', [this.reveal ? h(Results, { props }) : null]);
            }
        };
        const Host = {
            data: () => ({ visible: true }),
            render(h) {
                return h('keep-alive', [this.visible ? h(Page) : h('div')]);
            }
        };
        const wrapper = render(Host);
        const page = wrapper.findComponent(Page);
        await wrapper.setData({ visible: false });
        await page.setData({ reveal: true });
        await flush();
        expect(getProviders).not.toHaveBeenCalled();
        await wrapper.setData({ visible: true });
        await flush();
        expect(getProviders).toHaveBeenCalledTimes(1);
    });

    it('does not let an old empty initial lookup trigger a search after a refresh', async () => {
        const oldResults = deferred();
        getProviderCacheResults.mockReturnValueOnce(oldResults.promise);
        const wrapper = render();
        await flush();
        await wrapper.vm.getProviderResults();
        oldResults.resolve(emptyResults);
        await flush();
        expect(apiPut).not.toHaveBeenCalled();
    });

    it('rejects a cache completion when the requested episode has changed', async () => {
        const results = deferred();
        getProviderCacheResults.mockReturnValueOnce(results.promise);
        const wrapper = render();
        await flush();
        await wrapper.setProps({ episode: 3 });
        results.resolve(emptyResults);
        await flush();
        expect(apiPut).not.toHaveBeenCalled();
    });

    it('does not duplicate an explicit search when an earlier cache lookup finishes empty', async () => {
        jest.spyOn(console, 'info').mockImplementation(() => {});
        const results = deferred();
        getProviderCacheResults.mockReturnValueOnce(results.promise);
        const wrapper = render();
        await flush();
        await wrapper.vm.forceSearch();
        results.resolve(emptyResults);
        await flush();
        expect(apiPut).toHaveBeenCalledTimes(1);
    });

    it('does not auto-search a cancelled cache request', async () => {
        getProviderCacheResults.mockResolvedValue({ ...emptyResults, cancelled: true });
        render();
        await flush();
        expect(apiPut).not.toHaveBeenCalled();
    });

    it('still starts a search for an active page with an empty cache', async () => {
        jest.spyOn(console, 'info').mockImplementation(() => {});
        getProviderCacheResults.mockResolvedValue(emptyResults);
        render();
        await flush();
        expect(apiPut).toHaveBeenCalledTimes(1);
        expect(apiPut).toHaveBeenCalledWith('search/manual', {
            showSlug: 'tvdb123', options: {}, episodes: ['s01e02']
        });
    });

    it('does not auto-search when live results arrive during an empty cache lookup', async () => {
        const results = deferred();
        getProviderCacheResults.mockReturnValueOnce(results.promise);
        render();
        await flush();
        store.commit('setProviders', [{ id: 'provider', config: { enabled: true }, cache: [{
            identifier: 'live', showSlug: 'tvdb123', season: 1, episodes: [2]
        }] }]);
        results.resolve(emptyResults);
        await flush();
        expect(apiPut).not.toHaveBeenCalled();
    });

    it('clears the pending loading timer when a page is destroyed', async () => {
        jest.useFakeTimers();
        const wrapper = render();
        await flush();
        await wrapper.vm.getProviderResults();
        expect(jest.getTimerCount()).toBe(1);
        wrapper.destroy();
        expect(jest.getTimerCount()).toBe(0);
    });

    it('stops queue-triggered work between the history and cache requests', async () => {
        const history = deferred();
        getShowEpisodeHistory.mockReturnValueOnce(history.promise);
        const wrapper = render();
        await flush();
        getProviderCacheResults.mockClear();
        store.commit('setQueue', [{ name: 'SNATCH-RESULT', show: props.show, success: true,
            segment: [{ season: 1, episode: 2 }] }]);
        await flush();
        expect(getShowEpisodeHistory).toHaveBeenCalledTimes(1);
        wrapper.destroy();
        history.resolve();
        await flush();
        expect(getProviderCacheResults).not.toHaveBeenCalled();
    });

    it('ignores queue updates while cached and inactive', async () => {
        const wrapper = render(cachedHost());
        await flush();
        await wrapper.setData({ visible: false });
        getProviderCacheResults.mockClear();
        store.commit('setQueue', [{ name: 'SNATCH-RESULT', show: props.show, success: true,
            segment: [{ season: 1, episode: 2 }] }]);
        await flush();
        expect(getShowEpisodeHistory).not.toHaveBeenCalled();
        expect(getProviderCacheResults).not.toHaveBeenCalled();
    });

    it('ignores the same episode number from another show in the queue', async () => {
        render();
        await flush();
        store.commit('setQueue', [{ name: 'SNATCH-RESULT', show: { id: { slug: 'tvdb456' } }, success: true,
            segment: [{ season: 1, episode: 2 }] }]);
        await flush();
        expect(getShowEpisodeHistory).not.toHaveBeenCalled();
    });

    it('does not let an old loading timer hide a new manual search', async () => {
        jest.useFakeTimers();
        jest.spyOn(console, 'info').mockImplementation(() => {});
        const wrapper = render();
        await flush();
        await wrapper.vm.getProviderResults();
        await wrapper.vm.forceSearch();
        jest.runOnlyPendingTimers();
        expect(wrapper.vm.loading).toBe(true);
        expect(wrapper.vm.loadingMessage).toBe('Queued search...');
    });

    it('finishes loading after both a manual search and snatch complete', async () => {
        jest.useFakeTimers();
        const wrapper = render();
        await flush();
        await wrapper.setData({ loading: true });
        store.commit('setQueue', ['MANUAL-SEARCH', 'SNATCH-RESULT'].map(name => ({
            name, show: props.show, success: true, segment: [{ season: 1, episode: 2 }]
        })));
        await flush();
        jest.runOnlyPendingTimers();
        expect(wrapper.vm.loading).toBe(false);
        expect(wrapper.vm.loadingMessage).toBe('');
    });

    it('clears a completed search indicator even if its history refresh never settles', async () => {
        jest.useFakeTimers();
        getShowEpisodeHistory.mockReturnValueOnce(new Promise(() => {}));
        const wrapper = render();
        await flush();
        await wrapper.setData({ loading: true });
        store.commit('setQueue', ['MANUAL-SEARCH', 'SNATCH-RESULT'].map(name => ({
            name, show: props.show, success: true, segment: [{ season: 1, episode: 2 }]
        })));
        await flush();
        jest.runOnlyPendingTimers();
        expect(wrapper.vm.loading).toBe(false);
    });
});
