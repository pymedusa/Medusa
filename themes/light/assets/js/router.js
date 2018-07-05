const VueRouter = window.vueRouter;
const { routes, httpVueLoader } = window;

if (!window.router) {
    const configComponent = httpVueLoader('js/templates/config.vue');
    const addShowsComponent = httpVueLoader('js/templates/add-shows.vue');
    const addRecommendedComponent = httpVueLoader('js/templates/add-recommended.vue');
    // eslint-disable-next-line capitalized-comments
    // const scheduleComponent = httpVueLoader('js/templates/schedule.vue');
    const notFoundComponent = httpVueLoader('js/templates/http/404.vue');

    const router = new VueRouter({
        base: document.body.getAttribute('api-root').replace('api/v2/', ''),
        mode: 'history',
        routes: Object.assign(routes || [], [{
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
