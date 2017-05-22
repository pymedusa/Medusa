import Vue from 'vue';
import Vuex from 'vuex';

import auth from './modules/auth';
import config from './modules/config';
import series from './modules/series';
import user from './modules/user';

Vue.use(Vuex);

const debug = process.env.NODE_ENV !== 'production';

export default new Vuex.Store({
    modules: {
        auth,
        config,
        series,
        user
    },
    strict: debug
});
