import { api } from '../../api';
import { ADD_CONFIG } from '../mutation-types';
import { arrayUnique, arrayExclude } from '../../utils/core';

const state = {
    wikiUrl: null,
    donationsUrl: null,
    localUser: null,
    posterSortdir: null,
    locale: null,
    themeName: null,
    selectedRootIndex: null,
    webRoot: null,
    namingForceFolders: null,
    cacheDir: null,
    databaseVersion: {
        major: null,
        minor: null
    },
    programDir: null,
    dataDir: null,
    animeSplitHomeInTabs: null,
    layout: {
        show: {
            specials: null,
            showListOrder: []
        },
        home: null,
        history: null,
        schedule: null,
        wide: null
    },
    dbPath: null,
    configFile: null,
    fanartBackground: null,
    trimZero: null,
    animeSplitHome: null,
    gitUsername: null,
    branch: null,
    commitHash: null,
    indexers: {
        config: {
            main: {
                externalMappings: {},
                statusMap: {},
                traktIndexers: {},
                validLanguages: [],
                langabbvToId: {}
            },
            indexers: {
                tvdb: {
                    apiParams: {
                        useZip: null,
                        language: null
                    },
                    baseUrl: null,
                    enabled: null,
                    icon: null,
                    id: null,
                    identifier: null,
                    mappedTo: null,
                    name: null,
                    scene_loc: null, // eslint-disable-line camelcase
                    showUrl: null,
                    xemOrigin: null
                },
                tmdb: {
                    apiParams: {
                        useZip: null,
                        language: null
                    },
                    baseUrl: null,
                    enabled: null,
                    icon: null,
                    id: null,
                    identifier: null,
                    mappedTo: null,
                    name: null,
                    scene_loc: null, // eslint-disable-line camelcase
                    showUrl: null,
                    xemOrigin: null
                },
                tvmaze: {
                    apiParams: {
                        useZip: null,
                        language: null
                    },
                    baseUrl: null,
                    enabled: null,
                    icon: null,
                    id: null,
                    identifier: null,
                    mappedTo: null,
                    name: null,
                    scene_loc: null, // eslint-disable-line camelcase
                    showUrl: null,
                    xemOrigin: null
                }
            }
        }
    },
    sourceUrl: null,
    rootDirs: [],
    fanartBackgroundOpacity: null,
    appArgs: [],
    comingEpsDisplayPaused: null,
    sortArticle: null,
    timePreset: null,
    subtitles: {
        enabled: null
    },
    fuzzyDating: null,
    backlogOverview: {
        status: null,
        period: null
    },
    posterSortby: null,
    news: {
        lastRead: null,
        latest: null,
        unread: null
    },
    logs: {
        debug: null,
        dbDebug: null,
        loggingLevels: {},
        numErrors: null,
        numWarnings: null
    },
    failedDownloads: {
        enabled: null,
        deleteFailed: null
    },
    sslVersion: null,
    pythonVersion: null,
    comingEpsSort: null,
    githubUrl: null,
    datePreset: null,
    subtitlesMulti: null,
    pid: null,
    os: null,
    anonRedirect: null,
    logDir: null,
    recentShows: [],
    randomShowSlug: null, // @TODO: Recreate this in Vue when the webapp has a reliable list of shows to choose from.
    showDefaults: {
        status: null,
        statusAfter: null,
        quality: null,
        subtitles: null,
        seasonFolders: null,
        anime: null,
        scene: null
    },
    launchBrowser: null,
    defaultPage: null,
    trashRemoveShow: null,
    actualLogDir: null,
    logNr: null,
    logSize: null,
    indexerDefaultLanguage: null,
    showUpdateHour: null,
    indexerTimeout: null,
    indexerDefault: null,
    plexFallBack: {
        enable: null,
        notifications: null,
        timeout: null
    },
    versionNotify: null,
    autoUpdate: null,
    updateFrequency: null,
    notifyOnUpdate: null,
    availableThemes: null,
    comingEpsMissedRange: null,
    timeStyle: null,
    timePresets: [],
    datePresets: [],
    timezoneDisplay: null,
    webInterface: {
        apiKey: null,
        log: null,
        username: null,
        password: null,
        port: null,
        notifyOnLogin: null,
        ipv6: null,
        httpsEnable: null,
        httpsCert: null,
        httpsKey: null,
        handleReverseProxy: null
    },
    cpuPreset: null,
    cpuPresets: null,
    sslVerify: null,
    sslCaBundle: null,
    noRestart: null,
    encryptionVersion: null,
    calendarUnprotected: null,
    calendarIcons: null,
    proxySetting: null,
    proxyIndexers: null,
    skipRemovedFiles: null,
    epDefaultDeletedStatus: null,
    debug: null,
    dbDebug: null,
    subliminalLog: null,
    privacyLevel: null,
    developer: null,
    git: {
        username: null,
        password: null,
        token: null,
        authType: null,
        remote: null,
        remoteBranches: null,
        path: null,
        org: null,
        reset: null,
        resetBranches: null,
        url: null
    }
};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'main') {
            state = Object.assign(state, config);
        }
    }
};

const getters = {
    layout: state => layout => state.layout[layout],
    effectiveIgnored: (state, _, rootState) => series => {
        const seriesIgnored = series.config.release.ignoredWords.map(x => x.toLowerCase());
        const globalIgnored = rootState.search.filters.ignored.map(x => x.toLowerCase());
        if (!series.config.release.ignoredWordsExclude) {
            return arrayUnique(globalIgnored.concat(seriesIgnored));
        }
        return arrayExclude(globalIgnored, seriesIgnored);
    },
    effectiveRequired: (state, _, rootState) => series => {
        const globalRequired = rootState.search.filters.required.map(x => x.toLowerCase());
        const seriesRequired = series.config.release.requiredWords.map(x => x.toLowerCase());
        if (!series.config.release.requiredWordsExclude) {
            return arrayUnique(globalRequired.concat(seriesRequired));
        }
        return arrayExclude(globalRequired, seriesRequired);
    },
    // Get an indexer's name using its ID.
    indexerIdToName: state => indexerId => {
        if (!indexerId) {
            return undefined;
        }
        const { indexers } = state.indexers.config;
        return Object.keys(indexers).find(name => indexers[name].id === parseInt(indexerId, 10));
    },
    // Get an indexer's ID using its name.
    indexerNameToId: state => indexerName => {
        if (!indexerName) {
            return undefined;
        }
        const { indexers } = state.indexers.config;
        return indexers[name].id;
    }
};

const actions = {
    getConfig(context, section) {
        const { commit } = context;
        return api.get('/config/' + (section || '')).then(res => {
            if (section) {
                const config = res.data;
                commit(ADD_CONFIG, { section, config });
                return config;
            }

            const sections = res.data;
            Object.keys(sections).forEach(section => {
                const config = sections[section];
                commit(ADD_CONFIG, { section, config });
            });
            return sections;
        });
    },
    setConfig(context, { section, config }) {
        if (section !== 'main') {
            return;
        }

        // If an empty config object was passed, use the current state config
        config = Object.keys(config).length === 0 ? context.state : config;

        return api.patch('config/' + section, config);
    },
    updateConfig(context, { section, config }) {
        const { commit } = context;
        return commit(ADD_CONFIG, { section, config });
    },
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
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
