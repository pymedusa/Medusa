import {
    configSubMenu,
    errorlogsSubMenu,
    historySubMenu,
    showSubMenu
} from './sub-menus';

/** @type {import('.').Route[]} */
const homeRoutes = [
    {
        path: '/home',
        name: 'home',
        meta: {
            title: 'Home',
            topMenu: 'home',
            converted: true
        },
        component: () => import('../components/home.vue')
    },
    {
        path: '/home/editShow',
        name: 'editShow',
        meta: {
            topMenu: 'home',
            subMenu: showSubMenu,
            converted: true,
            nocache: true // Use this flag, to have the router-view use :key="$route.fullPath"
        },
        component: () => import('../components/edit-show.vue')
    },
    {
        path: '/home/displayShow',
        name: 'show',
        meta: {
            topMenu: 'home',
            subMenu: showSubMenu,
            converted: true,
            nocache: true // Use this flag, to have the router-view use :key="$route.fullPath"
        },
        component: () => import('../components/display-show.vue')
    },
    {
        path: '/home/snatchSelection',
        name: 'snatchSelection',
        meta: {
            topMenu: 'home',
            subMenu: showSubMenu,
            converted: true,
            nocache: true // Use this flag, to have the router-view use :key="$route.fullPath"
        },
        component: () => import('../components/snatch-selection.vue')
    },
    {
        path: '/home/testRename',
        name: 'testRename',
        meta: {
            title: 'Preview Rename',
            header: 'Preview Rename',
            topMenu: 'home'
        }
    },
    {
        path: '/home/postprocess',
        name: 'postprocess',
        meta: {
            title: 'Manual Post-Processing',
            header: 'Manual Post-Processing',
            topMenu: 'home'
        }
    },
    {
        path: '/home/status',
        name: 'status',
        meta: {
            title: 'Status',
            topMenu: 'system'
        }
    },
    {
        path: '/home/restart',
        name: 'restart',
        meta: {
            title: 'Restarting...',
            header: 'Performing Restart',
            topMenu: 'system',
            converted: true
        },
        component: () => import('../components/restart.vue')
    },
    {
        path: '/home/shutdown',
        name: 'shutdown',
        meta: {
            header: 'Shutting down',
            topMenu: 'system',
            converted: true
        },
        component: () => import('../components/restart.vue'),
        props: { shutdown: true }
    },
    {
        path: '/home/update',
        name: 'update',
        meta: {
            header: 'Update Medusa',
            topMenu: 'system',
            converted: true
        },
        component: () => import('../components/update.vue')
    }
];

/** @type {import('.').Route[]} */
const configRoutes = [
    {
        path: '/config',
        name: 'config',
        meta: {
            title: 'Help & Info',
            header: 'Medusa Configuration',
            topMenu: 'config',
            subMenu: configSubMenu,
            converted: true
        },
        component: () => import('../components/config.vue')
    },
    {
        path: '/config/anime',
        name: 'configAnime',
        meta: {
            title: 'Config - Anime',
            header: 'Anime',
            topMenu: 'config',
            subMenu: configSubMenu,
            converted: true
        },
        component: () => import('../components/config-anime.vue')
    },
    {
        path: '/config/backuprestore',
        name: 'configBackupRestore',
        meta: {
            title: 'Config - Backup/Restore',
            header: 'Backup/Restore',
            topMenu: 'config',
            subMenu: configSubMenu
        }
    },
    {
        path: '/config/general',
        name: 'configGeneral',
        meta: {
            title: 'Config - General',
            header: 'General Configuration',
            topMenu: 'config',
            subMenu: configSubMenu,
            converted: true
        },
        component: () => import('../components/config-general.vue')
    },
    {
        path: '/config/notifications',
        name: 'configNotifications',
        meta: {
            title: 'Config - Notifications',
            header: 'Notifications',
            topMenu: 'config',
            subMenu: configSubMenu,
            converted: true
        },
        component: () => import('../components/config-notifications.vue')
    },
    {
        path: '/config/postProcessing',
        name: 'configPostProcessing',
        meta: {
            title: 'Config - Post-Processing',
            header: 'Post-Processing',
            topMenu: 'config',
            subMenu: configSubMenu,
            converted: true
        },
        component: () => import('../components/config-post-processing.vue')
    },
    {
        path: '/config/providers',
        name: 'configSearchProviders',
        meta: {
            title: 'Config - Providers',
            header: 'Search Providers',
            topMenu: 'config',
            subMenu: configSubMenu
        }
    },
    {
        path: '/config/search',
        name: 'configSearchSettings',
        meta: {
            title: 'Config - Episode Search',
            header: 'Search Settings',
            topMenu: 'config',
            subMenu: configSubMenu,
            converted: true
        },
        component: () => import('../components/config-search.vue')
    },
    {
        path: '/config/subtitles',
        name: 'configSubtitles',
        meta: {
            title: 'Config - Subtitles',
            header: 'Subtitles',
            topMenu: 'config',
            subMenu: configSubMenu
        }
    }
];

