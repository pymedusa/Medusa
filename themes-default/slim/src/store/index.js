import Vue from 'vue';
import Vuex from 'vuex';
import VueNativeSock from 'vue-native-websocket';
import { api } from '../api';
import { auth, config, defaults, socket, notifications, qualities, statuses, metadata } from './modules';
import { ADD_SHOW } from './mutation-types';

const { Store } = Vuex;

Vue.use(Vuex);

const store = new Store({
    modules: {
        auth,
        config,
        defaults,
        socket,
        notifications,
        qualities,
        statuses,
        metadata
    },
    state: {
        shows: []
    },
    mutations: {
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
        }
    }
});

const websocketUrl = (() => {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const WSMessageUrl = '/ui';
    const webRoot = document.body.getAttribute('web-root');
    return proto + '//' + window.location.hostname + ':' + window.location.port + webRoot + '/ws' + WSMessageUrl;
})();

Vue.use(VueNativeSock, websocketUrl, {
    store,
    format: 'json',
    reconnection: true, // (Boolean) whether to reconnect automatically (false)
    reconnectionAttempts: 2, // (Number) number of reconnection attempts before giving up (Infinity),
    reconnectionDelay: 1000 // (Number) how long to initially wait before attempting a new (1000)
});

export default store;
