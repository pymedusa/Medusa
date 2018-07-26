import Vue from 'vue';
import Vuex, { mapState } from 'vuex';
import VueRouter from 'vue-router';
import ToggleButton from 'vue-js-toggle-button';
import httpVueLoader from 'http-vue-loader';
import store from './store';
import router from './router';

Vue.use(Vuex);
Vue.use(VueRouter);
Vue.use(ToggleButton);

// Load x-template components
window.components.forEach(component => {
    console.log(`Registering ${component.name}`);
    Vue.component(component.name, component);
});

// Global components
Vue.component('app-header', httpVueLoader('js/templates/app-header.vue'));
Vue.component('scroll-buttons', httpVueLoader('js/templates/scroll-buttons.vue'));
Vue.component('app-link', httpVueLoader('js/templates/app-link.vue'));
Vue.component('asset', httpVueLoader('js/templates/asset.vue'));
Vue.component('file-browser', httpVueLoader('js/templates/file-browser.vue'));
Vue.component('plot-info', httpVueLoader('js/templates/plot-info.vue'));
Vue.component('language-select', httpVueLoader('js/templates/language-select.vue'));
Vue.component('root-dirs', httpVueLoader('js/templates/root-dirs.vue'));
Vue.component('backstretch', httpVueLoader('js/templates/backstretch.vue'));

const app = new Vue({
    name: 'App',
    store,
    router,
    data() {
        return {
            globalLoading: false
        };
    },
    computed: {
        ...mapState(['auth', 'config'])
    },
    mounted() {
        console.log('App Mounted!');

        const { $store } = this;
        $store.dispatch('login', { username: window.username });
        $store.dispatch('getConfig');

        console.log('App Loaded!');
    }
}).$mount('#vue-wrap');

export default app;
