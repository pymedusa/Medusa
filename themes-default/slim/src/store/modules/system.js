import { ADD_CONFIG } from '../mutation-types';

const state = {
    memoryUsage: null,
    schedulers: [],
    showQueue: []
};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'system') {
            state = Object.assign(state, config);
        }
    }
};

const getters = {
    // Get a scheduler object using a key
    getScheduler: state => key => {
        return state.schedulers.find(scheduler => key === scheduler.key);
    }
};

const actions = {};

export default {
    state,
    mutations,
    getters,
    actions
};
