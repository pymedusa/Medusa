import { ADD_CONFIG } from '../mutation-types';

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
    torrents: {
        authType: null,
        dir: null,
        enabled: null,
        highBandwidth: null,
        host: null,
        label: null,
        labelAnime: null,
        method: null,
        path: null,
        paused: null,
        rpcurl: null,
        seedLocation: null,
        seedTime: null,
        username: null,
        verifySSL: null
    },
    layout: {
        show: {
            specials: null,
            showListOrder: [],
            allSeasons: null
        },
        home: null,
        history: null,
        schedule: null
    },
    dbPath: null,
    nzb: {
        enabled: null,
        method: null,
        nzbget: {
            category: null,
            categoryAnime: null,
            categoryAnimeBacklog: null,
            categoryBacklog: null,
            host: null,
            priority: null,
            useHttps: null,
            username: null
        },
        sabnzbd: {
            category: null,
            forced: null,
            categoryAnime: null,
            categoryBacklog: null,
            categoryAnimeBacklog: null,
            host: null,
            username: null
        }
    },
    configFile: null,
    fanartBackground: null,
    trimZero: null,
    animeSplitHome: null,
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
    emby: {
        enabled: null,
        host: null
    },
    comingEpsDisplayPaused: null,
    sortArticle: null,
    timePreset: null,
    plex: {
        client: {
            host: [],
            username: null,
            enabled: null
        },
        server: {
            updateLibrary: null,
            host: [],
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
    kodi: {
        enabled: null,
        alwaysOn: null,
        libraryCleanPending: null,
        cleanLibrary: null,
        host: [],
        notify: {
            snatch: null,
            download: null,
            subtitleDownload: null
        },
        update: {
            library: null,
            full: null,
            onlyFirst: null
        }
    },
    news: {
        lastRead: null,
        latest: null,
        unread: null
    },
    logs: {
        loggingLevels: {},
        numErrors: null,
        numWarnings: null
    },
    failedDownloads: {
        enabled: null,
        deleteFailed: null
    },
    postProcessing: {
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
        seriesDownloadDir: null,
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
        multiEpStrings: null
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
    recentShows: []
};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'main') {
            state = Object.assign(state, config);
        }
    }
};

const getters = {
    layout: layout => state => {
        return state.layout[layout];
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
