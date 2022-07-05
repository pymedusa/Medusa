import {
    AUTHENTICATE,
    CONNECT,
    LOGIN_PENDING,
    LOGIN_SUCCESS,
    LOGIN_FAILED,
    LOGOUT,
    REFRESH_TOKEN,
    REMOVE_AUTH_ERROR
} from '../mutation-types';
import ApiClient from '../../api';
import VueJwtDecode from 'vue-jwt-decode';

const state = {
    isAuthenticated: false,
    isConnected: false,
    user: {},
    tokens: {
        access: null,
        refresh: null
    },
    error: null,
    client: null,
    apiKey: null,
    webRoot: null
};

const mutations = {
    [LOGIN_PENDING]() { },
    [LOGIN_SUCCESS](state, user) {
        state.user.username = user.username;
        state.user.group = user.group;
        state.apiKey = user.apiKey;
        state.webRoot = user.webRoot;
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
    [REMOVE_AUTH_ERROR]() {},
    [AUTHENTICATE](state, client) {
        state.client = client;
        state.tokens.access = client.token;
    },
    [CONNECT](state, value) {
        state.isConnected = value;
    }
};

const getters = {};

const actions = {
    login({ commit, state }) {
        commit(LOGIN_PENDING);

        // Check if we got a token from the /token call.
        const { client } = state;
        const { token } = client;
        if (!token) {
            commit(LOGIN_FAILED, { error: 'Missing token' });
            return { success: false, error: 'Missing token' };
        }

        const credentials = VueJwtDecode.decode(token);

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
    },
    auth({ commit }) {
        // Get the JWT token
        return new Promise(resolve => {
            const apiClient = new ApiClient();
            apiClient.getToken()
                .then(() => {
                    commit(AUTHENTICATE, apiClient);
                    resolve();
                });
        });
    },
    connect({ commit }, connected) {
        commit(CONNECT, connected);
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
