const VueRouter = window.vueRouter;
const { routes, httpVueLoader } = window;

if (!window.router) {
    const loginComponent = httpVueLoader('js/templates/login.vue');
    const configComponent = httpVueLoader('js/templates/config.vue');
    const addShowsComponent = httpVueLoader('js/templates/add-shows.vue');
    const addRecommendedComponent = httpVueLoader('js/templates/add-recommended.vue');
    const notFoundComponent = httpVueLoader('js/templates/http/404.vue');

    const router = new VueRouter({
        base: document.body.getAttribute('web-root') + '/',
        mode: 'history',
        routes: Object.assign(routes || [], [{
            path: '/login',
            name: 'login',
            meta: {
                title: 'Login'
            },
            component: loginComponent
        }, {
            path: '/config',
            name: 'config',
            meta: {
                title: 'Help & Info',
                header: 'Medusa Configuration'
            },
            component: configComponent
        }, {
            path: '/addShows',
            name: 'addShows',
            meta: {
                title: 'Add Shows',
                header: 'Add Shows'
            },
            component: addShowsComponent
        }, {
            path: '/addRecommended',
            name: 'addRecommended',
            meta: {
                title: 'Add Recommended Shows',
                header: 'Add Recommended Shows'
            },
            component: addRecommendedComponent
        }, {
            path: '/not-found',
            name: 'not-found',
            meta: {
                title: '404',
                header: '404 - page not found'
            },
            component: notFoundComponent
        }, {
            path: '*',
            redirect: '/not-found'
        }])
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

    window.router = router;
}
