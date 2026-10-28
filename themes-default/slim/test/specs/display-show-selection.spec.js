import Vuex, { Store } from 'vuex';
import vueCookies from 'vue-cookies';
import cloneDeep from 'lodash/cloneDeep';
import { createLocalVue, mount } from '@vue/test-utils';
import DisplayShow from '../../src/components/display-show.vue';
import showsModule from '../../src/store/modules/shows';
import { ADD_SHOWS } from '../../src/store/mutation-types';

const showSlug = 'tvdb-selection';

const episode = (season, number) => ({
    episode: number,
    season,
    slug: `s${String(season).padStart(2, '0')}e${String(number).padStart(2, '0')}`,
    title: `Episode ${season}-${number}`,
    status: 'Skipped',
    quality: 0,
    watched: false,
    absoluteNumber: number,
    scene: { season, episode: number },
    sceneAbsolute: number,
    description: '',
    content: { hasNfo: false, hasTbn: false },
    file: { location: '', name: '', size: 0 },
    subtitles: []
});

const makeShow = () => ({
    id: { slug: showSlug, tvdb: 123 },
    title: 'Selection Test',
    config: { searchTemplates: [], qualities: [], aliases: [], anime: false, subtitlesEnabled: false },
    xemNumbering: [],
    seasonCount: [{ season: 0, episodeCount: 1 }, { season: 1, episodeCount: 2 }],
    seasons: [
        { season: 0, children: [episode(0, 1)] },
        { season: 1, children: [episode(1, 1), episode(1, 2)] }
    ]
});

const flush = async localVue => {
    await localVue.nextTick();
    await localVue.nextTick();
};

