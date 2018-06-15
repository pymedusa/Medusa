/* globals Vue */
const Puex = window.puex.default;
const VueNativeSock = window.VueNativeSock.default;
const displayNotification = window.displayNotification;

Vue.use(Puex);

// These are used for mutation names
// There are no naming conventions so try and match
// similarly to what we already use when adding new ones.
const mutationTypes = {
    LOGIN_PENDING: '🔒 Login Pending',
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
    ADD_CONFIG: '⚙️ Global config added to store',
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
        // Websocket
        socket: {
            isConnected: false,
            // Current message
            message: '',
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
            databaseVersion: null,
            programDir: null,
            animeSplitHomeInTabs: null,
            layout: {
                show: {
                    allSeasons: null
                }
            },
            dbPath: null,
            nzb: null,
            configFile: null,
            fanartBackground: null,
            trimZero: null,
            animeSplitHome: null,
            branch: null,
            commitHash: null,
            indexers: null,
            sourceUrl: null,
            rootDirs: null,
            fanartBackgroundOpacity: null,
            appArgs: null,
            emby: {},
            logDir: null,
            sortArticle: null,
            timePreset: null,
            plex: {},
            subtitles: {
                enabled: null
            },
            fuzzyDating: null,
            backlogOverview: null,
            posterSortby: null,
            kodi: {},
            sslVersion: null,
            pythonVersion: null,
            comingEpsSort: null,
            githubUrl: null,
            datePreset: null,
            subtitlesMulti: null,
            os: null,
            anonRedirect: null,
            torrents: null
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
        [LOGIN_SUCCESS]() {},
        [LOGIN_FAILED]() {},
        [LOGOUT]() {},
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
            const { body, hash, type, title } = data;

            // Set the current message
            state.socket.message = message;

            // Show the notification to the user
            if (event === 'notification') {
                displayNotification(type, title, body, hash);
            } else {
                displayNotification('info', '', message);
            }

            // Save it so we can look it up later
            const existingMessage = state.socket.messages.filter(message => message.hash === hash);
            if (existingMessage.length === 1) {
                state.socket.messages[state.socket.messages.indexOf(existingMessage)] = message;
            } else {
                state.socket.messages.push(message);
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
    // Please use store.commit to fire off a mutation that'll update the store
    actions: {
        getConfig(context, section) {
            return api.get('/config/' + (section || '')).then(res => {
                if (!section) {
                    const config = res.data;
                    return store.commit(ADD_CONFIG, { section, config });
                }
                Object.keys(res.data).forEach(section => {
                    const config = res.data[section];
                    store.commit(ADD_CONFIG, { section, config });
                });
            });
        },
        getShow(store, { indexer, id }) {
            return api.get('/series/' + indexer + id).then(res => {
                store.commit(ADD_SHOW, res.data);
            });
        },
        getShows(store, shows) {
            const { getShow } = this;
            return shows.forEach(show => getShow(show));
        },
        testNotifications() {
            return displayNotification('error', 'test', 'test<br><i class="test-class">hello <b>world</b></i><ul><li>item 1</li><li>item 2</li></ul>', 'notification-test--');
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
