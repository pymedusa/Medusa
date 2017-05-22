import Vue from 'vue';
import Vuex from 'vuex';

import auth from './modules/auth';
import series from './modules/series';

Vue.use(Vuex);

const debug = process.env.NODE_ENV !== 'production';

export default new Vuex.Store({
    modules: {
        auth,
        series
    },
    strict: debug
});
