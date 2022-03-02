import Vue from 'vue';
import { api } from '../../api';
import {
    ADD_RECOMMENDED_SHOW,
    SET_RECOMMENDED_SHOWS,
    SET_RECOMMENDED_SHOWS_TRAKT_REMOVED,
    SET_RECOMMENDED_SHOWS_CATEGORIES
} from '../mutation-types';

const IMDB = 10;
const ANIDB = 11;
const TRAKT = 12;
const ANILIST = 13;

const state = {
    limit: 500,
    page: {
        [IMDB]: 1,
        [ANIDB]: 1,
        [TRAKT]: 1,
        [ANILIST]: 1
    },
    shows: [],
    trakt: {
        removedFromMedusa: [],
        blacklistEnabled: false,
        availableLists: []
    },
    categories: {},
    externals: {
        IMDB,
        ANIDB,
        TRAKT,
        ANILIST
    },
    sourceToString: {
        [IMDB]: 'imdb',
        [ANIDB]: 'anidb',
        [TRAKT]: 'trakt',
        [ANILIST]: 'anilist'
    }
};

const mutations = {
    [ADD_RECOMMENDED_SHOW](state, show) {
        const existingShow = state.shows.find(({ seriesId, source }) => Number(show.seriesId[show.source]) === Number(seriesId[source]));

        if (!existingShow) {
            console.debug(`Adding ${show.title || show.source + String(show.seriesId)} as it wasn't found in the shows array`, show);
            state.shows.push(show);
            return;
        }

        // Merge new recommended show object over old one
        // this allows detailed queries to update the record
        // without the non-detailed removing the extra data
        console.debug(`Found ${show.title || show.source + String(show.seriesId)} in shows array attempting merge`);
        const newShow = {
            ...existingShow,
            ...show
        };

        // Update state
        Vue.set(state.shows, state.shows.indexOf(existingShow), newShow);
        console.debug(`Merged ${newShow.title || newShow.source + String(newShow.seriesId)}`, newShow);
    },
    [SET_RECOMMENDED_SHOWS](state, { shows, source }) {
        // if (identifier) {
        //     // If an identifier has been passed, remove the old shows for this identifier.
        //     const source = Number(Object.keys(state.sourceToString).find(key => state.sourceToString[key] === identifier));
        //     state.shows = state.shows.filter(show => show.source !== source);
        // } else {
        //     // No identifier passed, meaning remove all shows from store.
        //     state.shows = [];
        // }
        if (shows.length < state.limit) {
            state.page[source] = -1;
        }
        state.shows = [...state.shows, ...shows];
    },
    [SET_RECOMMENDED_SHOWS_TRAKT_REMOVED](state, data) {
        state.trakt.removedFromMedusa = data.removedFromMedusa;
        state.trakt.blacklistEnabled = data.blacklistEnabled;
        state.trakt.availableLists = data.availableLists;
    },
    [SET_RECOMMENDED_SHOWS_CATEGORIES](state, data) {
        state.categories = data;
    },
    increasePage(state, source) {
        state.page[source] += 1;
    }
};

const getters = {};

const actions = {
    /**
     * Get recommended shows from API and commit them to the store.
     *
     * @param {*} context - The store context.
     * @param {String} identifier - Identifier for the recommended shows list.
     * @returns {(undefined|Promise)} undefined if `shows` was provided or the API response if not.
     */
    getRecommendedShows({ state, commit }, source) {
        if (state.page[source] === -1) {
            return;
        }
        const identifier = source ? state.sourceToString[source] : '';
        const { page } = state;
        return api.get(`/recommended/${identifier}?page=${page[source]}&limit=${state.limit}`, { timeout: 60000 })
            .then(response => {
                commit(SET_RECOMMENDED_SHOWS, { shows: response.data, source });
            });
    },
    getRecommendedShowsOptions({ commit }) {
        api.get('/recommended/trakt/removed', { timeout: 60000 })
            .then(response => {
                commit(SET_RECOMMENDED_SHOWS_TRAKT_REMOVED, response.data);
            });
        api.get('/recommended/categories', { timeout: 60000 })
            .then(response => {
                commit(SET_RECOMMENDED_SHOWS_CATEGORIES, response.data);
            });
    },
    getMoreShows({ commit, dispatch }, source) {
        commit('increasePage', source);
        dispatch('getRecommendedShows', source);
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
