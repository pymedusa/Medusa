import Vue from 'vue';
import { api } from '../../api';
import { ADD_RECOMMENDED_SHOW } from '../mutation-types';

const state = {
    recommended: {
        shows: []
    }
};

const mutations = {
    [ADD_RECOMMENDED_SHOW](state, show) {
        const existingShow = state.recommended.shows.find(({ seriesId, source }) => Number(show.seriesId[show.source]) === Number(seriesId[source]));

        if (!existingShow) {
            console.debug(`Adding ${show.title || show.source + String(show.seriesId)} as it wasn't found in the shows array`, show);
            state.recommended.shows.push(show);
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
        Vue.set(state.recommended.shows, state.recommended.shows.indexOf(existingShow), newShow);
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
            const shows = res.data;
            return shows.forEach(show => {
                commit(ADD_RECOMMENDED_SHOW, show);
            });
        });
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
