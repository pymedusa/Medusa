import Vue from 'vue';

import { api } from '../../api';
import { ADD_HISTORY, ADD_SHOW_HISTORY, ADD_SHOW_EPISODE_HISTORY, INITIALIZE_HISTORY_STORE } from '../mutation-types';
import { episodeToSlug } from '../../utils/core';

const state = {
    remote: {
        rows: [],
        totalRows: 0,
        page: 1,
        perPage: 25
    },
    remoteCompact: {
        rows: [],
        totalRows: 0,
        page: 1,
        perPage: 25
    },
    episodeHistory: {},
    historyLast: null,
    historyLastCompact: null,
    loading: false
};

const mutations = {
    [ADD_HISTORY](state, { history, compact }) {
        // Only evaluate compact once.
        const historyKey = compact ? 'remoteCompact' : 'remote';

        // // Concat both
        // const concatHistory = [...state[historyKey].rows, ...history];

        // // Filter out duplicates
        // const filteredHistory = concatHistory.filter((historyObj, index, self) =>
        //     index === self.findIndex(t => (t.id === historyObj.id))
        // );

        // Update state
        Vue.set(state[historyKey], 'rows', history);

        // Update localStorage
        try {
            localStorage.setItem(historyKey, JSON.stringify(state[historyKey]));
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
    },
    setRemoteTotal(state, {total, compact=false}) {
        state[compact ? 'remoteCompact' : 'remote'].totalRows = total;
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
        let url = '/history';
        const page = args ? args.page : 1;
        const limit = args ? args.perPage : 1000;
        const showSlug = args ? args.showSlug : undefined;
        const compact = args ? args.compact : undefined;

        const params = {
            page,
            limit
        };

        if (showSlug) {
            url = `${url}/${showSlug}`;
        }

        if (compact) {
            params.compact = true;
        }

        // let page = 0;

        commit('setLoading', true);
        let response = null;
        try {
            response = await api.get(url, { params }); // eslint-disable-line no-await-in-loop
            if (response) {
                commit('setRemoteTotal', { total: Number(response.headers['x-pagination-count']), compact });
                if (showSlug) {
                    commit(ADD_SHOW_HISTORY, { showSlug, history: response.data, compact });
                } else {
                    commit(ADD_HISTORY, { history: response.data, compact });
                }
            }
        } catch (error) {
            if (error.response && error.response.status === 404) {
                console.debug(`No history available${showSlug ? ' for show ' + showSlug : ''}`);
            }
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
