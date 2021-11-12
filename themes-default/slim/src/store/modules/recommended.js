import Vue from 'vue';
import {
    ADD_RECOMMENDED_SHOW,
    SET_RECOMMENDED_SHOWS,
    SET_RECOMMENDED_SHOWS_OPTIONS
} from '../mutation-types';

const IMDB = 10;
const ANIDB = 11;
const TRAKT = 12;
const ANILIST = 13;

const state = {
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
    [SET_RECOMMENDED_SHOWS](state, { shows, identifier }) {
        if (identifier) {
            // If an identifier has been passed, remove the old shows for this identifier.
            const source = Number(Object.keys(state.sourceToString).find(key => state.sourceToString[key] === identifier));
            state.shows = state.shows.filter(show => show.source !== source);
        } else {
            // No identifier passed, meaning remove all shows from store.
            state.shows = [];
        }
        state.shows = [...state.shows, ...shows];
    },
    [SET_RECOMMENDED_SHOWS_OPTIONS](state, data) {
        state.trakt.removedFromMedusa = data.trakt.removedFromMedusa;
        state.trakt.blacklistEnabled = data.trakt.blacklistEnabled;
        state.trakt.availableLists = data.trakt.availableLists;
        state.categories = data.categories;
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
    getRecommendedShows({ rootState, commit }, identifier) {
        identifier = identifier ? identifier : '';
        return rootState.auth.client.api.get(`/recommended/${identifier}`, { timeout: 60000 })
            .then(response => {
                commit(SET_RECOMMENDED_SHOWS, { shows: response.data.shows, identifier });
                commit(SET_RECOMMENDED_SHOWS_OPTIONS, response.data);
            });
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
