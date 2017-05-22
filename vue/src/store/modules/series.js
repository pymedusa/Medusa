import series from '../../api/series';
import * as types from '../mutation-types';
import {seriesLogger as log} from '../../log';

const state = {
    all: []
};

const getters = {
    allSeries: state => state.all,
    seriesByName: (state, name) => {
        return state.all.find(series => {
            if (series) {
                return series.name === name;
            }
            return null;
        });
    },
    seriesById: (state, id) => {
        return state.all.find(series => {
            if (series) {
                return series.id === id;
            }
            return null;
        });
    }
};

const actions = {
    // Gets all the series from Medusa
    getAllSeries({commit}) {
        series.getAllSeries(data => {
            log.info(data);
            commit(types.RECEIVE_SERIES, {data});
        });
    },
    // Add a new series to Medusa
    addSeries({commit}, {id, name}) {
        // @TODO: This actually needs to hit the API instead of just returning the series object
        series.addSeries({id, name}, (err, data) => {
            if (err) {
                return err;
            }
            commit(types.RECEIVE_SERIES, {data});
        });
    }
};

const mutations = {
    // Add multiple series to the store
    [types.RECEIVE_SERIES](state, {series}) {
        state.all = series;
    },
    // Add a single series to the store
    [types.RECEIVE_SERIES](state, {series}) {
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
