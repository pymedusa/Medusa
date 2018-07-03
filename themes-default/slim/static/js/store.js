/* globals Vue */
const Puex = window.puex.default;
const VueNativeSock = window.VueNativeSock.default;
const displayNotification = window.displayNotification;

Vue.use(Puex);

// These are used for mutation names
// There are no naming conventions so try and match
// similarly to what we already use when adding new ones.
const mutationTypes = {
    LOGIN_PENDING: '🔒 Logging in',
    LOGIN_SUCCESS: '🔒 ✅ Login Successful',
    LOGIN_FAILED: '🔒 ❌ Login Failed',
    LOGOUT: '🔒 Logout',
    REFRESH_TOKEN: '🔒 Refresh Token',
    REMOVE_AUTH_ERROR: '🔒 Remove Auth Error',
    SOCKET_ONOPEN: 'SOCKET_ONOPEN',
    SOCKET_ONCLOSE: 'SOCKET_ONCLOSE',
    SOCKET_ONERROR: 'SOCKET_ONERROR',
    SOCKET_ONMESSAGE: 'SOCKET_ONMESSAGE',
    SOCKET_RECONNECT: 'SOCKET_RECONNECT',
    SOCKET_RECONNECT_ERROR: 'SOCKET_RECONNECT_ERROR',
    NOTIFICATIONS_ENABLED: '🔔 Notifications Enabled',
    NOTIFICATIONS_DISABLED: '🔔 Notifications Disabled',
    ADD_CONFIG: '⚙️ Config added to store',
    ADD_SHOW: '📺 Show added to store'
};

// This will be moved up later on
// once we move mutationTypes to a seperate file.
const {
    LOGIN_PENDING,
    LOGIN_SUCCESS,
    LOGIN_FAILED,
    LOGOUT,
    REFRESH_TOKEN,
    REMOVE_AUTH_ERROR,
    SOCKET_ONOPEN,
    SOCKET_ONCLOSE,
    SOCKET_ONERROR,
    SOCKET_ONMESSAGE,
    SOCKET_RECONNECT,
    SOCKET_RECONNECT_ERROR,
    NOTIFICATIONS_ENABLED,
    NOTIFICATIONS_DISABLED,
    ADD_CONFIG,
    ADD_SHOW
} = mutationTypes;

