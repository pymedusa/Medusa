import Vue from 'vue';
import Vuex, { mapState } from 'vuex';
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
    ShowSelector
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
    ShowSelector
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
    computed: Object.assign(mapState(['auth', 'config']), {}),
    mounted() {
        if (isDevelopment) {
            console.log('App Mounted!');
        }

        if (!document.location.pathname.includes('/login')) {
            const { $store } = this;
            $store.dispatch('login', { username: window.username });
            $store.dispatch('getConfig');

            if (isDevelopment) {
                console.log('App Loaded!');
            }
        }
    }
}).$mount('#vue-wrap');

export default app;
