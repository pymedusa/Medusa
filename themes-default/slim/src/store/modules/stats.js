import { SET_STATS, SET_MAX_DOWNLOAD_COUNT } from '../mutation-types';
import { api } from '../../api';

const state = {
    stats: [],
    maxDownloadCount: null
};

const mutations = {
    [SET_STATS](state, stats) {
        state.stats = stats;
    },
    [SET_MAX_DOWNLOAD_COUNT](state, downloadCount) {
        state.maxDownloadCount = downloadCount;
    }
};

const getters = {};

const actions = {
    getStats({ commit }) {
        return api.get('/stats').then(res => {
            commit(SET_STATS, res.data.seriesStat);
            commit(SET_MAX_DOWNLOAD_COUNT, res.data.maxDownloadCount);
            return res.data;
        });
    }
};

export default {
    namespaced: true,
    state,
    mutations,
    getters,
    actions
};
