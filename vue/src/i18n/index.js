import Vuex from 'vuex';

// Import translations
import enUs from './translations/en-us';

const debug = process.env.NODE_ENV !== 'production';

const store = new Vuex.Store({
    strict: debug
});

export {
    store as i18nstore,
    enUs
};
