import Vue from 'vue';

import { api } from '../../api';
import { ADD_HISTORY, ADD_SHOW_HISTORY, ADD_SHOW_EPISODE_HISTORY, INITIALIZE_HISTORY_STORE } from '../mutation-types';
import { episodeToSlug } from '../../utils/core';

const state = {
    history: [],
    historyCompact: [],
    page: 0,
    episodeHistory: {},
    historyLast: null,
    historyLastCompact: null,
    loading: false
};

const mutations = {
    [ADD_HISTORY](state, { history, compact }) {
        // Update state
        if (compact) {
            state.historyCompact = history;
        } else {
            state.history = history;
        }

        // Update localStorage
        const storeKey = compact ? 'historyCompact' : 'history';
        try {
            localStorage.setItem(storeKey, JSON.stringify(state[storeKey]));
        } catch(error) {
            console.log("Local Storage is full, can't store full history table");
        }
    },
    [ADD_SHOW_HISTORY](state, { showSlug, history, compact=false }) {
        // Add history data to episodeHistory, but without passing the show slug.
        for (const row of history) {
            if (!Object.keys(state.episodeHistory).includes(showSlug)) {
                Vue.set(state.episodeHistory, showSlug, {});
            }

            const episodeSlug = episodeToSlug(row.season, row.episode);
            if (!state.episodeHistory[showSlug][episodeSlug]) {
                state.episodeHistory[showSlug][episodeSlug] = [];
            }

            state.episodeHistory[showSlug][episodeSlug].push(row);
        }
    },
    [ADD_SHOW_EPISODE_HISTORY](state, { showSlug, episodeSlug, history }) {
        // Keep an object of shows, with their history per episode
        // Example: {tvdb1234: {s01e01: [history]}}

        if (!Object.keys(state.episodeHistory).includes(showSlug)) {
            Vue.set(state.episodeHistory, showSlug, {});
        }

        Vue.set(state.episodeHistory[showSlug], episodeSlug, history);
    },
    [INITIALIZE_HISTORY_STORE](state) {
        // Check if the ID exists
        // Replace the state object with the stored item
        // Get History
        if (localStorage.getItem('history')){
            const history = JSON.parse(localStorage.getItem('history'));
            if (history) {
                Vue.set(state, 'history', history);
            }    
        }

        if (localStorage.getItem('historyCompact')){
            const historyCompact = JSON.parse(localStorage.getItem('historyCompact'));
            if (historyCompact) {
                Vue.set(state, 'historyCompact', historyCompact);
            }    
        }

        // Get show history
        if (localStorage.getItem('showHistory')){
            const showHistory = JSON.parse(localStorage.getItem('showHistory'));
            if (showHistory) {
                this.replaceState(
                    Object.assign(state.history, showHistory)
                );
            }
        }

        // Get show history
        if (localStorage.getItem('episodeHistory')){
            const episodeHistory = JSON.parse(localStorage.getItem('episodeHistory'));
            if (episodeHistory) {
                this.replaceState(
                    Object.assign(state.episodeHistory, episodeHistory)
                );
            }
        }
    },
    setLoading(state, value) {
        state.loading = value;
    }
};

