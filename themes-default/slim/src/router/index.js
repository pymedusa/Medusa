import Vue from 'vue';
import VueRouter from 'vue-router';

import routes from './routes';

Vue.use(VueRouter);

export const base = document.body.getAttribute('web-root') + '/';

const router = new VueRouter({
    base,
    mode: 'history',
    routes
});

router.beforeEach((to, from, next) => {
    const { meta } = to;
    const { title } = meta;

    // If there's no title then it's not a .vue route
    // or it's handling its own title
    if (title) {
        document.title = `${title} | Medusa`;
    }

    // Always call next otherwise the <router-view> will be empty
    next();
});

export default router;
