import Vue from 'vue';
import Vuex from 'vuex';
import shows from './modules/shows';

Vue.use(Vuex);

const debug = process.env.NODE_ENV !== 'production';

export default new Vuex.Store({
    modules: {
        shows
    },
    strict: debug
});
