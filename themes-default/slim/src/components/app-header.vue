<template>
    <nav class="navbar navbar-default navbar-fixed-top hidden-print" role="navigation">
        <div class="container-fluid">
            <div class="navbar-header">
                <button type="button" class="navbar-toggle collapsed" data-toggle="collapse" data-target="#main_nav">
                    <span v-if="toolsBadgeCount > 0" :class="`floating-badge${toolsBadgeClass}`">{{ toolsBadgeCount }}</span>
                    <span class="sr-only">Toggle navigation</span>
                    <span class="icon-bar"></span>
                    <span class="icon-bar"></span>
                    <span class="icon-bar"></span>
                </button>
                <app-link class="navbar-brand" href="home/" title="Medusa"><img alt="Medusa" src="images/medusa.png" style="height: 50px;" class="img-responsive pull-left" /></app-link>
            </div>
            <div v-if="auth.isAuthenticated" class="collapse navbar-collapse" id="main_nav">
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
                            <li v-for="recentShow in recentShows" :key="recentShow.link">
                                <app-link :href="recentShow.link">
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
                        <app-link href="manage/episodeStatuses/" class="dropdown-toggle" aria-haspopup="true" data-toggle="dropdown" data-hover="dropdown">
                            <span>Manage</span> <b class="caret"></b>
                        </app-link>
                        <ul class="dropdown-menu">
                            <li><app-link href="manage/"><i class="menu-icon-manage"></i>&nbsp;Mass Update</app-link></li>
                            <li><app-link href="manage/backlogOverview/"><i class="menu-icon-backlog-view"></i>&nbsp;Backlog Overview</app-link></li>
                            <li><app-link href="manage/manageSearches/"><i class="menu-icon-manage-searches"></i>&nbsp;Manage Searches</app-link></li>
                            <li><app-link href="manage/episodeStatuses/"><i class="menu-icon-manage2"></i>&nbsp;Episode Status Management</app-link></li>
                            <li v-if="linkVisible.plex"><app-link href="home/updatePLEX/"><i class="menu-icon-plex"></i>&nbsp;Update PLEX</app-link></li>
                            <li v-if="linkVisible.kodi"><app-link href="home/updateKODI/"><i class="menu-icon-kodi"></i>&nbsp;Update KODI</app-link></li>
                            <li v-if="linkVisible.emby"><app-link href="home/updateEMBY/"><i class="menu-icon-emby"></i>&nbsp;Update Emby</app-link></li>
                            <!-- Avoid mixed content blocking by open manage torrent in new tab -->
                            <li v-if="linkVisible.manageTorrents"><app-link href="manage/manageTorrents/" target="_blank"><i class="menu-icon-bittorrent"></i>&nbsp;Manage Torrents</app-link></li>
                            <li v-if="linkVisible.failedDownloads"><app-link href="manage/failedDownloads/"><i class="menu-icon-failed-download"></i>&nbsp;Failed Downloads</app-link></li>
                            <li v-if="linkVisible.subtitleMissed"><app-link href="manage/subtitleMissed/"><i class="menu-icon-backlog"></i>&nbsp;Missed Subtitle Management</app-link></li>
                            <li v-if="linkVisible.subtitleMissedPP"><app-link href="manage/subtitleMissedPP/"><i class="menu-icon-backlog"></i>&nbsp;Missed Subtitle in Post-Process folder</app-link></li>
                        </ul>
                        <div style="clear:both;"></div>
                    </li>
                    <li id="NAVconfig" class="navbar-split dropdown" :class="{ active: topMenu === 'config' }">
                        <app-link href="config/" class="dropdown-toggle" aria-haspopup="true" data-toggle="dropdown" data-hover="dropdown">
                            <span class="visible-xs-inline">Config</span><img src="images/menu/system18.png" class="navbaricon hidden-xs" /> <b class="caret"></b>
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
                            <span v-if="toolsBadgeCount > 0" :class="`badge${toolsBadgeClass}`">{{ toolsBadgeCount }}</span>
                            <b class="caret"></b>
                        </app-link>
                        <ul class="dropdown-menu">
                            <li><app-link href="news/"><i class="menu-icon-news"></i>&nbsp;News <span v-if="config.news.unread > 0" class="badge">{{ config.news.unread }}</span></app-link></li>
                            <li><app-link href="IRC/"><i class="menu-icon-irc"></i>&nbsp;IRC</app-link></li>
                            <li><app-link href="changes/"><i class="menu-icon-changelog"></i>&nbsp;Changelog</app-link></li>
                            <li><app-link :href="config.donationsUrl"><i class="menu-icon-support"></i>&nbsp;Support Medusa</app-link></li>
                            <li role="separator" class="divider"></li>
                            <li v-if="config.logs.numErrors > 0"><app-link href="errorlogs/"><i class="menu-icon-error"></i>&nbsp;View Errors <span class="badge btn-danger">{{config.logs.numErrors}}</span></app-link></li>
                            <li v-if="config.logs.numWarnings > 0"><app-link :href="`errorlogs/?level=${warningLevel}`"><i class="menu-icon-viewlog-errors"></i>&nbsp;View Warnings <span class="badge btn-warning">{{config.logs.numWarnings}}</span></app-link></li>
                            <li><app-link href="errorlogs/viewlog/"><i class="menu-icon-viewlog"></i>&nbsp;View Log</app-link></li>
                            <li role="separator" class="divider"></li>
                            <li><app-link :href="`home/updateCheck?pid=${config.pid}`"><i class="menu-icon-update"></i>&nbsp;Check For Updates</app-link></li>
                            <li><app-link :href="`home/restart/?pid=${config.pid}`" @click.native.prevent="confirmDialog($event, 'restart')"><i class="menu-icon-restart"></i>&nbsp;Restart</app-link></li>
                            <li><app-link :href="`home/shutdown/?pid=${config.pid}`" @click.native.prevent="confirmDialog($event, 'shutdown')"><i class="menu-icon-shutdown"></i>&nbsp;Shutdown</app-link></li>
                            <li v-if="auth.user.username"><app-link href="logout" @click.native.prevent="confirmDialog($event, 'logout')"><i class="menu-icon-shutdown"></i>&nbsp;Logout</app-link></li>
                            <li role="separator" class="divider"></li>
                            <li><app-link href="home/status/"><i class="menu-icon-info"></i>&nbsp;Server Status</app-link></li>
                        </ul>
                        <div style="clear:both;"></div>
                    </li>
                </ul>
            </div><!-- /.navbar-collapse -->
        </div><!-- /.container-fluid -->
    </nav>
