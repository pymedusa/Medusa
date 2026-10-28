import Vuex, { Store } from 'vuex';
import VueRouter from 'vue-router';
import { createLocalVue, mount } from '@vue/test-utils';
import App from '../../src/components/app.vue';
import Home from '../../src/components/home.vue';
import { ProgressBar } from '../../src/components/helpers';
import showsModule from '../../src/store/modules/shows';
import statsModule from '../../src/store/modules/stats';

describe('Live homepage counters', () => {
    const showSlug = 'tvdb123';
    let localVue;
    let store;
    let get;
    let episode;
    let stats;
    let wrapper;

    const flush = async () => {
        for (let i = 0; i < 8; i++) {
            await localVue.nextTick(); // eslint-disable-line no-await-in-loop
        }
    };

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        localVue.use(VueRouter);
        episode = {
            showSlug, slug: 's01e02', season: 1, episode: 2,
            status: 'Wanted', airDate: '2026-01-01T20:00:00', file: {}
        };
        stats = { indexerId: 1, seriesId: 123, epDownloaded: 1, epSnatched: 0, epTotal: 3, seriesSize: 1000 };
        get = jest.fn().mockImplementation(url => Promise.resolve({
            data: url === '/stats/' ? {
                episodes: { downloaded: stats.epDownloaded, snatched: stats.epSnatched, total: stats.epTotal },
                shows: { total: 1, active: 1 }
            } : { stats: [{ ...stats }], maxDownloadCount: 100000 }
        }));
        store = new Store({
            state: {
                auth: { isAuthenticated: true, client: { api: { get } } },
                config: {
                    general: { rootDirs: ['0', '/shows'] }, system: { configLoaded: true },
                    layout: { home: 'simple', selectedRootIndex: -1, show: { showListOrder: [] }, local: { showFilterByName: '' } }
                }
            },
            getters: { indexerNameToId: () => () => 1 },
            modules: {
                shows: {
                    ...showsModule,
                    state: {
                        shows: [{
                            id: { slug: showSlug, tvdb: 123 }, indexer: 'tvdb', title: 'Example', size: 1000,
                            config: { location: '/shows/example', showLists: [], searchTemplates: [] },
                            seasons: [{ season: 1, children: [episode] }]
                        }],
                        currentShow: { showSlug: null }, loading: {}, queueitems: [], staleEpisodeShows: {}
                    }
                },
                stats: { ...statsModule, state: JSON.parse(JSON.stringify(statsModule.state)) }
            }
        });
        jest.spyOn(console, 'log').mockImplementation(() => {});
        jest.spyOn(console, 'debug').mockImplementation(() => {});
    });

    afterEach(() => {
        if (wrapper) {
            wrapper.destroy();
            wrapper = null;
        }
        jest.restoreAllMocks();
    });

    const openHome = async () => {
        const router = new VueRouter({ routes: [
            { path: '/home', name: 'home', component: Home },
            { path: '/show', name: 'show', component: { render: h => h('div') } }
        ] });
        await router.push('/home');
        wrapper = mount(App, {
            localVue, store, router,
            stubs: {
                'load-progress-bar': true, 'app-header': true, 'sub-menu': true, 'vue-snotify': true,
                alerts: true, 'app-footer': true, 'scroll-buttons': true, backstretch: true,
                // Keep the real homepage lifecycle/getters and the actual displayed counter.
                'show-list': {
                    props: ['shows'],
                    render(h) {
                        return h('div', this.shows.map(show => h(ProgressBar, { props: show.stats.tooltip })));
                    }
                }
            }
        });
        await flush();
        return router;
    };

    it('updates the cached homepage after snatching without remounting or reloading the show list', async () => {
        const router = await openHome();
        const home = wrapper.findComponent(Home).vm;
        expect(wrapper.findComponent(ProgressBar).text()).toBe('1 / 3');
        await router.push('/show');
        stats.epSnatched = 1;

        await store.dispatch('updateEpisode', { ...episode, status: 'Snatched' });
        await router.push('/home');
        await flush();

        expect(wrapper.findComponent(Home).vm).toBe(home);
        expect(wrapper.findComponent(ProgressBar).text()).toBe('1+1 / 3');
        expect(get.mock.calls).toEqual([
            ['/stats/show'], ['/stats/show', { params: { showslug: showSlug } }], ['/stats/']
        ]);
    });

    it('updates the counter while the homepage is already visible', async () => {
        await openHome();
        stats.epDownloaded = 2;
        await store.dispatch('updateEpisode', { ...episode, status: 'Downloaded' });
        await flush();

        expect(wrapper.findComponent(ProgressBar).text()).toBe('2 / 3');
        expect(get).toHaveBeenCalledTimes(3);
    });

    it('groups simultaneous episode status updates into one targeted statistics request', async () => {
        const secondEpisode = { ...episode, episode: 3, slug: 's01e03' };
        store.state.shows.shows[0].seasons[0].children.push(secondEpisode);
        stats.epSnatched = 2;

        await Promise.all([episode, secondEpisode].map(row => store.dispatch('updateEpisode', { ...row, status: 'Snatched' })));

        expect(get.mock.calls).toEqual([['/stats/show', { params: { showslug: showSlug } }], ['/stats/']]);
        expect(store.getters.showsWithStats[0].stats.tooltip.text).toBe('1+2 / 3');
    });

    it('refreshes counters for an episode whose season has never been loaded', async () => {
        store.state.shows.shows[0].seasons = [];
        stats.epSnatched = 1;

        await store.dispatch('updateEpisode', { ...episode, status: 'Snatched' });

        expect(get.mock.calls).toEqual([['/stats/show', { params: { showslug: showSlug } }], ['/stats/']]);
        expect(store.getters.showsWithStats[0].stats.episodes.snatched).toBe(1);
    });

    it('coalesces unchanged tracked episodes and ignores an untracked show', async () => {
        await Promise.all([
            store.dispatch('updateEpisode', { ...episode, watched: true, subtitles: ['eng'], quality: 4 }),
            store.dispatch('updateEpisode', { ...episode })
        ]);
        await store.dispatch('updateEpisode', { ...episode, showSlug: 'tvdb999', status: 'Snatched' });

        expect(get.mock.calls).toEqual([['/stats/show', { params: { showslug: showSlug } }], ['/stats/']]);
    });

    it('refreshes stale counters even when an episode request beats its live notification', async () => {
        await openHome();
        const snatched = { ...episode, status: 'Snatched' };
        stats.epSnatched = 1;
        get.mockResolvedValueOnce({ data: [snatched] });

        await store.dispatch('getEpisodes', { showSlug, season: 1 });
        await flush();
        expect(store.getters.getEpisode({ showSlug, season: 1, episode: 2 }).status).toBe('Snatched');
        expect(wrapper.findComponent(ProgressBar).text()).toBe('1 / 3');

        await store.dispatch('updateEpisode', { ...snatched });
        await flush();

        expect(wrapper.findComponent(ProgressBar).text()).toBe('1+1 / 3');
        expect(get.mock.calls.filter(([url]) => url === '/stats/show')).toEqual([
            ['/stats/show'], ['/stats/show', { params: { showslug: showSlug } }]
        ]);
    });

    it('refreshes the size and airdate-dependent totals without requesting show details', async () => {
        stats.seriesSize = 2000;
        await store.dispatch('updateEpisode', { ...episode, file: { size: 1000 } });
        expect(store.getters.showsWithStats[0].stats.episodes.size).toBe(2000);
        stats.epTotal = 2;
        await store.dispatch('updateEpisode', { ...episode, file: { size: 1000 }, airDate: null });

        expect(get.mock.calls).toEqual([
            ['/stats/show', { params: { showslug: showSlug } }],
            ['/stats/'],
            ['/stats/show', { params: { showslug: showSlug } }],
            ['/stats/']
        ]);
        expect(store.getters.showsWithStats[0].stats.episodes.total).toBe(2);
    });
});
