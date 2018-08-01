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
    console.log(`Registering ${component.name}`);
    Vue.component(component.name, component);
});

// Global components
Vue.component('app-header', AppHeader);
Vue.component('scroll-buttons', ScrollButtons);
Vue.component('app-link', AppLink);
Vue.component('asset', Asset);
Vue.component('file-browser', FileBrowser);
Vue.component('plot-info', PlotInfo);
Vue.component('name-pattern', NamePattern);
Vue.component('select-list', SelectList);
Vue.component('language-select', LanguageSelect);
Vue.component('root-dirs', RootDirs);
Vue.component('backstretch', Backstretch);

const app = new Vue({
    name: 'App',
    store,
    router,
    data() {
        return {
            globalLoading: false
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
