import Vue from 'vue';
import { ADD_QUEUE_ITEM } from '../mutation-types';

const state = {
    queueitems: []
};

const mutations = {
    [ADD_QUEUE_ITEM](state, queueItem) {
        const existingQueueItem = state.queueitems.find(item => item.identifier === queueItem.identifier);

        if (existingQueueItem) {
            Vue.set(state.queueitems, state.queueitems.indexOf(existingQueueItem), { ...existingQueueItem, ...queueItem });
        } else {
            Vue.set(state.queueitems, state.queueitems.length, queueItem);
        }
    }
};

const getters = {};

const actions = {
    updateSearchQueueItem(context, queueItem) {
        // Update store's search queue item. (provided through websocket)
        const { commit } = context;
        return commit(ADD_QUEUE_ITEM, queueItem);
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
