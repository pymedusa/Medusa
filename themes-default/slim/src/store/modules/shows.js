import Vue from 'vue';

import { api } from '../../api';
import { wait } from '../../utils/core';
import { ADD_SHOW } from '../mutation-types';

/**
 * @typedef {object} ShowIdentifier
 * @property {string} indexer The indexer name (e.g. `tvdb`)
 * @property {number} id The show ID on the indexer (e.g. `12345`)
 */

const state = {
    shows: [],
    currentShow: {
        indexer: null,
        id: null
    }
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
    },
    currentShow(state, { indexer, id }) {
        state.currentShow.indexer = indexer;
        state.currentShow.id = id;
    }
};

const getters = {
    getShowById: state => {
        /**
         * Get a show from the loaded shows state, identified by show ID and indexer name.
         *
         * @param {ShowIdentifier} show Show identifiers.
         * @returns {object|undefined} Show object or undefined if not found.
         */
        const getShowById = ({ id, indexer }) => state.shows.find(show => Number(show.id[indexer]) === Number(id));
        return getShowById;
    },
    getShowByTitle: state => title => state.shows.find(show => show.title === title),
    getSeason: state => ({ id, indexer, season }) => {
        const show = state.shows.find(show => Number(show.id[indexer]) === Number(id));
        return show && show.seasons ? show.seasons[season] : undefined;
    },
    getEpisode: state => ({ id, indexer, season, episode }) => {
        const show = state.shows.find(show => Number(show.id[indexer]) === Number(id));
        return show && show.seasons && show.seasons[season] ? show.seasons[season][episode] : undefined;
    },
    getCurrentShow: (state, getters, rootState) => {
        return state.shows.find(show => Number(show.id[state.currentShow.indexer]) === Number(state.currentShow.id)) || rootState.defaults.show;
    }
};

/**
 * An object representing request parameters for getting a show from the API.
 *
 * @typedef {object} ShowGetParameters
 * @property {boolean} detailed Fetch detailed information? (seasons & episodes)
 */

const actions = {
    /**
     * Get show from API and commit it to the store.
     *
     * @param {*} context The store context.
     * @param {ShowIdentifier&ShowGetParameters} parameters Request parameters.
     * @returns {Promise} The API response.
     */
    getShow(context, { indexer, id, detailed }) {
        return new Promise((resolve, reject) => {
            const { commit } = context;
            const params = {};

            if (detailed !== undefined) {
                params.detailed = Boolean(detailed);
            }

            api.get('/series/' + indexer + id, { params })
                .then(res => {
                    commit(ADD_SHOW, res.data);
                    resolve(res.data);
                })
                .catch(error => {
                    reject(error);
                });
        });
    },
    /**
     * Get shows from API and commit them to the store.
     *
     * @param {*} context - The store context.
     * @param {(ShowIdentifier&ShowGetParameters)[]} shows Shows to get. If not provided, gets the first 1k shows.
     * @returns {undefined|Promise} undefined if `shows` was provided or the API response if not.
     */
    getShows(context, shows) {
        const { commit, dispatch } = context;

        // If no shows are provided get the first 1000
        if (!shows) {
            return (() => {
                const limit = 1000;
                const page = 1;
                const params = {
                    limit,
                    page
                };

                // Get first page
                api.get('/series', { params })
                    .then(response => {
                        const totalPages = Number(response.headers['x-pagination-total']);
                        response.data.forEach(show => {
                            commit(ADD_SHOW, show);
                        });

                        // Optionally get additional pages
                        const pageRequests = [];
                        for (let page = 2; page <= totalPages; page++) {
                            const newPage = { page };
                            newPage.limit = params.limit;
                            pageRequests.push(api.get('/series', { params: newPage }).then(response => {
                                response.data.forEach(show => {
                                    commit(ADD_SHOW, show);
                                });
                            }));
                        }

                        return Promise.all(pageRequests);
                    })
                    .catch(() => {
                        console.log('Could not retrieve a list of shows');
                    });
            })();
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

        // Send to API and fetch the updated show
        return api.patch('series/' + indexer + id, data).then(() => {
            return wait(500).then(() => dispatch('getShow', { indexer, id }));
        });
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
