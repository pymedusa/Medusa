import Vuex, { Store } from 'vuex';
import { createLocalVue, mount } from '@vue/test-utils';
import { VueGoodTable } from 'vue-good-table';
import ShowResults from '../../src/components/show-results.vue';
import providerModule from '../../src/store/modules/provider';

const showSlug = 'tvdb123';
const flush = async localVue => {
    await localVue.nextTick();
    await localVue.nextTick();
    await localVue.nextTick();
};
const row = (identifier, release = `Match ${identifier}`) => ({
    identifier: String(identifier), release, showSlug, season: 1, episodes: [1],
    provider: { id: 'provider', name: 'Provider', imageName: 'missing.png' },
    quality: 0, size: 0
});

const mountResults = (perPage, options = {}) => {
    const localVue = createLocalVue();
    localVue.use(Vuex);
    const cookies = options.cookies || { 'showResults-pagination-perPage': JSON.stringify(perPage) };
    const cache = options.cache || [...Array.from({ length: 26 }, (_, i) => row(i)), row('hidden', 'Other release')];
    const refresh = jest.fn().mockResolvedValue({ providersSearched: 0, totalSearchResults: [] });
    const store = new Store({
        state: {
            provider: { providers: [{ id: 'provider', config: { enabled: true }, cache }] },
            config: { general: {}, layout: {}, search: { filters: { undesired: [] } } },
            history: { episodeHistory: {} }, queue: { queueitems: [] }, auth: { client: {} }
        },
        mutations: {
            claimProviderCache: jest.fn(),
            releaseProviderCache: jest.fn(),
            appendResult(state, result) {
                state.provider.providers[0].cache.push(result);
            },
            replaceResults(state, results) {
                state.provider.providers[0].cache = results;
            }
        },
        actions: {
            getProviders: jest.fn(),
            getProviderCacheResults: refresh
        },
        getters: {
            effectiveIgnored: () => () => [],
            effectiveRequired: () => () => [],
            fuzzyParseDateTime: () => value => value
        }
    });
    const wrapper = mount(ShowResults, {
        localVue, store,
        propsData: { show: { id: { slug: showSlug }, config: { anime: false } }, season: 1, episode: 1 },
        data() {
            return { columns: [
                { label: 'Release', field: 'release', filterOptions: { enabled: true } },
                { label: 'Provider', field: 'provider.name' }
            ] };
        },
        methods: { getSortBy: () => ({ field: 'release', type: 'asc' }) },
        mocks: { $cookies: {
            get: jest.fn(key => cookies[key] || null),
            set: jest.fn((key, value) => {
                cookies[key] = value;
            })
        } },
        stubs: { QualityPill: true, ManageWhitelist: true }
    });
    return { localVue, store, wrapper, table: wrapper.findComponent(VueGoodTable).vm, cookies, refresh };
};

