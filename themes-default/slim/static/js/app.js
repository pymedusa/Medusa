import Vue from 'vue';
import Vuex, { mapState } from 'vuex';
import VueRouter from 'vue-router';
import VueToggleButton from 'vue-js-toggle-button';
import httpVueLoader from 'http-vue-loader';
import store from './store';
import router from './router';

Vue.use(Vuex);
Vue.use(VueRouter);

// Load x-template components
window.components.forEach(component => {
    console.log(`Registering ${component.name}`);
    Vue.component(component.name, component);
});

// Global components
Vue.component('toggle-button', VueToggleButton);
Vue.component('app-header', httpVueLoader('js/templates/app-header.vue'));
Vue.component('scroll-buttons', httpVueLoader('js/templates/scroll-buttons.vue'));

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
