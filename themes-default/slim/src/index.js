/* eslint-disable import/no-unassigned-import */
import $ from 'jquery';
import 'bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'vue-snotify/styles/material.css';
import '../vendor/js/tablesorter';
import '../vendor/css/open-sans.css';
/* eslint-enable import/no-unassigned-import */

import Vue from 'vue';
import Vuex from 'vuex';
import { ToggleButton } from 'vue-js-toggle-button';
import axios from 'axios';
import debounce from 'lodash/debounce';
import store from './store';
import router from './router';
import { apiRoute, apiv1, api, webRoot, apiKey } from './api';
import globalVueShim from './global-vue-shim';

if (window) {
    // @TODO: Remove this before v1.0.0
    window.globalVueShim = globalVueShim;

    // Adding libs to window so mako files can use them
    window.$ = $;
    window.jQuery = $;
    window.Vue = Vue;
    window.Vuex = Vuex;
    window.ToggleButton = ToggleButton;
    window.axios = axios;
    window._ = { debounce };
    window.store = store;
    window.router = router;
    window.apiRoute = apiRoute;
    window.apiv1 = apiv1;
    window.api = api;

    window.MEDUSA = {
        common: {},
        config: {
            general: {},
            layout: {}
        },
        home: {},
        addShows: {}
    };
    window.webRoot = webRoot;
    window.apiKey = apiKey;

    // Push x-template components to this array to register them globally
    window.components = [];
}

const UTIL = {
    exec(controller, action) {
        const ns = MEDUSA;
        action = (action === undefined) ? 'init' : action;

        if (controller !== '' && ns[controller] && typeof ns[controller][action] === 'function') {
            ns[controller][action]();
        }
    },
    init() {
        $('[v-cloak]').removeAttr('v-cloak');

        const { body } = document;
        const controller = body.getAttribute('data-controller');
        const action = body.getAttribute('data-action');

        UTIL.exec('common'); // Load common
        UTIL.exec(controller); // Load MEDUSA[controller]
        UTIL.exec(controller, action); // Load MEDUSA[controller][action]

        window.dispatchEvent(new Event('medusa-loaded'));
    }
};

const { pathname } = window.location;
if (!pathname.includes('/login') && !pathname.includes('/apibuilder')) {
    const configLoaded = event => {
        const { general, layout } = event.detail;

        MEDUSA.config.general = {
            ...MEDUSA.config.general,
            ...general
        };

        const themeSpinner = layout.themeName === 'dark' ? '-dark' : '';
        MEDUSA.config.layout = {
            ...MEDUSA.config.layout,
            ...layout,
            themeSpinner,
            loading: '<img src="images/loading16' + themeSpinner + '.gif" height="16" width="16" />'
        };

        $(document).ready(UTIL.init);
    };
    window.addEventListener('medusa-config-loaded', configLoaded, { once: true });
}
