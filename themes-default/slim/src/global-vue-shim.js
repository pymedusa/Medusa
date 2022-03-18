// @TODO: Remove this file before v1.0.0
import Vue from 'vue';
import AsyncComputed from 'vue-async-computed';
import VueMeta from 'vue-meta';
import Snotify from 'vue-snotify';
import VueCookies from 'vue-cookies';
import VModal from 'vue-js-modal';
import { VTooltip } from 'v-tooltip';
import { library } from '@fortawesome/fontawesome-svg-core';
import { faAlignJustify, faImages } from '@fortawesome/free-solid-svg-icons';
import { faTimesCircle } from '@fortawesome/free-regular-svg-icons';

library.add([faAlignJustify, faImages, faTimesCircle]);

import { App } from './components';
import store from './store';
import { isDevelopment } from './utils/core';

/**
 * Register global components and x-template components.
 */
export const registerGlobalComponents = () => {
    // Start with the x-template components
    let { components = [] } = window;

    // Add global components (in use by `main.mako`)
    // @TODO: These should be registered in an `App.vue` component when possible,
    //        along with some of the `main.mako` template
    components = components.concat([
        App
    ]);

    // Register the components globally
    components.forEach(component => {
        if (isDevelopment) {
            console.debug(`Registering ${component.name}`);
        }
        Vue.component(component.name, component);
    });
};

/**
 * Register plugins.
 */
export const registerPlugins = () => {
    Vue.use(AsyncComputed);
    Vue.use(VueMeta);
    Vue.use(Snotify);
    Vue.use(VueCookies);
    Vue.use(VModal, { dynamicDefault: { height: 'auto' } });
    Vue.use(VTooltip);

    // Set default cookie expire time
    Vue.$cookies.config('10y');
};

/**
 * Apply the global Vue shim.
 */
export default () => {
    const warningTemplate = (name, state) =>
        `${name} is using the global Vuex '${state}' state, ` +
        `please replace that with a local one using: mapState(['${state}'])`;

    Vue.mixin({
        data() {
            // These are only needed for the root Vue
            if (this.$root === this) {
                return {
                    pageComponent: false,
                    showsLoading: false
                };
            }
            return {};
        },
        mounted() {
            if (this.$root === this && !window.location.pathname.includes('/login')) {
                const { username } = window;
                Promise.all([
                    /* This is used by the `app-header` component
                    to only show the logout button if a username is set */
                    store.dispatch('login', { username }),
                    store.dispatch('getConfig'),
                    store.dispatch('getStats')
                ]).then(([_, config]) => {
                    this.$root.$emit('loaded');
                    // Legacy - send config.general to jQuery (received by index.js)
                    const event = new CustomEvent('medusa-config-loaded', { detail: { general: config.main, layout: config.layout } });
                    window.dispatchEvent(event);
                }).catch(error => {
                    console.debug(error);
                    alert('Unable to connect to Medusa!'); // eslint-disable-line no-alert
                });
            }
        },
        // Make auth and config accessible to all components
        // @TODO: Remove this completely
        computed: {
            // Deprecate the global `Vuex.mapState(['auth', 'config'])`
            auth() {
                if (isDevelopment && !this.__VUE_DEVTOOLS_UID__) {
                    console.warn(warningTemplate(this._name, 'auth'));
                }
                return this.$store.state.auth;
            },
            config() {
                if (isDevelopment && !this.__VUE_DEVTOOLS_UID__) {
                    console.warn(warningTemplate(this._name, 'config'));
                }
                return this.$store.state.config;
            }
        }
    });

    if (isDevelopment) {
        console.debug('Loading local Vue');
    }

    registerPlugins();

    registerGlobalComponents();
};