describe('Manual search result pagination', () => {
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

    it('keeps a changed native page size and filtered page during a pending cache refresh', async () => {
        jest.useFakeTimers();
        const { localVue, store, wrapper, table, refresh } = mountResults(50);
        let resolveRefresh;
        let pending;
        try {
            await flush(localVue);
            await wrapper.find('select[name="perPageSelect"]').setValue('25');
            await flush(localVue);
            table.filterRows({ release: 'Match' });
            await flush(localVue);
            table.changePage(2);
            await flush(localVue);
            expect(table.currentPage).toBe(2);

            refresh.mockImplementationOnce(() => new Promise(resolve => {
                resolveRefresh = resolve;
            }));
            pending = wrapper.vm.getProviderResults();
            await flush(localVue);
            expect(table.currentPage).toBe(2);
            expect(table.currentPerPage).toBe(25);
            expect(table.columnFilters.release).toBe('Match');

            store.commit('appendResult', row('later'));
            resolveRefresh({ providersSearched: 0, totalSearchResults: [] });
            await pending;
            await flush(localVue);
            expect(table.currentPage).toBe(2);
            expect(table.totalRowCount).toBe(27);
            const preferenceKey = 'showResults-pagination-perPage';
            expect(wrapper.vm.$cookies.get.mock.calls.filter(([key]) => key === preferenceKey)).toHaveLength(1);
            expect(wrapper.vm.$cookies.set.mock.calls.filter(([key]) => key === preferenceKey))
                .toEqual([[preferenceKey, '25']]);
        } finally {
            if (resolveRefresh) {
                resolveRefresh({ providersSearched: 0, totalSearchResults: [] });
                await pending;
            }
            jest.runOnlyPendingTimers();
            jest.useRealTimers();
            wrapper.destroy();
        }
    });

    it('distinguishes native fixed 25 from All and restores All after filtered growth and remount', async () => {
        const cache = Array.from({ length: 25 }, (_, i) => row(i));
        const { localVue, store, wrapper, table, cookies } = mountResults(25, { cache });
        await flush(localVue);
        store.commit('appendResult', row('fixed-extra'));
        await flush(localVue);
        expect(table.currentPerPage).toBe(25);
        expect(table.paginated[0].children).toHaveLength(25);
        store.commit('replaceResults', cache.slice(0, 25));
        await flush(localVue);

        const selector = wrapper.find('select[name="perPageSelect"]');
        const allIndex = [...selector.element.options].findIndex(option => option.text === 'All');
        selector.element.selectedIndex = allIndex;
        await selector.trigger('change');
        await flush(localVue);
        expect(JSON.parse(cookies['showResults-pagination-perPage'])).toBe(-1);
        expect(table.currentPerPage).toBe(-1);

        store.commit('appendResult', row('all-extra'));
        store.commit('appendResult', row('hidden', 'Other release'));
        await flush(localVue);
        table.filterRows({ release: 'Match' });
        await flush(localVue);
        expect(table.paginated[0].children).toHaveLength(26);
        expect(selector.element.selectedOptions[0].text).toBe('All');
        expect(wrapper.find('.footer__navigation__page-info').text()).toBe('1 - 26 of 26');
        table.filterRows({ release: 'Match 0' });
        await flush(localVue);
        expect(table.paginated[0].children).toHaveLength(1);
        table.filterRows({ release: 'Match' });
        await flush(localVue);
        expect(table.paginated[0].children).toHaveLength(26);
        wrapper.destroy();

        const revisited = mountResults(50, { cookies, cache: store.state.provider.providers[0].cache });
        await flush(revisited.localVue);
        expect(revisited.table.currentPerPage).toBe(-1);
        expect(revisited.wrapper.find('select[name="perPageSelect"]').element.selectedOptions[0].text).toBe('All');
        expect(revisited.table.paginated[0].children).toHaveLength(27);
        revisited.store.commit('replaceResults', []);
        await flush(revisited.localVue);
        expect(revisited.wrapper.find('.footer__navigation__page-info').text()).toBe('0 - 0 of 0');
        revisited.wrapper.destroy();
    });

    it('keeps navigation on page one as All grows past a library default page size', async () => {
        const cache = Array.from({ length: 11 }, (_, i) => row(i));
        const { localVue, store, wrapper, table } = mountResults(-1, { cache });
        await flush(localVue);
        store.commit('replaceResults', cache.slice(0, 10));
        await flush(localVue);
        store.commit('appendResult', row('eleventh'));
        await flush(localVue);

        const footer = table.$refs.paginationBottom;
        expect(table.currentPerPage).toBe(-1);
        expect(footer.currentPerPage).toBe(-1);
        expect(footer.nextIsPossible).toBe(false);
        const next = wrapper.findAll('.footer__navigation__page-btn').wrappers.find(button => button.text() === 'Next');
        await next.trigger('click');
        await flush(localVue);
        expect(table.currentPage).toBe(1);
        expect(footer.currentPage).toBe(1);
        expect(table.paginated[0].children).toHaveLength(11);
        wrapper.destroy();
    });

    it('keeps a later filtered page while more matching provider results arrive', async () => {
        const { localVue, store, wrapper, table } = mountResults(25);
        await flush(localVue);
        table.filterRows({ release: 'Match' });
        await flush(localVue);
        table.changePage(2);
        await flush(localVue);
        expect(table.currentPage).toBe(2);

        store.commit('appendResult', row('later'));
        await flush(localVue);

        expect(table.columnFilters.release).toBe('Match');
        expect(table.totalRowCount).toBe(27);
        expect(table.currentPerPage).toBe(25);
        expect(table.currentPage).toBe(2);
        table.filterRows({ release: 'Match 0' });
        await flush(localVue);
        expect(table.currentPage).toBe(1);
        wrapper.destroy();
    });

    it('moves to a valid page if a provider update removes the old filtered page', async () => {
        const { localVue, store, wrapper, table } = mountResults(25);
        await flush(localVue);
        table.filterRows({ release: 'Match' });
        await flush(localVue);
        table.changePage(2);
        await flush(localVue);

        store.commit('replaceResults', [row('remaining')]);
        await flush(localVue);

        expect(table.currentPage).toBe(1);
        expect(table.totalRowCount).toBe(1);
        wrapper.destroy();
    });

    it('lets an intervening filter change override the retained page', async () => {
        const { localVue, store, wrapper, table } = mountResults(25);
        await flush(localVue);
        table.filterRows({ release: 'Match' });
        await flush(localVue);
        table.changePage(2);
        await flush(localVue);

        store.commit('appendResult', row('later'));
        localVue.nextTick(() => table.filterRows({ release: 'Mat' }));
        await flush(localVue);

        expect(table.columnFilters.release).toBe('Mat');
        expect(table.totalRowCount).toBe(27);
        expect(table.currentPage).toBe(1);
        wrapper.destroy();
    });

    it('keeps All mode and its filtered count when background results arrive', async () => {
        const { localVue, store, wrapper, table } = mountResults(-1);
        await flush(localVue);
        expect(table.currentPerPage).toBe(-1);
        table.filterRows({ release: 'Match' });
        await flush(localVue);
        store.commit('appendResult', row('later'));
        await flush(localVue);

        expect(table.currentPerPage).toBe(-1);
        expect(table.currentPage).toBe(1);
        expect(table.totalRowCount).toBe(27);
        expect(table.paginated[0].children).toHaveLength(27);
        wrapper.destroy();
    });

    it('retains every provider API page in the cache used by the table', async () => {
        const firstPage = Array.from({ length: 1000 }, (_, i) => row(i));
        const lastPage = [row('last')];
        const state = { providers: [{ id: 'provider', config: { enabled: true }, cache: [] }] };
        const get = jest.fn().mockResolvedValueOnce({ data: firstPage }).mockResolvedValueOnce({ data: lastPage });
        const commit = (type, payload) => providerModule.mutations[type](state, payload);
        const owner = {};
        commit('claimProviderCache', { owner, showSlug, season: 1, episode: 1 });

        const result = await providerModule.actions.getProviderCacheResults({
            state, commit, rootState: { auth: { client: { api: { get } } } }
        }, { owner, showSlug, season: 1, episode: 1 });

        expect(get).toHaveBeenCalledTimes(2);
        expect(result.totalSearchResults).toHaveLength(1001);
        expect(state.providers[0].cache.map(item => item.identifier)).toEqual(
            [...firstPage, ...lastPage].map(item => item.identifier)
        );
    });
});
