import Vuex, { Store } from 'vuex';
import { createLocalVue } from '@vue/test-utils';
import showsModule from '../../src/store/modules/shows';
import { REMOVE_SHOW } from '../../src/store/mutation-types';

describe('Recorded show size refresh', () => {
    const showSlug = 'tvdb123';
    let episode;
    let show;
    let store;
    let get;
    let warn;

    const showResponse = size => ({
        data: { id: show.id, indexer: show.indexer, config: show.config, size }
    });
    const respondWithFiles = (size, episodes) => {
        get.mockImplementation((url, { params }) => Promise.resolve(url.endsWith('/episodes') ?
            { data: episodes.filter(episode => episode.season === params.season) } : showResponse(size)));
    };
    const refreshItem = overrides => ({
        identifier: 'rescan-123',
        name: 'REFRESH',
        startTime: '2026-10-27 12:00:00',
        inProgress: false,
        success: null,
        show: { id: { slug: showSlug }, size: 1 },
        ...overrides
    });

    beforeEach(() => {
        const localVue = createLocalVue();
        localVue.use(Vuex);
        jest.spyOn(console, 'log').mockImplementation(() => {});
        jest.spyOn(console, 'debug').mockImplementation(() => {});
        warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
        episode = {
            showSlug,
            season: 1,
            episode: 1,
            slug: 's01e01',
            file: { size: 1000 },
            watched: false
        };
        show = {
            id: { slug: showSlug, tvdb: 123 },
            indexer: 'tvdb',
            config: { searchTemplates: [] },
            size: 10000,
            seasonCount: [{ season: 1, episodeCount: 1 }],
            seasons: [{ season: 1, children: [episode] }]
        };
        get = jest.fn();
        store = new Store({
            state: { auth: { client: { api: { get } } } },
            modules: {
                shows: {
                    ...showsModule,
                    state: {
                        shows: [show],
                        currentShow: { showSlug },
                        queueitems: [],
                        staleEpisodeShows: {}
                    }
                }
            }
        });
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    it('refreshes the authoritative total after a recorded episode size changes', async () => {
        const updatedEpisode = { ...episode, file: { size: 2000 } };
        respondWithFiles(20000, [updatedEpisode]);

        await store.dispatch('updateEpisode', updatedEpisode);

        expect(get).toHaveBeenCalledWith(`/series/${showSlug}`, {
            params: { detailed: true }, timeout: 60000
        });
        expect(store.getters.getCurrentShow.size).toBe(20000);
        expect(store.getters.getCurrentShow.seasons[0].children[0].file.size).toBe(2000);
        expect(store.getters.isShowEpisodeCacheStale(showSlug)).toBe(false);
        expect(warn).not.toHaveBeenCalled();
    });

    it('refreshes after a recorded file is removed and size is omitted', async () => {
        respondWithFiles(9000, [{ ...episode, file: {} }]);

        await store.dispatch('updateEpisode', { ...episode, file: {} });

        expect(store.getters.getCurrentShow.size).toBe(9000);
        expect(store.getters.getCurrentShow.seasons[0].children[0].file.size).toBeUndefined();
    });

    it('refreshes for an unloaded episode even when its new file size is zero', async () => {
        respondWithFiles(9000, [episode, { ...episode, season: 2, slug: 's02e01', file: {} }]);

        await store.dispatch('updateEpisode', {
            ...episode, season: 2, slug: 's02e01', file: {}
        });

        expect(store.getters.getCurrentShow.size).toBe(9000);
    });

    it('does not fetch a total for a watched update with unchanged size', async () => {
        await store.dispatch('updateEpisode', { ...episode, watched: true });

        expect(get).not.toHaveBeenCalled();
        expect(store.getters.getCurrentShow.seasons[0].children[0].watched).toBe(true);
    });

    it('ignores episode updates for an untracked show', async () => {
        await store.dispatch('updateEpisode', { ...episode, showSlug: 'tvdb999' });

        expect(store.state.shows.shows).toHaveLength(1);
        expect(get).not.toHaveBeenCalled();
    });

    it.each([null, undefined])('does not fetch a total before details are loaded (%s)', async size => {
        show.size = size;

        await store.dispatch('updateEpisode', { ...episode, file: { size: 2000 } });

        expect(get).not.toHaveBeenCalled();
    });

    it('does not fetch totals for an inactive show', async () => {
        store.state.shows.currentShow.showSlug = 'tvdb999';

        await store.dispatch('updateEpisode', { ...episode, file: { size: 2000 } });

        expect(get).not.toHaveBeenCalled();
    });

    it('refreshes the total and only cached seasons when a rescan finishes', async () => {
        show.seasons.push({ season: 4, children: [{ ...episode, season: 4, slug: 's04e01' }] });
        get.mockImplementation((url, { params }) => Promise.resolve(
            url.endsWith('/episodes') ?
                { data: [{ ...episode, season: params.season, slug: `s0${params.season}e01`, file: {} }] } :
                showResponse(8000)
        ));

        await store.dispatch('updateShowQueueItem', refreshItem());

        expect(get.mock.calls.map(([url, options]) => [url, options.params])).toEqual([
            [`/series/${showSlug}`, { detailed: true }],
            [`/series/${showSlug}/episodes`, { limit: 1000, season: 1 }],
            [`/series/${showSlug}/episodes`, { limit: 1000, season: 4 }]
        ]);
        expect(store.getters.getCurrentShow.size).toBe(8000);
        expect(store.getters.getCurrentShow.seasons.map(season => season.children[0].file.size))
            .toEqual([undefined, undefined]);
        expect(store.state.shows.queueitems[0].inProgress).toBe(false);
    });

    it.each([
        { startTime: null },
        { inProgress: true },
        { name: 'UPDATE' }
    ])('does not refresh for a queue item that is not a finished rescan (%j)', async overrides => {
        await store.dispatch('updateShowQueueItem', refreshItem(overrides));

        expect(get).not.toHaveBeenCalled();
    });

    it('defers episode total requests to completion while a rescan is active', async () => {
        await store.dispatch('updateShowQueueItem', refreshItem({ inProgress: true }));
        await store.dispatch('updateEpisode', { ...episode, file: { size: 2000 } });

        expect(get).not.toHaveBeenCalled();
        expect(store.getters.getCurrentShow.seasons[0].children[0].file.size).toBe(2000);
    });

    it('handles refresh failures without rejecting an unawaited socket action', async () => {
        get.mockRejectedValue(new Error('Offline'));

        await expect(store.dispatch('updateEpisode', { ...episode, file: {} })).resolves.toBeUndefined();

        expect(get).toHaveBeenCalledTimes(1);
        expect(warn).toHaveBeenCalled();
        expect(store.getters.getCurrentShow.size).toBe(10000);
    });

    it('serializes rapid refreshes so an older response cannot overwrite the latest total', async () => {
        let resolveFirst;
        get.mockImplementationOnce(() => new Promise(resolve => {
            resolveFirst = resolve;
        })).mockImplementation(url => Promise.resolve(url.endsWith('/episodes') ?
            { data: [episode] } : showResponse(30000)));

        const first = store.dispatch('refreshShowFiles', { showSlug });
        await Promise.resolve();
        const second = store.dispatch('refreshShowFiles', { showSlug });

        expect(get).toHaveBeenCalledTimes(1);
        resolveFirst(showResponse(20000));
        await Promise.all([first, second]);

        expect(get.mock.calls.map(([url]) => url)).toEqual([
            `/series/${showSlug}`,
            `/series/${showSlug}/episodes`,
            `/series/${showSlug}`,
            `/series/${showSlug}/episodes`
        ]);
        expect(store.getters.getCurrentShow.size).toBe(30000);
    });

    it('skips a queued refresh when navigation makes the show inactive', async () => {
        let resolveFirst;
        get.mockImplementationOnce(() => new Promise(resolve => {
            resolveFirst = resolve;
        }));

        const first = store.dispatch('refreshShowFiles', { showSlug });
        await Promise.resolve();
        const second = store.dispatch('refreshShowFiles', { showSlug });
        store.state.shows.currentShow.showSlug = 'tvdb999';
        resolveFirst(showResponse(20000));
        await Promise.all([first, second]);

        expect(get).toHaveBeenCalledTimes(1);
    });

    it('coalesces a burst into one pending refresh and preserves episode reload requests', async () => {
        let resolveFirst;
        get.mockImplementationOnce(() => new Promise(resolve => {
            resolveFirst = resolve;
        })).mockImplementation(url => Promise.resolve(url.endsWith('/episodes') ?
            { data: [{ ...episode, file: { size: 2000 } }] } : showResponse(30000)));

        const first = store.dispatch('refreshShowFiles', { showSlug });
        await Promise.resolve();
        const pending = [
            store.dispatch('refreshShowFiles', { showSlug }),
            store.dispatch('refreshShowFiles', { showSlug, episodes: true }),
            store.dispatch('refreshShowFiles', { showSlug })
        ];
        expect(get).toHaveBeenCalledTimes(1);
        resolveFirst(showResponse(20000));
        await Promise.all([first, ...pending]);

        expect(get.mock.calls.map(([url]) => url)).toEqual([
            `/series/${showSlug}`,
            `/series/${showSlug}/episodes`,
            `/series/${showSlug}`,
            `/series/${showSlug}/episodes`
        ]);
        expect(store.getters.getCurrentShow.size).toBe(30000);
        expect(store.getters.getCurrentShow.seasons[0].children[0].file.size).toBe(2000);
    });

    it('reloads rows when a newer episode update arrives during an older season request', async () => {
        let resolveSeason;
        let seasonRequested;
        const waitingForSeason = new Promise(resolve => {
            seasonRequested = resolve;
        });
        const updatedEpisode = { ...episode, file: { size: 2000 } };
        get.mockResolvedValueOnce(showResponse(10000))
            .mockImplementationOnce(() => new Promise(resolve => {
                resolveSeason = resolve;
                seasonRequested();
            }))
            .mockResolvedValueOnce(showResponse(20000))
            .mockResolvedValueOnce({ data: [updatedEpisode] });

        const first = store.dispatch('refreshShowFiles', { showSlug, episodes: true });
        await waitingForSeason;
        const update = store.dispatch('updateEpisode', updatedEpisode);
        resolveSeason({ data: [episode] });
        await Promise.all([first, update]);

        expect(store.getters.getCurrentShow.size).toBe(20000);
        expect(store.getters.getCurrentShow.seasons[0].children[0].file.size).toBe(2000);
        expect(get).toHaveBeenCalledTimes(4);
    });

    it('marks inactive rescan results stale without fetching episodes', async () => {
        store.state.shows.currentShow.showSlug = 'tvdb999';

        await store.dispatch('updateShowQueueItem', refreshItem());

        expect(store.state.shows.staleEpisodeShows[showSlug]).toBeDefined();
        expect(get).not.toHaveBeenCalled();
    });

    it('marks inactive download results stale without fetching episodes', async () => {
        store.state.shows.currentShow.showSlug = 'tvdb999';

        await store.dispatch('refreshShowFiles', { showSlug, episodes: true });

        expect(store.state.shows.staleEpisodeShows[showSlug]).toBeDefined();
        expect(get).not.toHaveBeenCalled();
    });

    it('marks changed file data stale even during an inactive rescan', async () => {
        store.state.shows.currentShow.showSlug = 'tvdb999';
        await store.dispatch('updateShowQueueItem', refreshItem({ inProgress: true }));

        await store.dispatch('updateEpisode', { ...episode, file: { size: 2000 } });

        expect(store.state.shows.staleEpisodeShows[showSlug]).toBeDefined();
        expect(get).not.toHaveBeenCalled();
    });

    it('clears a stale marker only after all cached seasons refresh successfully', async () => {
        store.state.shows.staleEpisodeShows[showSlug] = { revision: 100, seasons: null };
        show.seasons.push({ season: 4, children: [{ ...episode, season: 4, slug: 's04e01' }] });
        get.mockImplementation((url, { params }) => Promise.resolve(url.endsWith('/episodes') ?
            { data: [{ ...episode, season: params.season, slug: `s0${params.season}e01` }] } :
            showResponse(10000)));

        await store.dispatch('refreshShowFiles', { showSlug });

        expect(get).toHaveBeenCalledTimes(3);
        expect(store.getters.isShowEpisodeCacheStale(showSlug)).toBe(false);
    });

    it('keeps stale state when only some cached seasons refreshed successfully', async () => {
        store.state.shows.staleEpisodeShows[showSlug] = { revision: 100, seasons: null };
        show.seasons.push({ season: 4, children: [{ ...episode, season: 4, slug: 's04e01' }] });
        get.mockResolvedValueOnce(showResponse(10000))
            .mockResolvedValueOnce({ data: [episode] })
            .mockRejectedValueOnce(new Error('Season unavailable'));

        await store.dispatch('refreshShowFiles', { showSlug });

        expect(get).toHaveBeenCalledTimes(3);
        expect(store.state.shows.staleEpisodeShows[showSlug]).toBeDefined();
    });

    it('does not clear a newer inactive invalidation after an older refresh finishes', async () => {
        let resolveSeason;
        let seasonRequested;
        const waitingForSeason = new Promise(resolve => {
            seasonRequested = resolve;
        });
        get.mockResolvedValueOnce(showResponse(10000))
            .mockImplementationOnce(() => new Promise(resolve => {
                resolveSeason = resolve;
                seasonRequested();
            }));

        const first = store.dispatch('refreshShowFiles', { showSlug, episodes: true });
        await waitingForSeason;
        store.commit('currentShow', 'tvdb999');
        const second = store.dispatch('refreshShowFiles', { showSlug, episodes: true });
        const revision = store.state.shows.staleEpisodeShows[showSlug];
        resolveSeason({ data: [episode] });
        await Promise.all([first, second]);

        expect(revision).toBeDefined();
        expect(store.state.shows.staleEpisodeShows[showSlug]).toBe(revision);
    });

    it.each([
        { size: 20000 },
        { seasonCount: [{ season: 1, episodeCount: 2 }] }
    ])('invalidates cached rows when fresh show metadata changed (%j)', async changed => {
        get.mockResolvedValue({ data: { ...showResponse(10000).data, ...changed } });

        await store.dispatch('getShow', { showSlug, detailed: true });

        expect(store.state.shows.staleEpisodeShows[showSlug]).toBeDefined();
    });

    it('keeps cached rows clean when fresh show metadata is unchanged', async () => {
        get.mockResolvedValue({ data: { ...showResponse(10000).data, seasonCount: show.seasonCount } });

        await store.dispatch('getShow', { showSlug, detailed: true });

        expect(store.state.shows.staleEpisodeShows[showSlug]).toBeUndefined();
    });

    it('does not create stale markers for untracked shows', async () => {
        await store.dispatch('refreshShowFiles', { showSlug: 'tvdb999', episodes: true });

        expect(store.state.shows.staleEpisodeShows).toEqual({});
        expect(get).not.toHaveBeenCalled();
    });

    it('removes stale markers with their show', () => {
        store.commit('invalidateShowEpisodeCache', { showSlug });

        store.commit(REMOVE_SHOW, show);

        expect(store.getters.isShowEpisodeCacheStale(showSlug)).toBe(false);
    });

    it('invalidates episode caches restored from an earlier session', () => {
        localStorage.setItem('shows', JSON.stringify([show]));

        store.commit('loadShowsFromStore', '');

        expect(store.getters.isShowEpisodeCacheStale(showSlug)).toBe(true);
        localStorage.removeItem('shows');
    });

    it('retries when a rescan changes cached files during an in-flight season refresh', async () => {
        let resolveSeason;
        let seasonRequested;
        const waitingForSeason = new Promise(resolve => {
            seasonRequested = resolve;
        });
        const updatedEpisode = { ...episode, file: { size: 2000 } };
        get.mockResolvedValueOnce(showResponse(10000))
            .mockImplementationOnce(() => new Promise(resolve => {
                resolveSeason = resolve;
                seasonRequested();
            }))
            .mockResolvedValueOnce(showResponse(20000))
            .mockResolvedValueOnce({ data: [updatedEpisode] });
        await store.dispatch('updateShowQueueItem', refreshItem({ inProgress: true }));

        const refresh = store.dispatch('refreshShowFiles', { showSlug, episodes: true });
        await waitingForSeason;
        await store.dispatch('updateEpisode', updatedEpisode);
        resolveSeason({ data: [episode] });
        await refresh;

        expect(get).toHaveBeenCalledTimes(4);
        expect(store.getters.getCurrentShow.seasons[0].children[0].file.size).toBe(2000);
        expect(store.getters.isShowEpisodeCacheStale(showSlug)).toBe(false);
    });

    it('retries the total when a rescan changes files during the show metadata request', async () => {
        let resolveShow;
        const updatedEpisode = { ...episode, file: { size: 2000 } };
        get.mockImplementationOnce(() => new Promise(resolve => {
            resolveShow = resolve;
        })).mockImplementation(url => Promise.resolve(url.endsWith('/episodes') ?
            { data: [updatedEpisode] } : showResponse(20000)));
        await store.dispatch('updateShowQueueItem', refreshItem({ inProgress: true }));

        const refresh = store.dispatch('refreshShowFiles', { showSlug, episodes: true });
        await Promise.resolve();
        await store.dispatch('updateEpisode', updatedEpisode);
        resolveShow(showResponse(10000));
        await refresh;

        expect(store.getters.getCurrentShow.size).toBe(20000);
        expect(store.getters.getCurrentShow.seasons[0].children[0].file.size).toBe(2000);
        expect(store.getters.isShowEpisodeCacheStale(showSlug)).toBe(false);
    });

    it('ignores a page request that finishes after a newer shared refresh', async () => {
        let resolveOldSeason;
        const updatedEpisode = { ...episode, file: { size: 2000 } };
        get.mockImplementationOnce(() => new Promise(resolve => {
            resolveOldSeason = resolve;
        })).mockResolvedValueOnce(showResponse(20000))
            .mockResolvedValueOnce({ data: [updatedEpisode] });

        const oldRequest = store.dispatch('getEpisodes', { showSlug, season: 1 });
        await store.dispatch('refreshShowFiles', { showSlug, episodes: true });
        resolveOldSeason({ data: [episode] });
        await oldRequest;

        expect(store.getters.getCurrentShow.seasons[0].children[0].file.size).toBe(2000);
        expect(store.getters.isShowEpisodeCacheStale(showSlug)).toBe(false);
    });

    it('keeps stale state when a superseding page request fails', async () => {
        let resolveRefreshSeason;
        let rejectPageSeason;
        let seasonRequested;
        const waitingForSeason = new Promise(resolve => {
            seasonRequested = resolve;
        });
        get.mockResolvedValueOnce(showResponse(10000))
            .mockImplementationOnce(() => new Promise(resolve => {
                resolveRefreshSeason = resolve;
                seasonRequested();
            }))
            .mockImplementationOnce(() => new Promise((resolve, reject) => {
                rejectPageSeason = reject;
            }));

        const refresh = store.dispatch('refreshShowFiles', { showSlug, episodes: true });
        await waitingForSeason;
        const pageRequest = store.dispatch('getEpisodes', { showSlug, season: 1 }).catch(error => error);
        resolveRefreshSeason({ data: [episode] });
        await refresh;
        rejectPageSeason(new Error('Page request failed'));
        await expect(pageRequest).resolves.toEqual(new Error('Page request failed'));

        expect(store.getters.isShowEpisodeCacheStale(showSlug)).toBe(true);
    });

    it('refreshes only the changed episode season when the total changes', async () => {
        const otherEpisode = { ...episode, season: 4, slug: 's04e01' };
        const updatedEpisode = { ...episode, file: { size: 2000 } };
        show.seasons.push({ season: 4, children: [otherEpisode] });
        respondWithFiles(20000, [updatedEpisode, otherEpisode]);

        await store.dispatch('updateEpisode', updatedEpisode);

        expect(get.mock.calls.filter(([url]) => url.endsWith('/episodes')).map(([, options]) => options.params.season))
            .toEqual([1]);
        expect(store.getters.getCurrentShow.size).toBe(20000);
        expect(store.getters.getCurrentShow.seasons[1].children[0]).toEqual(otherEpisode);
    });

    it.each([0, 4])('refreshes only a known downloaded season (%s)', async season => {
        const downloadedEpisode = { ...episode, season, slug: `s0${season}e01`, file: { size: 2000 } };
        show.seasons.push({ season, children: [downloadedEpisode] });
        respondWithFiles(20000, [episode, downloadedEpisode]);

        await store.dispatch('refreshShowFiles', { showSlug, episodes: true, season });

        expect(get.mock.calls.filter(([url]) => url.endsWith('/episodes')).map(([, options]) => options.params.season))
            .toEqual([season]);
        expect(store.getters.isShowEpisodeCacheStale(showSlug)).toBe(false);
    });

    it.each([undefined, null, -1, 1.5, '4'])('refreshes all cached seasons for an unknown downloaded season (%s)', async season => {
        const otherEpisode = { ...episode, season: 4, slug: 's04e01' };
        show.seasons.push({ season: 4, children: [otherEpisode] });
        respondWithFiles(20000, [episode, otherEpisode]);

        await store.dispatch('refreshShowFiles', { showSlug, episodes: true, season });

        expect(get.mock.calls.filter(([url]) => url.endsWith('/episodes')).map(([, options]) => options.params.season))
            .toEqual([1, 4]);
    });

    it('reuses fresh show details while refreshing targeted cached rows', async () => {
        store.commit('currentShow', 'tvdb999');
        await store.dispatch('refreshShowFiles', { showSlug, episodes: true, season: 1 });
        respondWithFiles(20000, [{ ...episode, file: { size: 2000 } }]);

        const details = await store.dispatch('getShow', { showSlug, detailed: true, withFileCacheRevision: true });
        expect(details.fileCacheRevision).toBeDefined();
        store.commit('currentShow', showSlug);
        await store.dispatch('refreshShowFiles', { showSlug, freshDetailsRevision: details.fileCacheRevision });

        expect(get.mock.calls.map(([url]) => url)).toEqual([
            `/series/${showSlug}`,
            `/series/${showSlug}/episodes`
        ]);
        expect(store.getters.isShowEpisodeCacheStale(showSlug)).toBe(false);
    });

    it('does not reuse details if a file event arrived during the metadata request', async () => {
        let resolveShow;
        store.commit('currentShow', 'tvdb999');
        await store.dispatch('refreshShowFiles', { showSlug, episodes: true, season: 1 });
        get.mockImplementationOnce(() => new Promise(resolve => {
            resolveShow = resolve;
        }));

        const detailsRequest = store.dispatch('getShow', { showSlug, detailed: true, withFileCacheRevision: true });
        await store.dispatch('refreshShowFiles', { showSlug, episodes: true, season: 1 });
        resolveShow(showResponse(10000));
        const details = await detailsRequest;
        expect(details.show).toBeDefined();
        expect(details.fileCacheRevision).toBeUndefined();
        respondWithFiles(20000, [{ ...episode, file: { size: 2000 } }]);
        store.commit('currentShow', showSlug);
        await store.dispatch('refreshShowFiles', { showSlug, freshDetailsRevision: details.fileCacheRevision });

        expect(get.mock.calls.filter(([url]) => !url.endsWith('/episodes'))).toHaveLength(2);
        expect(store.getters.getCurrentShow.size).toBe(20000);
    });

    it('does not fetch episode rows for a known season that is not cached', async () => {
        get.mockResolvedValue(showResponse(20000));

        await store.dispatch('refreshShowFiles', { showSlug, episodes: true, season: 4 });

        expect(get.mock.calls.map(([url]) => url)).toEqual([`/series/${showSlug}`]);
        expect(store.getters.isShowEpisodeCacheStale(showSlug)).toBe(false);
    });

    it('unions changed seasons without refreshing unaffected cached seasons', async () => {
        const episodes = [episode, ...[4, 6].map(season => ({ ...episode, season, slug: `s0${season}e01` }))];
        show.seasons = episodes.map(episode => ({ season: episode.season, children: [episode] }));
        store.commit('currentShow', 'tvdb999');
        await store.dispatch('refreshShowFiles', { showSlug, episodes: true, season: 1 });
        await store.dispatch('refreshShowFiles', { showSlug, episodes: true, season: 4 });
        respondWithFiles(20000, episodes);
        store.commit('currentShow', showSlug);

        await store.dispatch('refreshShowFiles', { showSlug });

        expect(get.mock.calls.filter(([url]) => url.endsWith('/episodes')).map(([, options]) => options.params.season))
            .toEqual([1, 4]);
        expect(store.getters.isShowEpisodeCacheStale(showSlug)).toBe(false);
    });

    it('rejects details reuse after a concurrent invalidation was already refreshed clean', async () => {
        let resolveOldDetails;
        const updatedEpisode = { ...episode, file: { size: 2000 } };
        get.mockImplementationOnce(() => new Promise(resolve => {
            resolveOldDetails = resolve;
        })).mockResolvedValueOnce(showResponse(20000))
            .mockResolvedValueOnce({ data: [updatedEpisode] });

        const oldDetails = store.dispatch('getShow', { showSlug, detailed: true, withFileCacheRevision: true });
        await store.dispatch('refreshShowFiles', { showSlug, episodes: true, season: 1 });
        expect(store.getters.isShowEpisodeCacheStale(showSlug)).toBe(false);
        resolveOldDetails(showResponse(10000));
        const details = await oldDetails;

        expect(details.fileCacheRevision).toBeUndefined();
    });
});
