<template>
    <nav class="navbar navbar-default navbar-fixed-top hidden-print" role="navigation">
        <div class="container-fluid">
            <div class="navbar-header">
                <button type="button" class="navbar-toggle collapsed" data-toggle="collapse" data-target="#main_nav">
                    <span v-if="toolsBadgeCount > 0" :class="`floating-badge${toolsBadgeClass}`">{{ toolsBadgeCount }}</span>
                    <span class="sr-only">Toggle navigation</span>
                    <span class="icon-bar" />
                    <span class="icon-bar" />
                    <span class="icon-bar" />
                </button>
                <app-link class="navbar-brand" href="home/" title="Medusa"><img alt="Medusa" src="images/medusa.png" style="height: 50px;" class="img-responsive pull-left"></app-link>
            </div>
            <div v-if="isAuthenticated" class="collapse navbar-collapse" id="main_nav">
                <ul class="nav navbar-nav navbar-right">
                    <li id="NAVhome" class="navbar-split dropdown" :class="{ active: topMenu === 'home' }">
                        <app-link href="home/" class="dropdown-toggle" aria-haspopup="true" data-toggle="dropdown" data-hover="dropdown"><span>Shows</span>
                            <b class="caret" />
                        </app-link>
                        <ul class="dropdown-menu">
                            <li><app-link href="home/"><i class="menu-icon-home" />&nbsp;Show List</app-link></li>
                            <li><app-link href="addShows/"><i class="menu-icon-addshow" />&nbsp;Add Shows</app-link></li>
                            <li><app-link href="addRecommended/"><i class="menu-icon-addshow" />&nbsp;Add Recommended Shows</app-link></li>
                            <li><app-link href="home/postprocess/"><i class="menu-icon-postprocess" />&nbsp;Manual Post-Processing</app-link></li>
                            <li v-if="recentShows.length > 0" role="separator" class="divider" />
                            <li v-for="recentShow in recentShows" :key="recentShow.link">
                                <app-link :href="recentShow.link">
                                    <i class="menu-icon-addshow" />&nbsp;{{ recentShow.name }}
                                </app-link>
                            </li>
                        </ul>
                        <div style="clear:both;" />
                    </li>
                    <li id="NAVschedule" class="navbar-split" :class="{ active: topMenu === 'schedule' }">
                        <app-link href="schedule/">Schedule</app-link>
                    </li>
                    <li id="NAVhistory" class="navbar-split" :class="{ active: topMenu === 'history' }">
                        <app-link href="history/">History</app-link>
                    </li>
                    <li id="NAVmanage" class="navbar-split dropdown" :class="{ active: topMenu === 'manage' }">
                        <app-link href="manage/episodeStatuses/" class="dropdown-toggle" aria-haspopup="true" data-toggle="dropdown" data-hover="dropdown">
                            <span>Manage</span> <b class="caret" />
                        </app-link>
                        <ul class="dropdown-menu">
                            <li><app-link href="manage/"><i class="menu-icon-manage" />&nbsp;Mass Update</app-link></li>
                            <li><app-link href="manage/backlogOverview/"><i class="menu-icon-backlog-view" />&nbsp;Backlog Overview</app-link></li>
                            <li><app-link href="manage/manageSearches/"><i class="menu-icon-manage-searches" />&nbsp;Manage Searches</app-link></li>
                            <li><app-link href="manage/episodeStatuses/"><i class="menu-icon-manage2" />&nbsp;Episode Status Management</app-link></li>
                            <li v-if="linkVisible.plex"><app-link href="home/updatePLEX/"><i class="menu-icon-plex" />&nbsp;Update PLEX</app-link></li>
                            <li v-if="linkVisible.kodi"><app-link href="home/updateKODI/"><i class="menu-icon-kodi" />&nbsp;Update KODI</app-link></li>
                            <li v-if="linkVisible.emby"><app-link href="home/updateEMBY/"><i class="menu-icon-emby" />&nbsp;Update Emby</app-link></li>
                            <!-- Avoid mixed content blocking by open manage torrent in new tab -->
                            <li v-if="linkVisible.manageTorrents"><app-link href="manage/manageTorrents/" target="_blank"><i class="menu-icon-bittorrent" />&nbsp;Manage Torrents</app-link></li>
                            <li v-if="linkVisible.failedDownloads"><app-link href="manage/failedDownloads/"><i class="menu-icon-failed-download" />&nbsp;Failed Downloads</app-link></li>
                            <li v-if="linkVisible.subtitleMissed"><app-link href="manage/subtitleMissed/"><i class="menu-icon-backlog" />&nbsp;Missed Subtitle Management</app-link></li>
                            <li v-if="linkVisible.subtitleMissedPP"><app-link href="manage/subtitleMissedPP/"><i class="menu-icon-backlog" />&nbsp;Missed Subtitle in Post-Process folder</app-link></li>
                        </ul>
                        <div style="clear:both;" />
                    </li>
                    <li id="NAVconfig" class="navbar-split dropdown" :class="{ active: topMenu === 'config' }">
                        <app-link href="config/" class="dropdown-toggle" aria-haspopup="true" data-toggle="dropdown" data-hover="dropdown">
                            <span class="visible-xs-inline">Config</span><img src="images/menu/system18.png" class="navbaricon hidden-xs"> <b class="caret" />
                        </app-link>
                        <ul class="dropdown-menu">
                            <li><app-link href="config/"><i class="menu-icon-help" />&nbsp;Help &amp; Info</app-link></li>
                            <li><app-link href="config/general/"><i class="menu-icon-config" />&nbsp;General</app-link></li>
                            <li><app-link href="config/backuprestore/"><i class="menu-icon-backup" />&nbsp;Backup &amp; Restore</app-link></li>
                            <li><app-link href="config/search/"><i class="menu-icon-manage-searches" />&nbsp;Search Settings</app-link></li>
                            <li><app-link href="config/providers/"><i class="menu-icon-provider" />&nbsp;Search Providers</app-link></li>
                            <li><app-link href="config/subtitles/"><i class="menu-icon-backlog" />&nbsp;Subtitles Settings</app-link></li>
                            <li><app-link href="config/postProcessing/"><i class="menu-icon-postprocess" />&nbsp;Post-Processing</app-link></li>
                            <li><app-link href="config/notifications/"><i class="menu-icon-notification" />&nbsp;Notifications</app-link></li>
                            <li><app-link href="config/anime/"><i class="menu-icon-anime" />&nbsp;Anime</app-link></li>
                        </ul>
                        <div style="clear:both;" />
                    </li>
                    <li id="NAVsystem" class="navbar-split dropdown" :class="{ active: topMenu === 'system' }">
                        <app-link href="home/status/" class="padding-right-15 dropdown-toggle" aria-haspopup="true" data-toggle="dropdown" data-hover="dropdown"><span class="visible-xs-inline">Tools</span><img src="images/menu/system18-2.png" class="navbaricon hidden-xs">
                            <span v-if="toolsBadgeCount > 0" :class="`badge${toolsBadgeClass}`">{{ toolsBadgeCount }}</span>
                            <b class="caret" />
                        </app-link>
                        <ul class="dropdown-menu">
                            <li><app-link href="news/"><i class="menu-icon-news" />&nbsp;News <span v-if="system.news.unread > 0" class="badge">{{ system.news.unread }}</span></app-link></li>
                            <li><app-link href="IRC/"><i class="menu-icon-irc" />&nbsp;IRC</app-link></li>
                            <li><app-link href="changes/"><i class="menu-icon-changelog" />&nbsp;Changelog</app-link></li>
                            <li role="separator" class="divider" />
                            <li v-if="config.logs.numErrors > 0"><app-link href="errorlogs/"><i class="menu-icon-error" />&nbsp;View Errors <span class="badge btn-danger">{{config.logs.numErrors}}</span></app-link></li>
                            <li v-if="config.logs.numWarnings > 0"><app-link :href="`errorlogs/?level=${warningLevel}`"><i class="menu-icon-viewlog-errors" />&nbsp;View Warnings <span class="badge btn-warning">{{config.logs.numWarnings}}</span></app-link></li>
                            <li><app-link href="errorlogs/viewlog/"><i class="menu-icon-viewlog" />&nbsp;View Log</app-link></li>
                            <li role="separator" class="divider" />
                            <li><app-link :href="'home/update'" @click.native.prevent="checkForupdates($event)"><i class="menu-icon-update" />&nbsp;Check For Updates</app-link></li>
                            <li><app-link :href="'home/restart'"><i class="menu-icon-restart" />&nbsp;Restart</app-link></li>
                            <li><app-link :href="'home/shutdown'" @click.prevent="$router.push({ name: 'shutdown' });"><i class="menu-icon-shutdown" />&nbsp;Shutdown</app-link></li>
                            <li v-if="username"><app-link href="logout" @click.native.prevent="confirmDialog($event, 'logout')"><i class="menu-icon-shutdown" />&nbsp;Logout</app-link></li>
                            <li role="separator" class="divider" />
                            <li><app-link href="home/status/"><i class="menu-icon-info" />&nbsp;Server Status</app-link></li>
                        </ul>
                        <div style="clear:both;" />
                    </li>
                </ul>
            </div><!-- /.navbar-collapse -->
        </div><!-- /.container-fluid -->
    </nav>
