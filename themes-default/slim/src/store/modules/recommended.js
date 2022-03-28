import Vue from 'vue';
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
const ALL = -1;

const state = {
    limit: 1000,
    page: {
        [IMDB]: 1,
        [ANIDB]: 1,
        [TRAKT]: 1,
        [ANILIST]: 1,
        [ALL]: 1
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
    },
    resetPage(state, source) {
        state.page[source] = 1;
    }
};

const getters = {};

const actions = {
    /**
     * Get recommended shows from API and commit them to the store.
     *
     * @param {*} context - The store context.
     * @param {String} source - Identifier for the recommended shows list.
     * @returns {(undefined|Promise)} undefined if `shows` was provided or the API response if not.
     */
    getRecommendedShows({ rootState, state, commit }, source) {
        if (state.page[source] === -1) {
            return;
        }
        const identifier = source ? state.sourceToString[source] : '';
        const { page } = state;
        return rootState.auth.client.api.get(`/recommended/${identifier}?page=${page[source]}&limit=${state.limit}`, { timeout: 90000 })
            .then(response => {
                commit(SET_RECOMMENDED_SHOWS, { shows: response.data, source });
            });
    },
    getRecommendedShowsOptions({ rootState, commit }) {
        rootState.auth.client.api.get('/recommended/trakt/removed', { timeout: 60000 })
            .then(response => {
                commit(SET_RECOMMENDED_SHOWS_TRAKT_REMOVED, response.data);
            });
        rootState.auth.client.api.get('/recommended/categories', { timeout: 60000 })
            .then(response => {
                commit(SET_RECOMMENDED_SHOWS_CATEGORIES, response.data);
            });
    },
    /**
     * Get more recommended shows from the paginated api.
     *
     * This method is triggered through a manual user interaction,
     * clicking on a "Get More" button.
     *
     * @param {*} param - Commit and dispatch.
     * @param {*} source - Get a specific source (imdb, trakt, all, ..)
     * @returns {Promise} - A promise from the getRecommendedShows method.
     */
    getMoreShows({ commit, dispatch }, source) {
        commit('increasePage', source);
        return dispatch('getRecommendedShows', source);
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
