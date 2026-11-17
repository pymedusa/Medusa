import Vuex, { Store } from 'vuex';
import { createLocalVue } from '@vue/test-utils';
import DisplayShow from '../../src/components/display-show.vue';
import showsModule from '../../src/store/modules/shows';
import historyModule from '../../src/store/modules/history';

describe('Opening a cached show', () => {
    const showSlug = 'tvdb123';
    let context;

    beforeEach(() => {
        context = {
            showSlug,
            show: {
                id: { slug: showSlug },
                title: 'Test Show',
                seasonCount: [{ season: 0, episodeCount: 1 }, { season: 1, episodeCount: 1 }],
                seasons: [
                    { season: 0, children: [{ file: { size: 1000 } }] },
                    { season: 1, children: [{ file: { size: 1000 } }] }
                ]
            },
            getShow: jest.fn().mockResolvedValue({ fileCacheRevision: 123 }),
            setCurrentShow: jest.fn(),
            setRecentShow: jest.fn(),
            isShowEpisodeCacheStale: jest.fn().mockReturnValue(false),
            refreshShowFiles: jest.fn().mockResolvedValue(undefined),
            neededSeasons: jest.fn().mockReturnValue([1]),
            getEpisodes: jest.fn().mockResolvedValue(undefined)
        };
        context.initializeEpisodes = DisplayShow.methods.initializeEpisodes.bind(context);
        context.loadEpisodes = DisplayShow.methods.loadEpisodes.bind(context);
        context.isSeasonLoaded = DisplayShow.methods.isSeasonLoaded.bind(context);
    });

    it('reuses complete unchanged episode rows when revisiting a show', async () => {
        await DisplayShow.methods.loadShow.call(context);

        expect(context.getShow).toHaveBeenCalledWith({ showSlug, detailed: true, withFileCacheRevision: true });
        expect(context.refreshShowFiles).not.toHaveBeenCalled();
        expect(context.getEpisodes).not.toHaveBeenCalled();
    });

    it('reconciles invalidated rows through the shared refresh action before reusing them', async () => {
        context.isShowEpisodeCacheStale.mockReturnValue(true);

        await DisplayShow.methods.loadShow.call(context);

        expect(context.refreshShowFiles).toHaveBeenCalledWith({ showSlug, freshDetailsRevision: 123 });
        expect(context.setCurrentShow.mock.invocationCallOrder[0])
            .toBeLessThan(context.refreshShowFiles.mock.invocationCallOrder[0]);
        expect(context.getEpisodes).not.toHaveBeenCalled();
    });

    it('loads a partially cached season without refetching complete specials', async () => {
        context.show.seasonCount[1].episodeCount = 2;

        await DisplayShow.methods.loadShow.call(context);

        expect(context.getEpisodes).toHaveBeenCalledTimes(1);
        expect(context.getEpisodes).toHaveBeenCalledWith({ showSlug, season: 1 });
    });

    it('loads missing specials without refetching the complete first page', async () => {
        context.show.seasons.shift();

        await DisplayShow.methods.loadShow.call(context);

        expect(context.getEpisodes).toHaveBeenCalledTimes(1);
        expect(context.getEpisodes).toHaveBeenCalledWith({ showSlug, season: 0 });
    });

    it('still loads episodes and specials on the first visit', async () => {
        delete context.show.seasons;

        await DisplayShow.methods.loadShow.call(context);

        expect(context.getEpisodes).toHaveBeenCalledTimes(2);
        expect(context.getEpisodes).toHaveBeenCalledWith({ showSlug, season: 1 });
        expect(context.getEpisodes).toHaveBeenCalledWith({ showSlug, season: 0 });
    });

    it('keeps explicit forced episode refreshes working', () => {
        context.initializeEpisodes(true);

        expect(context.getEpisodes).toHaveBeenCalledTimes(2);
    });
});

