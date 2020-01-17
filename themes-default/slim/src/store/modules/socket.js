import {
    SOCKET_ONOPEN,
    SOCKET_ONCLOSE,
    SOCKET_ONERROR,
    SOCKET_ONMESSAGE,
    SOCKET_RECONNECT,
    SOCKET_RECONNECT_ERROR
} from '../mutation-types';

const state = {
    isConnected: false,
    // Current message
    message: {},
    // Delivered messages for this session
    messages: [],
    reconnectError: false
};

const mutations = {
    [SOCKET_ONOPEN](state) {
        state.isConnected = true;
    },
    [SOCKET_ONCLOSE](state) {
        state.isConnected = false;
    },
    [SOCKET_ONERROR](state, event) {
        console.error(state, event);
    },
    // Default handler called for all websocket methods
    [SOCKET_ONMESSAGE](state, message) {
        const { data, event } = message;

        // Set the current message
        state.message = message;

        if (event === 'notification') {
            // Save it so we can look it up later
            const existingMessage = state.messages.filter(message => message.hash === data.hash);
            if (existingMessage.length === 1) {
                state.messages[state.messages.indexOf(existingMessage)] = message;
            } else {
                state.messages.push(message);
            }
        }
    },
    // Mutations for websocket reconnect methods
    [SOCKET_RECONNECT](state, count) {
        console.info(state, count);
    },
    [SOCKET_RECONNECT_ERROR](state) {
        state.reconnectError = true;

        const title = 'Error connecting to websocket';
        let error = '';
        error += 'Please check your network connection. ';
        error += 'If you are using a reverse proxy, please take a look at our wiki for config examples.';

        window.displayNotification('notice', title, error);
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
