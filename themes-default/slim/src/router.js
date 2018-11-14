import VueRouter from 'vue-router';

const AddRecommended = () => import('./components/add-recommended.vue');
const AddShows = () => import('./components/add-shows.vue');
const Config = () => import('./components/config.vue');
const ConfigPostProcessing = () => import('./components/config-post-processing.vue');
const IRC = () => import('./components/irc.vue');
const Login = () => import('./components/login.vue');
const NotFound = () => import('./components/http/404.vue');

const homeRoutes = [{
    path: '/home',
    name: 'home',
    meta: {
        title: 'Home',
        header: 'Show List',
        topMenu: 'home'
    }
}, {
    path: '/home/editShow',
    name: 'editShow',
    meta: {
        topMenu: 'home'
    }
}, {
    path: '/home/displayShow',
    name: 'show',
    meta: {
        topMenu: 'home'
    }
}, {
    path: '/home/snatchSelection',
    name: 'snatchSelection',
    meta: {
        topMenu: 'home'
    }
}, {
    path: '/home/testRename',
    name: 'testRename',
    meta: {
        title: 'Preview Rename',
        header: 'Preview Rename',
        topMenu: 'home'
    }
}, {
    path: '/home/postprocess',
    name: 'postprocess',
    meta: {
        title: 'Manual Post-Processing',
        header: 'Manual Post-Processing',
        topMenu: 'home'
    }
}, {
    path: '/home/status',
    name: 'status',
    meta: {
        title: 'Status',
        topMenu: 'system'
    }
}, {
    path: '/home/restart',
    name: 'restart',
    meta: {
        title: 'Restarting...',
        header: 'Performing Restart',
        topMenu: 'system'
    }
}, {
    path: '/home/shutdown',
    name: 'shutdown',
    meta: {
        header: 'Shutting down',
        topMenu: 'system'
    }
}, {
    path: '/home/update',
    name: 'update',
    meta: {
        topMenu: 'system'
    }
}];

const configRoutes = [{
    path: '/config',
    name: 'config',
    meta: {
        title: 'Help & Info',
        header: 'Medusa Configuration',
        topMenu: 'config',
        converted: true
    },
    component: Config
}, {
    path: '/config/anime',
    name: 'configAnime',
    meta: {
        title: 'Config - Anime',
        header: 'Anime',
        topMenu: 'config'
    }
}, {
    path: '/config/backuprestore',
    name: 'configBackupRestore',
    meta: {
        title: 'Config - Backup/Restore',
        header: 'Backup/Restore',
        topMenu: 'config'
    }
}, {
    path: '/config/general',
    name: 'configGeneral',
    meta: {
        title: 'Config - General',
        header: 'General Configuration',
        topMenu: 'config'
    }
}, {
    path: '/config/notifications',
    name: 'configNotifications',
    meta: {
        title: 'Config - Notifications',
        header: 'Notifications',
        topMenu: 'config'
    }
}, {
    path: '/config/postProcessing',
    name: 'configPostProcessing',
    meta: {
        title: 'Config - Post Processing',
        header: 'Post Processing',
        topMenu: 'config'
    },
    component: ConfigPostProcessing
}, {
    path: '/config/providers',
    name: 'configSearchProviders',
    meta: {
        title: 'Config - Providers',
        header: 'Search Providers',
        topMenu: 'config'
    }
}, {
    path: '/config/search',
    name: 'configSearchSettings',
    meta: {
        title: 'Config - Episode Search',
        header: 'Search Settings',
        topMenu: 'config'
    }
}, {
    path: '/config/subtitles',
    name: 'configSubtitles',
    meta: {
        title: 'Config - Subtitles',
        header: 'Subtitles',
        topMenu: 'config'
    }
}];

const addShowRoutes = [{
    path: '/addShows',
    name: 'addShows',
    meta: {
        title: 'Add Shows',
        header: 'Add Shows',
        topMenu: 'home',
        converted: true
    },
    component: AddShows
}, {
    path: '/addShows/addExistingShows',
    name: 'addExistingShows',
    meta: {
        title: 'Add Existing Shows',
        header: 'Add Existing Shows',
        topMenu: 'home'
    }
}, {
    path: '/addShows/newShow',
    name: 'addNewShow',
    meta: {
        title: 'Add New Show',
        header: 'Add New Show',
        topMenu: 'home'
    }
}, {
    path: '/addShows/trendingShows',
    name: 'addTrendingShows',
    meta: {
        topMenu: 'home'
    }
}, {
    path: '/addShows/popularShows',
    name: 'addPopularShows',
    meta: {
        title: 'Popular Shows',
        header: 'Popular Shows',
        topMenu: 'home'
    }
}, {
    path: '/addShows/popularAnime',
    name: 'addPopularAnime',
    meta: {
        title: 'Popular Anime Shows',
        header: 'Popular Anime Shows',
        topMenu: 'home'
    }
}];

