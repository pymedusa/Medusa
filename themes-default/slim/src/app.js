import Vue from 'vue';
import Vuex from 'vuex';
import VueRouter from 'vue-router';
import AsyncComputed from 'vue-async-computed';
import Snotify from 'vue-snotify';
import store from './store';
import router from './router';
import { isDevelopment } from './utils';
import {
    AnidbReleaseGroupUi,
    AppHeader,
    AppLink,
    Asset,
    Backstretch,
    Config,
    FileBrowser,
    LanguageSelect,
    NamePattern,
    PlotInfo,
    RootDirs,
    ScrollButtons,
    SelectList,
    Show,
    ShowSelector,
    SubMenu
} from './components';

Vue.config.devtools = true;
Vue.config.performance = true;

Vue.use(Vuex);
Vue.use(VueRouter);
Vue.use(AsyncComputed);
Vue.use(Snotify);

// Load x-template components
window.components.forEach(component => {
    if (isDevelopment) {
        console.debug(`Registering ${component.name}`);
    }
    Vue.component(component.name, component);
});

// Global components
const globalComponents = [
    AnidbReleaseGroupUi,
    AppHeader,
    AppLink,
    Asset,
    Backstretch,
    Config,
    FileBrowser,
    LanguageSelect,
    NamePattern,
    PlotInfo,
    RootDirs,
    ScrollButtons,
    SelectList,
    Show,
    ShowSelector,
    SubMenu
];

globalComponents.forEach(component => {
    Vue.component(component.name, component);
});

const app = new Vue({
    name: 'App',
    store,
    router,
    components: {
    },
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
