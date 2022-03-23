import Vue from 'vue';
import { ADD_QUEUE_ITEM, SET_LAST_ITEM } from '../mutation-types';

const state = {
    queueitems: [],
    last: null
};

const mutations = {
    [ADD_QUEUE_ITEM](state, queueItem) {
        const existingQueueItem = state.queueitems.find(item => item.identifier === queueItem.identifier);

        if (existingQueueItem) {
            Vue.set(state.queueitems, state.queueitems.indexOf(existingQueueItem), { ...existingQueueItem, ...queueItem });
        } else {
            Vue.set(state.queueitems, state.queueitems.length, queueItem);
        }
    },
    [SET_LAST_ITEM](state, queueItem) {
        state.last = queueItem;
    }
};

const getters = {
    getQueueItemsByName: state => name => state.queueitems.filter(q => name.includes(q.name)),
    getQueueItemsByIdentifier: state => identifier => state.queueitems.filter(q => q.identifier === identifier)
};

const actions = {
    updateQueueItem(context, queueItem) {
        // Update store's search queue item. (provided through websocket)
        const { commit } = context;
        commit(SET_LAST_ITEM, queueItem);
        return commit(ADD_QUEUE_ITEM, queueItem);
    }
};

export default {
    state,
    mutations,
    getters,
    actions
};
