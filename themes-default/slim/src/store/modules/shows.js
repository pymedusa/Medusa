import Vue from 'vue';
import {
    ADD_SHOW,
    ADD_SHOW_QUEUE_ITEM,
    ADD_SHOW_CONFIG,
    ADD_SHOWS,
    ADD_SHOW_CONFIG_TEMPLATE,
    ADD_SHOW_EPISODE,
    ADD_SHOW_SCENE_EXCEPTION,
    REMOVE_SHOW_SCENE_EXCEPTION,
    REMOVE_SHOW,
    REMOVE_SHOW_CONFIG_TEMPLATE
} from '../mutation-types';

/**
 * @typedef {object} ShowIdentifier
 * @property {string} indexer The indexer name (e.g. `tvdb`)
 * @property {number} id The show ID on the indexer (e.g. `12345`)
 */

const state = {
    shows: [],
    currentShow: {
        showSlug: null
    },
    loading: {
        total: null,
        current: null,
        display: false,
        finished: false
    },
    queueitems: [],
    staleEpisodeShows: {}
};

let episodeCacheRevision = 0;

const mutations = {
    invalidateShowEpisodeCache(state, { showSlug, season }) {
        if (!state.staleEpisodeShows) {
            Vue.set(state, 'staleEpisodeShows', {});
        }
        const existing = state.staleEpisodeShows[showSlug];
        const allSeasons = !Number.isInteger(season) || season < 0 || (existing && existing.seasons === null);
        const seasons = allSeasons ? null : [...new Set([...(existing ? existing.seasons : []), season])];
        Vue.set(state.staleEpisodeShows, showSlug, { revision: ++episodeCacheRevision, seasons });
    },
    clearShowEpisodeCacheStale(state, { showSlug, revision }) {
        const cache = state.staleEpisodeShows && state.staleEpisodeShows[showSlug];
        if (cache && cache.revision === revision) {
            cache.seasons = [];
        }
    },
    [ADD_SHOW](state, show) {
        const existingShow = state.shows.find(({ id, indexer }) => Number(show.id[show.indexer]) === Number(id[indexer]));

        if (!existingShow) {
            console.debug(`Adding ${show.title || show.indexer + String(show.id)} as it wasn't found in the shows array`, show);
            state.shows.push(show);
            return;
        }

        // Merge new show object over old one
        // this allows detailed queries to update the record
        // without the non-detailed removing the extra data
        console.debug(`Found ${show.title || show.indexer + String(show.id)} in shows array attempting merge`);
        const newShow = {
            ...existingShow,
            ...show
        };

        // Repair the searchTemplates
        newShow.config.searchTemplates = show.config.searchTemplates ? show.config.searchTemplates : existingShow.config.searchTemplates;

        // Update state
        Vue.set(state.shows, state.shows.indexOf(existingShow), newShow);
        console.debug(`Merged ${newShow.title || newShow.indexer + String(newShow.id)}`, newShow);
    },
    [ADD_SHOWS](state, shows) {
        // If the show is already available, we only want to merge values
        const mergedShows = [];
        for (const newShow of shows) {
            const existing = state.shows.find(stateShow => stateShow.id.slug === newShow.id.slug);
            if (existing) {
                const {
                    sceneAbsoluteNumbering,
                    xemAbsoluteNumbering,
                    sceneNumbering,
                    ...showWithoutDetailed
                } = newShow;

                // Repair searchTemplates.
                const mergedShow = { ...existing, ...showWithoutDetailed };
                mergedShow.config.searchTemplates = showWithoutDetailed.config.searchTemplates ? showWithoutDetailed.config.searchTemplates : existing.config.searchTemplates;

                mergedShows.push(mergedShow);
            } else {
                mergedShows.push(newShow);
            }
        }
        state.shows = mergedShows;
        console.debug(`Added ${shows.length} shows to store`);
    },
    [ADD_SHOW_CONFIG](state, { show, config }) {
        const existingShow = state.shows.find(({ id, indexer }) => Number(show.id[show.indexer]) === Number(id[indexer]));
        existingShow.config = { ...existingShow.config, ...config };
    },
    currentShow(state, showSlug) {
        state.currentShow.showSlug = showSlug;
    },
    setLoadingTotal(state, total) {
        state.loading.total = total;
    },
    setLoadingCurrent(state, current) {
        state.loading.current = current;
    },
    updateLoadingCurrent(state, current) {
        state.loading.current += current;
    },
    setLoadingDisplay(state, display) {
        state.loading.display = display;
    },
    setLoadingFinished(state, finished) {
        state.loading.finished = finished;
    },
    [ADD_SHOW_EPISODE](state, { show, episodes }) {
        // Creating a new show object (from the state one) as we want to trigger a store update
        const newShow = Object.assign({}, state.shows.find(({ id, indexer }) => Number(show.id[show.indexer]) === Number(id[indexer])));

        if (!newShow.seasons) {
            newShow.seasons = [];
        }

        // Recreate an Array with season objects, with each season having an episodes array.
        // This format is used by vue-good-table (displayShow).
        episodes.forEach(episode => {
            let existingSeason = newShow.seasons.find(season => season.season === episode.season);

            if (existingSeason) {
                // Shallow copy
                existingSeason = { ...existingSeason };

                const foundIndex = existingSeason.children.findIndex(element => element.slug === episode.slug);
                if (foundIndex === -1) {
                    existingSeason.children.push(episode);
                } else {
                    existingSeason.children.splice(foundIndex, 1, episode);
                }
            } else {
                const newSeason = {
                    season: episode.season,
                    children: [],
                    html: false,
                    mode: 'span',
                    label: 1
                };
                newShow.seasons.push(newSeason);
                newSeason.children.push(episode);
            }
        });

        // Update state
        const existingShow = state.shows.find(({ id, indexer }) => Number(show.id[show.indexer]) === Number(id[indexer]));
        Vue.set(state.shows, state.shows.indexOf(existingShow), newShow);
        console.log(`Storing episodes for show ${newShow.title} seasons: ${[...new Set(episodes.map(episode => episode.season))].join(', ')}`);
    },
    [ADD_SHOW_SCENE_EXCEPTION](state, { show, exception }) {
        // Get current show object
        const currentShow = Object.assign({}, state.shows.find(({ id, indexer }) => Number(show.id[show.indexer]) === Number(id[indexer])));

        if (currentShow.config.aliases.find(e => e.title === exception.title && e.season === exception.season)) {
            console.warn(`Can't add exception ${exception.title} with season ${exception.season} to show ${currentShow.title} as it already exists.`);
            return;
        }

        currentShow.config.aliases.push(exception);
    },
    [REMOVE_SHOW_SCENE_EXCEPTION](state, { show, exception }) {
        // Get current show object
        const currentShow = Object.assign({}, state.shows.find(({ id, indexer }) => Number(show.id[show.indexer]) === Number(id[indexer])));

        if (!currentShow.config.aliases.find(e => e.title === exception.title && e.season === exception.season)) {
            console.warn(`Can't remove exception ${exception.title} with season ${exception.season} to show ${currentShow.title} as it does not exist.`);
            return;
        }

        currentShow.config.aliases.splice(currentShow.config.aliases.indexOf(exception), 1);
    },
    [ADD_SHOW_QUEUE_ITEM](state, queueItem) {
        const existingQueueItem = state.queueitems.find(item => item.identifier === queueItem.identifier);

        if (existingQueueItem) {
            Vue.set(state.queueitems, state.queueitems.indexOf(existingQueueItem), { ...existingQueueItem, ...queueItem });
        } else {
            Vue.set(state.queueitems, state.queueitems.length, queueItem);
        }
    },
    [ADD_SHOW_CONFIG_TEMPLATE](state, { show, template }) {
        // Get current show object
        const currentShow = Object.assign({}, state.shows.find(({ id, indexer }) => Number(show.id[show.indexer]) === Number(id[indexer])));

        if (currentShow.config.searchTemplates.find(
            t => t.template === template.template &&
                t.title === template.title &&
                t.season === template.season &&
                t.seasonSearch === template.seasonSearch
        )) {
            console.warn(`Can't add template (${template.template}) to show ${currentShow.title} as it already exists.`);
            return;
        }

        currentShow.config.searchTemplates.push(template);
    },
    [REMOVE_SHOW_CONFIG_TEMPLATE](state, { show, template }) {
        // Get current show object
        const currentShow = Object.assign({}, state.shows.find(({ id, indexer }) => Number(show.id[show.indexer]) === Number(id[indexer])));

        if (template.id) {
            currentShow.config.searchTemplates = currentShow.config.searchTemplates.filter(
                t => t.id !== template.id
            );
            return;
        }

        currentShow.config.searchTemplates = currentShow.config.searchTemplates.filter(
            t => !(t.title === template.title && t.season === template.season && t.template === template.template)
        );
    },
    [REMOVE_SHOW](state, removedShow) {
        state.shows = state.shows.filter(existingShow => removedShow.id.slug !== existingShow.id.slug);
        if (state.staleEpisodeShows) {
            Vue.delete(state.staleEpisodeShows, removedShow.id.slug);
        }
    },
    loadShowsFromStore(state, namespace) {
        // Check if the ID exists
        // Update (namespaced) localStorage
        if (localStorage.getItem('shows')) {
            Vue.set(state, 'shows', JSON.parse(localStorage.getItem(`${namespace}shows`)));
            state.shows.filter(show => show.seasons).forEach(show => {
                mutations.invalidateShowEpisodeCache(state, { showSlug: show.id.slug });
            });
        }
    }
};

