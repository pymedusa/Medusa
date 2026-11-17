import Vuex, { Store } from 'vuex';
import { createLocalVue, mount } from '@vue/test-utils';
import AppFooter from '../../src/components/app-footer.vue';
import showsModule from '../../src/store/modules/shows';
import statsModule from '../../src/store/modules/stats';

describe('Live footer counters', () => {
    const showSlug = 'tvdb123';
    let localVue;
    let store;
    let get;
    let episode;
    let overall;
    let wrapper;

    const overallResponse = stats => ({ data: JSON.parse(JSON.stringify(stats)) });
    const deferred = () => {
        let resolve;
        const promise = new Promise(fulfill => {
            resolve = fulfill;
        });
        return { promise, resolve };
    };
    const flush = async () => {
        for (let i = 0; i < 8; i++) {
            await localVue.nextTick(); // eslint-disable-line no-await-in-loop
        }
    };

    beforeEach(() => {
        localVue = createLocalVue();
        localVue.use(Vuex);
        episode = {
            showSlug, slug: 's01e02', season: 1, episode: 2,
            status: 'Wanted', airDate: '2026-01-01T20:00:00', file: {}
        };
        overall = { shows: { total: 1, active: 1 }, episodes: { downloaded: 1, snatched: 0, total: 3 } };
        get = jest.fn().mockImplementation(url => Promise.resolve(url === '/stats/' ? overallResponse(overall) : {
            data: {
                stats: [{
                    indexerId: 1, seriesId: 123, epDownloaded: overall.episodes.downloaded,
                    epSnatched: overall.episodes.snatched, epTotal: 3, seriesSize: 1000
                }],
                maxDownloadCount: 100000
            }
        }));
        store = new Store({
            state: {
                auth: { client: { api: { get } } },
                config: { layout: { dateStyle: '%Y-%m-%d', timeStyle: '%H:%M:%S' }, system: {} }
            },
            getters: {
                indexerNameToId: () => () => 1,
                getStatus: () => () => ({ value: 2 }),
                getScheduler: () => () => ({ nextRun: null })
            },
            modules: {
                shows: {
                    ...showsModule,
                    state: {
                        shows: [{
                            id: { slug: showSlug, tvdb: 123 }, indexer: 'tvdb',
                            seasons: [{ season: 1, children: [episode] }]
                        }],
                        currentShow: { showSlug: null }, queueitems: [], staleEpisodeShows: {}
                    }
                },
                stats: {
                    ...statsModule,
                    state: { overall: overallResponse(overall).data, show: { stats: [], maxDownloadCount: 100000 } }
                }
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

    it('updates snatched and downloaded counts in the mounted footer', async () => {
        wrapper = mount(AppFooter, {
            localVue, store, stubs: { 'app-link': { template: '<a><slot /></a>' } }
        });
        const footer = wrapper.vm;
        expect(wrapper.find('a').exists()).toBe(false);
        expect(wrapper.findAll('.footerhighlight').at(2).text()).toBe('1');
        overall.episodes.snatched = 1;

        await store.dispatch('updateEpisode', { ...episode, status: 'Snatched' });
        await localVue.nextTick();

        expect(wrapper.find('a').text()).toBe('+1');
        expect(wrapper.findAll('.footerhighlight').at(2).text()).toBe('1');
        overall.episodes = { downloaded: 2, snatched: 0, total: 3 };

        await store.dispatch('updateEpisode', { ...episode, status: 'Downloaded' });
        await localVue.nextTick();

        expect(wrapper.vm).toBe(footer);
        expect(wrapper.find('a').exists()).toBe(false);
        expect(wrapper.findAll('.footerhighlight').at(2).text()).toBe('2');
        expect(wrapper.text()).toContain('(66.7%)');
    });

    it('coalesces a same-show burst into one targeted request and one overall request', async () => {
        const second = { ...episode, episode: 3, slug: 's01e03' };
        store.state.shows.shows[0].seasons[0].children.push(second);
        overall.episodes.snatched = 2;

        await Promise.all([episode, second].map(row => store.dispatch('updateEpisode', { ...row, status: 'Snatched' })));

        expect(get.mock.calls).toEqual([
            ['/stats/show', { params: { showslug: showSlug } }], ['/stats/']
        ]);
        expect(store.state.stats.overall.episodes.snatched).toBe(2);
    });

    it('refreshes again when an episode update arrives during initial overall loading', async () => {
        const initial = deferred();
        const oldResponse = overallResponse(overall);
        get.mockReturnValueOnce(initial.promise);
        const loading = store.dispatch('getStats');
        await flush();
        Object.assign(overall.episodes, { snatched: 1 });
        const updating = store.dispatch('updateEpisode', { ...episode, status: 'Snatched' });
        await flush();
        const requestsBeforeCompletion = get.mock.calls.length;

        initial.resolve(oldResponse);
        await Promise.all([loading, updating]);

        expect(requestsBeforeCompletion).toBe(1);
        expect(get.mock.calls).toEqual([
            ['/stats/'], ['/stats/show', { params: { showslug: showSlug } }], ['/stats/']
        ]);
        expect(store.state.stats.overall.episodes.snatched).toBe(1);
    });

    it('keeps a second update queued while the first overall refresh is in flight', async () => {
        const initial = deferred();
        const defaultResponse = get.getMockImplementation();
        get.mockImplementation(url => {
            if (url === '/stats/' && get.mock.calls.filter(([path]) => path === '/stats/').length === 1) {
                return initial.promise;
            }
            return defaultResponse(url);
        });
        overall.episodes.snatched = 1;
        const oldResponse = overallResponse(overall);
        const snatching = store.dispatch('updateEpisode', { ...episode, status: 'Snatched' });
        await flush();
        Object.assign(overall.episodes, { downloaded: 2, snatched: 0, total: 3 });
        const downloading = store.dispatch('updateEpisode', { ...episode, status: 'Downloaded' });
        await flush();
        const requestsBeforeCompletion = get.mock.calls.length;

        initial.resolve(oldResponse);
        await Promise.all([snatching, downloading]);

        expect(requestsBeforeCompletion).toBe(2);
        expect(get.mock.calls).toEqual([
            ['/stats/show', { params: { showslug: showSlug } }],
            ['/stats/'],
            ['/stats/show', { params: { showslug: showSlug } }],
            ['/stats/']
        ]);
        expect(store.state.stats.overall.episodes).toEqual({ downloaded: 2, snatched: 0, total: 3 });
    });
});
