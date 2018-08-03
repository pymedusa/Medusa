import Vue from 'vue';
import Vuex, { mapState } from 'vuex';
import VueRouter from 'vue-router';
import AsyncComputed from 'vue-async-computed';
import ToggleButton from 'vue-js-toggle-button';
import Snotify from 'vue-snotify';
import store from './store';
import router from './router';
import AppHeader from './templates/app-header.vue';
import ScrollButtons from './templates/scroll-buttons.vue';
import AppLink from './templates/app-link.vue';
import Asset from './templates/asset.vue';
import FileBrowser from './templates/file-browser.vue';
import PlotInfo from './templates/plot-info.vue';
import NamePattern from './templates/name-pattern.vue';
import SelectList from './templates/select-list.vue';
import LanguageSelect from './templates/language-select.vue';
import RootDirs from './templates/root-dirs.vue';
import Backstretch from './templates/backstretch.vue';

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
    FileBrowser,
    LanguageSelect,
    NamePattern,
    PlotInfo,
    RootDirs,
    ScrollButtons,
    SelectList
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

        const { $store } = this;
        $store.dispatch('login', { username: window.username });
        $store.dispatch('getConfig');

        console.log('App Loaded!');
    }
}).$mount('#vue-wrap');

export default app;
