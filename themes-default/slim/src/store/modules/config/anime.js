import { ADD_CONFIG } from '../../mutation-types';

const state = {
    anidb: {
        enabled: false,
        username: null,
        password: null,
        useMylist: false
    },
    autoAnimeToList: false,
    showlistDefaultAnime: null
};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'anime') {
            state = Object.assign(state, config);
        }
    }
};

const getters = {};

const actions = {};

export default {
    state,
    mutations,
    getters,
    actions
};
