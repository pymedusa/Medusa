import Vue from 'vue';

import { api } from '../../api';
import { ADD_HISTORY } from '../mutation-types';

const state = {
    history: [],
    page: 0
};

const mutations = {
    [ADD_HISTORY](state, history) {
        // Update state
        state.history.push(...history);
    }
};

const getters = {
    getShowHistoryBySlug: state => showSlug => state.history.find(history => history.series === showSlug)
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
    getShowHistory(context, { slug }) {
        return new Promise((resolve, reject) => {
            const { commit } = context;

            api.get(`/history/${slug}`)
                .then(res => {
                    commit(ADD_HISTORY, res.data);
                    resolve(res.data);
                })
                .catch(error => {
                    reject(error);
                });
        });
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
            // response.data.forEach(history => {
            //     commit(ADD_HISTORY, history);
            // });
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
