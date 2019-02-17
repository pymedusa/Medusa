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
import VueMeta from 'vue-meta';
import VueRouter from 'vue-router';
import VueNativeSock from 'vue-native-websocket';
import AsyncComputed from 'vue-async-computed';
import { ToggleButton } from 'vue-js-toggle-button';
import Snotify from 'vue-snotify';
import axios from 'axios';
import debounce from 'lodash/debounce';
import store from './store';
import router from './router';
import { isDevelopment } from './utils';
import { apiRoute, apiv1, api, webRoot, apiKey } from './api';
import {
    AddShowOptions,
    AnidbReleaseGroupUi,
    AppHeader,
    AppLink,
    Asset,
    Backstretch,
    ConfigTemplate,
    ConfigTextbox,
    ConfigTextboxNumber,
    ConfigToggleSlider,
    FileBrowser,
    Home,
    LanguageSelect,
    ManualPostProcess,
    NamePattern,
    PlotInfo,
    QualityPill,
    RootDirs,
    ScrollButtons,
    SelectList,
    Show,
    ShowSelector,
    SnatchSelection,
    StateSwitch,
    Status
} from './components';

if (window) {
    window.isDevelopment = isDevelopment;

    // Adding libs to window so mako files can use them
    window.$ = $;
    window.jQuery = $;
    window.Vue = Vue;
    window.Vuex = Vuex;
    window.VueMeta = VueMeta;
    window.VueRouter = VueRouter;
    window.VueNativeSock = VueNativeSock;
    window.AsyncComputed = AsyncComputed;
    window.ToggleButton = ToggleButton;
    window.Snotify = Snotify;
    window.axios = axios;
    window._ = { debounce };
    window.store = store;
    window.router = router;
    window.apiRoute = apiRoute;
    window.apiv1 = apiv1;
    window.api = api;

    window.MEDUSA = {
        common: {},
        config: {},
        home: {},
        addShows: {}
    };
    window.webRoot = webRoot;
    window.apiKey = apiKey;
    window.apiRoot = webRoot + '/api/v2/';

    // Push pages that load via a vue file but still use `el` for mounting
    window.components = [];
    window.components.push(AddShowOptions);
    window.components.push(AnidbReleaseGroupUi);
    window.components.push(AppHeader);
    window.components.push(AppLink);
    window.components.push(Asset);
    window.components.push(Backstretch);
    window.components.push(ConfigTemplate);
    window.components.push(ConfigTextbox);
    window.components.push(ConfigTextboxNumber);
    window.components.push(ConfigToggleSlider);
    window.components.push(FileBrowser);
    window.components.push(Home);
    window.components.push(LanguageSelect);
    window.components.push(ManualPostProcess);
    window.components.push(NamePattern);
    window.components.push(PlotInfo);
    window.components.push(QualityPill); // This component is also used in a hack/workaround in `./static/js/ajax-episode-search.js`
    window.components.push(RootDirs);
    window.components.push(ScrollButtons);
    window.components.push(SelectList);
    window.components.push(Show);
    window.components.push(ShowSelector);
    window.components.push(SnatchSelection);
    window.components.push(StateSwitch);
    window.components.push(Status);
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
    api.get('config/main').then(response => {
        $.extend(MEDUSA.config, response.data);
        MEDUSA.config.themeSpinner = MEDUSA.config.themeName === 'dark' ? '-dark' : '';
        MEDUSA.config.loading = '<img src="images/loading16' + MEDUSA.config.themeSpinner + '.gif" height="16" width="16" />';

        $(document).ready(UTIL.init);

        MEDUSA.config.indexers.indexerIdToName = indexerId => {
            if (!indexerId) {
                return '';
            }
            return Object.keys(MEDUSA.config.indexers.config.indexers).filter(indexer => { // eslint-disable-line array-callback-return
                if (MEDUSA.config.indexers.config.indexers[indexer].id === parseInt(indexerId, 10)) {
                    return MEDUSA.config.indexers.config.indexers[indexer].name;
                }
            })[0];
        };

        MEDUSA.config.indexers.nameToIndexerId = name => {
            if (!name) {
                return '';
            }
            return MEDUSA.config.indexers.config.indexers[name];
        };
    }).catch(error => {
        console.debug(error);
        alert('Unable to connect to Medusa!'); // eslint-disable-line no-alert
    });
}
