import VueRouter from 'vue-router';
import { Login, Config, AddShows, AddRecommended, NotFound } from './templates';

const router = new VueRouter({
    base: document.body.getAttribute('web-root') + '/',
    mode: 'history',
    routes: [{
        path: '/login',
        name: 'login',
        meta: {
            title: 'Login'
        },
        component: Login
    }, {
        path: '/config',
        name: 'config',
        meta: {
            title: 'Help & Info',
            header: 'Medusa Configuration'
        },
        component: Config
    }, {
        path: '/addShows',
        name: 'addShows',
        meta: {
            title: 'Add Shows',
            header: 'Add Shows'
        },
        component: AddShows
    }, {
        path: '/addRecommended',
        name: 'addRecommended',
        meta: {
            title: 'Add Recommended Shows',
            header: 'Add Recommended Shows'
        },
        component: AddRecommended
    }, {
        path: '/schedule',
        name: 'schedule',
        meta: {
            title: 'Schedule',
            header: 'Schedule'
        }, // eslint-disable-line comma-dangle
        // component: scheduleComponent
    }, {
        path: '/not-found',
        name: 'not-found',
        meta: {
            title: '404',
            header: '404 - page not found'
        },
        component: NotFound
    // @NOTE: Redirect can only be added once all routes are vue
    // }, {
    //     path: '*',
    //     redirect: '/not-found'
    }]
});

router.beforeEach((to, from, next) => {
    const { meta } = to;
    const { title } = meta;

    // If there's no title then it's not a .vue route so skip
    if (title) {
        document.title = `${to.meta.title} | Medusa`;
    }

    // Always call next otherwise the <router-view> will be empty
    next();
});

export default router;
