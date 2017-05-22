import Vue from 'vue';
import VueRouter from 'vue-router';

import HomeComponent from '../components/home.vue';

import ConfigComponent from '../components/config.vue';
import ConfigInfoComponent from '../components/config/info.vue';
import ConfigGeneralComponent from '../components/config/general.vue';

import NotFoundComponent from '../components/not-found.vue';

Vue.use(VueRouter);

const routes = [{
    name: 'home',
    path: '/',
    component: HomeComponent
    // This can't have auth until we add the login page.
    // meta: {
    //     auth: true
    // }
}, {
    name: 'config',
    path: '/config',
    component: ConfigComponent,
    children: [{
        path: 'info',
        component: ConfigInfoComponent
    }, {
        path: 'general',
        component: ConfigGeneralComponent
    }],
    meta: {
        auth: true
    }
}, {
    name: 'not-found',
    path: '*',
    component: NotFoundComponent
}];

const router = new VueRouter({
    routes,
    base: '/vue/',
    mode: 'history'
});

router.beforeEach((to, from, next) => {
    const token = localStorage.getItem('token');
    if (to.meta.auth && !token) {
        return next({name: 'home'});
    }
    next();
});

export default router;
