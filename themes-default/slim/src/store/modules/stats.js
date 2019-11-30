import { api } from '../../api';
import { ADD_STATS, SET_STATS, SET_MAX_DOWNLOAD_COUNT } from '../mutation-types';

const state = {
    overall: {
        episodes: {
            downloaded: null,
            snatched: null,
            total: null
        },
        shows: {
            active: null,
            total: null
        }
    },
    show: {
        maxDownloadCount: 0,
        stats: []
    }
};

const mutations = {
    [ADD_STATS](state, payload) {
        const { type, stats } = payload;
        state[type] = Object.assign(state[type], stats);
    },
    [SET_STATS](state, stats) {
        state.stats = stats;
    },
    [SET_MAX_DOWNLOAD_COUNT](state, downloadCount) {
        state.maxDownloadCount = downloadCount;
    }
};

const getters = {};

const actions = {
    getStats(context, type) {
        const { commit } = context;
        return api.get(`/stats/${(type || '')}`).then(res => {
            commit(ADD_STATS, {
                type: (type || 'overall'),
                stats: res.data
            });
        });
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