describe('DisplayShow episode selection', () => {
    let localVue;
    let store;
    let wrapper;
    let previousResizeObserver;

    beforeEach(() => {
        previousResizeObserver = global.ResizeObserver;
        global.ResizeObserver = class {
            observe() {}

            disconnect() {}
        };
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(vueCookies);
        const show = makeShow();
        store = new Store({
            state: {
                config: {
                    layout: { themeName: 'light', show: { specials: true, pagination: { enable: false } } },
                    subtitles: { enabled: false },
                    system: { configLoaded: true },
                    search: { general: { failedDownloads: { enabled: false } } }
                },
                auth: { client: { api: { put: jest.fn(), patch: jest.fn() } } },
                defaults: { show: { id: { slug: null }, seasons: [], config: { qualities: [], aliases: [] } } }
            },
            mutations: {
                setSpecials(state, enabled) {
                    state.config.layout.show.specials = enabled;
                }
            },
            modules: {
                shows: {
                    ...showsModule,
                    state: { shows: [show], currentShow: { showSlug }, staleEpisodeShows: {} }
                }
            },
            getters: {
                getOverviewStatus: () => status => status,
                fuzzyParseDateTime: () => () => ''
            },
            actions: {
                getShow: jest.fn().mockResolvedValue({ fileCacheRevision: 1 }),
                getEpisodes: jest.fn().mockResolvedValue(undefined),
                setCurrentShow: jest.fn(),
                setRecentShow: jest.fn(),
                refreshShowFiles: jest.fn().mockResolvedValue(undefined)
            }
        });
        wrapper = null;
    });

    afterEach(() => {
        if (wrapper) {
            wrapper.destroy();
        }
        if (previousResizeObserver) {
            global.ResizeObserver = previousResizeObserver;
        } else {
            delete global.ResizeObserver;
        }
        localVue.prototype.$cookies.remove('displayShow-pagination-perPage');
        jest.restoreAllMocks();
    });

    const mountShow = (getCookie = null) => {
        const methods = { ...DisplayShow.methods, loadShow: jest.fn(), reflowLayout: jest.fn() };
        if (getCookie) {
            methods.getCookie = getCookie;
        }
        const component = {
            ...DisplayShow,
            methods
        };
        wrapper = mount(component, {
            localVue,
            store,
            propsData: { slug: showSlug },
            stubs: [
                'app-link',
                'backstretch',
                'plot-info',
                'quality-pill',
                'search',
                'scene-number-input',
                'scene-number-anime-input',
                'show-header',
                'subtitle-search',
                'vue-snotify',
                'modal'
            ]
        });
        return wrapper;
    };

    it('keeps an actual table checkbox selected after a summary-only ADD_SHOWS merge', async () => {
        const page = mountShow();
        await flush(localVue);
        const tables = page.findAll('.vgt-wrap');
        expect(tables.length).toBe(2);
        const normalCheckbox = tables.at(0).find('tbody .vgt-checkbox-col input[type="checkbox"]');
        const specialCheckbox = tables.at(1).find('tbody .vgt-checkbox-col input[type="checkbox"]');
        expect(normalCheckbox.exists()).toBe(true);
        expect(specialCheckbox.exists()).toBe(true);
        await normalCheckbox.trigger('click');
        await specialCheckbox.trigger('click');
        await flush(localVue);
        expect(page.vm.selectedEpisodes.map(row => row.slug)).toEqual(['s00e01', 's01e02']);

        store.commit(ADD_SHOWS, [{
            id: { slug: showSlug, tvdb: 123 },
            title: 'Selection Test Updated',
            config: { searchTemplates: [], qualities: [], aliases: [], anime: false, subtitlesEnabled: false }
        }]);
        await flush(localVue);

        const updatedTables = page.findAll('.vgt-wrap');
        expect(updatedTables.at(0).find('tbody .vgt-checkbox-col input[type="checkbox"]').element.checked).toBe(true);
        expect(updatedTables.at(1).find('tbody .vgt-checkbox-col input[type="checkbox"]').element.checked).toBe(true);
        const currentEpisodes = store.getters.getShowById(showSlug).seasons.flatMap(season => season.children);
        expect(page.vm.selectedEpisodes).toEqual([currentEpisodes[0], currentEpisodes[2]]);
        expect(page.vm.selectedEpisodes[0]).toBe(currentEpisodes[0]);
        expect(page.vm.selectedEpisodes[1]).toBe(currentEpisodes[2]);
        expect(currentEpisodes.every(row => !Object.prototype.hasOwnProperty.call(row, 'vgtSelected'))).toBe(true);
        expect(page.vm.seasonTableRows.flatMap(season => season.children).every(row => !row.vgtSelected)).toBe(true);
        expect(page.vm.specialTableRows.flatMap(season => season.children).every(row => !row.vgtSelected)).toBe(true);

        const refreshedShow = store.getters.getShowById(showSlug);
        store.commit(ADD_SHOWS, [{ ...refreshedShow, seasons: cloneDeep(refreshedShow.seasons) }]);
        await flush(localVue);
        const freshEpisodes = store.getters.getShowById(showSlug).seasons.flatMap(season => season.children);
        expect(page.vm.selectedEpisodes[0]).toBe(freshEpisodes[0]);
        expect(page.vm.selectedEpisodes[1]).toBe(freshEpisodes[2]);
        expect(page.findAll('.vgt-wrap').at(0).find('tbody .vgt-checkbox-col input[type="checkbox"]').element.checked).toBe(true);
        expect(page.findAll('.vgt-wrap').at(1).find('tbody .vgt-checkbox-col input[type="checkbox"]').element.checked).toBe(true);
    });

    it.each([null, false])('shows page-size controls when pagination loads after mounting with %s', async initialPagination => {
        store.state.config.layout.show.pagination.enable = initialPagination;
        const page = mountShow();
        await flush(localVue);

        const seasonTable = page.findComponent({ ref: 'table-seasons' });
        const initialPerPage = seasonTable.find('select[name="perPageSelect"]');
        expect(initialPerPage.exists()).toBe(false);
        expect(seasonTable.vm.$refs.paginationBottom).toBeUndefined();

        store.state.config.layout.show.pagination.enable = true;
        await flush(localVue);

        expect(page.findComponent({ ref: 'table-seasons' }).vm).toBe(seasonTable.vm);
        const perPage = seasonTable.find('select[name="perPageSelect"]');
        expect(perPage.exists()).toBe(true);
        expect(seasonTable.findAll('.vgt-wrap__footer select[name="perPageSelect"]')).toHaveLength(1);
        expect(seasonTable.find('.vgt-wrap__actions-footer').exists()).toBe(false);
        expect(seasonTable.vm.$refs.paginationBottom).toBeDefined();
        expect(seasonTable.find('.vgt-wrap__footer label').attributes('for')).toBe(perPage.attributes('id'));
        expect(perPage.isVisible()).toBe(true);
        expect([...perPage.element.options].map(option => option.text)).toEqual(['25', '50', '100', '250', '500', 'All']);

        const normalCheckbox = seasonTable.find('tbody .vgt-checkbox-col input[type="checkbox"]');
        await normalCheckbox.trigger('click');
        await flush(localVue);
        expect(page.vm.selectedEpisodes.map(row => row.slug)).toEqual(['s01e02']);

        const allOption = [...perPage.element.options].find(option => option.text === 'All');
        perPage.element.value = allOption.value;
        await perPage.trigger('change');
        await flush(localVue);
        expect(page.vm.paginationPerPage).toBe(-1);
        expect(localVue.prototype.$cookies.get('displayShow-pagination-perPage')).toBe('-1');
        expect(seasonTable.find('tbody .vgt-checkbox-col input[type="checkbox"]').element.checked).toBe(true);

        store.state.config.layout.show.pagination.enable = false;
        await flush(localVue);
        expect(seasonTable.find('select[name="perPageSelect"]').exists()).toBe(false);
        store.state.config.layout.show.pagination.enable = true;
        await flush(localVue);
        expect(page.findComponent({ ref: 'table-seasons' }).vm).toBe(seasonTable.vm);
        expect(seasonTable.find('.vgt-wrap__footer select[name="perPageSelect"]').isVisible()).toBe(true);
        expect(seasonTable.find('tbody .vgt-checkbox-col input[type="checkbox"]').element.checked).toBe(true);
        expect(page.vm.selectedEpisodes.map(row => row.slug)).toEqual(['s01e02']);
    });

    it('keeps page-two and All-mode selection stable through checkbox and summary updates', async () => {
        const show = store.getters.getShowById(showSlug);
        show.seasons[1].children.push(episode(1, 3));
        show.seasons[1].children.push({ ...episode(1, 4), title: 'Excluded item' });
        show.seasonCount[1].episodeCount = 4;
        store.state.config.layout.show.pagination.enable = true;
        const page = mountShow();
        page.vm.paginationPerPage = 1;
        await flush(localVue);

        const seasonTable = page.findComponent({ ref: 'table-seasons' });
        const search = seasonTable.find('.vgt-global-search input');
        await search.setValue('Episode 1-');
        await search.trigger('keyup.enter');
        seasonTable.vm.filterRows({ title: 'Episode 1-' });
        await flush(localVue);
        await seasonTable.findAll('.footer__navigation__page-btn').at(1).trigger('click');
        await flush(localVue);
        expect(seasonTable.vm.columnFilters.title).toBe('Episode 1-');
        expect(seasonTable.vm.searchTerm).toBe('Episode 1-');
        expect(seasonTable.vm.totalRowCount).toBe(3);
        expect(seasonTable.vm.currentPage).toBe(2);
        const pageTwoCheckbox = seasonTable.find('tbody .vgt-checkbox-col input[type="checkbox"]');
        await pageTwoCheckbox.trigger('click');
        await flush(localVue);
        expect(page.vm.selectedEpisodes.map(row => row.slug)).toEqual(['s01e03']);

        store.commit(ADD_SHOWS, [{
            id: { slug: showSlug, tvdb: 123 },
            title: 'Selection Test Refreshed',
            config: { searchTemplates: [], qualities: [], aliases: [], anime: false, subtitlesEnabled: false }
        }]);
        await flush(localVue);
        expect(seasonTable.vm.columnFilters.title).toBe('Episode 1-');
        expect(seasonTable.vm.searchTerm).toBe('Episode 1-');
        expect(seasonTable.vm.currentPage).toBe(2);
        expect(seasonTable.find('tbody .vgt-checkbox-col input[type="checkbox"]').element.checked).toBe(true);

        const perPage = seasonTable.find('.footer__row-count__select');
        const allOption = [...perPage.element.options].find(option => option.text === 'All');
        expect(allOption).toBeDefined();
        perPage.element.value = allOption.value;
        await perPage.trigger('change');
        await flush(localVue);
        expect(page.vm.paginationPerPage).toBe(-1);
        expect(seasonTable.vm.currentPerPage).toBe(-1);
        expect(seasonTable.findAll('tbody .vgt-checkbox-col input[type="checkbox"]').length).toBeGreaterThan(1);
        expect(seasonTable.findAll('tbody tr').wrappers.filter(row => {
            const checkbox = row.find('input[type="checkbox"]');
            return checkbox.exists() && checkbox.element.checked;
        })).toHaveLength(1);

        store.commit(ADD_SHOWS, [{
            id: { slug: showSlug, tvdb: 123 },
            title: 'Selection Test All Refreshed',
            config: { searchTemplates: [], qualities: [], aliases: [], anime: false, subtitlesEnabled: false }
        }]);
        await flush(localVue);
        expect(seasonTable.findAll('tbody tr').wrappers.filter(row => {
            const checkbox = row.find('input[type="checkbox"]');
            return checkbox.exists() && checkbox.element.checked;
        })).toHaveLength(1);
        expect(page.vm.selectedEpisodes.map(row => row.slug)).toEqual(['s01e03']);

        seasonTable.vm.filterRows({ title: 'Excluded item' });
        await flush(localVue);
        expect(page.vm.selectedEpisodes).toEqual([]);
        seasonTable.vm.filterRows({ title: 'Episode 1-' });
        await flush(localVue);
        expect(page.vm.selectedEpisodes).toEqual([]);
    });

    it('restores persisted All mode and keeps selected rows after a summary refresh', async () => {
        store.state.config.layout.show.pagination.enable = true;
        localVue.prototype.$cookies.set('displayShow-pagination-perPage', '-1');
        const page = mountShow(key => {
            const cookie = localVue.prototype.$cookies.get(`displayShow-${key}`);
            try {
                return JSON.parse(cookie);
            } catch {
                return cookie;
            }
        });
        await flush(localVue);

        expect(page.vm.paginationPerPage).toBe(-1);
        const seasonTable = page.findComponent({ ref: 'table-seasons' });
        expect(seasonTable.find('select[name="perPageSelect"]').element.selectedOptions[0].text).toBe('All');
        expect(seasonTable.vm.currentPerPage).toBe(-1);
        expect(seasonTable.findAll('tbody .vgt-checkbox-col input[type="checkbox"]').length).toBe(2);
        await seasonTable.find('tbody .vgt-checkbox-col input[type="checkbox"]').trigger('click');
        await flush(localVue);
        const selectedSlug = page.vm.selectedEpisodes[0].slug;

        store.commit(ADD_SHOWS, [{
            id: { slug: showSlug, tvdb: 123 },
            title: 'Selection Test All Refreshed',
            config: { searchTemplates: [], qualities: [], aliases: [], anime: false, subtitlesEnabled: false }
        }]);
        await flush(localVue);

        expect(page.vm.paginationPerPage).toBe(-1);
        expect(seasonTable.vm.currentPerPage).toBe(-1);
        expect(page.vm.selectedEpisodes.map(row => row.slug)).toEqual([selectedSlug]);
        expect(seasonTable.findAll('tbody .vgt-checkbox-col input[type="checkbox"]')
            .wrappers.some(checkbox => checkbox.element.checked)).toBe(true);
    });

    it.each([1, 2])('loads uncached seasons once when native All is chosen on page %i', async currentPage => {
        store.state.config.layout.show.pagination.enable = true;
        const show = store.getters.getShowById(showSlug);
        show.seasons[1].children = Array.from({ length: 26 }, (_, index) => episode(1, index + 1));
        show.seasonCount[1].episodeCount = 26;
        show.seasonCount.push({ season: 2, episodeCount: 1 });
        let resolveEpisodes;
        const getEpisodes = jest.fn().mockImplementation(({ season }) => new Promise(resolve => {
            resolveEpisodes = () => {
                show.seasons.push({ season, children: [episode(season, 1)] });
                resolve();
            };
        }));
        store._actions.getEpisodes = [getEpisodes];
        const page = mountShow();
        await flush(localVue);
        const table = page.findComponent({ ref: 'table-seasons' });
        if (currentPage === 2) {
            page.vm.paginationPerPage = 25;
            await flush(localVue);
            table.vm.changePage(2);
            await flush(localVue);
        }
        expect(table.vm.currentPage).toBe(currentPage);
        expect(getEpisodes).not.toHaveBeenCalled();
        const setCookie = jest.spyOn(page.vm, 'setCookie');
        const loadEpisodes = jest.spyOn(page.vm, 'loadEpisodes');
        const selector = table.find('select[name="perPageSelect"]');
        const allIndex = [...selector.element.options].findIndex(option => option.text === 'All');
        selector.element.selectedIndex = allIndex;
        await selector.trigger('change');
        await flush(localVue);
        await flush(localVue);

        expect(page.vm.paginationPerPage).toBe(-1);
        expect(setCookie).toHaveBeenCalledTimes(1);
        expect(setCookie).toHaveBeenCalledWith('pagination-perPage', -1);
        expect(loadEpisodes).toHaveBeenCalledTimes(1);
        expect(getEpisodes).toHaveBeenCalledTimes(1);
        expect(getEpisodes).toHaveBeenCalledWith({ showSlug, season: 2 });
        expect(table.vm.totalRowCount).toBe(26);
        expect(show.seasons.some(season => season.season === 2)).toBe(false);
        resolveEpisodes();
        await flush(localVue);
        await flush(localVue);
        expect(getEpisodes).toHaveBeenCalledTimes(1);
        expect(table.vm.totalRowCount).toBe(27);
        expect(table.vm.paginated.reduce((count, group) => count + group.children.length, 0)).toBe(27);
        expect(table.find('select[name="perPageSelect"]').element.selectedOptions[0].text).toBe('All');

        show.seasons.find(season => season.season === 2).children.push(episode(2, 2));
        show.seasonCount.find(season => season.season === 2).episodeCount = 2;
        await flush(localVue);
        table.vm.filterRows({ title: 'Episode 2-' });
        await flush(localVue);
        expect(table.vm.paginated.reduce((count, group) => count + group.children.length, 0)).toBe(2);
        table.vm.filterRows({ title: '' });
        await flush(localVue);
        expect(table.vm.paginated.reduce((count, group) => count + group.children.length, 0)).toBe(28);
        expect(table.find('.footer__navigation__page-info').text()).toBe('1 - 28 of 28');
        page.destroy();

        const revisited = mountShow();
        await flush(localVue);
        const restoredTable = revisited.findComponent({ ref: 'table-seasons' });
        expect(revisited.vm.paginationPerPage).toBe(-1);
        expect(restoredTable.vm.currentPerPage).toBe(-1);
        expect(restoredTable.find('select[name="perPageSelect"]').element.selectedOptions[0].text).toBe('All');
        expect(restoredTable.vm.paginated.reduce((count, group) => count + group.children.length, 0)).toBe(28);
    });

    it('clears selections after deselect, removal, specials hide, or owner change', async () => {
        const page = mountShow();
        await flush(localVue);
        const tables = page.findAll('.vgt-wrap');
        await tables.at(0).find('tbody .vgt-checkbox-col input[type="checkbox"]').trigger('click');
        await tables.at(1).find('tbody .vgt-checkbox-col input[type="checkbox"]').trigger('click');
        await flush(localVue);
        expect(page.vm.selectedEpisodes).toHaveLength(2);

        await tables.at(0).find('tbody .vgt-checkbox-col input[type="checkbox"]').trigger('click');
        await tables.at(1).find('tbody .vgt-checkbox-col input[type="checkbox"]').trigger('click');
        await flush(localVue);
        store.commit(ADD_SHOWS, [{
            id: { slug: showSlug, tvdb: 123 },
            title: 'Selection Test After Clear',
            config: { searchTemplates: [], qualities: [], aliases: [], anime: false, subtitlesEnabled: false }
        }]);
        await flush(localVue);
        expect(page.vm.selectedEpisodes).toEqual([]);

        const currentTables = page.findAll('.vgt-wrap');
        await currentTables.at(1).find('tbody .vgt-checkbox-col input[type="checkbox"]').trigger('click');
        await flush(localVue);
        store.commit('setSpecials', false);
        await flush(localVue);
        expect(page.vm.selectedEpisodes).toEqual([]);
        store.commit('setSpecials', true);
        await flush(localVue);
        expect(page.vm.selectedEpisodes).toEqual([]);

        const selectedRow = page.find('.vgt-wrap tbody .vgt-checkbox-col input[type="checkbox"]');
        expect(selectedRow.exists()).toBe(true);
        await selectedRow.trigger('click');
        await flush(localVue);
        expect(page.vm.selectedEpisodes).toHaveLength(1);
        const removedSlug = page.vm.selectedEpisodes[0].slug;
        const latestShow = store.getters.getShowById(showSlug);
        store.commit(ADD_SHOWS, [{
            ...latestShow,
            seasons: latestShow.seasons.map(season => season.season === 1 ? {
                ...season,
                children: season.children.filter(row => row.slug !== removedSlug)
            } : season),
            seasonCount: latestShow.seasonCount.map(season => season.season === 1 ? { ...season, episodeCount: 1 } : season)
        }]);
        await flush(localVue);
        expect(page.vm.selectedEpisodes).toEqual([]);

        const otherShow = { ...makeShow(), id: { slug: 'tvdb-other', tvdb: 456 } };
        store.commit(ADD_SHOWS, [store.getters.getShowById(showSlug), otherShow]);
        expect(store.getters.getShowById('tvdb-other')).toBeDefined();
        const sharedSlug = store.getters.getShowById(showSlug).seasons[1].children[0].slug;
        page.vm.updateSelectedEpisodes('seasons', [{ slug: sharedSlug }]);
        await flush(localVue);
        expect(page.vm.selectedEpisodes).toHaveLength(1);
        store.commit('currentShow', 'tvdb-other');
        await flush(localVue);
        expect(page.vm.selectedEpisodes).toEqual([]);
        expect(page.vm.seasonTableRows.flatMap(season => season.children).every(row => !row.vgtSelected)).toBe(true);

        store.commit('currentShow', showSlug);
        await flush(localVue);
        const currentEpisode = store.getters.getShowById(showSlug).seasons[1].children[0];
        page.vm.updateSelectedEpisodes('seasons', [{ slug: currentEpisode.slug }]);
        await flush(localVue);
        expect(page.vm.selectedEpisodes).toHaveLength(1);
        currentEpisode.status = 'Wanted';
        await flush(localVue);
        expect(page.vm.selectedEpisodes).toEqual([]);
        expect(page.vm.seasonTableRows[0].children.some(row => row.status === 'Wanted')).toBe(true);
    });
});
