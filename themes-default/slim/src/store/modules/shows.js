import { ADD_SHOW } from '../mutation-types';

const state = {
    shows: []
};

const mutations = {
    [ADD_SHOW](state, show) {
        const { shows } = state;
        const showExists = shows.filter(({ id, indexer }) => id[indexer] === show.id[indexer]).length === 1;
        if (showExists) {
            state.shows[shows.indexOf(showExists)] = show;
        } else {
            state.shows.push(show);
        }
    }
};

const getters = {};

const actions = {
    getShow(context, { indexer, id }) {
        const { commit } = context;
        return api.get('/series/' + indexer + id).then(res => {
            commit(ADD_SHOW, res.data);
        });
    },
    getShows(context, shows) {
        const { commit, dispatch } = context;

        // If no shows are provided get all of them
        if (!shows) {
            return api.get('/series?limit=1000').then(res => {
                const shows = res.data;
                return shows.forEach(show => {
                    commit(ADD_SHOW, show);
                });
            });
        }

        return shows.forEach(show => dispatch('getShow', show));
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
