<script type="text/x-template" id="app-header-template">
<!-- BEGIN HEADER -->
<nav class="navbar navbar-default navbar-fixed-top hidden-print" role="navigation">
    <div class="container-fluid">
        <div class="navbar-header">
            <button type="button" class="navbar-toggle collapsed" data-toggle="collapse" data-target="#main_nav">
                <span v-if="toolsBadgeCount > 0" :class="'floating-badge' + toolsBadgeClass">{{ toolsBadgeCount }}</span>
                <span class="sr-only">Toggle navigation</span>
                <span class="icon-bar"></span>
                <span class="icon-bar"></span>
                <span class="icon-bar"></span>
            </button>
            <app-link class="navbar-brand" href="home/" title="Medusa"><img alt="Medusa" src="images/medusa.png" style="height: 50px;" class="img-responsive pull-left" /></app-link>
        </div>
        <div v-if="loggedIn" class="collapse navbar-collapse" id="main_nav">
            <ul class="nav navbar-nav navbar-right">
                <li id="NAVhome" class="navbar-split dropdown" :class="{ active: topMenu === 'home' }">
                    <app-link href="home/" class="dropdown-toggle" aria-haspopup="true" data-toggle="dropdown" data-hover="dropdown"><span>Shows</span>
                    <b class="caret"></b>
                    </app-link>
                    <ul class="dropdown-menu">
                        <li><app-link href="home/"><i class="menu-icon-home"></i>&nbsp;Show List</app-link></li>
                        <li><app-link href="addShows/"><i class="menu-icon-addshow"></i>&nbsp;Add Shows</app-link></li>
                        <li><app-link href="addRecommended/"><i class="menu-icon-addshow"></i>&nbsp;Add Recommended Shows</app-link></li>
                        <li><app-link href="home/postprocess/"><i class="menu-icon-postprocess"></i>&nbsp;Manual Post-Processing</app-link></li>
                        <template v-if="recentShows.length > 0">
                        <li role="separator" class="divider"></li>
                        <li v-for="recentShow in recentShows">
                            <app-link :indexer-id="String(recentShow.indexer)" :href="'home/displayShow?indexername=indexer-to-name&amp;seriesid=' + recentShow.indexerid">
                                <i class="menu-icon-addshow"></i>&nbsp;{{ recentShow.name }}
                            </app-link>
                        </li>
                        </template>
                    </ul>
                    <div style="clear:both;"></div>
                </li>
                <li id="NAVschedule" :class="{ active: topMenu === 'schedule' }">
                    <app-link href="schedule/">Schedule</app-link>
                </li>
                <li id="NAVhistory" :class="{ active: topMenu === 'history' }">
                    <app-link href="history/">History</app-link>
                </li>
                <li id="NAVmanage" class="navbar-split dropdown" :class="{ active: topMenu === 'manage' }">
                    <app-link href="manage/episodeStatuses/" class="dropdown-toggle" aria-haspopup="true" data-toggle="dropdown" data-hover="dropdown"><span>Manage</span>
                    <b class="caret"></b>
                    </app-link>
                    <ul class="dropdown-menu">
                        <li><app-link href="manage/"><i class="menu-icon-manage"></i>&nbsp;Mass Update</app-link></li>
                        <li><app-link href="manage/backlogOverview/"><i class="menu-icon-backlog-view"></i>&nbsp;Backlog Overview</app-link></li>
                        <li><app-link href="manage/manageSearches/"><i class="menu-icon-manage-searches"></i>&nbsp;Manage Searches</app-link></li>
                        <li><app-link href="manage/episodeStatuses/"><i class="menu-icon-manage2"></i>&nbsp;Episode Status Management</app-link></li>
                        <li v-if="linkVisible.plex"><app-link href="home/updatePLEX/"><i class="menu-icon-plex"></i>&nbsp;Update PLEX</app-link></li>
                        <li v-if="linkVisible.kodi"><app-link href="home/updateKODI/"><i class="menu-icon-kodi"></i>&nbsp;Update KODI</app-link></li>
                        <li v-if="linkVisible.emby"><app-link href="home/updateEMBY/"><i class="menu-icon-emby"></i>&nbsp;Update Emby</app-link></li>
                        ## Avoid mixed content blocking by open manage torrent in new tab
                        <li v-if="linkVisible.manageTorrents"><app-link href="manage/manageTorrents/" target="_blank"><i class="menu-icon-bittorrent"></i>&nbsp;Manage Torrents</app-link></li>
                        <li v-if="failedDownloadsEnabled"><app-link href="manage/failedDownloads/"><i class="menu-icon-failed-download"></i>&nbsp;Failed Downloads</app-link></li>
                        <li v-if="config.subtitles.enabled"><app-link href="manage/subtitleMissed/"><i class="menu-icon-backlog"></i>&nbsp;Missed Subtitle Management</app-link></li>
                        <li v-if="postponeIfNoSubs"><app-link href="manage/subtitleMissedPP/"><i class="menu-icon-backlog"></i>&nbsp;Missed Subtitle in Post-Process folder</app-link></li>
                    </ul>
                    <div style="clear:both;"></div>
                </li>
                <li id="NAVconfig" class="navbar-split dropdown" :class="{ active: topMenu === 'config' }">
                    <app-link href="config/" class="dropdown-toggle" aria-haspopup="true" data-toggle="dropdown" data-hover="dropdown"><span class="visible-xs-inline">Config</span><img src="images/menu/system18.png" class="navbaricon hidden-xs" />
                    <b class="caret"></b>
                    </app-link>
                    <ul class="dropdown-menu">
                        <li><app-link href="config/"><i class="menu-icon-help"></i>&nbsp;Help &amp; Info</app-link></li>
                        <li><app-link href="config/general/"><i class="menu-icon-config"></i>&nbsp;General</app-link></li>
                        <li><app-link href="config/backuprestore/"><i class="menu-icon-backup"></i>&nbsp;Backup &amp; Restore</app-link></li>
                        <li><app-link href="config/search/"><i class="menu-icon-manage-searches"></i>&nbsp;Search Settings</app-link></li>
                        <li><app-link href="config/providers/"><i class="menu-icon-provider"></i>&nbsp;Search Providers</app-link></li>
                        <li><app-link href="config/subtitles/"><i class="menu-icon-backlog"></i>&nbsp;Subtitles Settings</app-link></li>
                        <li><app-link href="config/postProcessing/"><i class="menu-icon-postprocess"></i>&nbsp;Post Processing</app-link></li>
                        <li><app-link href="config/notifications/"><i class="menu-icon-notification"></i>&nbsp;Notifications</app-link></li>
                        <li><app-link href="config/anime/"><i class="menu-icon-anime"></i>&nbsp;Anime</app-link></li>
                    </ul>
                    <div style="clear:both;"></div>
                </li>
                <li id="NAVsystem" class="navbar-split dropdown" :class="{ active: topMenu === 'system' }">
                    <app-link href="home/status/" class="padding-right-15 dropdown-toggle" aria-haspopup="true" data-toggle="dropdown" data-hover="dropdown"><span class="visible-xs-inline">Tools</span><img src="images/menu/system18-2.png" class="navbaricon hidden-xs" />
                    <span v-if="toolsBadgeCount > 0" :class="'badge' + toolsBadgeClass">{{ toolsBadgeCount }}</span>
                    <b class="caret"></b>
                    </app-link>
                    <ul class="dropdown-menu">
                        <li><app-link href="news/"><i class="menu-icon-news"></i>&nbsp;News <span v-if="config.news.unread > 0" class="badge">{{ config.news.unread }}</span></app-link></li>
                        <li><app-link href="IRC/"><i class="menu-icon-irc"></i>&nbsp;IRC</app-link></li>
                        <li><app-link href="changes/"><i class="menu-icon-changelog"></i>&nbsp;Changelog</app-link></li>
                        <li><app-link :href="donationsUrl"><i class="menu-icon-support"></i>&nbsp;Support Medusa</app-link></li>
                        <li role="separator" class="divider"></li>
                        <li v-if="numErrors > 0"><app-link href="errorlogs/"><i class="menu-icon-error"></i>&nbsp;View Errors <span class="badge btn-danger">{{numErrors}}</span></app-link></li>
                        <li v-if="numWarnings > 0"><app-link :href="'errorlogs/?level=' + loggerWarning"><i class="menu-icon-viewlog-errors"></i>&nbsp;View Warnings <span class="badge btn-warning">{{numWarnings}}</span></app-link></li>
                        <li><app-link href="errorlogs/viewlog/"><i class="menu-icon-viewlog"></i>&nbsp;View Log</app-link></li>
                        <li role="separator" class="divider"></li>
                        <li><app-link :href="'home/updateCheck?pid=' + medusaPID"><i class="menu-icon-update"></i>&nbsp;Check For Updates</app-link></li>
                        <li><app-link :href="'home/restart/?pid=' + medusaPID" class="confirm restart"><i class="menu-icon-restart"></i>&nbsp;Restart</app-link></li>
                        <li><app-link :href="'home/shutdown/?pid=' + medusaPID" class="confirm shutdown"><i class="menu-icon-shutdown"></i>&nbsp;Shutdown</app-link></li>
                        <li v-if="loggedIn !== true"><app-link href="logout" class="confirm logout"><i class="menu-icon-shutdown"></i>&nbsp;Logout</app-link></li>
                        <li role="separator" class="divider"></li>
                        <li><app-link href="home/status/"><i class="menu-icon-info"></i>&nbsp;Server Status</app-link></li>
                    </ul>
                    <div style="clear:both;"></div>
                </li>
            </ul>
        </div><!-- /.navbar-collapse -->
    </div><!-- /.container-fluid -->
