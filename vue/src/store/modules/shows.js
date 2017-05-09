import show from '../../api/show';
import * as types from '../mutation-types';

const state = {
    all: []
};

const getters = {
    allShows: state => state.all,
    showByName: (state, name) => {
        return state.all.find(show => show.name === name);
    },
    showById: (state, id) => {
        return state.all.find(show => show.id === id);
    }
};

const actions = {
    // Gets all the shows from Medusa
    getAllShows({commit}) {
        show.getShows(shows => {
            commit(types.RECEIVE_SHOWS, {shows});
        });
    },
    // Add a new Show to Medusa
    addShow({commit}, {id, name}) {
        // @TODO: This actually needs to hit the API instead of just returning the show object
        show.addShow({id, name}, (err, show) => {
            if (err) {
                return err;
            }
            commit(types.RECEIVE_SHOW, {show});
        });
    }
};

const mutations = {
    // Add multiple shows to the store
    [types.RECEIVE_SHOWS](state, {shows}) {
        state.all = shows;
    },
    // Add a single show to the store
    [types.RECEIVE_SHOW](state, {show}) {
        let foundShow = state.all.find(x => x.id === show.id);
        if (foundShow) {
            // Replace current store's version of the show with the new one
            foundShow = show;
        } else {
            state.all.push(show);
        }
    }
};

export default {
    state,
    getters,
    actions,
    mutations
};
