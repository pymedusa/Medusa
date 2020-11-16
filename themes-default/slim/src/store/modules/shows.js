import Vue from 'vue';

import { api } from '../../api';
import {
    ADD_SHOW,
    ADD_SHOW_QUEUE_ITEM,
    ADD_SHOW_CONFIG,
    ADD_SHOWS,
    ADD_SHOW_EPISODE,
    ADD_SHOW_SCENE_EXCEPTION,
    REMOVE_SHOW_SCENE_EXCEPTION
} from '../mutation-types';

/**
 * @typedef {object} ShowIdentifier
 * @property {string} indexer The indexer name (e.g. `tvdb`)
 * @property {number} id The show ID on the indexer (e.g. `12345`)
 */

const state = {
    shows: [],
    currentShow: {
        indexer: null,
        id: null
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

        // Update state
        Vue.set(state.shows, state.shows.indexOf(existingShow), newShow);
        console.debug(`Merged ${newShow.title || newShow.indexer + String(newShow.id)}`, newShow);
    },
    [ADD_SHOWS](state, shows) {
        // Quick check on duplicate shows.
        const newShows = shows.filter(newShow => {
            return !state.shows.find(
                ({ id, indexer }) => Number(newShow.id[newShow.indexer]) === Number(id[indexer]) && newShow.indexer === indexer
            );
        });

        Vue.set(state, 'shows', [...state.shows, ...newShows]);
        console.debug(`Added ${shows.length} shows to store`);
    },
    [ADD_SHOW_CONFIG](state, { show, config }) {
        const existingShow = state.shows.find(({ id, indexer }) => Number(show.id[show.indexer]) === Number(id[indexer]));
        existingShow.config = { ...existingShow.config, ...config };
    },
    currentShow(state, { indexer, id }) {
        state.currentShow.indexer = indexer;
        state.currentShow.id = id;
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
            const existingSeason = newShow.seasons.find(season => season.season === episode.season);

            if (existingSeason) {
                const foundIndex = existingSeason.episodes.findIndex(element => element.slug === episode.slug);
                if (foundIndex === -1) {
                    existingSeason.episodes.push(episode);
                } else {
                    existingSeason.episodes.splice(foundIndex, 1, episode);
                }
            } else {
                const newSeason = {
                    season: episode.season,
                    episodes: [],
                    html: false,
                    mode: 'span',
                    label: 1
                };
                newShow.seasons.push(newSeason);
                newSeason.episodes.push(episode);
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
    }

};

const getters = {
    getShowById: state => {
        /**
         * Get a show from the loaded shows state, identified by show ID and indexer name.
         *
         * @param {ShowIdentifier} show Show identifiers.
         * @returns {object|undefined} Show object or undefined if not found.
         */
        const getShowById = ({ id, indexer }) => state.shows.find(show => Number(show.id[indexer]) === Number(id));
        return getShowById;
    },
    getShowByTitle: state => title => state.shows.find(show => show.title === title),
    getSeason: state => ({ showSlug, season }) => {
        const show = state.shows.find(show => show.id.slug === showSlug);
        return show && show.seasons ? show.seasons[season] : undefined;
    },
    getEpisode: state => ({ showSlug, season, episode }) => {
        const show = state.shows.find(show => show.id.slug === showSlug);
        return show && show.seasons && show.seasons.find(s => s.season === season) ? show.seasons.find(s => s.season === season).episodes.find(ep => ep.episode === episode) : undefined;
    },
    getCurrentShow: (state, getters, rootState) => {
        return state.shows.find(show => Number(show.id[state.currentShow.indexer]) === Number(state.currentShow.id)) || rootState.defaults.show;
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
    getShow(context, { indexer, id, detailed, episodes }) {
        return new Promise((resolve, reject) => {
            const { commit } = context;
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

            api.get(`/series/${indexer}${id}`, { params, timeout })
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
    getEpisodes({ commit, getters }, { indexer, id, season }) {
        return new Promise((resolve, reject) => {
            const { getShowById } = getters;
            const show = getShowById({ id, indexer });

            const limit = 1000;
            const params = {
                limit
            };

            if (season !== undefined) {
                params.season = season;
            }

            // Get episodes
            api.get(`/series/${indexer}${id}/episodes`, { params })
                .then(response => {
                    commit(ADD_SHOW_EPISODE, { show, episodes: response.data });
                    resolve();
                })
                .catch(error => {
                    console.log(`Could not retrieve a episodes for show ${indexer}${id}, error: ${error}`);
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
        const { commit, dispatch } = context;

        // If no shows are provided get the first 1000
        if (!shows) {
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

            // Get first page
            pageRequests.push(api.get('/series', { params })
                .then(response => {
                    commit('setLoadingTotal', Number(response.headers['x-pagination-count']));
                    const totalPages = Number(response.headers['x-pagination-total']);

                    commit(ADD_SHOWS, response.data);

                    commit('updateLoadingCurrent', response.data.length);
                    // Optionally get additional pages

                    for (let page = 2; page <= totalPages; page++) {
                        const newPage = { page };
                        newPage.limit = params.limit;
                        pageRequests.push(api.get('/series', { params: newPage })
                            .then(response => {
                                commit(ADD_SHOWS, response.data);
                                commit('updateLoadingCurrent', response.data.length);
                            }));
                    }
                })
                .catch(() => {
                    console.log('Could not retrieve a list of shows');
                })
            );

            return Promise.all(pageRequests);
        }

        return shows.forEach(show => dispatch('getShow', show));
    },
    setShow(context, { indexer, id, data }) {
        // Update show, updated show will arrive over a WebSocket message
        return api.patch(`series/${indexer}${id}`, data);
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
    setCurrentShow(context, { indexer, id }) {
        // Set current show
        const { commit } = context;
        return commit('currentShow', { indexer, id });
    },
    setShowConfig(context, { show, config }) {
        const { commit } = context;
        commit(ADD_SHOW_CONFIG, { show, config });
    },
    updateShowQueueItem(context, queueItem) {
        // Update store's search queue item. (provided through websocket)
        const { commit } = context;
        return commit(ADD_SHOW_QUEUE_ITEM, queueItem);
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
