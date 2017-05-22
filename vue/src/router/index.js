import Vue from 'vue';
import VueRouter from 'vue-router';

import HomeComponent from '../components/home.vue';
import NotFoundComponent from '../components/not-found.vue';

Vue.use(VueRouter);

const routes = [{
    name: 'home',
    path: '/',
    component: HomeComponent
}, {
    name: 'not-found',
    path: '*',
    component: NotFoundComponent
}];

export default new VueRouter({
    routes,
    base: '/vue/',
    mode: 'history'
});
