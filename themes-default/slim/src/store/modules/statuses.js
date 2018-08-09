import { ADD_CONFIG } from '../mutation-types';

const state = {
    values: {},
    strings: {}
};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'statuses') {
            state = Object.assign(state, config);
        }
    }
};

const getters = {};

const actions = {};

export default {
    state,
    mutations,
    getters,
    actions
};
