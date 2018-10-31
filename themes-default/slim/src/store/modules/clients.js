import { ADD_CONFIG } from '../mutation-types';

const state = {
    torrents: {
        authType: null,
        dir: null,
        enabled: null,
        highBandwidth: null,
        host: null,
        label: null,
        labelAnime: null,
        method: null,
        path: null,
        paused: null,
        rpcurl: null,
        seedLocation: null,
        seedTime: null,
        username: null,
        verifySSL: null,
        testStatus: 'Click below to test'
    },
    nzb: {
        enabled: null,
        method: null,
        nzbget: {
            category: null,
            categoryAnime: null,
            categoryAnimeBacklog: null,
            categoryBacklog: null,
            host: null,
            priority: null,
            useHttps: null,
            username: null,
            priorityOptions: {
                'Very low': -100,
                'Low': -50,
                'Normal': 0,
                'High': 50,
                'Very high': 100,
                'Force': 900
            },
            testStatus: 'Click below to test'
        },
        sabnzbd: {
            category: null,
            forced: null,
            categoryAnime: null,
            categoryBacklog: null,
            categoryAnimeBacklog: null,
            host: null,
            username: null,
            password: null,
            apiKey: null,
            testStatus: 'Click below to test'
        }
    }
};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'clients') {
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
