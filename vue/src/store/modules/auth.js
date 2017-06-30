import {auth} from '../../api/';
import * as types from '../mutation-types';

const state = {
    isAuthenticated: false,
    error: null,
    stack: null
};

const getters = {
    isAuthenticated: state => state.isAuthenticated,
    authError: state => state.error,
    authStack: state => state.stack
};

const actions = {
    signin({commit}, {username, password}) {
        return new Promise((resolve, reject) => {
            auth.signin({username, password}).then(({token}) => {
                commit(types.AUTHENTICATION_SUCCESS, {token});
                resolve({token});
            }).catch(err => {
                const {error, stack} = err.response.data;
                commit(types.AUTHENTICATION_FAILURE, {error, stack});
                reject(err);
            });
        });
    },
    signout({commit}) {
        return new Promise(resolve => {
            commit(types.AUTHENTICATION_SIGNOUT);
            resolve();
        });
    },
    checkAuth({commit}) {
        return new Promise(resolve => {
            const token = localStorage.getItem('token');
            if (token) {
                commit(types.AUTHENTICATION_SUCCESS, {token});
                resolve({token});
            } else {
                commit(types.AUTHENTICATION_SIGNOUT);
            }
        });
    }
};

const mutations = {
    [types.AUTHENTICATION_SUCCESS](state, {token}) {
        localStorage.setItem('token', token);
        state.isAuthenticated = true;
        state.error = null;
        state.stack = null;
    },
    [types.AUTHENTICATION_FAILURE](state, {error, stack}) {
        localStorage.removeItem('token');
        state.isAuthenticated = false;
        state.error = error;
        state.stack = stack;
    },
    [types.AUTHENTICATION_SIGNOUT](state) {
        localStorage.removeItem('token');
        state.isAuthenticated = false;
        state.error = null;
        state.stack = null;
    }
};

export default {
    state,
    getters,
    actions,
    mutations
};
