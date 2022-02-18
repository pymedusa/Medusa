import {
    LOGIN_PENDING,
    LOGIN_SUCCESS,
    LOGIN_FAILED,
    LOGOUT,
    REFRESH_TOKEN,
    REMOVE_AUTH_ERROR
} from '../mutation-types';

const state = {
    isAuthenticated: false,
    user: {},
    tokens: {
        access: null,
        refresh: null
    },
    error: null
};

const mutations = {
    [LOGIN_PENDING]() { },
    [LOGIN_SUCCESS](state, user) {
        state.user = user;
        state.isAuthenticated = true;
        state.error = null;
    },
    [LOGIN_FAILED](state, { error }) {
        state.user = {};
        state.isAuthenticated = false;
        state.error = error;
    },
    [LOGOUT](state) {
        state.user = {};
        state.isAuthenticated = false;
        state.error = null;
    },
    [REFRESH_TOKEN]() {},
    [REMOVE_AUTH_ERROR]() {}
};

const getters = {};

const actions = {
    login(context, credentials) {
        const { commit } = context;
        commit(LOGIN_PENDING);

        // @TODO: Add real JWT login
        const apiLogin = credentials => Promise.resolve(credentials);

        return apiLogin(credentials).then(user => {
            commit(LOGIN_SUCCESS, user);
            return { success: true };
        }).catch(error => {
            commit(LOGIN_FAILED, { error, credentials });
            return { success: false, error };
        });
    },
    logout(context) {
        const { commit } = context;
        commit(LOGOUT);
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
