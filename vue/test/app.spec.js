import Vue from 'vue';
import VueRouter from 'vue-router';
import test from 'ava';
import App from '../src/app.vue';
import HomeComponent from '../src/components/home.vue';

test.only('App should render', t => {
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
        render: h => h(App)
    }).$mount();
    const tree = {$el: vm.$el.outerHTML};
    t.snapshot(tree);
});
