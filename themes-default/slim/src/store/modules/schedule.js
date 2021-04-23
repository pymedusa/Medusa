import Vue from 'vue';

import { api } from '../../api';
import { ADD_SCHEDULE } from '../mutation-types';

const state = {
    categories: ['later', 'missed', 'soon', 'today'],
    later: [],
    missed: [],
    soon: [],
    today: [],
    displayCategory: {
        later: false,
        missed: false,
        soon: true,
        today: true
    }
};

const mutations = {
    [ADD_SCHEDULE](state, schedule) {
        for (const category in schedule) {
            state[category] = schedule[category];
        }
    }
};

const getters = {
    getScheduleFlattened: state => {
        const flattendedSchedule = [];
        for (const category of state.categories) {
            const episodes = state[category];
            for (const episode of episodes) {
                episode.category = category;
            }
            flattendedSchedule.push(...episodes); 
        }
        return flattendedSchedule;
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
     * Get show schedule from API and commit it to the store.
     *
     * @param {*} context The store context.
     * @param {ShowIdentifier&ShowGetParameters} parameters Request parameters.
     * @returns {Promise} The API response.
     */
    async getSchedule({ commit, state }) {
        const params = {
            category: state.categories,
            paused: true
        };
        const response = await api.get(`/schedule`, { params });
        if (response.data) {
            commit(ADD_SCHEDULE, response.data);
        }
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
