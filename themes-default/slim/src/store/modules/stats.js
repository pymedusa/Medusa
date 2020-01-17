import { api } from '../../api';
import { ADD_STATS } from '../mutation-types';

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
    }
};

const mutations = {
    [ADD_STATS](state, payload) {
        const { type, stats } = payload;
        state[type] = Object.assign(state[type], stats);
    }
};

const getters = {};

const actions = {
    getStats(context, type) {
        const { commit } = context;
        return api.get('/stats/' + (type || '')).then(res => {
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
