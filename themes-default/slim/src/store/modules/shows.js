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
    queueitems: []
};

const mutations = {
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

        if (currentShow.config.searchTemplates.find(t => t.template === template.pattern)) {
            console.warn(`Can't add template (${template.pattern} to show ${currentShow.title} as it already exists.`);
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
    },
    loadShowsFromStore(state, namespace) {
        // Check if the ID exists
        // Update (namespaced) localStorage
        if (localStorage.getItem('shows')) {
            Vue.set(state, 'shows', JSON.parse(localStorage.getItem(`${namespace}shows`)));
        }
    }
};

const getters = {
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
 */

const actions = {
    /**
     * Get show from API and commit it to the store.
     *
     * @param {*} context The store context.
     * @param {ShowIdentifier&ShowGetParameters} parameters Request parameters.
     * @returns {Promise} The API response.
     */
    getShow({ rootState, commit }, { showSlug, detailed, episodes }) {
        return new Promise((resolve, reject) => {
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
                    commit(ADD_SHOW, res.data);
                    resolve(res.data);
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
                    commit(ADD_SHOW_EPISODE, { show, episodes: response.data });
                    resolve();
                })
                .catch(error => {
                    console.log(`Could not retrieve a episodes for show ${showSlug}, error: ${error}`);
                    reject(error);
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
    updateShowQueueItem(context, queueItem) {
        // Update store's search queue item. (provided through websocket)
        const { commit } = context;
        return commit(ADD_SHOW_QUEUE_ITEM, queueItem);
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
    updateEpisode({ state, commit }, episode) {
        const show = state.shows.find(({ id }) => id.slug === episode.showSlug);
        commit(ADD_SHOW_EPISODE, { show, episodes: [episode] });
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
