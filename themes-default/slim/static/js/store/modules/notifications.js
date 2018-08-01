import { NOTIFICATIONS_ENABLED, NOTIFICATIONS_DISABLED } from '../mutation-types';

const state = {
    enabled: true
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