describe('Show page request counts', () => {
    const showSlug = 'tvdb123';
    let store;
    let context;
    let get;
    let episodes;

    beforeEach(() => {
        const localVue = createLocalVue();
        localVue.use(Vuex);
        jest.spyOn(console, 'debug').mockImplementation(() => {});
        jest.spyOn(console, 'log').mockImplementation(() => {});
        episodes = [1, 2, 3].map(season => ({
            showSlug, season, episode: 1, slug: `s0${season}e01`, file: { size: 1000 }
        }));
        const show = {
            id: { slug: showSlug, tvdb: 123 },
            indexer: 'tvdb',
            config: { searchTemplates: [] },
            size: 3000,
            seasonCount: episodes.map(episode => ({ season: episode.season, episodeCount: 1 })),
            seasons: episodes.map(episode => ({ season: episode.season, children: [episode] }))
        };
        get = jest.fn((url, { params }) => Promise.resolve(url.endsWith('/episodes') ?
            { data: episodes.filter(episode => episode.season === params.season) } :
            { data: { id: show.id, indexer: show.indexer, config: show.config, size: 4000, seasonCount: show.seasonCount } }));
        store = new Store({
            state: {
                auth: { client: { api: { get } } },
                config: { layout: { history: 'detailed' } }
            },
            actions: { refreshShowStats: jest.fn() },
            modules: {
                shows: {
                    ...showsModule,
                    state: { shows: [show], currentShow: { showSlug: 'tvdb999' }, queueitems: [], staleEpisodeShows: {} }
                },
                history: { ...historyModule, state: JSON.parse(JSON.stringify(historyModule.state)) }
            }
        });
        context = {
            showSlug,
            getShow: args => store.dispatch('getShow', args),
            setCurrentShow: slug => store.dispatch('setCurrentShow', slug),
            isShowEpisodeCacheStale: slug => store.getters.isShowEpisodeCacheStale(slug),
            refreshShowFiles: args => store.dispatch('refreshShowFiles', args),
            getEpisodes: args => store.dispatch('getEpisodes', args),
            setRecentShow: jest.fn(),
            neededSeasons: () => [1]
        };
        Object.defineProperty(context, 'show', { get: () => store.getters.getShowById(showSlug) });
        context.initializeEpisodes = DisplayShow.methods.initializeEpisodes.bind(context);
        context.loadEpisodes = DisplayShow.methods.loadEpisodes.bind(context);
        context.isSeasonLoaded = DisplayShow.methods.isSeasonLoaded.bind(context);
        episodes[2] = { ...episodes[2], file: { size: 2000 } };
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    it.each(['episode', 'download'])('fetches details once and only the changed season after an inactive %s update', async event => {
        if (event === 'episode') {
            await store.dispatch('updateEpisode', episodes[2]);
        } else {
            await store.dispatch('updateHistory', { series: showSlug, statusName: 'Downloaded', season: 3, episode: 1 });
        }
        expect(get).not.toHaveBeenCalled();

        await DisplayShow.methods.loadShow.call(context);

        expect(get.mock.calls.map(([url, { params }]) => [url, params.season])).toEqual([
            [`/series/${showSlug}`, undefined],
            [`/series/${showSlug}/episodes`, 3]
        ]);
        expect(context.show.size).toBe(4000);
        expect(context.show.seasons[2].children[0].file.size).toBe(2000);
        expect(store.getters.isShowEpisodeCacheStale(showSlug)).toBe(false);
    });

    it('refreshes all cached seasons after a rescan using one details request', async () => {
        await store.dispatch('updateShowQueueItem', {
            identifier: 'refresh-123', name: 'REFRESH', startTime: '2026-10-27 12:00:00',
            inProgress: false, show: { id: { slug: showSlug } }
        });

        await DisplayShow.methods.loadShow.call(context);

        expect(get.mock.calls.filter(([url]) => !url.endsWith('/episodes'))).toHaveLength(1);
        expect(get.mock.calls.filter(([url]) => url.endsWith('/episodes')).map(([, { params }]) => params.season)).toEqual([1, 2, 3]);
        expect(store.getters.isShowEpisodeCacheStale(showSlug)).toBe(false);
    });

    it('refreshes all cached seasons when the details reveal an unexplained size change', async () => {
        await DisplayShow.methods.loadShow.call(context);

        expect(get.mock.calls.filter(([url]) => !url.endsWith('/episodes'))).toHaveLength(1);
        expect(get.mock.calls.filter(([url]) => url.endsWith('/episodes')).map(([, { params }]) => params.season)).toEqual([1, 2, 3]);
        expect(store.getters.isShowEpisodeCacheStale(showSlug)).toBe(false);
    });
});
