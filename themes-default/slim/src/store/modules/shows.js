import Vue from 'vue';
import { api } from '../../api';
import { ADD_SHOW } from '../mutation-types';

const state = {
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

/**
 * An object representing request parameters for getting a show from the API.
 *
 * @typedef {Object} ShowParameteres
 * @property {string} indexer - The indexer name (e.g. `tvdb`)
 * @property {string} id - The show ID on the indexer (e.g. `12345`)
 * @property {boolean} detailed - Whether to fetch detailed information (seasons & episodes)
 * @property {boolean} fetch - Whether to fetch external information (for example AniDB release groups)
 */
const actions = {
    /**
     * Get show from API and commit it to the store.
     *
     * @param {*} context - The store context.
     * @param {ShowParameteres} parameters - Request parameters.
     * @returns {Promise} The API response.
     */
    getShow(context, { indexer, id, detailed, fetch }) {
        const { commit } = context;
        const params = {};
        if (detailed !== undefined) {
            params.detailed = Boolean(detailed);
        }
        if (fetch !== undefined) {
            params.fetch = Boolean(fetch);
        }
        return api.get('/series/' + indexer + id, { params }).then(res => {
            commit(ADD_SHOW, res.data);
        });
    },
    /**
     * Get shows from API and commit them to the store.
     *
     * @param {*} context - The store context.
     * @param {ShowParameteres[]} shows - Shows to get. If not provided, gets the first 10k shows.
     * @returns {(undefined|Promise)} undefined if `shows` was provided or the API response if not.
     */
    getShows(context, shows) {
        const { commit, dispatch } = context;

        // If no shows are provided get the first 10k
        if (!shows) {
            const params = {
                limit: 10000
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
    /**
     * Add a new show to the API and commit it to the store.
     *
     * @param {*} context - The store context.
     * @param {ShowParameteres} show - Show to add.
     * @returns {(undefined|Promise)} undefined if `shows` was provided or the API response if not.
     */
    addShow(context, show) {
        const { commit } = context;
        debugger;
        return api.post('/series', show).then(res => {
            commit(ADD_SHOW, show);
        });
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
