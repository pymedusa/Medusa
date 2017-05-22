import {series} from '../../api';
import * as types from '../mutation-types';

const state = {
    all: []
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
    }
};

const actions = {
    // Gets all the series from Medusa
    getAllSeries({commit}) {
        series.getAllSeries().then(({series}) => {
            commit(types.SERIES_RECIEVE_MULTIPLE, {series});
        });
    }
};

const mutations = {
    // Add multiple series to the store
    [types.SERIES_RECIEVE_MULTIPLE](state, {series}) {
        state.all = series;
    },
    // Add a single series to the store
    [types.SERIES_RECIEVE_SINGULAR](state, {series}) {
        let foundSeries = state.all.find(x => x.id === series.id);
        if (foundSeries) {
            // Replace current store's version of the series with the new one
            foundSeries = series;
        } else {
            state.all.push(series);
        }
    }
};

export default {
    state,
    getters,
    actions,
    mutations
};
