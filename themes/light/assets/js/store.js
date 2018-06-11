/* globals Vue */
const Puex = window.puex.default;
const VueNativeSock = window.VueNativeSock.default;

Vue.use(Puex);

const mutationTypes = {
    LOGIN_PENDING: '🔒 Login Pending',
    LOGIN_SUCCESS: '🔒 ✅ Login Successful',
    LOGIN_FAILED: '🔒 ❌ Login Failed',
    LOGOUT: '🔒 Logout',
    REFRESH_TOKEN: '🔒 Refresh Token',
    REMOVE_AUTH_ERROR: '🔒 Remove Auth Error',
    SOCKET_ONOPEN: '',
    SOCKET_ONCLOSE: '',
    SOCKET_ONERROR: '',
    SOCKET_ONMESSAGE: '',
    SOCKET_RECONNECT: '',
    SOCKET_RECONNECT_ERROR: '',
    ADD_CONFIG: '⚙️ Global config added to store',
    ADD_SHOW: '📺 Show added to store'
};

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
    ADD_CONFIG,
    ADD_SHOW
} = mutationTypes;

const store = new Puex({
    state: {
        socket: {
            isConnected: false,
            message: '',
            reconnectError: false
        },
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
        shows: [],
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
        // Default handler called for all socket methods
        [SOCKET_ONMESSAGE](state, message) {
            state.socket.message = message;
        },
        // Mutations for socket reconnect methods
        [SOCKET_RECONNECT](state, count) {
            console.info(state, count);
        },
        [SOCKET_RECONNECT_ERROR](state) {
            state.socket.reconnectError = true;
        },
        [ADD_CONFIG](state, config) {
            state.config = config;
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
    actions: {
        getConfig(store) {
            return api.get('/config/main').then(res => {
                store.commit(ADD_CONFIG, res.data);
            });
        },
        getShow(store, { indexer, id }) {
            return api.get('/series/' + indexer + id).then(res => {
                store.commit(ADD_SHOW, res.data);
            });
        }
    },
    plugins: []
});

Vue.use(VueNativeSock, 'ws://localhost:8081/x/ws/ui', {
    store: window.store,
    format: 'json'
});

window.store = store;
