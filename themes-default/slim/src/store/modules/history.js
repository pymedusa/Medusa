import Vue from 'vue';

import { api } from '../../api';
import { ADD_HISTORY } from '../mutation-types';

const state = {
    history: []
};

const mutations = {
    [ADD_HISTORY](state, history) {
        // Maybe we can just check the last id. And if the id's are newer, add them. Less fancy, much more fast.
        const existingHistory = state.history.find(row => history.id === row.id);

        if (!existingHistory) {
            state.history.push(history);
            return;
        }

        // Merge new show object over old one
        // this allows detailed queries to update the record
        // without the non-detailed removing the extra data
        const newHistory = {
            ...existingHistory,
            ...history
        };

        // Update state
        Vue.set(state.shows, state.shows.indexOf(existingHistory), newHistory);
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
     * Get shows from API and commit them to the store.
     *
     * @param {*} context - The store context.
     * @param {(ShowIdentifier&ShowGetParameters)[]} shows Shows to get. If not provided, gets the first 1k shows.
     * @returns {undefined|Promise} undefined if `shows` was provided or the API response if not.
     */
    async getHistory(context) {
        const { commit } = context;
        const limit = 1000;

        let lastPage = false;
        let response = null;
        while (lastPage) {
            response = await api.get(`/history`); // No way around this.
            response.data.forEach(history => {
                commit(ADD_HISTORY, history);
            });

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
