import Vue from 'vue';
import { ADD_SHOW } from '../mutation-types';

const state = {
    // Currently loaded show
    show: {},
    shows: []
};

const mutations = {
    [ADD_SHOW](state, show) {
        const existingShow = state.shows.find(({ id, indexer }) => Number(show.id[show.indexer]) === Number(id[indexer]));

        if (!existingShow) {
            console.debug(`Adding ${show.title || show.indexer + String(show.id)} as it wasn't found in the shows array`, show);
            state.shows.push(show);
            return;
        }

        // Merge new show object over old one
        // this allows detailed queries to update the record
        // without the non-detailed removing the extra data
        console.debug(`Found ${show.title || show.indexer + String(show.id)} in shows array attempting merge`);
        const newShow = {
            ...existingShow,
            ...show
        };

        // Update state
        Vue.set(state.shows, state.shows.indexOf(existingShow), newShow);
        console.debug(`Merged ${newShow.title || newShow.indexer + String(newShow.id)}`, newShow);
    }
};

const getters = {
    getShowById: state => ({ id, indexer }) => state.shows.find(show => Number(show.id[indexer]) === Number(id)),
    getShowByTitle: state => title => state.shows.find(show => show.title === title),
    getSeason: state => ({ id, indexer, season }) => {
        const show = state.shows.find(show => Number(show.id[indexer]) === Number(id));
        return show && show.seasons ? show.seasons[season] : undefined;
    },
    getEpisode: state => ({ id, indexer, season, episode }) => {
        const show = state.shows.find(show => Number(show.id[indexer]) === Number(id));
        return show && show.seasons && show.seasons[season] ? show.seasons[season][episode] : undefined;
    }
};

const actions = {
    getShow(context, { indexer, id, detailed }) {
        const { commit } = context;
        const params = {};
        if (detailed !== undefined) {
            params.detailed = Boolean(detailed);
        }
        return api.get('/series/' + indexer + id, { params }).then(res => {
            commit(ADD_SHOW, res.data);
        });
    },
    getShows(context, shows) {
        const { commit, dispatch } = context;

        // If no shows are provided get the first 1000
        if (!shows) {
            const params = {
                limit: 1000
            };
            return api.get('/series', { params }).then(res => {
                const shows = res.data;
                return shows.forEach(show => {
                    commit(ADD_SHOW, show);
                });
            });
        }

        return shows.forEach(show => dispatch('getShow', show));
    },
    setShow(context, { indexer, id, data, save }) {
        const { commit, dispatch } = context;

        // Just update local store
        if (!save) {
            return api.get('/series/' + indexer + id).then(response => {
                const show = Object.assign({}, response.data, data);
                commit(ADD_SHOW, show);
            });
        }

        // Send to API
        return api.patch('series/' + indexer + id, data).then(setTimeout(() => dispatch('getShow', { indexer, id }), 500));
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