const getters = {
    isShowEpisodeCacheStale: state => showSlug => {
        const cache = state.staleEpisodeShows && state.staleEpisodeShows[showSlug];
        return Boolean(cache && (cache.seasons === null || cache.seasons.length > 0));
    },
    getShowById: state => {
        /**
         * Get a show from the loaded shows state, identified by show slug.
         *
         * @param {string} showSlug Show identifier.
         * @returns {object|undefined} Show object or undefined if not found.
         */
        const getShowById = showSlug => state.shows.find(show => show.id.slug === showSlug);
        return getShowById;
    },
    getShowByTitle: state => title => state.shows.find(show => show.title === title),
    getSeason: state => ({ showSlug, season }) => {
        const show = state.shows.find(show => show.id.slug === showSlug);
        return show && show.seasons ? show.seasons[season] : undefined;
    },
    getEpisode: state => ({ showSlug, season, episode }) => {
        const show = state.shows.find(show => show.id.slug === showSlug);
        return show && show.seasons && show.seasons.find(s => s.season === season) ? show.seasons.find(s => s.season === season).children.find(ep => ep.episode === episode) : undefined;
    },
    getCurrentShow: (state, _, rootState) => {
        return state.shows.find(show => show.id.slug === state.currentShow.showSlug) || rootState.defaults.show;
    },
    getShowIndexerUrl: (state, getters, rootState) => show => {
        const indexerConfig = rootState.config.indexers.indexers;
        if (!show.indexer || !indexerConfig[show.indexer]) {
            return;
        }

        const id = show.id[show.indexer];
        const indexerUrl = indexerConfig[show.indexer].showUrl;

        if (show.indexer === 'imdb') {
            return `${indexerUrl}${String(id).padStart(7, '0')}`;
        }
        return `${indexerUrl}${id}`;
    },
    showsWithStats: (state, getters, rootState) => {
        if (!state.shows) {
            return [];
        }

        return state.shows.map(show => {
            let showStats = rootState.stats.show.stats.find(stat => stat.indexerId === getters.indexerNameToId(show.indexer) && stat.seriesId === show.id[show.indexer]);
            const newLine = '\u000D';
            let text = 'Unaired';
            let title = '';

            if (!showStats) {
                showStats = {
                    epDownloaded: 0,
                    epSnatched: 0,
                    epTotal: 0,
                    seriesSize: 0
                };
            }

            if (showStats.epTotal >= 1) {
                text = showStats.epDownloaded;
                title = `Downloaded: ${showStats.epDownloaded}`;

                if (showStats.epSnatched) {
                    text += `+${showStats.epSnatched}`;
                    title += `${newLine}Snatched: ${showStats.epSnatched}`;
                }

                text += ` / ${showStats.epTotal}`;
                title += `${newLine}Total: ${showStats.epTotal}`;
            }

            show.stats = {
                episodes: {
                    total: showStats.epTotal,
                    snatched: showStats.epSnatched,
                    downloaded: showStats.epDownloaded,
                    size: showStats.seriesSize
                },
                tooltip: {
                    text,
                    title,
                    percentage: (showStats.epDownloaded * 100) / (showStats.epTotal || 1)
                }
            };
            return show;
        });
    },
    showsInLists: (state, getters, rootState) => {
        const { layout, general } = rootState.config;
        const { show } = layout;
        const { showListOrder } = show;
        const { rootDirs } = general;
        const { selectedRootIndex, local } = layout;
        const { showFilterByName } = local;

        const { showsWithStats } = getters;

        let shows = null;

        // Filter root dirs
        shows = showsWithStats.filter(show => selectedRootIndex === -1 || show.config.location.includes(rootDirs.slice(1)[selectedRootIndex]));

        // Filter by text for the banner, simple and smallposter layouts.
        // The Poster layout uses vue-isotope and this does not respond well to changes to the `list` property.
        if (layout.home !== 'poster') {
            shows = shows.filter(show => show.title.toLowerCase().includes(showFilterByName.toLowerCase()));
        }

        const categorizedShows = showListOrder.filter(
            listTitle => shows.filter(
                show => show.config.showLists.map(
                    list => list.toLowerCase()
                ).includes(listTitle.toLowerCase())
            ).length > 0
        ).map(
            listTitle => ({ listTitle, shows: shows.filter(
                show => show.config.showLists.map(list => list.toLowerCase()).includes(listTitle.toLowerCase())
            ) })
        );

        // Check for shows that are not in any category anymore
        const uncategorizedShows = shows.filter(show => {
            return show.config.showLists.map(item => {
                return showListOrder.map(list => list.toLowerCase()).includes(item.toLowerCase());
            }).every(item => !item);
        });

        if (uncategorizedShows.length > 0) {
            categorizedShows.push({ listTitle: 'uncategorized', shows: uncategorizedShows });
        }

        if (categorizedShows.length === 0 && uncategorizedShows.length === 0) {
            categorizedShows.push({ listTitle: 'Series', shows: [] });
        }

        return categorizedShows;
    }
};

