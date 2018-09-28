import { ADD_CONFIG } from '../mutation-types';

const state = {
    emby: {
        enabled: null,
        host: null,
        apiKey: null
    },
    kodi: {
        enabled: null,
        alwaysOn: null,
        libraryCleanPending: null,
        cleanLibrary: null,
        host: [],
        username: null,
        password: null,
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
    plex: {
        client: {
            host: [],
            username: null,
            enabled: null,
            notifyOnSnatch: null,
            notifyOnDownload: null,
            notifyOnSubtitleDownload: null
        },
        server: {
            updateLibrary: null,
            host: [],
            enabled: null,
            https: null,
            username: null,
            password: null,
            token: null,
            notify: {
                download: null,
                subtitleDownload: null,
                snatch: null
            }
        }
    },
    nmj: {
        enabled: null,
        host: null,
        database: null,
        mount: null
    },
    nmjv2: {
        enabled: null,
        host: null,
        dbloc: null,
        database: null
    },
    synologyIndex: {
        enabled: null
    },
    synology: {
        enabled: null,
        notifyOnSnatch: null,
        notifyOnDownload: null,
        notifyOnSubtitleDownload: null
    },
    pyTivo: {
        enabled: null,
        host: null,
        name: null,
        shareName: null
    },
    growl: {
        enabled: null,
        host: null,
        password: null,
        notifyOnSnatch: null,
        notifyOnDownload: null,
        notifyOnSubtitleDownload: null
    },
    prowl: {
        enabled: null,
        api: null,
        messageTitle: null,
        piority: null,
        notifyOnSnatch: null,
        notifyOnDownload: null,
        notifyOnSubtitleDownload: null
    },
    libnotify: {
        enabled: null,
        notifyOnSnatch: null,
        notifyOnDownload: null,
        notifyOnSubtitleDownload: null
    },
    pushover: {
        enabled: null,
        apiKey: null,
        userKey: null,
        device: [],
        sound: null,
        notifyOnSnatch: null,
        notifyOnDownload: null,
        notifyOnSubtitleDownload: null
    },
    boxcar2: {
        enabled: null,
        notifyOnSnatch: null,
        notifyOnDownload: null,
        notifyOnSubtitleDownload: null,
        accessToken: null
    },
    pushalot: {
        enabled: null,
        notifyOnSnatch: null,
        notifyOnDownload: null,
        notifyOnSubtitleDownload: null,
        authToken: null
    },
    pushbullet: {
        enabled: null,
        notifyOnSnatch: null,
        notifyOnDownload: null,
        notifyOnSubtitleDownload: null,
        authToken: null,
        device: null
    }
};

const mutations = {
    [ADD_CONFIG](state, { section, config }) {
        if (section === 'notifiers') {
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
