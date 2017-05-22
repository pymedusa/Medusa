import {config} from '../../api/';
import * as types from '../mutation-types';

const state = {
    config: {
        wikiUrl: null,
        localUser: null,
        posterSortdir: null,
        locale: null,
        themeName: null,
        selectedRootIndex: null,
        namingForceFolders: null,
        cacheDir: null,
        databaseVersion: {
            major: null,
            minor: null
        },
        programDir: null,
        layout: {
            show: {
                specials: null,
                allSeasons: null
            },
            home: null,
            history: null,
            schedule: null
        },
        nzb: {
            username: null,
            priority: null,
            password: null,
            enabled: null
        },
        configFile: null,
        fanartBackground: null,
        trimZero: null,
        animeSplitHome: null,
        branch: null,
        commitHash: null,
        sourceUrl: null,
        rootDirs: null,
        fanartBackgroundOpacity: null,
        appArgs: [],
        subtitlesMulti: null,
        logDir: null,
        sortArticle: null,
        timePreset: null,
        plex: {
            client: {
                enabled: null
            },
            server: {
                updateLibrary: null,
                enabled: null,
                notify: {
                    download: null,
                    subtitleDownload: null,
                    snatch: null
                }
            }
        },
        subtitles: {
            enabled: null
        },
        fuzzyDating: null,
        backlogOverview: {
            status: null,
            period: null
        },
        posterSortby: null,
        dbFilename: null,
        kodi: {
            enabled: null
        },
        sslVersion: null,
        pythonVersion: null,
        comingEpsSort: null,
        githubUrl: null,
        datePreset: null,
        emby: {
            enabled: null
        },
        release: null,
        os: null,
        anonRedirect: null,
        torrents: {
            highBandwidth: null,
            seedTime: null,
            rpcurl: null,
            enabled: null,
            paused: null,
            method: null,
            verifySSL: null
        }
    },
    error: null,
    stack: null
};

const getters = {
    config: state => state.config,
    statError: state => state.error,
    statStack: state => state.stack
};

const actions = {
    getConfig({commit}) {
        return new Promise((resolve, reject) => {
            config.getConfig().then(({config}) => {
                commit(types.CONFIG_RECIEVE_MULTIPLE, {config});
                resolve({config});
            }).catch(err => {
                const {error, stack} = err.response.data;
                commit(types.CONFIG_FAILURE, {error, stack});
                reject(err);
            });
        });
    }
};

const mutations = {
    // Add config to the store
    [types.CONFIG_RECIEVE_MULTIPLE](state, {config}) {
        state.config = config;
    },
    [types.CONFIG_FAILURE](state, {error, stack}) {
        state.error = error;
        state.stack = stack;
    }
};

export default {
    state,
    getters,
    actions,
    mutations
};
