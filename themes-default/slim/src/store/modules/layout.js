import { ADD_CONFIG } from '../mutation-types';
import { api } from '../../api';

const state = {
    show: {
        specials: null,
        showListOrder: []
    },
    home: null,
    history: null,
    historyLimit: null,
    schedule: null,
    wide: null,
    posterSortdir: null,
    timezoneDisplay: null,
    timeStyle: null,
    dateStyle: null,
    themeName: null,
    animeSplitHomeInTabs: null,
    animeSplitHome: null,
    fanartBackground: null,
    fanartBackgroundOpacity: null,
    trimZero: null,
    sortArticle: null,
    fuzzyDating: null,
    posterSortby: null,
    comingEps: {
        missedRange: null,
        sort: null,
        displayPaused: null,
        layout: null
    },
    backlogOverview: {
        status: null,
        period: null
    }
};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'layout') {
            state = Object.assign(state, config);
        }
    }
};

const getters = {};

const actions = {
    setLayout(context, { page, layout }) {
        return api.patch('config/main', {
            layout: {
                [page]: layout
            }
        }).then(() => {
            setTimeout(() => {
                // For now we reload the page since the layouts use python still
                location.reload();
            }, 500);
        });
    },
    setTheme(context, { themeName }) {
        const { commit } = context;
        return api.patch('config/main', { layout: { themeName } })
            .then(() => {
                return commit(ADD_CONFIG, { section: 'layout', layout: { themeName } });
            });
    }

};

export default {
    state,
    mutations,
    getters,
    actions
};
