import {config} from '../../api/';
import * as types from '../mutation-types';

const state = {
    config: {},
    error: null,
    stack: null
};

const getters = {
    config: state => state.config,
    statError: state => state.error,
    statStack: state => state.stack
};

const actions = {
    getConfig({commit}) {
        return new Promise((resolve, reject) => {
            config.getConfig().then(({config}) => {
                commit(types.CONFIG_RECIEVE_MULTIPLE, {config});
                resolve({config});
            }).catch(err => {
                const {error, stack} = err.response.data;
                commit(types.CONFIG_FAILURE, {error, stack});
                reject(err);
            });
        });
    }
};

const mutations = {
    // Add config to the store
    [types.CONFIG_RECIEVE_MULTIPLE](state, {config}) {
        state.config = config;
    },
    [types.CONFIG_FAILURE](state, {error, stack}) {
        state.error = error;
        state.stack = stack;
    }
};

export default {
    state,
    getters,
    actions,
    mutations
};
