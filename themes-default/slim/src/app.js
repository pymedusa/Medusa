import Vue from 'vue';

import { registerGlobalComponents, registerPlugins } from './global-vue-shim';
import router from './router';
import store from './store';
import { mapActions, mapMutations } from 'vuex';
import { isDevelopment } from './utils/core';
import { App } from './components';

Vue.config.devtools = true;
Vue.config.performance = true;

if (document.body.getAttribute('developer') === 'True') {
    Vue.config.devtools = true;
    Vue.config.performance = true;
}

registerPlugins();

// @TODO: Remove this before v1.0.0
registerGlobalComponents();

export default new Vue({
    name: 'index',
    router,
    store,
    data() {
        return {
            isAuthenticated: false
        };
    },
    async mounted() {
        const { getShows, setLoadingDisplay, setLoadingFinished } = this;

        if (isDevelopment) {
            console.log('App Mounted!');
        }

        await this.$store.dispatch('auth');

        if (!window.location.pathname.includes('/login')) {
            const { $store } = this;
            await $store.dispatch('login');
            this.isAuthenticated = true;

            Promise.all([
                $store.dispatch('getConfig'),
                $store.dispatch('getStats')
            ]).then(([config]) => {
                if (isDevelopment) {
                    console.log('App Loaded!');
                }
                // Legacy - send config.general to jQuery (received by index.js)
                const event = new CustomEvent('medusa-config-loaded', { detail: { general: config.general, layout: config.layout } });
                window.dispatchEvent(event);

                // Let's bootstrap the app with essential data like the shows.
                // For the storing of the shows in the browsers cache, we depend on config/general.
                getShows()
                    .then(() => {
                        console.log('Finished loading all shows.');
                        setTimeout(() => {
                            setLoadingFinished(true);
                            setLoadingDisplay(false);
                        }, 2000);
                        this.connect(true);
                    });
            }).catch(error => {
                console.debug(error);
                alert('Unable to connect to Medusa!'); // eslint-disable-line no-alert
                this.connect(false);
            });
        }
    },
    methods: {
        ...mapActions({
            getShows: 'getShows',
            connect: 'connect'

        }),
        ...mapMutations([
            'setLoadingDisplay',
            'setLoadingFinished'
        ])
    },
    render(h) { // eslint-disable-line vue/require-render-return
        // Do not start with rendering the app, before we're sure we authenticated.
        if (this.isAuthenticated || window.location.pathname.includes('/login')) {
            return h(App);
        }
    }
}).$mount('#app-wrapper');

