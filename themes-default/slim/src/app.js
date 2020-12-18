import Vue from 'vue';

import { registerGlobalComponents, registerPlugins } from './global-vue-shim';
import router from './router';
import store from './store';
import { mapActions, mapMutations, mapState } from 'vuex';
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
    computed: {
        ...mapState({
            showsLoading: state => state.shows.loading
        })
    },
    mounted() {
        const { getShows, setLoadingDisplay, setLoadingFinished } = this;

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
                // Legacy - send config.general to jQuery (received by index.js)
                const event = new CustomEvent('medusa-config-loaded', { detail: { general: config.general, layout: config.layout } });
                window.dispatchEvent(event);
            }).catch(error => {
                console.debug(error);
                alert('Unable to connect to Medusa!'); // eslint-disable-line no-alert
            });
        }

        // Let's bootstrap the app with essential data.
        getShows()
            .then(() => {
                console.log('Finished loading all shows.');
                setTimeout(() => {
                    setLoadingFinished(true);
                    setLoadingDisplay(false);
                }, 2000);
            });
    },
    methods: {
        ...mapActions({
            getShows: 'getShows'
        }),
        ...mapMutations([
            'setLoadingDisplay',
            'setLoadingFinished'
        ])
    }
}).$mount('#vue-wrap');

export default app;
