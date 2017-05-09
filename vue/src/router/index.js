import Vue from 'vue';
import VueRouter from 'vue-router'

import HomeComponent from '../components/home.vue';
import NotFoundComponent from '../components/not-found.vue';

Vue.use(VueRouter);

const routes = [{
    name: 'Home',
    path: '/',
    component: HomeComponent
}, {
    name: 'NotFound',
    path: '*',
    component: NotFoundComponent
}];

export default new VueRouter({
    routes,
    base: '/vue/',
    mode: 'history'
});
