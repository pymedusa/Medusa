import Vue from 'vue';
import Vuex, { mapState } from 'vuex';
import VueRouter from 'vue-router';
import AsyncComputed from 'vue-async-computed';
import ToggleButton from 'vue-js-toggle-button';
import Snotify from 'vue-snotify';
import store from './store';
import router from './router';
import { AppHeader, ScrollButtons, AppLink, Asset, FileBrowser, PlotInfo, NamePattern, SelectList, LanguageSelect, RootDirs, Backstretch, DisplayShow, ShowSelector, Config } from './templates';

Vue.config.devtools = true;
Vue.config.performance = true;

Vue.use(Vuex);
Vue.use(VueRouter);
Vue.use(AsyncComputed);
Vue.use(ToggleButton);
Vue.use(Snotify);

// Load x-template components
window.components.forEach(component => {
    console.debug(`Registering ${component.name}`);
    Vue.component(component.name, component);
});

// Global components
const globalComponents = [
    AppHeader,
    AppLink,
    Asset,
    Backstretch,
    Config,
    DisplayShow,
    FileBrowser,
    LanguageSelect,
    NamePattern,
    PlotInfo,
    RootDirs,
    ScrollButtons,
    SelectList,
    ShowSelector
];

globalComponents.forEach(component => {
    Vue.component(component.name, component);
});

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
    computed: Object.assign(mapState(['auth', 'config']), {}),
    mounted() {
        console.log('App Mounted!');

        if (!document.location.pathname.includes('/login')) {
            const { $store } = this;
            $store.dispatch('login', { username: window.username });
            $store.dispatch('getConfig');

            console.log('App Loaded!');
        }
    }
}).$mount('#vue-wrap');

export default app;
