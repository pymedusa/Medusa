import { NOTIFICATIONS_ENABLED, NOTIFICATIONS_DISABLED } from '../mutation-types';

const state = {
    enabled: true,
    emby: {
        enabled: null,
        host: null
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
            notify: {
                download: null,
                subtitleDownload: null,
                snatch: null
            }
        }
    }
};

const mutations = {
    [NOTIFICATIONS_ENABLED](state) {
        state.enabled = true;
    },
    [NOTIFICATIONS_DISABLED](state) {
        state.enabled = false;
    }
};

const getters = {};

const actions = {
    enable(context) {
        const { commit } = context;
        commit(NOTIFICATIONS_ENABLED);
    },
    disable(context) {
        const { commit } = context;
        commit(NOTIFICATIONS_DISABLED);
    },
    test() {
        return window.displayNotification('error', 'test', 'test<br><i class="test-class">hello <b>world</b></i><ul><li>item 1</li><li>item 2</li></ul>', 'notification-test');
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