</template>
<script>
import AppLink from './app-link.vue';

module.exports = {
    name: 'app-header',
    components: {
        AppLink
    },
    data() {
        return {
            topMenuMapping: [
                ['system', ['/home/restart', '/home/status', '/errorlogs', '/changes', '/news', '/IRC']],
                ['home', ['/home', '/addShows', '/addRecommended']],
                ['config', ['/config']],
                ['history', ['/history']],
                ['schedule', ['/schedule']],
                ['manage', ['/manage']],
                ['login', ['/login']]
            ]
        };
    },
    computed: {
        config() {
            return this.$store.state.config;
        },
        auth() {
            return this.$store.state.auth;
        },
        warningLevel() {
            return this.config.logs.loggingLevels.warning;
        },
        recentShows() {
            const { config } = this;
            const { recentShows } = config;
            return recentShows.map(show => {
                const { name, indexerName, showId } = show;
                const link = `home/displayShow?indexername=${indexerName}&seriesid=${showId}`;
                return { name, link };
            });
        },
        topMenu() {
            // This is a workaround, until we're able to use VueRouter to determine that.
            // The possible `topmenu` values are: config, history, schedule, system, home, manage, login [unused]
            const { topMenuMapping } = this;
            const { pathname } = window.location;

            for (const item of topMenuMapping) {
                const [topMenu, routes] = item; // Unpacking
                for (const route of routes) {
                    if (pathname.includes(route)) {
                        return topMenu;
                    }
                }
            }
            return null;
        },
        toolsBadgeCount() {
            const { config } = this;
            const { news, logs } = config;
            return logs.numErrors + logs.numWarnings + news.unread;
        },
        toolsBadgeClass() {
            const { config } = this;
            const { logs } = config;
            if (logs.numErrors > 0) {
                return ' btn-danger';
            }
            if (logs.numWarnings > 0) {
                return ' btn-warning';
            }
            return '';
        },
        linkVisible() {
            const { config } = this;
            const { plex, kodi, emby, torrents, failedDownloads, subtitles, postProcessing } = config;

            return {
                plex: plex.server.enabled && plex.server.host.length !== 0,
                kodi: kodi.enabled && kodi.host.length !== 0,
                /* @TODO: Originally there was a check to make sure the API key
                   was configured for Emby: ` app.EMBY_APIKEY != '' ` */
                emby: emby.enabled && emby.host,
                manageTorrents: torrents.enabled && torrents.method !== 'blackhole',
                failedDownloads: failedDownloads.enabled,
                subtitleMissed: subtitles.enabled,
                subtitleMissedPP: postProcessing.postponeIfNoSubs
            };
        }
    },
    mounted() {
        const { $el } = this;

        // Hover Dropdown for Nav
        $($el).on({
            mouseenter(event) {
                const $target = $(event.currentTarget);
                $target.find('.dropdown-menu').stop(true, true).delay(200).fadeIn(500, () => {
                    $target.find('.dropdown-toggle').attr('aria-expanded', 'true');
                });
            },
            mouseleave(event) {
                const $target = $(event.currentTarget);
                $target.find('.dropdown-toggle').attr('aria-expanded', 'false');
                $target.find('.dropdown-menu').stop(true, true).delay(200).fadeOut(500);
            }
        }, 'ul.nav li.dropdown');

        // @TODO Replace this with a real touchscreen check
        // hack alert: if we don't have a touchscreen, and we are already hovering the mouse, then click should link instead of toggle
        if ((navigator.maxTouchPoints || 0) < 2) {
            $($el).on('click', '.dropdown-toggle', event => {
                const $target = $(event.currentTarget);
                if ($target.attr('aria-expanded') === 'true') {
                    window.location.href = $target.attr('href');
                }
            });
        }
    },
    methods: {
        confirmDialog(event, action) {
            const options = {
                confirmButton: 'Yes',
                cancelButton: 'Cancel',
                dialogClass: 'modal-dialog',
                post: false,
                button: $(event.currentTarget),
                confirm($element) {
                    window.location.href = $element[0].href;
                }
            };

            if (action === 'restart') {
                options.title = 'Restart';
                options.text = 'Are you sure you want to restart Medusa?';
            } else if (action === 'shutdown') {
                options.title = 'Shutdown';
                options.text = 'Are you sure you want to shutdown Medusa?';
            } else if (action === 'logout') {
                options.title = 'Logout';
                options.text = 'Are you sure you want to logout from Medusa?';
            } else {
                return;
            }

            $.confirm(options, event);
        }
    }
};
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
