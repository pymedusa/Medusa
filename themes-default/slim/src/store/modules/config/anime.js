import { ADD_CONFIG, UPDATE_SHOWLIST_DEFAULT } from '../../mutation-types';

const state = {
    anidb: {
        enabled: false,
        username: null,
        password: null,
        useMylist: false
    },
    autoAnimeToList: false,
    showlistDefaultAnime: []
};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'anime') {
            state = Object.assign(state, config);
        }
    },
    [UPDATE_SHOWLIST_DEFAULT](state, value) {
        state.showlistDefaultAnime = value;
    }
};

const getters = {};

const actions = {
    updateShowlistDefault(context, showlistDefaultAnime) {
        const { commit } = context;
        return commit(UPDATE_SHOWLIST_DEFAULT, showlistDefaultAnime);
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
