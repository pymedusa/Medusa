import Vue from 'vue';
import Vuex from 'vuex';
import VueRouter from 'vue-router';
import AsyncComputed from 'vue-async-computed';
import Snotify from 'vue-snotify';

import { registerGlobalComponents } from './global-vue-shim';
import store from './store';
import router from './router';
import { isDevelopment } from './utils/core';

Vue.config.devtools = true;
Vue.config.performance = true;

Vue.use(Vuex);
Vue.use(VueRouter);
Vue.use(AsyncComputed);
Vue.use(Snotify);

// @TODO: Remove this before v1.0.0
registerGlobalComponents();

const app = new Vue({
    name: 'App',
    store,
    router,
    data() {
        return {
            globalLoading: false,
            pageComponent: false
        };
    },
    mounted() {
        if (isDevelopment) {
            console.log('App Mounted!');
        }

        if (!document.location.pathname.includes('/login')) {
            const { $store } = this;
            Promise.all([
                $store.dispatch('login', { username: window.username }),
                $store.dispatch('getConfig')
            ]).then(([_, config]) => {
                if (isDevelopment) {
                    console.log('App Loaded!');
                }
                // Legacy - send config.main to jQuery (received by index.js)
                const event = new CustomEvent('medusa-config-loaded', { detail: config.main });
                window.dispatchEvent(event);
            }).catch(error => {
                console.debug(error);
                alert('Unable to connect to Medusa!'); // eslint-disable-line no-alert
            });
        }
    }
}).$mount('#vue-wrap');

export default app;
