import Vuex, { Store } from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import { VueGoodTable } from 'vue-good-table';
import App from '../../src/components/app.vue';
import SnatchSelection from '../../src/components/snatch-selection.vue';
import ShowResults from '../../src/components/show-results.vue';
import providerModule from '../../src/store/modules/provider';

const deferred = () => {
    let resolve;
    const promise = new Promise(done => {
        resolve = done;
    });
    return { promise, resolve };
};
const resultRow = (showSlug, identifier, episodes = [1]) => ({
    identifier, showSlug, season: 1, episodes, release: identifier, size: 1,
    provider: { id: 'provider', name: 'Provider' }
});

// Use the real result lifecycle and table while keeping unrelated UI controls out of the fixture.
const Results = {
    ...ShowResults,
    render(h) {
        return h(VueGoodTable, {
            props: {
                columns: [{ label: 'Release', field: 'release' }], rows: this.combinedResults,
                paginationOptions: { enabled: true, perPage: this.paginationPerPage }
            }
        });
    }
};

describe('Active search result retention', () => {
    let localVue;
    let store;
    let router;
    let wrapper;
    let get;
    let put;
    let cookies;

    const originalResizeObserver = global.ResizeObserver;
    beforeAll(() => {
        global.ResizeObserver = class {
            observe() {}

            unobserve() {}

            disconnect() {}
        };
    });
    afterAll(() => {
        global.ResizeObserver = originalResizeObserver;
    });

    const flush = async () => {
        for (let i = 0; i < 10; i++) {
            await localVue.nextTick(); // eslint-disable-line no-await-in-loop
        }
    };
    const path = slug => `/search?showslug=${slug}&season=1&episode=1`;
    const cache = () => store.state.provider.providers.flatMap(provider => provider.cache || []);

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);
        cookies = {};
        get = jest.fn((url, { params } = {}) => {
            if (url === '/providers') {
                return Promise.resolve({ data: [{ id: 'provider', name: 'Provider', config: { enabled: true } }] });
            }
            return Promise.resolve({ data: [
                resultRow(params.showslug, 'single'), resultRow(params.showslug, 'multi', [1, 2])
            ] });
        });
        put = jest.fn().mockResolvedValue({});
        store = new Store({
            state: {
                auth: { isAuthenticated: true, client: { api: { get, put } } },
                shows: { loading: {}, current: 'tvdb123', shows: ['tvdb123', 'tvdb456'].map(slug => ({ id: { slug }, title: slug })) },
                config: { general: {}, layout: {}, search: { filters: { undesired: [] } } },
                history: { episodeHistory: {} }, queue: { queueitems: [] }
            },
            modules: { provider: { ...providerModule, state: { providers: [], activeCache: null } } },
            mutations: { currentShow(state, slug) {
                state.shows.current = slug;
            } },
            getters: {
                getCurrentShow: state => state.shows.shows.find(show => show.id.slug === state.shows.current),
                effectiveIgnored: () => () => [], effectiveRequired: () => () => [],
                fuzzyParseDateTime: () => value => value, getShowHistoryBySlug: () => () => [], getEpisode: () => () => null
            },
            actions: { getShow: jest.fn() }
        });
        router = new VueRouter({ routes: [
            { path: '/home', name: 'home', component: { render: h => h('div') } },
            { path: '/search', name: 'snatchSelection', meta: { nocache: true }, component: SnatchSelection }
        ] });
    });

    afterEach(() => {
        if (wrapper) {
            wrapper.destroy();
            wrapper = null;
        }
    });

    const open = async slug => {
        await router.push(path(slug));
        wrapper = mount(App, {
            localVue, store, router,
            mocks: { $cookies: {
                get: key => cookies[key] || null,
                set: (key, value) => {
                    cookies[key] = value;
                }
            } },
            stubs: {
                'load-progress-bar': true, 'app-header': true, 'sub-menu': true, 'vue-snotify': true,
                alerts: true, 'app-footer': true, 'scroll-buttons': true, 'show-history': true, backstretch: true,
                'show-results': Results,
                'show-header': {
                    props: ['slug'],
                    mounted() {
                        this.$store.commit('currentShow', this.slug);
                    },
                    render: h => h('div')
                }
            }
        });
        await flush();
    };

    it('destroys departed pages and their tables, then restores multi-episode rows on return', async () => {
        await open('tvdb123');
        const firstPage = wrapper.findComponent(SnatchSelection).vm;
        const firstTable = wrapper.findComponent(VueGoodTable).vm;
        expect(cache().map(row => row.identifier)).toEqual(['single', 'multi']);
        wrapper.findComponent(Results).vm.updatePaginationPerPage(25);

        await router.push(path('tvdb456'));
        await flush();
        expect(firstPage._isDestroyed).toBe(true);
        expect(firstTable._isDestroyed).toBe(true);
        expect(cache().every(row => row.showSlug === 'tvdb456')).toBe(true);

        await router.push('/home');
        await flush();
        expect(cache()).toEqual([]);
        await store.dispatch('addManualSearchResult', resultRow('tvdb456', 'late'));
        expect(cache()).toEqual([]);

        await router.push(path('tvdb123'));
        await flush();
        expect(wrapper.findComponent(SnatchSelection).vm).not.toBe(firstPage);
        expect(cache().map(row => row.identifier)).toEqual(['single', 'multi']);
        expect(wrapper.findComponent(VueGoodTable).vm.rows).toHaveLength(2);
        expect(wrapper.findComponent(VueGoodTable).vm.currentPerPage).toBe(25);
        expect(put).not.toHaveBeenCalled();
    });

    it('does not retain a response that finishes after leaving the results page', async () => {
        const pending = deferred();
        get.mockImplementation(url => url === '/providers' ? Promise.resolve({
            data: [{ id: 'provider', name: 'Provider', config: { enabled: true } }]
        }) : pending.promise);
        await open('tvdb123');
        await router.push('/home');
        await flush();
        pending.resolve({ data: [resultRow('tvdb123', 'late')] });
        await flush();
        expect(cache()).toEqual([]);
        expect(put).not.toHaveBeenCalled();
    });
});
