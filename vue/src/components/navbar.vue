<template>
    <nav class="navbar navbar-default navbar-fixed-top hidden-print" role="navigation">
        <div class="container-fluid">
            <div v-if="mobileNav" class="navbar-header">
                <button type="button" class="navbar-toggle collapsed" data-toggle="collapse" data-target="#main_nav">
                    <span class="sr-only">Toggle navigation</span>
                    <span class="icon-bar"></span>
                    <span class="icon-bar"></span>
                    <span class="icon-bar"></span>
                </button>
                <a class="navbar-brand" href="home/" title="Medusa"><img alt="Medusa" src="/images/medusa.png" style="height: 50px;" class="img-responsive pull-left" /></a>
            </div>
            <div v-if="isAuthenticated" class="collapse navbar-collapse" id="main_nav">
                <ul class="nav navbar-nav navbar-right">
                    <dropdown title="Series">
                        <li><router-link :to="{ name: 'home' }"><i class="menu-icon-home"></i> Series List</router-link></li>
                        <li><router-link :to="{ name: 'series-add' }"><i class="menu-icon-addshow"></i> Add Series</router-link></li>
                        <li><router-link :to="{ name: 'series-add', params: { type: 'recommended' } }"><i class="menu-icon-addshow"></i> Add Recommended Series</router-link></li>
                        <li><router-link :to="{ name: 'to-be-implemented' }"><i class="menu-icon-postprocess"></i> Manual Post-Processing</router-link></li>
                        <li v-if="recentSeries" role="separator" class="divider"></li>
                        <li>
                            <router-link v-for"series in recentSeries" :to="{ name: 'series', params: { id: series.id[series.indexer], indexer: series.indexer } }"><i class="menu-icon-addshow"></i> ${recentShow['name']|trim,h}</a>
                        </li>
                    </dropdown>
                    <li><router-link :to="{ name: 'to-be-implemented' }">Schedule</router-link></li>
                    <li><router-link :to="{ name: 'to-be-implemented' }">History</router-link></li>
                    <dropdown title="Manage">
                        <li><router-link :to="{ name: 'to-be-implemented' }"><i class="menu-icon-manage"></i> Mass Update</router-link></li>
                        <li><router-link :to="{ name: 'to-be-implemented' }"><i class="menu-icon-backlog-view"></i> Backlog Overview</router-link></li>
                        <li><router-link :to="{ name: 'to-be-implemented' }"><i class="menu-icon-manage-searches"></i> Manage Searches</router-link></li>
                        <li><router-link :to="{ name: 'to-be-implemented' }"><i class="menu-icon-manage2"></i> Episode Status Management</router-link></li>
                        <!-- The update buttons below could probably be moved to buttons which just hit the API. -->
                        <li v-if="config.plex.server.enabled"><a href="home/updatePLEX/"><i class="menu-icon-plex"></i> Update PLEX</a></li>
                        <li v-if="config.kodi.enabled"><a href="home/updateKODI/"><i class="menu-icon-kodi"></i> Update KODI</a></li>
                        <li v-if="config.emby.enabled"><a href="home/updateEMBY/"><i class="menu-icon-emby"></i> Update Emby</a></li>
                        <li v-if="config.torrents.enabled"><a href="manage/manageTorrents/"><i class="menu-icon-bittorrent"></i> Manage Torrents</a></li>
                        <li v-if="failedDownloads"><router-link :to="{ name: 'to-be-implemented' }"><i class="menu-icon-download"></i> Failed Downloads</router-link></li>
                        <li v-if="useSubtitles"><router-link :to="{ name: 'to-be-implemented' }"><i class="menu-icon-backlog"></i> Missed Subtitle Management</router-link></li>
                        <li v-if="POSTPONE_IF_NO_SUBS"><router-link :to="{ name: 'to-be-implemented' }"><i class="menu-icon-backlog"></i> Missed Subtitle in Post-Process folder</router-link></li>
                    </dropdown>
                    <dropdown title="Config" icon="/images/menu/system18.png">
                        <li><router-link :to="{ name: 'config-info' }"><i class="menu-icon-help"></i> Help &amp; Info</router-link></li>
                        <li><router-link :to="{ name: 'config-general' }"><i class="menu-icon-config"></i> General</router-link></li>
                        <li><router-link :to="{ name: 'to-be-implemented' }"><i class="menu-icon-backup"></i> Backup &amp; Restore</router-link></li>
                        <li><router-link :to="{ name: 'to-be-implemented' }"><i class="menu-icon-searches"></i> Search Settings</router-link></li>
                        <li><router-link :to="{ name: 'to-be-implemented' }"><i class="menu-icon-postprocess"></i> Post Processing</router-link></li>
                        <li><router-link :to="{ name: 'to-be-implemented' }"><i class="menu-icon-notification"></i> Notifications</router-link></li>
                        <li><router-link :to="{ name: 'to-be-implemented' }"><i class="menu-icon-anime"></i> Anime</router-link></li>
                    </dropdown>
                    <dropdown title="Tools" icon="/images/menu/system18-2.png" :badge="toolsBadge">
                        <li><a href="news/"><i class="menu-icon-news"></i> News${newsBadge}</a></li>
                        <li><a href="IRC/"><i class="menu-icon-irc"></i> IRC</a></li>
                        <li><a href="changes/"><i class="menu-icon-changelog"></i> Changelog</a></li>
                        <li><a href="${app.DONATIONS_URL}" rel="noreferrer" onclick="window.open('${app.ANON_REDIRECT}' + this.href); return false;"><i class="menu-icon-support"></i> Support Medusa</a></li>
                        <li role="separator" class="divider"></li>
                        %if numErrors:
                            <li><a href="errorlogs/"><i class="menu-icon-error"></i> View Errors <span class="badge btn-danger">${numErrors}</span></a></li>
                        %endif
                        %if numWarnings:
                            <li><a href="errorlogs/?level=${logger.WARNING}"><i class="menu-icon-viewlog-errors"></i> View Warnings <span class="badge btn-warning">${numWarnings}</span></a></li>
                        %endif
                        <li><a href="errorlogs/viewlog/"><i class="menu-icon-viewlog"></i> View Log</a></li>
                        <li role="separator" class="divider"></li>
                        <li><a href="home/updateCheck?pid=${sbPID}"><i class="menu-icon-update"></i> Check For Updates</a></li>
                        <li><a href="home/restart/?pid=${sbPID}" class="confirm restart"><i class="menu-icon-restart"></i> Restart</a></li>
                        <li><a href="home/shutdown/?pid=${sbPID}" class="confirm shutdown"><i class="menu-icon-shutdown"></i> Shutdown</a></li>
                        <li><router-link v-if="!isAuthenticated" :to="{ name: 'to-be-implemented' }" class="confirm logout"><i class="menu-icon-shutdown"></i> Logout</router-link></li>
                        <li role="separator" class="divider"></li>
                        <li><a href="home/status/"><i class="menu-icon-info"></i> Server Status</a></li>
                    </dropdown>
                </ul>
            </div>
        </div>
    </nav>
</template>

<script>
import {mapGetters} from 'vuex';

import dropdown from './dropdown.vue';

export default {
    name: 'navbar',
    data() {
        // All of the returns here are because we're currently missing the field in the API.
        // The only one that's not missing is mobileNav, that's here until w fix the nav working on mobile
        return {
            mobileNav: null,
            recentSeries: null,
            failedDownloads: null,
            useSubtitles: null,
            POSTPONE_IF_NO_SUBS: null
        };
    },
    computed: {
        ...mapGetters([
            'isAuthenticated',
            'config'
        ])
    },
    components: {
        dropdown
    }
};
</script>