const getters = {
    getShowHistoryBySlug: state => showSlug => state.showHistory[showSlug],
    getLastReleaseName: state => ({ showSlug, episodeSlug }) => {
        if (state.episodeHistory[showSlug] !== undefined) {
            if (state.episodeHistory[showSlug][episodeSlug] !== undefined) {
                if (state.episodeHistory[showSlug][episodeSlug].length === 1) {
                    return state.episodeHistory[showSlug][episodeSlug][0].resource;
                }
                const filteredHistory = state.episodeHistory[showSlug][episodeSlug]
                    .sort((a, b) => (a.actionDate - b.actionDate) * -1)
                    .filter(ep => ['Snatched', 'Downloaded'].includes(ep.statusName) && ep.resource !== '');
                if (filteredHistory.length > 0) {
                    return filteredHistory[0].resource;
                }
            }
        }
    },
    getEpisodeHistory: state => ({ showSlug, episodeSlug }) => {
        if (state.episodeHistory[showSlug] === undefined) {
            return [];
        }

        return state.episodeHistory[showSlug][episodeSlug] || [];
    },
    getSeasonHistory: state => ({ showSlug, season }) => {
        if (state.episodeHistory[showSlug] === undefined) {
            return [];
        }

        return Object.values(state.episodeHistory[showSlug]).flat().filter(row => row.season === season) || [];
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
     * Get show history from API and commit it to the store.
     *
     * @param {*} context The store context.
     * @param {ShowIdentifier&ShowGetParameters} parameters Request parameters.
     * @returns {Promise} The API response.
     */
    async getShowHistory(context, { slug }) {
        const { commit } = context;

        const response = await api.get(`/history/${slug}`);
        if (response.data.length > 0) {
            commit(ADD_SHOW_HISTORY, { showSlug: slug, history: response.data });
        }
    },
    /**
     * Get detailed history from API and commit them to the store.
     *
     * @param {*} context - The store context.
     * @param {string} showSlug Slug for the show to get. If not provided, gets the first 1k shows.
     * @returns {undefined|Promise} undefined if `shows` was provided or the API response if not.
     */
    async getHistory(context, args) {
        const { commit, state } = context;
        const limit = 1000;
        const params = { limit };
        let url = '/history';
        const showSlug = args ? args.showSlug : undefined;
        const compact = args ? args.compact : undefined;
        const total_rows = args ? args.total : undefined;

        if (showSlug) {
            url = `${url}/${showSlug}`;
        }

        if (compact) {
            params.compact = true;
        }

        if (total_rows) {
            params.total = total_rows;
        }

        let page = 0;
        let lastPage = false;
        let result = [];
        
        commit('setLoading', true);
        while (!lastPage) {
            let response = null;
            page += 1;
            params.page = page;

            try {
                response = await api.get(url, { params }); // eslint-disable-line no-await-in-loop
            } catch (error) {
                if (error.response && error.response.status === 404) {
                    console.debug(`No history available${showSlug ? ' for show ' + showSlug : ''}`);
                }
                lastPage = true;
            }

            if (response) {
                result.push(...response.data);
                if (response.data.length < limit) {
                    lastPage = true;
                }
            } else {
                lastPage = true;
            }
        }

        if (showSlug) {
            commit(ADD_SHOW_HISTORY, { showSlug, history: result, compact });
        } else {
            commit(ADD_HISTORY, { history: result, compact });
        }
        commit('setLoading', false);

    },
    /**
     * Get episode history from API and commit it to the store.
     *
     * @param {*} context The store context.
     * @param {ShowIdentifier&ShowGetParameters} parameters Request parameters.
     * @returns {Promise} The API response.
     */
    getShowEpisodeHistory(context, { showSlug, episodeSlug }) {
        return new Promise(resolve => {
            const { commit } = context;

            api.get(`/history/${showSlug}/episode/${episodeSlug}`)
                .then(response => {
                    if (response.data.length > 0) {
                        commit(ADD_SHOW_EPISODE_HISTORY, { showSlug, episodeSlug, history: response.data });
                    }
                    resolve();
                })
                .catch(() => {
                    console.warn(`No episode history found for show ${showSlug} and episode ${episodeSlug}`);
                });
        });
    },
    initHistoryStore({ commit }) {
        commit(INITIALIZE_HISTORY_STORE);
    },
    checkHistory({ state, rootState, dispatch }) {
        // retrieve the last history item from api.
        // Compare the states last history or historyCompact row.
        // and get new history data.
        const { layout } = rootState.config;
        const params = { last: true };
        const historyParams = {};

        if (layout.historyLimit) {
            historyParams.total = layout.historyLimit;
        }

        let history = [];
        const compact = layout.history === 'compact';
        if (compact) {
            history = state.historyCompact;
        } else {
            history = state.history;
        }

        if (!history || history.length === 0) {
            dispatch('getHistory', {compact: compact});
        }

        api.get('/history', { params })
            .then(response => {
                if (response.data && response.data.date > history[0].actionDate) {
                    dispatch('getHistory', {compact: compact});
                }
            })
            .catch(() => {
                console.info(`No history record found`);
            });
    },
    updateHistory({dispatch}, queueItem) {
        // Update store's search queue item. (provided through websocket)
        dispatch('checkHistory', {});
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
