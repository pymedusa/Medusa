import Vue from 'vue';

import { registerGlobalComponents, registerPlugins } from './global-vue-shim';
import router from './router';
import store from './store';
import { isDevelopment } from './utils/core';

Vue.config.devtools = true;
Vue.config.performance = true;

registerPlugins();

// @TODO: Remove this before v1.0.0
registerGlobalComponents();

const app = new Vue({
    name: 'app',
    router,
    store,
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

        if (!window.location.pathname.includes('/login')) {
            const { $store } = this;
            Promise.all([
                $store.dispatch('login', { username: window.username }),
                $store.dispatch('getConfig'),
                $store.dispatch('getStats')
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
