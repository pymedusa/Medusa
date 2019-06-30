const showSubMenu = function() {
    const { $route, $store } = this;
    const { config, notifiers } = $store.state;

    const indexerName = $route.params.indexer || $route.query.indexername;
    const showId = $route.params.id || $route.query.seriesid;

    const show = $store.getters.getCurrentShow;
    const { showQueueStatus } = show;

    const queuedActionStatus = action => {
        if (!showQueueStatus) {
            return false;
        }
        return Boolean(showQueueStatus.find(status => status.action === action && status.active === true));
    };

    const isBeingAdded = queuedActionStatus('isBeingAdded');
    const isBeingUpdated = queuedActionStatus('isBeingUpdated');
    const isBeingSubtitled = queuedActionStatus('isBeingSubtitled');

    let menu = [{
        title: 'Edit',
        path: `home/editShow?indexername=${indexerName}&seriesid=${showId}`,
        icon: 'ui-icon ui-icon-pencil'
    }];
    if (!isBeingAdded && !isBeingUpdated) {
        menu = menu.concat([
            {
                title: show.config.paused ? 'Resume' : 'Pause',
                path: `home/togglePause?indexername=${indexerName}&seriesid=${showId}`,
                icon: `ui-icon ui-icon-${show.config.paused ? 'play' : 'pause'}`
            },
            {
                title: 'Remove',
                path: `home/deleteShow?indexername=${indexerName}&seriesid=${showId}`,
                confirm: 'removeshow',
                icon: 'ui-icon ui-icon-trash'
            },
            {
                title: 'Re-scan files',
                path: `home/refreshShow?indexername=${indexerName}&seriesid=${showId}`,
                icon: 'ui-icon ui-icon-refresh'
            },
            {
                title: 'Force Full Update',
                path: `home/updateShow?indexername=${indexerName}&seriesid=${showId}`,
                icon: 'ui-icon ui-icon-transfer-e-w'
            },
            {
                title: 'Update show in KODI',
                path: `home/updateKODI?indexername=${indexerName}&seriesid=${showId}`,
                requires: notifiers.kodi.enabled && notifiers.kodi.update.library,
                icon: 'menu-icon-kodi'
            },
            {
                title: 'Update show in Emby',
                path: `home/updateEMBY?indexername=${indexerName}&seriesid=${showId}`,
                requires: notifiers.emby.enabled,
                icon: 'menu-icon-emby'
            },
            {
                title: 'Preview Rename',
                path: `home/testRename?indexername=${indexerName}&seriesid=${showId}`,
                icon: 'ui-icon ui-icon-tag'
            },
            {
                title: 'Download Subtitles',
                path: `home/subtitleShow?indexername=${indexerName}&seriesid=${showId}`,
                requires: config.subtitles.enabled && !isBeingSubtitled && show.config.subtitlesEnabled,
                icon: 'menu-icon-backlog'
            }
        ]);
    }
    return menu;
};

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
        topMenu: 'home',
        subMenu: showSubMenu
    },
    component: () => import('../components/edit-show.vue')
}, {
    path: '/home/displayShow',
    name: 'show',
    meta: {
        topMenu: 'home',
        subMenu: showSubMenu
    },
    component: () => import('./components/display-show.vue')
}, {
    path: '/home/snatchSelection',
    name: 'snatchSelection',
    meta: {
        topMenu: 'home',
        subMenu: showSubMenu
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

const configSubMenu = [
    { title: 'General', path: 'config/general/', icon: 'menu-icon-config' },
    { title: 'Backup/Restore', path: 'config/backuprestore/', icon: 'menu-icon-backup' },
    { title: 'Search Settings', path: 'config/search/', icon: 'menu-icon-manage-searches' },
    { title: 'Search Providers', path: 'config/providers/', icon: 'menu-icon-provider' },
    { title: 'Subtitles Settings', path: 'config/subtitles/', icon: 'menu-icon-backlog' },
    { title: 'Post Processing', path: 'config/postProcessing/', icon: 'menu-icon-postprocess' },
    { title: 'Notifications', path: 'config/notifications/', icon: 'menu-icon-notification' },
    { title: 'Anime', path: 'config/anime/', icon: 'menu-icon-anime' }
];
const configRoutes = [{
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
}, {
    path: '/config/anime',
    name: 'configAnime',
    meta: {
        title: 'Config - Anime',
        header: 'Anime',
        topMenu: 'config',
        subMenu: configSubMenu
    }
}, {
    path: '/config/backuprestore',
    name: 'configBackupRestore',
    meta: {
        title: 'Config - Backup/Restore',
        header: 'Backup/Restore',
        topMenu: 'config',
        subMenu: configSubMenu
    }
}, {
    path: '/config/general',
    name: 'configGeneral',
    meta: {
        title: 'Config - General',
        header: 'General Configuration',
        topMenu: 'config',
        subMenu: configSubMenu
    }
}, {
    path: '/config/notifications',
    name: 'configNotifications',
    meta: {
        title: 'Config - Notifications',
        header: 'Notifications',
        topMenu: 'config',
        subMenu: configSubMenu
    }
}, {
    path: '/config/postProcessing',
    name: 'configPostProcessing',
    meta: {
        title: 'Config - Post Processing',
        header: 'Post Processing',
        topMenu: 'config',
        subMenu: configSubMenu,
        converted: true
    },
    component: () => import('../components/config-post-processing.vue')
}, {
    path: '/config/providers',
    name: 'configSearchProviders',
    meta: {
        title: 'Config - Providers',
        header: 'Search Providers',
        topMenu: 'config',
        subMenu: configSubMenu
    }
}, {
    path: '/config/search',
    name: 'configSearchSettings',
    meta: {
        title: 'Config - Episode Search',
        header: 'Search Settings',
        topMenu: 'config',
        subMenu: configSubMenu
    }
}, {
    path: '/config/subtitles',
    name: 'configSubtitles',
    meta: {
        title: 'Config - Subtitles',
        header: 'Subtitles',
        topMenu: 'config',
        subMenu: configSubMenu
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
    component: () => import('../components/add-shows.vue')
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
    component: () => import('../components/login.vue')
};

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

const scheduleRoute = {
    path: '/schedule',
    name: 'schedule',
    meta: {
        title: 'Schedule',
        header: 'Schedule',
        topMenu: 'schedule'
    }
};

const historySubMenu = [
    { title: 'Clear History', path: 'history/clearHistory', icon: 'ui-icon ui-icon-trash', confirm: 'clearhistory' },
    { title: 'Trim History', path: 'history/trimHistory', icon: 'menu-icon-cut', confirm: 'trimhistory' }
];
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
        header: 'Failed Downloads',
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

const errorlogsSubMenu = function() {
    const { $route, $store } = this;
    const level = $route.params.level || $route.query.level;
    const { config } = $store.state;
    const { loggingLevels, numErrors, numWarnings } = config.logs;
    if (Object.keys(loggingLevels).length === 0) {
        return [];
    }

    const isLevelError = (level === undefined || Number(level) === loggingLevels.error);

    return [
        {
            title: 'Clear Errors',
            path: 'errorlogs/clearerrors/',
            requires: numErrors >= 1 && isLevelError,
            icon: 'ui-icon ui-icon-trash'
        },
        {
            title: 'Clear Warnings',
            path: `errorlogs/clearerrors/?level=${loggingLevels.warning}`,
            requires: numWarnings >= 1 && Number(level) === loggingLevels.warning,
            icon: 'ui-icon ui-icon-trash'
        },
        {
            title: 'Submit Errors',
            path: 'errorlogs/submit_errors/',
            requires: numErrors >= 1 && isLevelError,
            confirm: 'submiterrors',
            icon: 'ui-icon ui-icon-arrowreturnthick-1-n'
        }
    ];
};
const errorLogsRoutes = [{
    path: '/errorlogs',
    name: 'errorlogs',
    meta: {
        title: 'Logs & Errors',
        topMenu: 'system',
        subMenu: errorlogsSubMenu
    }
}, {
    path: '/errorlogs/viewlog',
    name: 'viewlog',
    meta: {
        title: 'Logs',
        header: 'Log File',
        topMenu: 'system',
        converted: true
    },
    component: () => import('../components/logs.vue')
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
        topMenu: 'system',
        converted: true
    },
    component: () => import('../components/irc.vue')
};

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
const notFoundRedirect = {
    path: '*',
    redirect: '/not-found'
};
*/

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
