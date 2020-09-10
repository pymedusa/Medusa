import { ADD_CONFIG } from '../../mutation-types';

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
        rpcUrl: null,
        seedLocation: null,
        seedTime: null,
        username: null,
        password: null,
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
            password: null
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
            apiKey: null
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