const loginRoute = {
    path: '/login',
    name: 'login',
    meta: {
        title: 'Login'
    },
    component: Login
};

const addRecommendedRoute = {
    path: '/addRecommended',
    name: 'addRecommended',
    meta: {
        title: 'Add Recommended Shows',
        header: 'Add Recommended Shows',
        topMenu: 'home'
    },
    component: AddRecommended
};

const scheduleRoute = {
    path: '/schedule',
    name: 'schedule',
    meta: {
        title: 'Schedule',
        header: 'Schedule',
        topMenu: 'schedule'
    }
};

const historyRoute = {
    path: '/history',
    name: 'history',
    meta: {
        title: 'History',
        header: 'History',
        topMenu: 'history'
    }
};

const manageRoutes = [{
    path: '/manage',
    name: 'manage',
    meta: {
        title: 'Mass Update',
        header: 'Mass Update',
        topMenu: 'manage'
    }
}, {
    path: '/manage/backlogOverview',
    name: 'manageBacklogOverview',
    meta: {
        title: 'Backlog Overview',
        header: 'Backlog Overview',
        topMenu: 'manage'
    }
}, {
    path: '/manage/episodeStatuses',
    name: 'manageEpisodeOverview',
    meta: {
        title: 'Episode Overview',
        header: 'Episode Overview',
        topMenu: 'manage'
    }
}, {
    path: '/manage/failedDownloads',
    name: 'manageFailedDownloads',
    meta: {
        title: 'Failed Downloads',
        header: 'Failed Downlaods',
        topMenu: 'manage'
    }
}, {
    path: '/manage/manageSearches',
    name: 'manageManageSearches',
    meta: {
        title: 'Manage Searches',
        header: 'Manage Searches',
        topMenu: 'manage'
    }
}, {
    path: '/manage/massEdit',
    name: 'manageMassEdit',
    meta: {
        title: 'Mass Edit',
        topMenu: 'manage'
    }
}, {
    path: '/manage/subtitleMissed',
    name: 'manageSubtitleMissed',
    meta: {
        title: 'Missing Subtitles',
        header: 'Missing Subtitles',
        topMenu: 'manage'
    }
}, {
    path: '/manage/subtitleMissedPP',
    name: 'manageSubtitleMissedPP',
    meta: {
        title: 'Missing Subtitles in Post-Process folder',
        header: 'Missing Subtitles in Post-Process folder',
        topMenu: 'manage'
    }
}];

const errorLogsRoutes = [{
    path: '/errorlogs',
    name: 'errorlogs',
    meta: {
        title: 'Logs & Errors',
        topMenu: 'system'
    }
}, {
    path: '/errorlogs/viewlog',
    name: 'viewlog',
    meta: {
        title: 'Logs',
        header: 'Log File',
        topMenu: 'system'
    }
}];

const newsRoute = {
    path: '/news',
    name: 'news',
    meta: {
        title: 'News',
        header: 'News',
        topMenu: 'system'
    }
};

const changesRoute = {
    path: '/changes',
    name: 'changes',
    meta: {
        title: 'Changelog',
        header: 'Changelog',
        topMenu: 'system'
    }
};

const ircRoute = {
    path: '/IRC',
    name: 'IRC',
    meta: {
        title: 'IRC',
        topMenu: 'system'
    },
    component: IRC
};

const notFoundRoute = {
    path: '/not-found',
    name: 'not-found',
    meta: {
        title: '404',
        header: '404 - page not found'
    },
    component: NotFound
};

// @NOTE: Redirect can only be added once all routes are vue
/*
const notFoundRedirect = {
    path: '*',
    redirect: '/not-found'
};
*/

const routes = [
    ...homeRoutes,
    ...configRoutes,
    ...addShowRoutes,
    loginRoute,
    addRecommendedRoute,
    scheduleRoute,
    historyRoute,
    ...manageRoutes,
    ...errorLogsRoutes,
    newsRoute,
    changesRoute,
    ircRoute,
    notFoundRoute
];

const router = new VueRouter({
    base: document.body.getAttribute('web-root') + '/',
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
