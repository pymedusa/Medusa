import Vuex, { Store } from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount, shallowMount } from '@vue/test-utils';
import SnatchSelection from '../../src/components/snatch-selection.vue';
import ShowResults from '../../src/components/show-results.vue';
import providerModule from '../../src/store/modules/provider';
import { ADD_PROVIDER_CACHE } from '../../src/store/mutation-types';

const makeShow = slug => ({ id: { slug }, title: slug });

const deferred = () => {
    let resolve;
    const promise = new Promise(done => {
        resolve = done;
    });
    return { promise, resolve };
};

const flush = async localVue => {
    await localVue.nextTick();
    await localVue.nextTick();
};

const makeRouter = () => {
    const router = new VueRouter({
        routes: [{ path: '/snatch', name: 'snatch', component: { render: h => h('div') } }]
    });
    router.push('/snatch?season=1&episode=1');
    return router;
};

describe('snatch results loading scope', () => {
    let localVue;

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);
    });

    it('waits for the requested show and mounts results once with that show', async () => {
        const target = makeShow('tvdb-target');
        const loaded = deferred();
        const getShow = jest.fn(() => loaded.promise);
        const showResultsMounted = jest.fn();
        const header = {
            props: ['slug'],
            mounted() {
                // ShowHeader synchronously selects its requested show during mounted.
                this.$store.commit('currentShow', this.slug);
            },
            render: h => h('div')
        };
        const results = {
            name: 'show-results',
            props: ['show', 'season', 'episode'],
            mounted() {
                showResultsMounted(this.show.id.slug);
            },
            render: h => h('div')
        };
        const store = new Store({
            state: {
                shows: { shows: [], currentShow: { showSlug: null } },
                defaults: { show: { id: { slug: null } } },
                config: { general: {}, search: {} },
                history: {}
            },
            mutations: {
                currentShow(state, slug) {
                    state.shows.currentShow.showSlug = slug;
                },
                addShow(state, show) {
                    state.shows.shows.push(show);
                }
            },
            getters: {
                getCurrentShow: (state, getters, rootState) => state.shows.shows.find(
                    show => show.id.slug === state.shows.currentShow.showSlug
                ) || rootState.defaults.show,
                effectiveIgnored: () => () => [],
                effectiveRequired: () => () => [],
                getShowHistoryBySlug: () => () => [],
                getEpisode: () => () => null
            },
            actions: {
                getShow({ commit }, request) {
                    return getShow(request).then(() => commit('addShow', target));
                }
            }
        });
        const wrapper = mount(SnatchSelection, {
            localVue,
            store,
            router: makeRouter(),
            propsData: { slug: target.id.slug },
            stubs: {
                'show-header': header,
                'show-history': true,
                'show-results': results,
                backstretch: true,
                'vue-snotify': true
            }
        });

        await flush(localVue);
        expect(getShow).toHaveBeenCalledWith({ showSlug: target.id.slug, detailed: false });
        expect(showResultsMounted).not.toHaveBeenCalled();

        loaded.resolve();
        await flush(localVue);
        expect(showResultsMounted).toHaveBeenCalledTimes(1);
        expect(showResultsMounted).toHaveBeenCalledWith(target.id.slug);
        wrapper.destroy();
    });

    it('never mounts results for a previously selected show while switching to the requested show', async () => {
        const previous = makeShow('tvdb-previous');
        const target = makeShow('tvdb-target');
        const loaded = deferred();
        const getShow = jest.fn(() => loaded.promise);
        const mountedFor = [];
        const header = {
            props: ['slug'],
            mounted() {
                // Match the real header's synchronous setCurrentShow lifecycle.
                this.$store.commit('currentShow', this.slug);
            },
            render: h => h('div')
        };
        const results = {
            name: 'show-results',
            props: ['show'],
            mounted() {
                mountedFor.push(this.show.id.slug);
            },
            render: h => h('div')
        };
        const store = new Store({
            state: {
                shows: { shows: [previous], currentShow: { showSlug: previous.id.slug } },
                defaults: { show: { id: { slug: null } } },
                config: { general: {}, search: {} },
                history: {}
            },
            mutations: {
                currentShow(state, slug) {
                    state.shows.currentShow.showSlug = slug;
                },
                addShow(state, show) {
                    state.shows.shows.push(show);
                }
            },
            getters: {
                getCurrentShow: (state, getters, rootState) => state.shows.shows.find(
                    show => show.id.slug === state.shows.currentShow.showSlug
                ) || rootState.defaults.show,
                effectiveIgnored: () => () => [],
                effectiveRequired: () => () => [],
                getShowHistoryBySlug: () => () => [],
                getEpisode: () => () => null
            },
            actions: {
                getShow({ commit }, request) {
                    return getShow(request).then(() => commit('addShow', target));
                }
            }
        });
        const wrapper = mount(SnatchSelection, {
            localVue,
            store,
            router: makeRouter(),
            propsData: { slug: target.id.slug },
            stubs: {
                'show-header': header,
                'show-history': true,
                'show-results': results,
                backstretch: true,
                'vue-snotify': true
            }
        });

        await flush(localVue);
        expect(getShow).toHaveBeenCalledWith({ showSlug: target.id.slug, detailed: false });
        expect(mountedFor).toEqual([]);
        loaded.resolve();
        await flush(localVue);
        expect(mountedFor).toEqual([target.id.slug]);
        wrapper.destroy();
    });

    it('restores the cached show when returning to its route', async () => {
        const first = makeShow('tvdb-first');
        const second = makeShow('tvdb-second');
        const activeResults = [];
        const headerInstances = [];
        const getShow = jest.fn();
        const recordActiveResult = function() {
            activeResults.push(this.show.id.slug);
        };
        const results = {
            name: 'show-results',
            props: ['show'],
            mounted: recordActiveResult,
            activated: recordActiveResult,
            render: h => h('div')
        };
        const header = {
            props: ['slug'],
            mounted() {
                // The real ShowHeader selects on mount. It does not select again on activation.
                this.$store.commit('currentShow', this.slug);
                headerInstances.push({ slug: this.slug, parent: this.$parent });
            },
            render: h => h('div')
        };
        const store = new Store({
            state: {
                shows: { shows: [first, second], currentShow: { showSlug: first.id.slug } },
                defaults: { show: { id: { slug: null } } },
                config: { general: {}, search: {} },
                history: {}
            },
            mutations: {
                currentShow(state, slug) {
                    state.shows.currentShow.showSlug = slug;
                }
            },
            getters: {
                getCurrentShow: (state, getters, rootState) => state.shows.shows.find(
                    show => show.id.slug === state.shows.currentShow.showSlug
                ) || rootState.defaults.show,
                effectiveIgnored: () => () => [],
                effectiveRequired: () => () => [],
                getShowHistoryBySlug: () => () => [],
                getEpisode: () => () => null
            },
            actions: { getShow }
        });
        const router = new VueRouter({
            routes: [{
                path: '/home/snatchSelection',
                name: 'snatchSelection',
                component: SnatchSelection,
                meta: { nocache: true }
            }]
        });
        const host = {
            render(h) {
                return h('keep-alive', [h('router-view', { key: this.$route.fullPath })]);
            }
        };
        router.push('/home/snatchSelection?showslug=tvdb-first&season=1&episode=1');
        const wrapper = mount(host, {
            localVue,
            store,
            router,
            stubs: {
                'show-header': header,
                'show-history': true,
                'show-results': results,
                backstretch: true,
                'vue-snotify': true
            }
        });

        await flush(localVue);
        expect(store.state.shows.currentShow.showSlug).toBe(first.id.slug);
        const firstPage = wrapper.findComponent(SnatchSelection).vm;
        await router.push('/home/snatchSelection?showslug=tvdb-second&season=1&episode=1');
        await flush(localVue);
        expect(store.state.shows.currentShow.showSlug).toBe(second.id.slug);
        await router.push('/home/snatchSelection?showslug=tvdb-first&season=1&episode=1');
        await flush(localVue);

        expect(store.state.shows.currentShow.showSlug).toBe(first.id.slug);
        expect(activeResults).toContain(second.id.slug);
        expect(activeResults[activeResults.length - 1]).toBe(first.id.slug);
        expect(headerInstances.map(({ slug }) => slug)).toEqual([first.id.slug, second.id.slug]);
        expect(wrapper.findComponent(SnatchSelection).vm).toBe(firstPage);
        expect(getShow).not.toHaveBeenCalled();
        wrapper.destroy();
    });

    it('returns an empty result without network or cache changes when show scope is missing', async () => {
        const apiGet = jest.fn();
        const commit = jest.fn();
        const existingCache = [{ identifier: 'cached-result' }];
        const state = {
            providers: [{ id: 'provider', name: 'Provider', config: { enabled: true }, cache: existingCache }]
        };
        const result = await providerModule.actions.getProviderCacheResults({
            rootState: { auth: { client: { api: { get: apiGet } } } },
            commit,
            state
        }, { showSlug: null, season: 1, episode: 2 });

        expect(result).toEqual({ providersSearched: 0, totalSearchResults: [] });
        expect(apiGet).not.toHaveBeenCalled();
        expect(commit).not.toHaveBeenCalled();
        expect(state.providers[0].cache).toBe(existingCache);
    });

    it.each([
        ['episode', { showSlug: 'tvdb-target', season: 2, episode: 3 }, { showslug: 'tvdb-target', season: 2, episode: 3, limit: 1000, page: 1 }],
        ['season', { showSlug: 'tvdb-target', season: 2, episode: undefined }, { showslug: 'tvdb-target', season: 2, limit: 1000, page: 1 }]
    ])('preserves valid %s cache searches and results', async (_label, request, expectedParams) => {
        const row = { identifier: 'result', showSlug: request.showSlug, season: request.season };
        const apiGet = jest.fn().mockResolvedValue({ data: [row] });
        const commit = jest.fn();
        const state = { providers: [{ id: 'provider', name: 'Provider', config: { enabled: true } }] };

        const result = await providerModule.actions.getProviderCacheResults({
            rootState: { auth: { client: { api: { get: apiGet } } } },
            commit,
            state
        }, request);

        expect(apiGet).toHaveBeenCalledWith('/providers/provider/results', { params: expectedParams });
        expect(result).toEqual({ providersSearched: 1, totalSearchResults: [row] });
        expect(commit).toHaveBeenCalledWith(ADD_PROVIDER_CACHE, expect.objectContaining({ providerId: 'provider', cache: [row] }));
    });

    it('does not automatically force search when the valid cache lookup searched zero providers', async () => {
        const apiPut = jest.fn();
        const localVueWithCookies = createLocalVue();
        localVueWithCookies.use(Vuex);
        const getProviderCacheResults = jest.fn().mockResolvedValue({ providersSearched: 0, totalSearchResults: [] });
        const getProviders = jest.fn();
        const store = new Store({
            state: { provider: { providers: [] }, history: { episodeHistory: {} }, config: { general: {}, search: {} }, queue: { queueitems: [] }, auth: { client: { api: { put: apiPut } } } },
            actions: {
                getProviders,
                getProviderCacheResults
            },
            getters: {
                fuzzyParseDateTime: () => () => '',
                effectiveIgnored: () => () => [],
                effectiveRequired: () => () => []
            }
        });
        const wrapper = shallowMount(ShowResults, {
            localVue: localVueWithCookies,
            store,
            propsData: { show: makeShow('tvdb-target'), season: 2, episode: 3 },
            mocks: { $cookies: { get: () => null } }
        });

        await flush(localVueWithCookies);
        expect(getProviderCacheResults).toHaveBeenCalledWith(expect.anything(), expect.objectContaining({
            showSlug: 'tvdb-target', season: 2, episode: 3
        }));
        expect(apiPut).not.toHaveBeenCalled();
        wrapper.destroy();
    });
});
