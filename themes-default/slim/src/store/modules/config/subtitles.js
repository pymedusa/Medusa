import { ADD_CONFIG } from '../../mutation-types';

const state = {
    acceptUnknownEmbeddedSubs: null,
    codeFilter: [],
    enabled: null,
    eraseCache: null,
    extraScripts: [],
    finderFrequency: null,
    hearingImpaired: null,
    ignoreEmbeddedSubs: null,
    keepOnlyWanted: null,
    location: null,
    logHistory: null,
    multiLanguage: null,
    perfectMatch: null,
    preScripts: [],
    providerLogins: {
        addic7ed: { user: '', pass: '' },
        legendastv: { user: '', pass: '' },
        opensubtitles: { user: '', pass: '' }
    },
    services: [],
    stopAtFirst: null,
    wantedLanguages: [],
    wikiUrl: ''
};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'subtitles') {
            state = Object.assign(state, config);
        }
    }
};

const getters = {};

const actions = {
};

export default {
    state,
    mutations,
    getters,
    actions
};
