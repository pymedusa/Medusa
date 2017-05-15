import Vue from 'vue';
import VueRouter from 'vue-router';
import vuexI18n from 'vuex-i18n';
import test from 'ava';

import store from '../src/store';

import App from '../src/components/app.vue';
import HomeComponent from '../src/components/home.vue';

// Import translations and store
import {
    i18nstore,
    enUs
} from '../src/i18n';

test('App should render', t => {
    Vue.use(vuexI18n.plugin, i18nstore);

    // Add translations directly to Vue
    Vue.i18n.add('en-us', enUs);

    // Set the start locale to use
    Vue.i18n.set('en');
    Vue.use(VueRouter);
    const router = new VueRouter({
        routes: [{
            name: 'home',
            path: '/',
            component: HomeComponent
        }]
    });
    const vm = new Vue({
        router,
        render: h => h(App),
        store
    }).$mount();
    const tree = {$el: vm.$el.outerHTML};
    t.snapshot(tree);
});
