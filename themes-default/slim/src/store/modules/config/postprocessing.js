import { ADD_CONFIG } from '../../mutation-types';

const state = {
    naming: {
        pattern: null,
        multiEp: null,
        enableCustomNamingSports: null,
        enableCustomNamingAirByDate: null,
        patternSports: null,
        patternAirByDate: null,
        enableCustomNamingAnime: null,
        patternAnime: null,
        animeMultiEp: null,
        animeNamingType: null,
        stripYear: null
    },
    showDownloadDir: null,
    processAutomatically: null,
    processMethod: null,
    deleteRarContent: null,
    unpack: null,
    noDelete: null,
    reflinkAvailable: null,
    postponeIfSyncFiles: null,
    autoPostprocessorFrequency: 10,
    airdateEpisodes: null,
    moveAssociatedFiles: null,
    allowedExtensions: [],
    addShowsWithoutDir: null,
    createMissingShowDirs: null,
    renameEpisodes: null,
    postponeIfNoSubs: null,
    nfoRename: null,
    syncFiles: [],
    fileTimestampTimezone: 'local',
    extraScripts: [],
    extraScriptsUrl: null,
    multiEpStrings: {}
};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'postprocessing') {
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