/**
 * An object representing request parameters for getting a show from the API.
 *
 * @typedef {object} ShowGetParameters
 * @property {boolean} detailed Fetch detailed information? (e.g. scene/xem numbering)
 * @property {boolean} episodes Fetch seasons & episodes?
 * @property {boolean} withFileCacheRevision Return a revision for reusing these fresh details?
 */

// Coalesce file refreshes and prevent older responses replacing newer totals.
const fileRefreshes = new Map();
const episodeRequests = new Map();

const actions = {
    /**
     * Get show from API and commit it to the store.
     *
     * @param {*} context The store context.
     * @param {ShowIdentifier&ShowGetParameters} parameters Request parameters.
     * @returns {Promise} The API response.
     */
    getShow({ state, rootState, commit, getters }, { showSlug, detailed, episodes, withFileCacheRevision }) {
        return new Promise((resolve, reject) => {
            const requestRevision = state.staleEpisodeShows?.[showSlug]?.revision || 0;
            const params = {};
            let timeout = 30000;

            if (detailed !== undefined) {
                params.detailed = detailed;
                timeout = 60000;
                timeout = 60000;
            }

            if (episodes !== undefined) {
                params.episodes = episodes;
                timeout = 60000;
            }

            rootState.auth.client.api.get(`/series/${showSlug}`, { params, timeout })
                .then(res => {
                    const unchangedRevision = requestRevision === (state.staleEpisodeShows?.[showSlug]?.revision || 0);
                    const existingShow = state.shows.find(show => show.id.slug === showSlug);
                    if (existingShow && existingShow.seasons && (
                        (res.data.size !== undefined && res.data.size !== existingShow.size && !getters.isShowEpisodeCacheStale(showSlug)) ||
                        (res.data.seasonCount !== undefined && JSON.stringify(res.data.seasonCount) !== JSON.stringify(existingShow.seasonCount))
                    )) {
                        commit('invalidateShowEpisodeCache', { showSlug });
                    }
                    commit(ADD_SHOW, res.data);
                    const fileCacheRevision = unchangedRevision ? (state.staleEpisodeShows?.[showSlug]?.revision || 0) : undefined;
                    resolve(withFileCacheRevision ? { show: res.data, fileCacheRevision } : res.data);
                })
                .catch(error => {
                    reject(error);
                });
        });
    },
    /**
     * Get episdoes for a specified show from API and commit it to the store.
     *
     * @param {*} context - The store context.
     * @param {ShowParameteres} parameters - Request parameters.
     * @returns {Promise} The API response.
     */
    getEpisodes({ rootState, commit, getters }, { showSlug, season }) {
        return new Promise((resolve, reject) => {
            const { getShowById } = getters;
            const show = getShowById(showSlug);
            const requestKey = `${showSlug}/${season}`;
            const request = {};
            episodeRequests.set(requestKey, request);

            const limit = 1000;
            const params = {
                limit
            };

            if (season !== undefined) {
                params.season = season;
            }

            // Get episodes
            rootState.auth.client.api.get(`/series/${showSlug}/episodes`, { params })
                .then(response => {
                    if (episodeRequests.get(requestKey) === request) {
                        commit(ADD_SHOW_EPISODE, { show, episodes: response.data });
                        resolve();
                    } else {
                        // A newer request owns this season's cached rows.
                        resolve(false);
                    }
                })
                .catch(error => {
                    console.log(`Could not retrieve a episodes for show ${showSlug}, error: ${error}`);
                    reject(error);
                })
                .finally(() => {
                    if (episodeRequests.get(requestKey) === request) {
                        episodeRequests.delete(requestKey);
                    }
                });
        });
    },
    /**
     * Get shows from API and commit them to the store.
     *
     * @param {*} context - The store context.
     * @param {(ShowIdentifier&ShowGetParameters)[]} shows Shows to get. If not provided, gets the first 1k shows.
     * @returns {undefined|Promise} undefined if `shows` was provided or the API response if not.
     */
    getShows(context, shows) {
        const { commit, dispatch, state, rootState } = context;

        // If no shows are provided get the first 1000
        if (shows) {
            // Return a specific show list. (not used afaik).
            return shows.forEach(show => dispatch('getShow', show));
        }

        return new Promise((resolve, _) => {
            // Loading new shows, commit show loading information to state.
            commit('setLoadingTotal', 0);
            commit('setLoadingCurrent', 0);
            commit('setLoadingDisplay', true);

            const limit = 1000;
            const page = 1;
            const params = {
                limit,
                page
            };

            const pageRequests = [];
            const newShows = [];

            // Get first page
            pageRequests.push(rootState.auth.client.api.get('/series', { params })
                .then(response => {
                    commit('setLoadingTotal', Number(response.headers['x-pagination-count']));
                    const totalPages = Number(response.headers['x-pagination-total']);

                    newShows.push(...response.data);

                    commit('updateLoadingCurrent', response.data.length);

                    // Optionally get additional pages
                    for (let page = 2; page <= totalPages; page++) {
                        pageRequests.push(new Promise((resolve, reject) => {
                            const newPage = { page };
                            newPage.limit = params.limit;
                            return rootState.auth.client.api.get('/series', { params: newPage })
                                .then(response => {
                                    newShows.push(...response.data);
                                    commit('updateLoadingCurrent', response.data.length);
                                    resolve();
                                })
                                .catch(error => {
                                    reject(error);
                                });
                        }));
                    }
                })
                .catch(() => {
                    console.log('Could not retrieve a list of shows');
                })
                .finally(() => {
                    Promise.all(pageRequests)
                        .then(() => {
                            // Commit all the found shows to store.
                            commit(ADD_SHOWS, newShows);

                            // Update (namespaced) localStorage
                            const namespace = rootState.config.system.webRoot ? `${rootState.config.system.webRoot}_` : '';
                            try {
                                localStorage.setItem(`${namespace}shows`, JSON.stringify(state.shows));
                            } catch (error) {
                                console.warn(error);
                            }
                            resolve();
                        });
                })
            );
        });
    },
    setShow({ rootState }, { showSlug, data }) {
        // Update show, updated show will arrive over a WebSocket message
        return rootState.auth.client.api.patch(`series/${showSlug}`, data);
    },
    updateShow(context, show) {
        // Update local store
        const { commit } = context;
        return commit(ADD_SHOW, show);
    },
    addSceneException(context, { show, exception }) {
        const { commit } = context;
        commit(ADD_SHOW_SCENE_EXCEPTION, { show, exception });
    },
    removeSceneException(context, { show, exception }) {
        const { commit } = context;
        commit(REMOVE_SHOW_SCENE_EXCEPTION, { show, exception });
    },
    setCurrentShow(context, showSlug) {
        return new Promise(resolve => {
            // Set current show
            const { commit } = context;
            commit('currentShow', showSlug);
            resolve();
        });
    },
    setShowConfig(context, { show, config }) {
        const { commit } = context;
        commit(ADD_SHOW_CONFIG, { show, config });
    },
    removeShow({ commit, rootState, state }, show) {
        // Remove the show from store and localStorage (provided through websocket)
        commit(REMOVE_SHOW, show);

        // Update recentShows.
        rootState.config.general.recentShows = rootState.config.general.recentShows.filter(
            recentShow => recentShow.showSlug !== show.id.slug
        );
        const config = {
            recentShows: rootState.config.general.recentShows
        };
        rootState.auth.client.api.patch('config/main', config);

        // Update (namespaced) localStorage
        const namespace = rootState.config.system.webRoot ? `${rootState.config.system.webRoot}_` : '';
        try {
            localStorage.setItem(`${namespace}shows`, JSON.stringify(state.shows));
        } catch (error) {
            console.warn(error);
        }
    },
    updateShowQueueItem({ commit, dispatch }, queueItem) {
        // Update store's search queue item. (provided through websocket)
        commit(ADD_SHOW_QUEUE_ITEM, queueItem);
        if (queueItem.name === 'REFRESH' && queueItem.startTime && queueItem.inProgress === false) {
            return dispatch('refreshShowFiles', { showSlug: queueItem.show.id.slug, episodes: true });
        }
    },
    addSearchTemplate({ rootState, getters, commit }, { show, template }) {
        commit(ADD_SHOW_CONFIG_TEMPLATE, { show, template });
        const data = {
            config: {
                searchTemplates: getters.getCurrentShow.config.searchTemplates
            }
        };
        return rootState.auth.client.api.patch(`series/${show.indexer}${show.id[show.indexer]}`, data);
    },
    removeSearchTemplate({ rootState, getters, commit }, { show, template }) {
        commit(REMOVE_SHOW_CONFIG_TEMPLATE, { show, template });
        const data = {
            config: {
                searchTemplates: getters.getCurrentShow.config.searchTemplates
            }
        };
        return rootState.auth.client.api.patch(`series/${show.indexer}${show.id[show.indexer]}`, data);
    },
    initShowsFromLocalStorage({ rootState, commit }) {
        const namespace = rootState.config.system.webRoot ? `${rootState.config.system.webRoot}_` : '';
        return commit('loadShowsFromStore', namespace);
    },
    refreshShowFiles({ state, commit, dispatch }, { showSlug, episodes = false, season, freshDetailsRevision }) {
        if (!state.shows.some(show => show.id.slug === showSlug)) {
            return;
        }
        if (episodes || season !== undefined) {
            commit('invalidateShowEpisodeCache', { showSlug, season });
        }
        const pendingRefresh = fileRefreshes.get(showSlug);
        if (pendingRefresh) {
            pendingRefresh.pending = true;
            return pendingRefresh.promise;
        }

        const refresh = { pending: true };
        let detailsRevision = freshDetailsRevision;
        refresh.promise = Promise.resolve().then(async () => {
            try {
                while (refresh.pending) {
                    refresh.pending = false;
                    const show = state.shows.find(({ id }) => id.slug === showSlug);
                    if (!show || state.currentShow.showSlug !== showSlug || show.size === null || !(show.size >= 0)) {
                        return;
                    }

                    try {
                        const reuseDetails = detailsRevision !== undefined &&
                            detailsRevision === (state.staleEpisodeShows?.[showSlug]?.revision || 0);
                        detailsRevision = undefined;
                        if (!reuseDetails) {
                            // Finish each pass before starting the latest requested refresh.
                            await dispatch('getShow', { showSlug, detailed: true }); // eslint-disable-line no-await-in-loop
                        }
                        const cache = state.staleEpisodeShows?.[showSlug];
                        const revision = cache ? cache.revision : 0;
                        const currentShow = state.shows.find(({ id }) => id.slug === showSlug);
                        if (!currentShow || state.currentShow.showSlug !== showSlug) {
                            return;
                        }
                        const seasons = (currentShow.seasons || []).map(season => season.season)
                            .filter(season => cache && (cache.seasons === null || cache.seasons.includes(season)));
                        let episodesRefreshed = true;
                        for (const season of seasons) {
                            // Load cached seasons sequentially, as on the show page.
                            const result = await dispatch('getEpisodes', { showSlug, season }); // eslint-disable-line no-await-in-loop
                            episodesRefreshed = result !== false && episodesRefreshed;
                        }
                        if (!episodesRefreshed) {
                            continue;
                        }
                        if ((state.staleEpisodeShows?.[showSlug]?.revision || 0) !== revision) {
                            // Setting true preserves any concurrently queued refresh.
                            refresh.pending = true; // eslint-disable-line require-atomic-updates
                        } else if (!refresh.pending) {
                            commit('clearShowEpisodeCacheStale', { showSlug, revision });
                        }
                    } catch (error) {
                        console.warn(`Could not refresh recorded files for show ${showSlug}: ${error}`);
                    }
                }
            } finally {
                fileRefreshes.delete(showSlug);
            }
        });
        fileRefreshes.set(showSlug, refresh);
        return refresh.promise;
    },
    async updateEpisode({ state, commit, dispatch }, episode) {
        const show = state.shows.find(({ id }) => id.slug === episode.showSlug);
        if (!show) {
            return;
        }

        const season = (show.seasons || []).find(season => season.season === episode.season);
        const previousEpisode = season && season.children.find(item => item.slug === episode.slug);
        const previousSize = (previousEpisode && previousEpisode.file && previousEpisode.file.size) || 0;
        const size = (episode.file && episode.file.size) || 0;
        const previousLocation = previousEpisode && previousEpisode.file && previousEpisode.file.location;
        const location = episode.file && episode.file.location;
        const fileChanged = !previousEpisode || previousSize !== size || previousLocation !== location;
        commit(ADD_SHOW_EPISODE, { show, episodes: [episode] });
        // Counters are cached separately from episode rows. Even an identical row can
        // follow a newer HTTP episode load while the counters still need refreshing.
        const statsRefresh = dispatch('refreshShowStats', episode.showSlug);
        if (fileChanged) {
            commit('invalidateShowEpisodeCache', { showSlug: episode.showSlug, season: episode.season });
            const refresh = fileRefreshes.get(episode.showSlug);
            if (refresh) {
                refresh.pending = true;
            }
        }

        const rescanning = state.queueitems.some(item => item.name === 'REFRESH' &&
            item.inProgress && item.show.id.slug === episode.showSlug);
        if (!rescanning && fileChanged) {
            await Promise.all([statsRefresh, dispatch('refreshShowFiles', { showSlug: episode.showSlug })]);
        } else {
            await statsRefresh;
        }
    },
    saveShowConfig({ rootState }, { show }) {
        const showConfig = show.config;
        const data = {
            config: {
                aliases: showConfig.aliases,
                defaultEpisodeStatus: showConfig.defaultEpisodeStatus,
                dvdOrder: showConfig.dvdOrder,
                seasonFolders: showConfig.seasonFolders,
                anime: showConfig.anime,
                scene: showConfig.scene,
                sports: showConfig.sports,
                paused: showConfig.paused,
                location: showConfig.location,
                airByDate: showConfig.airByDate,
                subtitlesEnabled: showConfig.subtitlesEnabled,
                release: {
                    requiredWords: showConfig.release.requiredWords,
                    ignoredWords: showConfig.release.ignoredWords,
                    requiredWordsExclude: showConfig.release.requiredWordsExclude,
                    ignoredWordsExclude: showConfig.release.ignoredWordsExclude
                },
                qualities: {
                    preferred: showConfig.qualities.preferred,
                    allowed: showConfig.qualities.allowed
                },
                airdateOffset: showConfig.airdateOffset,
                showLists: showConfig.showLists,
                templates: showConfig.templates,
                searchTemplates: showConfig.searchTemplates
            },
            language: show.language
        };

        if (data.config.anime) {
            data.config.release.blacklist = showConfig.release.blacklist;
            data.config.release.whitelist = showConfig.release.whitelist;
        }

        return rootState.auth.client.api.patch(`series/${show.id.slug}`, data);
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
