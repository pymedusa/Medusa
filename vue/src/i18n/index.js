import Vuex from 'vuex';

// Import translations
import english from './translations/english';
import german from './translations/german';
import french from './translations/french';

const debug = process.env.NODE_ENV !== 'production';

const store = new Vuex.Store({
    strict: debug
});

export {
    store as i18nstore,
    english,
    german,
    french
};