</template>
<script>
import { api } from '../api';
import { mapState } from 'vuex';
import { AppLink } from './helpers';

export default {
    name: 'app-header',
    components: {
        AppLink
    },
    computed: {
        ...mapState({
            config: state => state.config.general,
            clients: state => state.config.clients,
            notifiers: state => state.config.notifiers,
            postprocessing: state => state.config.postprocessing,
            search: state => state.config.search,
            system: state => state.config.system,
            isAuthenticated: state => state.auth.isAuthenticated,
            username: state => state.auth.user.username,
            warningLevel: state => state.config.general.logs.loggingLevels.warning
        }),
        /**
         * Moved into a computed, so it's easier to mock in Jest.
         * @returns {Object} - Route name and query.
         */
        currentShowRoute() {
            const { $route } = this;
            return {
                name: $route.name,
                query: $route.query
            };
        },
        recentShows() {
            const { config, currentShowRoute } = this;
            const { recentShows } = config;

            const showAlreadyActive = show => !currentShowRoute.name === 'show' || !(show.indexerName === currentShowRoute.query.indexername && show.showId === Number(currentShowRoute.query.seriesid));

            return recentShows.filter(showAlreadyActive)
                .map(show => {
                    const { name, indexerName, showId } = show;
                    const link = `home/displayShow?indexername=${indexerName}&seriesid=${showId}`;
                    return { name, link };
                });
        },
        topMenu() {
            return this.$route.meta.topMenu;
        },
        toolsBadgeCount() {
            const { config } = this;
            const { system } = this;
            const { logs } = config;
            const { news } = system;
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
            const { clients, config, notifiers, postprocessing, search } = this;
            const { subtitles } = config;
            const { general } = search;
            const { kodi, plex, emby } = notifiers;

            return {
                plex: plex.server.enabled && plex.server.host.length !== 0,
                kodi: kodi.enabled && kodi.host.length !== 0,
                /* @TODO: Originally there was a check to make sure the API key
                   was configured for Emby: ` app.EMBY_APIKEY != '' ` */
                emby: emby.enabled && emby.host,
                manageTorrents: clients.torrents.enabled && clients.torrents.method !== 'blackhole',
                failedDownloads: general.failedDownloads.enabled,
                subtitleMissed: subtitles.enabled,
                subtitleMissedPP: postprocessing.postponeIfNoSubs
            };
        }
    },
    mounted() {
        const { $el } = this;

        // Auto close menus when clicking a RouterLink
        $el.clickCloseMenus = event => {
            const { target } = event;
            if (target.matches('#main_nav a.router-link, #main_nav a.router-link *')) {
                const dropdown = target.closest('.dropdown');
                dropdown.querySelector('.dropdown-toggle').setAttribute('aria-expanded', false);
                dropdown.querySelector('.dropdown-menu').style.display = 'none';
                // Also collapse the main nav if it's open
                $('#main_nav').collapse('hide');
            }
        };
        $el.addEventListener('click', $el.clickCloseMenus, { passive: true });

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
    destroyed() {
        // Revert `mounted()`
        const { $el } = this;

        // Auto close menus when clicking a RouterLink
        $el.removeEventListener('click', $el.clickCloseMenus);

        // Hover Dropdown for Nav
        $($el).off('mouseenter mouseleave', 'ul.nav li.dropdown');

        // @TODO Replace this with a real touchscreen check
        // hack alert: if we don't have a touchscreen, and we are already hovering the mouse, then click should link instead of toggle
        if ((navigator.maxTouchPoints || 0) < 2) {
            $($el).off('click', '.dropdown-toggle');
        }
    },
    methods: {
        confirmDialog(event, action) {
            const options = {
                confirmButton: 'Yes',
                cancelButton: 'Cancel',
                dialogClass: 'modal-dialog',
                post: false,
                button: $(event.currentTarget || event.target),

                confirm($element) {
                    window.location.href = $element[0].href;
                }
            };

            if (action === 'newversion') {
                options.title = 'New version';
                options.text = 'New version available, update now?';
            } else if (action === 'logout') {
                options.title = 'Logout';
                options.text = 'Are you sure you want to logout from Medusa?';
            } else {
                return;
            }

            $.confirm(options, event);
        },
        async checkForupdates(event) {
            const { confirmDialog } = this;
            try {
                this.$snotify.info(
                    'Checking for a new version...'
                );
                await api.post('system/operation', { type: 'CHECKFORUPDATE' });
                confirmDialog(event, 'newversion');
            } catch (error) {
                this.$snotify.info(
                    'You are already on the latest version'
                );
            }
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
