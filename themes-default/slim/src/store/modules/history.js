import Vue from 'vue';

import { api } from '../../api';
import { ADD_HISTORY, ADD_SHOW_HISTORY, ADD_SHOW_EPISODE_HISTORY } from '../mutation-types';

const state = {
    history: [],
    page: 0,
    showHistory: {},
    episodeHistory: {}
};

const mutations = {
    [ADD_HISTORY](state, history) {
        // Update state
        state.history.push(...history);
    },
    [ADD_SHOW_HISTORY](state, { showSlug, history }) {
        // Keep an array of shows, with their history
        // Maybe we can just check the last id. And if the id's are newer, add them. Less fancy, much more fast.
        Vue.set(state.showHistory, showSlug, history);
    },
    [ADD_SHOW_EPISODE_HISTORY](state, { showSlug, episodeSlug, history }) {
        // Keep an object of shows, with their history per episode
        // Example: {tvdb1234: {s01e01: [history]}}

        if (!Object.keys(state.episodeHistory).includes(showSlug)) {
            Vue.set(state.episodeHistory, showSlug, {});
        }

        Vue.set(state.episodeHistory[showSlug], episodeSlug, history);
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
     * Get history from API and commit them to the store.
     *
     * @param {*} context - The store context.
     * @param {(ShowIdentifier&ShowGetParameters)[]} shows Shows to get. If not provided, gets the first 1k shows.
     * @returns {undefined|Promise} undefined if `shows` was provided or the API response if not.
     */
    async getHistory(context) {
        const { commit, state } = context;
        const limit = 1000;
        const params = { limit };

        let lastPage = false;
        let response = null;
        while (!lastPage) {
            state.page += 1;
            params.page = state.page;
            response = await api.get('/history', { params }); // eslint-disable-line no-await-in-loop
            commit(ADD_HISTORY, response.data);

            if (response.data.length < limit) {
                lastPage = true;
            }
        }
    },
    /**
     * Get episode history from API and commit it to the store.
     *
     * @param {*} context The store context.
     * @param {ShowIdentifier&ShowGetParameters} parameters Request parameters.
     * @returns {Promise} The API response.
     */
    async getShowEpisodeHistory(context, { showSlug, episodeSlug }) {
        const { commit } = context;

        try {
            const response = await api.get(`/history/${showSlug}/episode/${episodeSlug}`);
            if (response.data.length > 0) {
                commit(ADD_SHOW_EPISODE_HISTORY, { showSlug, episodeSlug, history: response.data });
            }
        } catch {
            console.warn(`No episode history found for show ${showSlug} and episode ${episodeSlug}`);
        }
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
