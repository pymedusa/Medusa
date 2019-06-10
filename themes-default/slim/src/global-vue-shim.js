// @TODO: Remove this file before v1.0.0
import Vue from 'vue';
import Vuex from 'vuex';
import VueMeta from 'vue-meta';
import VueRouter from 'vue-router';
import AsyncComputed from 'vue-async-computed';
import Snotify from 'vue-snotify';

import store from './store';
import { isDevelopment } from './utils/core';

export default () => {
    const warningTemplate = (name, state) =>
        `${name} is using the global Vuex '${state}' state, ` +
        `please replace that with a local one using: mapState(['${state}'])`;

    Vue.mixin({
        data() {
            // These are only needed for the root Vue
            if (this.$root === this) {
                return {
                    globalLoading: true,
                    pageComponent: false
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
                    store.dispatch('getConfig')
                ]).then(([_, config]) => {
                    this.$emit('loaded');
                    // Legacy - send config.main to jQuery (received by index.js)
                    const event = new CustomEvent('medusa-config-loaded', { detail: config.main });
                    window.dispatchEvent(event);
                }).catch(error => {
                    console.debug(error);
                    alert('Unable to connect to Medusa!'); // eslint-disable-line no-alert
                });
            }

            this.$once('loaded', () => {
                this.$root.globalLoading = false;
            });
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

    Vue.use(Vuex);
    Vue.use(VueRouter);
    Vue.use(AsyncComputed);
    Vue.use(VueMeta);

    // Register components
    window.components.forEach(component => {
        if (isDevelopment) {
            console.debug(`Registering ${component.name}`);
        }
        Vue.component(component.name, component);
    });

    // Global components
    Vue.use(Snotify);
};
