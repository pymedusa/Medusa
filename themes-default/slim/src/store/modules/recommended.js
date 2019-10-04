import Vue from 'vue';
import { api } from '../../api';
import { ADD_RECOMMENDED_SHOW } from '../mutation-types';

const state = {
    shows: [],
    trakt: {
        removedFromMedusa: [],
        blacklistEnabled: false
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
    }
};

const getters = {};

const actions = {
    /**
     * Get recommended shows from API and commit them to the store.
     *
     * @param {*} context - The store context.
     * @param {String} identifier - Identifier for the recommended shows list.
     * @Param {String} params - Filter params, for getting a specific recommended list type.
     * @returns {(undefined|Promise)} undefined if `shows` was provided or the API response if not.
     */
    getRecommendedShows(context, identifier, params) {
        const { commit } = context;
        params = {};

        identifier = identifier ? identifier : '';
        return api.get('/recommended/' + identifier, { params }).then(res => {
            const { data } = res;
            state.trakt.removedFromMedusa = data.trakt.removedFromMedusa;
            state.trakt.blacklistEnabled = data.trakt.blacklistEnabled;
            if (data.shows && data.shows.length > 0) {
                return data.shows.forEach(show => {
                    commit(ADD_RECOMMENDED_SHOW, show);
                });
            }
            return [];
        });
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
