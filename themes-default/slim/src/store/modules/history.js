import Vue from 'vue';
import { ADD_HISTORY, ADD_HISTORY_ROW, ADD_SHOW_HISTORY, ADD_SHOW_EPISODE_HISTORY } from '../mutation-types';
import { episodeToSlug } from '../../utils/core';

const state = {
    remote: {
        rows: [],
        totalRows: 0,
        page: 1,
        perPage: 25,
        sort: [{
            field: 'date',
            type: 'desc'
        }],
        filter: null
    },
    remoteCompact: {
        rows: [],
        totalRows: 0,
        page: 1,
        perPage: 25,
        sort: [{
            field: 'date',
            type: 'desc'
        }],
        filter: null
    },
    episodeHistory: {},
    historyLast: null,
    historyLastCompact: null,
    loading: false
};

const mutations = {
    [ADD_HISTORY_ROW](state, { history, compact }) {
        // Only evaluate compact once.
        const historyKey = compact ? 'remoteCompact' : 'remote';

        // Update state, add one item at the top.
        state[historyKey].rows.unshift(history);
    },
    [ADD_HISTORY](state, { history, compact }) {
        // Only evaluate compact once.
        const historyKey = compact ? 'remoteCompact' : 'remote';

        // Update state
        Vue.set(state[historyKey], 'rows', history);
    },
    [ADD_SHOW_HISTORY](state, { showSlug, history }) {
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
    setLoading(state, value) {
        state.loading = value;
    },
    setRemoteTotal(state, { total, compact = false }) {
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
                    .slice()
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
    async getShowHistory({ rootState, commit }, { slug }) {
        const response = await rootState.auth.client.api.get(`/history/${slug}`);
        if (response.data.length > 0) {
            commit(ADD_SHOW_HISTORY, { showSlug: slug, history: response.data });
        }
    },
    /**
     * Get detailed history from API and commit them to the store.
     *
     * @param {*} context - The store context.
     * @param {object} args - arguments.
     */
    async getHistory({ rootState, commit }, args) {
        let url = '/history';
        const page = args?.page || 1;
        const limit = args?.perPage || 1000;
        let sort = args?.sort || [{ field: 'date', type: 'desc' }];
        const filter = args?.filter || {};
        const showSlug = args?.showSlug;
        const compact = args?.compact;

        const params = {
            page,
            limit
        };

        if (sort) {
            if (!Array.isArray(sort)) {
                sort = [sort];
            }
            params.sort = JSON.stringify(sort);
        }

        if (filter) {
            params.filter = JSON.stringify(filter);
        }

        if (showSlug) {
            url = `${url}/${showSlug}`;
        }

        if (compact) {
            params.compact = true;
        }

        commit('setLoading', true);
        let response = null;
        try {
            response = await rootState.auth.client.api.get(url, { params }); // eslint-disable-line no-await-in-loop
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
    getShowEpisodeHistory({ rootState, commit }, { showSlug, episodeSlug }) {
        return new Promise(resolve => {
            rootState.auth.client.api.get(`/history/${showSlug}/episode/${episodeSlug}`)
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
    updateHistory({ rootState, commit }, data) {
        // Update store's search queue item. (provided through websocket)
        const compact = rootState.config.layout.history === 'compact';
        // We can't live update the compact layout, as it requires to aggregate the data.
        if (compact) {
            return;
        }
        commit(ADD_HISTORY_ROW, { history: data });
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
