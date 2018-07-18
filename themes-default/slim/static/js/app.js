// @ts-check
import Vue from 'vue';
import Vuex, { mapState } from 'vuex';
import VueRouter from 'vue-router';
import httpVueLoader from 'http-vue-loader';
import store from './store';
import router from './router';

Vue.use(Vuex);
Vue.use(VueRouter);

Vue.component('app-header', httpVueLoader('js/templates/app-header.vue'));
Vue.component('scroll-buttons', httpVueLoader('js/templates/scroll-buttons.vue'));

// Load x-template components
// @ts-ignore
window.components.forEach(component => {
    console.log(`Registering ${component.name}`);
    Vue.component(component.name, component);
});

const app = new Vue({
    name: 'App',
    store,
    router,
    data() {
        return {
            globalLoading: false
        }
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
