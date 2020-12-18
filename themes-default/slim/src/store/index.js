import Vue from 'vue';
import Vuex, { Store } from 'vuex';
import VueNativeSock from 'vue-native-websocket';
import {
    auth,
    config,
    defaults,
    history,
    notifications,
    provider,
    shows,
    search,
    socket,
    stats
} from './modules';
import {
    SOCKET_ONOPEN,
    SOCKET_ONCLOSE,
    SOCKET_ONERROR,
    SOCKET_ONMESSAGE,
    SOCKET_RECONNECT,
    SOCKET_RECONNECT_ERROR
} from './mutation-types';

Vue.use(Vuex);

const store = new Store({
    modules: {
        auth,
        config,
        defaults,
        history,
        notifications,
        provider,
        search,
        shows,
        socket,
        stats
    },
    state: {},
    mutations: {},
    getters: {},
    actions: {}
});

// Keep as a non-arrow function for `this` context.
const passToStoreHandler = function(eventName, event, next) {
    const target = eventName.toUpperCase();
    const eventData = event.data;

    if (target === 'SOCKET_ONMESSAGE') {
        const message = JSON.parse(eventData);
        const { data, event } = message;

        // Show the notification to the user
        if (event === 'notification') {
            const { body, hash, type, title } = data;
            window.displayNotification(type, title, body, hash);
        } else if (event === 'configUpdated') {
            const { section, config } = data;
            this.store.dispatch('updateConfig', { section, config });
        } else if (event === 'showUpdated' || event === 'showAdded') {
            this.store.dispatch('updateShow', data);
        } else if (event === 'addManualSearchResult') {
            this.store.dispatch('addManualSearchResult', data);
        } else if (event === 'QueueItemUpdate') {
            this.store.dispatch('updateSearchQueueItem', data);
        } else if (event === 'QueueItemShowAdd') {
            this.store.dispatch('updateShowQueueItem', data);
        } else {
            window.displayNotification('info', event, data);
        }
    }

    // Resume normal 'passToStore' handling
    next(eventName, event);
};

const websocketUrl = (() => {
    const { protocol, host } = window.location;
    const proto = protocol === 'https:' ? 'wss:' : 'ws:';
    const WSMessageUrl = '/ui';
    const webRoot = document.body.getAttribute('web-root');
    return `${proto}//${host}${webRoot}/ws${WSMessageUrl}`;
})();

Vue.use(VueNativeSock, websocketUrl, {
    store,
    format: 'json',
    reconnection: true, // (Boolean) whether to reconnect automatically (false)
    reconnectionAttempts: 2, // (Number) number of reconnection attempts before giving up (Infinity),
    reconnectionDelay: 1000, // (Number) how long to initially wait before attempting a new (1000)
    passToStoreHandler, // (Function|<false-y>) Handler for events triggered by the WebSocket (false)
    mutations: {
        SOCKET_ONOPEN,
        SOCKET_ONCLOSE,
        SOCKET_ONERROR,
        SOCKET_ONMESSAGE,
        SOCKET_RECONNECT,
        SOCKET_RECONNECT_ERROR
    }
});

export default store;
