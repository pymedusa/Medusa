import VueRouter from 'vue-router';
import {
    AddRecommended,
    AddShows,
    Config,
    ConfigPostProcessing,
    IRC,
    Login,
    NotFound
} from './components';

const homeRoutes = [{
    path: '/home',
    name: 'home',
    meta: {
        title: 'Home',
        header: 'Show List'
    }
}, {
    path: '/home/editShow',
    name: 'editShow'
}, {
    path: '/home/displayShow',
    name: 'show'
}, {
    path: '/home/snatchSelection',
    name: 'snatchSelection'
}, {
    path: '/home/testRename',
    name: 'testRename',
    meta: {
        title: 'Preview Rename',
        header: 'Preview Rename'
    }
}, {
    path: '/home/postprocess',
    name: 'postprocess',
    meta: {
        title: 'Manual Post-Processing',
        header: 'Manual Post-Processing'
    }
}, {
    path: '/home/status',
    name: 'status',
    meta: {
        title: 'Status'
    }
}, {
    path: '/home/restart',
    name: 'restart',
    meta: {
        title: 'Restarting...',
        header: 'Performing Restart'
    }
}, {
    path: '/home/shutdown',
    name: 'shutdown',
    meta: {
        header: 'Shutting down'
    }
}];

const configRoutes = [{
    path: '/config',
    name: 'config',
    meta: {
        title: 'Help & Info',
        header: 'Medusa Configuration',
        converted: true
    },
    component: Config
}, {
    path: '/config/anime',
    name: 'configAnime',
    meta: {
        title: 'Config - Anime',
        header: 'Anime'
    }
}, {
    path: '/config/backuprestore',
    name: 'configBackupRestore',
    meta: {
        title: 'Config - Backup/Restore',
        header: 'Backup/Restore'
    }
}, {
    path: '/config/general',
    name: 'configGeneral',
    meta: {
        title: 'Config - General',
        header: 'General Configuration'
    }
}, {
    path: '/config/notifications',
    name: 'configNotifications',
    meta: {
        title: 'Config - Notifications',
        header: 'Notifications'
    }
}, {
    path: '/config/postProcessing',
    name: 'configPostProcessing',
    meta: {
        title: 'Config - Post Processing',
        header: 'Post Processing'
    },
    component: ConfigPostProcessing
}, {
    path: '/config/providers',
    name: 'configSearchProviders',
    meta: {
        title: 'Config - Providers',
        header: 'Search Providers'
    }
}, {
    path: '/config/search',
    name: 'configSearchSettings',
    meta: {
        title: 'Config - Episode Search',
        header: 'Search Settings'
    }
}, {
    path: '/config/subtitles',
    name: 'configSubtitles',
    meta: {
        title: 'Config - Subtitles',
        header: 'Subtitles'
    }
}];

const addShowRoutes = [{
    path: '/addShows',
    name: 'addShows',
    meta: {
        title: 'Add Shows',
        header: 'Add Shows',
        converted: true
    },
    component: AddShows
}, {
    path: '/addShows/addExistingShows',
    name: 'addExistingShows',
    meta: {
        title: 'Add Existing Shows',
        header: 'Add Existing Shows'
    }
}, {
    path: '/addShows/newShow',
    name: 'addNewShow',
    meta: {
        title: 'Add New Show',
        header: 'Add New Show'
    }
}, {
    path: '/addShows/trendingShows',
    name: 'addTrendingShows'
}, {
    path: 'popularShows',
    name: 'addPopularShows',
    meta: {
        title: 'Popular Shows',
        header: 'Popular Shows'
    }
}, {
    path: '/addShows/popularAnime',
    name: 'addPopularAnime',
    meta: {
        title: 'Popular Anime Shows',
        header: 'Popular Anime Shows'
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
        header: 'Add Recommended Shows'
    },
    component: AddRecommended
};

const scheduleRoute = {
    path: '/schedule',
    name: 'schedule',
    meta: {
        title: 'Schedule',
        header: 'Schedule'
    }
};

const historyRoute = {
    path: '/history',
    name: 'history',
    meta: {
        title: 'History',
        header: 'History'
    }
};

const manageRoutes = [{
    path: '/manage',
    name: 'manage',
    meta: {
        title: 'Mass Update',
        header: 'Mass Update'
    }
}, {
    path: '/manage/backlogOverview',
    name: 'manageBacklogOverview',
    meta: {
        title: 'Backlog Overview',
        header: 'Backlog Overview'
    }
}, {
    path: '/manage/episodeStatuses',
    name: 'manageEpisodeOverview',
    meta: {
        title: 'Episode Overview',
        header: 'Episode Overview'
    }
}, {
    path: '/manage/failedDownloads',
    name: 'manageFailedDownloads',
    meta: {
        title: 'Failed Downloads',
        header: 'Failed Downlaods'
    }
}, {
    path: '/manage/manageSearches',
    name: 'manageManageSearches',
    meta: {
        title: 'Manage Searches',
        header: 'Manage Searches'
    }
}, {
    path: '/manage/massEdit',
    name: 'manageMassEdit',
    meta: {
        title: 'Mass Edit'
    }
}, {
    path: '/manage/subtitleMissed',
    name: 'manageSubtitleMissed',
    meta: {
        title: 'Missing Subtitles',
        header: 'Missing Subtitles'
    }
}, {
    path: '/manage/subtitleMissedPP',
    name: 'manageSubtitleMissedPP',
    meta: {
        title: 'Missing Subtitles in Post-Process folder',
        header: 'Missing Subtitles in Post-Process folder'
    }
}];

const errorLogsRoutes = [{
    path: '/errorlogs',
    name: 'errorlogs',
    meta: {
        title: 'Logs & Errors'
    }
}, {
    path: '/errorlogs/viewlog',
    name: 'viewlog',
    meta: {
        title: 'Logs',
        header: 'Log File'
    }
}];

const newsRoute = {
    path: '/news',
    name: 'news',
    meta: {
        title: 'News',
        header: 'News'
    }
};

const changesRoute = {
    path: '/changes',
    name: 'changes',
    meta: {
        title: 'Changelog',
        header: 'Changelog'
    }
};

const ircRoute = {
    path: '/IRC',
    name: 'IRC',
    meta: {
        title: 'IRC'
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
