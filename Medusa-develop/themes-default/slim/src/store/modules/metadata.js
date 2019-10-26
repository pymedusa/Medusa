import { ADD_CONFIG } from '../mutation-types';

const state = {
    metadataProviders: {}
};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'metadata') {
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
