/** @type {import('.').SubMenu} */
export const configSubMenu = [
    { title: 'General', path: 'config/general/', icon: 'menu-icon-config' },
    { title: 'Backup/Restore', path: 'config/backuprestore/', icon: 'menu-icon-backup' },
    { title: 'Search Settings', path: 'config/search/', icon: 'menu-icon-manage-searches' },
    { title: 'Search Providers', path: 'config/providers/', icon: 'menu-icon-provider' },
    { title: 'Subtitles Settings', path: 'config/subtitles/', icon: 'menu-icon-backlog' },
    { title: 'Post-Processing', path: 'config/postProcessing/', icon: 'menu-icon-postprocess' },
    { title: 'Notifications', path: 'config/notifications/', icon: 'menu-icon-notification' },
    { title: 'Anime', path: 'config/anime/', icon: 'menu-icon-anime' }
];

// eslint-disable-next-line valid-jsdoc
/** @type {import('.').SubMenuFunction} */
export const errorlogsSubMenu = vm => {
    const { $route, $store } = vm;
    const level = $route.params.level || $route.query.level;
    const { config } = $store.state;
    const { loggingLevels, numErrors, numWarnings } = config.general.logs;
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

/** @type {import('.').SubMenu} */
export const historySubMenu = [
    { title: 'Clear History', path: 'history/clearHistory', icon: 'ui-icon ui-icon-trash', confirm: 'clearhistory' },
    { title: 'Trim History', path: 'history/trimHistory', icon: 'menu-icon-cut', confirm: 'trimhistory' }
];

// eslint-disable-next-line valid-jsdoc
/** @type {import('.').SubMenuFunction} */
export const showSubMenu = vm => {
    const { $route, $store } = vm;
    const { config } = $store.state;
    const { notifiers } = config;

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

    /** @type {import('.').SubMenu} */
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
                requires: config.general.subtitles.enabled && !isBeingSubtitled && show.config.subtitlesEnabled,
                icon: 'menu-icon-backlog'
            }
        ]);
    }
    return menu;
};