const store = new Puex({
    state: {
        auth: {
            isAuthenticated: false,
            user: {},
            tokens: {
                access: null,
                refresh: null
            },
            error: null
        },
        // Websocket
        socket: {
            isConnected: false,
            // Current message
            message: {},
            // Delivered messages for this session
            messages: [],
            reconnectError: false
        },
        notifications: {
            enabled: true
        },
        qualities: {},
        statuses: {},
        // Main config
        config: {
            wikiUrl: null,
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
                enabled: null
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
            sslVersion: null,
            pythonVersion: null,
            comingEpsSort: null,
            githubUrl: null,
            datePreset: null,
            subtitlesMulti: null,
            os: null,
            anonRedirect: null,
            logDir: null
        },
        // Loaded show list
        // New shows can be added via
        // $store.dispatch('getShow', { indexer, id });
        shows: [],
        // We use this so we can fallback to a
        // default object that resides in the shows array
        defaults: {
            show: {
                id: {
                    tvdb: null,
                    slug: null
                },
                rating: {
                    imdb: {
                        rating: null,
                        votes: null
                    }
                },
                country_codes: [], // eslint-disable-line camelcase
                network: null,
                airs: null,
                config: {
                    qualities: null,
                    defaultEpisodeStatus: null,
                    dvdOrder: null,
                    seasonFolders: null,
                    scene: null,
                    sports: null,
                    paused: null,
                    location: null,
                    airByDate: null,
                    release: null,
                    aliases: null,
                    subtitlesEnabled: null,
                    anime: null
                }
            }
        }
    },
    // The only place the state should be updated is here
    // Please add new mutations in the same order as the mutatinType list
    mutations: {
        [LOGIN_PENDING]() {},
        [LOGIN_SUCCESS](state, user) {
            state.auth.user = user;
            state.auth.isAuthenticated = true;
            state.auth.error = null;
        },
        [LOGIN_FAILED](state, { error }) {
            state.auth.user = {};
            state.auth.isAuthenticated = false;
            state.auth.error = error;
        },
        [LOGOUT](state) {
            state.auth.user = {};
            state.auth.isAuthenticated = false;
            state.auth.error = null;
        },
        [REFRESH_TOKEN]() {},
        [REMOVE_AUTH_ERROR]() {},
        [SOCKET_ONOPEN](state) {
            state.socket.isConnected = true;
        },
        [SOCKET_ONCLOSE](state) {
            state.socket.isConnected = false;
        },
        [SOCKET_ONERROR](state, event) {
            console.error(state, event);
        },
        // Default handler called for all websocket methods
        [SOCKET_ONMESSAGE](state, message) {
            const { data, event } = message;

            // Set the current message
            state.socket.message = message;

            if (event === 'notification') {
                // Save it so we can look it up later
                const existingMessage = state.socket.messages.filter(message => message.hash === data.hash);
                if (existingMessage.length === 1) {
                    state.socket.messages[state.socket.messages.indexOf(existingMessage)] = message;
                } else {
                    state.socket.messages.push(message);
                }
            }
        },
        // Mutations for websocket reconnect methods
        [SOCKET_RECONNECT](state, count) {
            console.info(state, count);
        },
        [SOCKET_RECONNECT_ERROR](state) {
            state.socket.reconnectError = true;

            const title = 'Error connecting to websocket';
            let error = '';
            error += 'Please check your network connection. ';
            error += 'If you are using a reverse proxy, please take a look at our wiki for config examples.';

            displayNotification('notice', title, error);
        },
        [NOTIFICATIONS_ENABLED](state) {
            state.notifications.enabled = true;
        },
        [NOTIFICATIONS_DISABLED](state) {
            state.notifications.enabled = false;
        },
        [ADD_CONFIG](state, { section, config }) {
            if (section === 'main') {
                state.config = config;
            }
            if (['qualities', 'statuses'].includes(section)) {
                state[section] = config;
            }
        },
        [ADD_SHOW](state, show) {
            const { shows } = state;
            const showExists = shows.filter(({ id, indexer }) => id[indexer] === show.id[indexer]).length === 1;
            if (showExists) {
                state.shows[shows.indexOf(showExists)] = show;
            } else {
                state.shows.push(show);
            }
        }
    },
    // Add all blocking code here
    // No actions should write to the store
    // Please use context.commit to fire off a mutation that'll update the store
    // Do not use store.commit in any actions!
    actions: {
        login(context, credentials) {
            const { commit } = context;
            commit(LOGIN_PENDING);

            // @TODO: Add real JWT login
            const apiLogin = () => Promise.resolve({ username: 'admin' });

            apiLogin(credentials).then(user => {
                return commit(LOGIN_SUCCESS, user);
            }).catch(error => {
                commit(LOGIN_FAILED, { error, credentials });
            });
        },
        logout(context) {
            const { commit } = context;
            commit(LOGOUT);
        },
        getConfig(context, section) {
            const { commit } = context;
            return api.get('/config/' + (section || '')).then(res => {
                if (section) {
                    const config = res.data;
                    return commit(ADD_CONFIG, { section, config });
                }
                Object.keys(res.data).forEach(section => {
                    const config = res.data[section];
                    commit(ADD_CONFIG, { section, config });
                });
            });
        },
        setConfig(context, { section, config }) {
            if (section !== 'main') {
                return;
            }
            return api.patch('config/' + section, config);
        },
        updateConfig(context, { section, config }) {
            return store.commit(ADD_CONFIG, { section, config });
        },
        getShow(context, { indexer, id }) {
            const { commit } = context;
            return api.get('/series/' + indexer + id).then(res => {
                commit(ADD_SHOW, res.data);
            });
        },
        getShows(context, shows) {
            const { commit, dispatch } = context;

            // If no shows are provided get all of them
            if (!shows) {
                return api.get('/series?limit=1000').then(res => {
                    const shows = res.data;
                    return shows.forEach(show => {
                        commit(ADD_SHOW, show);
                    });
                });
            }

            return shows.forEach(show => dispatch('getShow', show));
        },
        testNotifications() {
            return displayNotification('error', 'test', 'test<br><i class="test-class">hello <b>world</b></i><ul><li>item 1</li><li>item 2</li></ul>', 'notification-test');
        },
        setLayout(context, { page, layout }) {
            return api.patch('config/main', {
                layout: {
                    [page]: layout
                }
            // For now we reload the page since the layouts use python still
            }).then(setTimeout(() => location.reload(), 500));
        }
    },
    // @TODO Add logging here
    plugins: []
});

const websocketUrl = (() => {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const webRoot = apiRoot.replace('/api/v2/', '');
    const WSMessageUrl = '/ui';
    return proto + '//' + window.location.hostname + ':' + window.location.port + webRoot + '/ws' + WSMessageUrl;
})();

Vue.use(VueNativeSock, websocketUrl, {
    store,
    format: 'json',
    reconnection: true, // (Boolean) whether to reconnect automatically (false)
    reconnectionAttempts: 2, // (Number) number of reconnection attempts before giving up (Infinity),
    reconnectionDelay: 1000 // (Number) how long to initially wait before attempting a new (1000)
});

window.store = store;
