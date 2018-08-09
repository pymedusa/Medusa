import { ADD_CONFIG } from '../mutation-types';

const state = {
    values: {},
    anySets: {},
    presets: {},
    strings: {
        values: {},
        anySets: {},
        presets: {},
        cssClass: {}
    }
};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'qualities') {
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
