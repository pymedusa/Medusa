import Vue from 'vue';
import Vuex from 'vuex'; // eslint-disable-line import/no-unresolved
import series from './modules/series';

Vue.use(Vuex);

const debug = process.env.NODE_ENV !== 'production';

export default new Vuex.Store({
    modules: {
        series
    },
    strict: debug
});
