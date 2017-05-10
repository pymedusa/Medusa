import Vue from 'vue';
import vuexI18n from 'vuex-i18n';
import VueResource from 'vue-resource';
import router from './router';
import store from './store';
import App from './components/app.vue';

// Import translations and store
import {
    i18nstore,
    english,
    german,
    french
} from './i18n';

Vue.use(vuexI18n.plugin, i18nstore);
Vue.use(VueResource);

// Add translations directly to Vue
Vue.i18n.add('en', english);
Vue.i18n.add('ge', german);
Vue.i18n.add('fr', french);

// Set the start locale to use
Vue.i18n.set('en');

new Vue({ // eslint-disable-line no-new
    el: '#app',
    router,
    render: h => h(App),
    store
});