</nav>
<!-- END HEADER -->
</script>
<%!
    import json
    from medusa import app, logger
%>
<script>
Vue.component('app-header', {
    template: '#app-header-template',
    data() {
        return {
            // Python conversions
            medusaPID: ${json.dumps(sbPID)},
            loggedIn: ${json.dumps(loggedIn)},
            recentShows: ${json.dumps(app.SHOWS_RECENT)},
            numErrors: ${numErrors}, // numeric
            numWarnings: ${numWarnings}, // numeric
            donationsUrl: ${json.dumps(app.DONATIONS_URL)},
            loggerWarning: ${logger.WARNING}, // numeric

            <% has_emby_api_key = json.dumps(app.EMBY_APIKEY != '') %>
            hasEmbyApiKey: ${has_emby_api_key},

            failedDownloadsEnabled: ${json.dumps(bool(app.USE_FAILED_DOWNLOADS))},
            postponeIfNoSubs: ${json.dumps(bool(app.POSTPONE_IF_NO_SUBS))},

            // JS Only
            topMenuMapping: {
                system: ['/home/restart', '/home/status', '/errorlogs', '/changes', '/news', '/IRC'],
                home: ['/home', '/addShows', '/addRecommended'],
                config: ['/config'],
                history: ['/history'],
                schedule: ['/schedule'],
                manage: ['/manage'],
                login: ['/login']
            }
        };
    },
    computed: {
        topMenu() {
            // This is a workaround, until we're able to use VueRouter to determine that.
            // The possible `topmenu` values are: config, history, schedule, system, home, manage, login [unused]
            const { topMenuMapping } = this;
            const { pathname } = window.location;

            for (const item of Object.entries(topMenuMapping)) {
                const [topmenu, routes] = item; // Unpacking
                for (const route of routes) {
                    if (pathname.includes(route)) {
                        return topmenu;
                    }
                }
            }
            return null;
        },
        toolsBadgeCount() {
            const { config, numErrors, numWarnings } = this;
            const { news } = config;
            return numErrors + numWarnings + news.unread;
        },
        toolsBadgeClass() {
            const { numErrors, numWarnings } = this;
            if (numErrors > 0) {
                return ' btn-danger';
            }
            if (numWarnings > 0) {
                return ' btn-warning';
            }
            return '';
        },
        linkVisible() {
            const { config } = this;
            const { plex, kodi, emby, torrents, hasEmbyApiKey } = config;

            return {
                plex: plex.server.enabled && plex.server.host.length !== 0,
                kodi: kodi.enabled && kodi.host.length !== 0,
                emby: emby.enabled && emby.host && hasEmbyApiKey,
                manageTorrents: torrents.enabled && torrents.method !== 'blackhole'
            };
        }
    }
});
</script>
<style>
.floating-badge {
    position: absolute;
    top: -5px;
    right: -8px;
    padding: 0 4px;
    background-color: #777;
    border: 2px solid #959595;
    border-radius: 100px;
    font-size: 12px;
    font-weight: bold;
    text-decoration: none;
    color: white;
}
</style>
