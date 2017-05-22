import {series} from '../../api';
import * as types from '../mutation-types';

const state = {
    all: [],
    recent: []
};

const getters = {
    allSeries: state => state.all,
    seriesEnded: state => {
        return state.all.filter(series => {
            return series.status.toLowerCase() === 'ended';
        });
    },
    seriesActive: state => {
        return state.all.filter(series => {
            return series.status.toLowerCase() === 'active';
        });
    },
    recentSeries: state => state.recent
};

const actions = {
    // Gets all the series from Medusa
    getAllSeries({commit}) {
        return new Promise((resolve, reject) => {
            series.getAllSeries().then(({series}) => {
                commit(types.SERIES_RECIEVE_MULTIPLE, {series});
                resolve({series});
            }).catch(reject);
        });
    },
    getRecentShows({commit}) {
        return new Promise(resolve => {
            const recentShows = JSON.parse(localStorage.getItem('recentSeries'));
            commit(types.SERIES_RECENT_MULTIPLE, {series: recentShows});
            resolve({series: recentShows});
        });
    }
};

const mutations = {
    // Add a single series to the store
    [types.SERIES_RECIEVE_SINGULAR](state, {series}) {
        let foundSeries = state.all.find(x => x.id === series.id);
        if (foundSeries) {
            // Replace current store's version of the series with the new one
            foundSeries = series;
        } else {
            state.all.push(series);
        }
    },
    // Add multiple series to the store
    [types.SERIES_RECIEVE_MULTIPLE](state, {series}) {
        state.all = series;
    },
    [types.SERIES_RECENT_SINGULAR](state, {series}) {
        state.recent.pop();
        state.recent.unshift(series);
        localStorage.setItem('recentSeries', JSON.stringify(state.recent));
    },
    [types.SERIES_RECENT_MULTIPLE](state, {series}) {
        state.recent = series;
        localStorage.setItem('recentSeries', JSON.stringify(state.recent));
    }
};

export default {
    state,
    getters,
    actions,
    mutations
};
