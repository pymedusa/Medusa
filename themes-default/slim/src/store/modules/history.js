import Vue from 'vue';

import { api } from '../../api';
import { ADD_HISTORY, ADD_SHOW_HISTORY } from '../mutation-types';

const state = {
    history: [],
    page: 0,
    showHistory: {}
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
    }
};

const getters = {
    getShowHistoryBySlug: state => showSlug => state.showHistory[showSlug]
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
            response = await api.get(`/history`, { params }); // No way around this.
            commit(ADD_HISTORY, response.data);

            if (response.data.length < limit) {
                lastPage = true;
            }
        }
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
