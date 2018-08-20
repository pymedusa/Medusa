import Vue from 'vue';
import Vuex from 'vuex';
import VueNativeSock from 'vue-native-websocket';
import {
    auth,
    config,
    defaults,
    metadata,
    notifications,
    qualities,
    shows,
    socket,
    statuses
} from './modules';
import { SOCKET_ONMESSAGE } from './mutation-types';

const { Store } = Vuex;

Vue.use(Vuex);

const store = new Store({
    modules: {
        auth,
        config,
        defaults,
        metadata,
        notifications,
        qualities,
        shows,
        socket,
        statuses
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

    if (target === SOCKET_ONMESSAGE) {
        const message = JSON.parse(eventData);
        const { data, event } = message;

        // Show the notification to the user
        if (event === 'notification') {
            const { body, hash, type, title } = data;
            window.displayNotification(type, title, body, hash);
        } else if (event === 'configUpdated') {
            const { section, config } = data;
            this.store.dispatch('updateConfig', { section, config });
        } else {
            window.displayNotification('info', event, data);
        }
    }

    // Resume normal 'passToStore' handling
    next(eventName, event);
};

const websocketUrl = (() => {
    const { protocol, hostname, port } = window.location;
    const proto = protocol === 'https:' ? 'wss:' : 'ws:';
    const WSMessageUrl = '/ui';
    const wsPort = port ? `:${port}` : '';
    const webRoot = document.body.getAttribute('web-root');
    return `${proto}//${hostname}${wsPort}${webRoot}/ws${WSMessageUrl}`;
})();

Vue.use(VueNativeSock, websocketUrl, {
    store,
    format: 'json',
    reconnection: true, // (Boolean) whether to reconnect automatically (false)
    reconnectionAttempts: 2, // (Number) number of reconnection attempts before giving up (Infinity),
    reconnectionDelay: 1000, // (Number) how long to initially wait before attempting a new (1000)
    passToStoreHandler // (Function|<false-y>) Handler for events triggered by the WebSocket (false)
});

export default store;