/** @type {import('.').Route[]} */
const addShowRoutes = [
    {
        path: '/addShows',
        name: 'addShows',
        meta: {
            title: 'Add Shows',
            header: 'Add Shows',
            topMenu: 'home',
            converted: true
        },
        component: () => import('../components/add-shows.vue')
    },
    {
        path: '/addShows/existingShows',
        name: 'addExistingShows',
        meta: {
            title: 'Add Existing Shows',
            header: 'Add Existing Shows',
            topMenu: 'home',
            converted: true
        },
        component: () => import('../components/new-shows-existing.vue')
    },
    {
        path: '/addShows/newShow',
        name: 'addNewShow',
        meta: {
            title: 'Add New Show',
            header: 'Add New Show',
            topMenu: 'home',
            converted: true
        },
        component: () => import('../components/new-show.vue')
    },
    {
        path: '/addShows/trendingShows',
        name: 'addTrendingShows',
        meta: {
            topMenu: 'home'
        }
    },
    {
        path: '/addShows/popularShows',
        name: 'addPopularShows',
        meta: {
            title: 'Popular Shows',
            header: 'Popular Shows',
            topMenu: 'home'
        }
    },
    {
        path: '/addShows/popularAnime',
        name: 'addPopularAnime',
        meta: {
            title: 'Popular Anime Shows',
            header: 'Popular Anime Shows',
            topMenu: 'home'
        }
    }
];

/** @type {import('.').Route} */
const loginRoute = {
    path: '/login',
    name: 'login',
    meta: {
        title: 'Login'
    },
    component: () => import('../components/login.vue')
};

/** @type {import('.').Route} */
const addRecommendedRoute = {
    path: '/addRecommended',
    name: 'addRecommended',
    meta: {
        title: 'Add Recommended Shows',
        header: 'Add Recommended Shows',
        topMenu: 'home',
        converted: true
    },
    component: () => import('../components/add-recommended.vue')
};

/** @type {import('.').Route} */
const scheduleRoute = {
    path: '/schedule',
    name: 'schedule',
    meta: {
        title: 'Schedule',
        header: 'Schedule',
        topMenu: 'schedule'
    }
};

/** @type {import('.').Route} */
const historyRoute = {
    path: '/history',
    name: 'history',
    meta: {
        title: 'History',
        header: 'History',
        topMenu: 'history',
        subMenu: historySubMenu
    }
};

/** @type {import('.').Route[]} */
const manageRoutes = [
    {
        path: '/manage',
        name: 'manage',
        meta: {
            title: 'Mass Update',
            header: 'Mass Update',
            topMenu: 'manage'
        }
    },
    {
        path: '/manage/backlogOverview',
        name: 'manageBacklogOverview',
        meta: {
            title: 'Backlog Overview',
            header: 'Backlog Overview',
            topMenu: 'manage'
        }
    },
    {
        path: '/manage/episodeStatuses',
        name: 'manageEpisodeOverview',
        meta: {
            title: 'Episode Overview',
            header: 'Episode Overview',
            topMenu: 'manage'
        }
    },
    {
        path: '/manage/failedDownloads',
        name: 'manageFailedDownloads',
        meta: {
            title: 'Failed Downloads',
            header: 'Failed Downloads',
            topMenu: 'manage'
        }
    },
    {
        path: '/manage/manageSearches',
        name: 'manageManageSearches',
        meta: {
            title: 'Manage Searches',
            header: 'Manage Searches',
            topMenu: 'manage'
        }
    },
    {
        path: '/manage/massEdit',
        name: 'manageMassEdit',
        meta: {
            title: 'Mass Edit',
            topMenu: 'manage'
        }
    },
    {
        path: '/manage/subtitleMissed',
        name: 'manageSubtitleMissed',
        meta: {
            title: 'Missing Subtitles',
            header: 'Missing Subtitles',
            topMenu: 'manage'
        }
    },
    {
        path: '/manage/subtitleMissedPP',
        name: 'manageSubtitleMissedPP',
        meta: {
            title: 'Missing Subtitles in Post-Process folder',
            header: 'Missing Subtitles in Post-Process folder',
            topMenu: 'manage'
        }
    }
];

/** @type {import('.').Route[]} */
const errorLogsRoutes = [
    {
        path: '/errorlogs',
        name: 'errorlogs',
        meta: {
            title: 'Logs & Errors',
            topMenu: 'system',
            subMenu: errorlogsSubMenu
        }
    },
    {
        path: '/errorlogs/viewlog',
        name: 'viewlog',
        meta: {
            title: 'Logs',
            header: 'Log File',
            topMenu: 'system',
            converted: true
        },
        component: () => import('../components/logs.vue')
    }
];

/** @type {import('.').Route} */
const newsRoute = {
    path: '/news',
    name: 'news',
    meta: {
        title: 'News',
        header: 'News',
        topMenu: 'system'
    }
};

/** @type {import('.').Route} */
const changesRoute = {
    path: '/changes',
    name: 'changes',
    meta: {
        title: 'Changelog',
        header: 'Changelog',
        topMenu: 'system'
    }
};

/** @type {import('.').Route} */
const ircRoute = {
    path: '/IRC',
    name: 'IRC',
    meta: {
        title: 'IRC',
        topMenu: 'system',
        converted: true
    },
    component: () => import('../components/irc.vue')
};

/** @type {import('.').Route} */
const notFoundRoute = {
    path: '/not-found',
    name: 'not-found',
    meta: {
        title: '404',
        header: '404 - page not found'
    },
    component: () => import('../components/http/404.vue')
};

// @NOTE: Redirect can only be added once all routes are vue
/*
/** @type {import('.').Route} *-/
const notFoundRedirect = {
    path: '*',
    redirect: '/not-found'
};
*/

/** @type {import('.').Route[]} */
export default [
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
