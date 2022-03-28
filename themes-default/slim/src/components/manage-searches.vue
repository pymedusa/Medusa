<template>
    <div class="align-left">
        <div v-if="schedulerStatus" class="row">
            <div class="col-lg-12">
                <h3>Backlog Search:</h3>
                <h5>Note: Limited by backlog days setting: last {{ search.general.backlogDays }} days</h5>
                <button class="btn-medusa" @click="forceBacklog">
                    <i class="icon-exclamation-sign" /> Force
                </button>
                <button class="btn-medusa" @click="toggleBacklog">
                    <template v-if="schedulerStatus.backlogPaused"><i class="icon-play" /> Unpause</template>
                    <template v-else><i class="icon-paused" /> Pause</template>
                </button>
                <template v-if="!schedulerStatus.backlogRunning">Not in progress</template>
                <template v-else>{{ schedulerStatus.backlogPaused ? 'Paused: ' : '' }}Currently running</template>
            </div>
        </div>

        <div v-if="schedulerStatus" class="row">
            <div class="col-lg-12">
                <h3>Daily Search:</h3>
                <button class="btn-medusa" @click="forceDaily">
                    <i class="icon-exclamation-sign" /> Force
                </button>
                {{ schedulerStatus.dailySearchStatus ? 'In Progress' : 'Not in progress' }}
            </div>
        </div>

        <div v-if="schedulerStatus" class="row">
            <div class="col-lg-12">
                <h3>Propers Search:</h3>
                <button class="btn-medusa" :disabled="!search.general.downloadPropers" @click="forceFindPropers">
                    <i class="icon-exclamation-sign" /> Force
                </button>
                <template v-if="!search.general.downloadPropers">Propers search disabled</template>
                <template v-else>{{ schedulerStatus.properSearchStatus ? 'In Progress' : 'Not in progress' }}</template>
            </div>
        </div>

        <div v-if="schedulerStatus" class="row">
            <div class="col-lg-12">
                <h3>Subtitle Search:</h3>
                <button class="btn-medusa" :disabled="!subtitles.enabled" @click="forceSubtitlesFinder">
                    <i class="icon-exclamation-sign" /> Force
                </button>
                <template v-if="!subtitles.enabled">Subtitle search disabled</template>
                <template v-else>{{ schedulerStatus.subtitlesFinderStatus ? 'In Progress' : 'Not in progress' }}</template>
            </div>
        </div>

        <div v-if="schedulerStatus" class="row">
            <div class="col-lg-12">
                <h3>Download Handler:</h3>
                <button class="btn-medusa" :disabled="schedulerStatus.downloadHandlerStatus" @click="forceDownloadHandler">
                    <i class="icon-exclamation-sign" /> Force
                </button>
                <template>{{ schedulerStatus.downloadHandlerStatus ? 'In Progress' : 'Not in progress' }}</template>
            </div>
        </div>

        <div class="row">
            <div class="col-lg-12">
                <h3>Scene Exceptions:</h3>
                <button class="btn-medusa" :disabled="sceneRefresh.inProgress" @click="forceSceneExceptionRefresh">
                    <i class="icon-exclamation-sign" /> Force
                </button>
                <span v-show="sceneRefresh.message">
                    <img v-show="sceneRefresh.showSpinner" :src="spinnerSrc" height="16" width="16">
                    {{ sceneRefresh.message }}
                </span>
                <ul class="simpleList" v-if="!sceneRefresh.inProgress && sceneExceptions.every(item => item.lastRefresh)">
                    <li v-for="item in sceneExceptions" :key="item.id">
                        <app-link v-if="item.url" :href="item.url">Last updated {{ item.name }} exceptions</app-link>
                        <template v-else>Last updated {{ item.name }} exceptions</template>
                        {{ item.lastRefresh }}
                    </li>
                </ul>
                <app-link v-if="!sceneRefresh.inProgress" href="internal/deleteSceneExceptions" class="clean-cache" @click.native.prevent="cleanScenExceptionCache">Clean scene exception cache</app-link>
                <transition name="fade">
                    <state-switch v-if="sceneExceptionsDeleted" state="yes" />
                </transition>
            </div>
        </div>

        <div class="row">
            <div class="col-lg-12">
                <h3>Force refresh recommended list:</h3>
                <span>
                    Note! Syncing shows with a recommended list may take a while.
                    The action will be queued. For example, starting syncs for Trakt and Imdb.
                    You will not see results for Imdb until after the sync of Trakt has finished.
                </span>
                <ul class="simpleList recommended-list">
                    <li><span @click="searchRecommendedShows('trakt')">Trakt</span></li>
                    <li><span @click="searchRecommendedShows('imdb')">Imdb</span></li>
                    <li><span @click="searchRecommendedShows('anidb')">Anidb</span></li>
                    <li><span @click="searchRecommendedShows('anilist')">AniList</span></li>
                </ul>
            </div>
        </div>

        <div v-if="schedulerStatus" class="row">
            <div class="col-lg-12">
                <h3>Search Queue:</h3>
                <ul class="simpleList">
                    <li>Backlog: <i>{{ schedulerStatus.searchQueueLength.backlog }} pending items</i></li>
                    <li>Daily: <i>{{ schedulerStatus.searchQueueLength.daily }} pending items</i></li>
                    <li>Forced: <i>{{ schedulerStatus.forcedSearchQueueLength.backlog_search }} pending items</i></li>
                    <li>Manual: <i>{{ schedulerStatus.forcedSearchQueueLength.manual_search }} pending items</i></li>
                    <li>Failed: <i>{{ schedulerStatus.forcedSearchQueueLength.failed }} pending items</i></li>
                </ul>
            </div>
        </div>
    </div>
</template>

<script>
import { mapActions, mapGetters, mapState } from 'vuex';
import { AppLink } from './helpers';
import StateSwitch from './helpers/state-switch.vue';

export default {
    name: 'manage-searches',
    components: {
        AppLink,
        StateSwitch
    },
    data() {
        return {
            sceneExceptions: [{
                id: 'local',
                name: "Medusa's",
                url: 'https://github.com/pymedusa/Medusa/wiki/Scene-exceptions-and-numbering',
                lastRefresh: ''
            }, {
                id: 'xem',
                name: 'XEM',
                url: 'http://thexem.de',
                lastRefresh: ''
            }, {
                id: 'anidb',
                name: 'AniDB',
                url: '',
                lastRefresh: ''
            }],
            sceneRefresh: {
                inProgress: true,
                showSpinner: false,
                message: ''
            },
            sceneExceptionsDeleted: false
        };
    },
    computed: {
        // @TODO: Replace with mapState
        ...mapState({
            general: state => state.config.general,
            subtitles: state => state.config.subtitles,
            system: state => state.config.system,
            search: state => state.config.search,
            queueItems: state => state.queue.queueitems,
            client: state => state.auth.client
        }),
        ...mapGetters({
            getQueueItemsByName: 'getQueueItemsByName'
        }),
        spinnerSrc() {
            const { general } = this;
            const { themeName } = general;
            const themeSpinner = themeName === 'dark' ? '-dark' : '';
            return 'images/loading32' + themeSpinner + '.gif';
        },
        schedulerStatus() {
            const { getQueueItemsByName, system } = this;
            const { schedulers } = system;

            if (schedulers.length === 0) {
                return;
            }

            const backlog = schedulers.find(scheduler => scheduler.key === 'backlog');
            const daily = schedulers.find(scheduler => scheduler.key === 'dailySearch');
            const proper = schedulers.find(scheduler => scheduler.key === 'properFinder');
            const search = schedulers.find(scheduler => scheduler.key === 'searchQueue');
            const forcedSearch = schedulers.find(scheduler => scheduler.key === 'forcedSearchQueue');
            const subtitles = schedulers.find(scheduler => scheduler.key === 'subtitlesFinder');
            const downloadHandler = schedulers.find(scheduler => scheduler.key === 'downloadHandler');

            const downloadHanlderQueueItems = getQueueItemsByName('DOWNLOADHANDLER');
            if (downloadHanlderQueueItems.length > 0) {
                // Found a queueitem from the DOWNLOADHANDLER. Check last item for an isActive state.
                const lastItem = downloadHanlderQueueItems.slice(-1);
                downloadHandler.isActive = lastItem[0].isActive;
            }

            return {
                backlogPaused: backlog.isEnabled === 'Paused',
                backlogRunning: backlog.isActive,
                dailySearchStatus: daily.isActive,
                searchQueueLength: search.queueLength,
                forcedSearchQueueLength: forcedSearch.queueLength,
                subtitlesFinderStatus: subtitles.isActive,
                properSearchStatus: proper.isActive,
                downloadHandlerStatus: downloadHandler.isActive
            };
        }
    },
    methods: {
        ...mapActions({
            getConfig: 'getConfig'
        }),
        /**
         * Trigger the force refresh of all the exception types.
         */
        forceSceneExceptionRefresh() {
            const { client, updateExceptionData, sceneRefresh } = this;
            // Start a spinner.
            sceneRefresh.showSpinner = true;
            sceneRefresh.inProgress = true;
            sceneRefresh.message = 'Retrieving scene exceptions...';

            client.api.post('alias-source/all/operation', { type: 'REFRESH' }, {
                timeout: 60000
            }).then(() => {
                client.api.get('alias-source').then(response => {
                    updateExceptionData(response.data);
                }).catch(error => {
                    console.error('Trying to get scene exceptions failed with error: ' + error);
                    sceneRefresh.showSpinner = false;
                    sceneRefresh.inProgress = false;
                    sceneRefresh.message = 'Trying to get scene exceptions failed with error: ' + error;
                });

                sceneRefresh.message = 'Finished updating scene exceptions.';
            }).catch(error => {
                console.error('Trying to update scene exceptions failed with error: ' + error);
                sceneRefresh.message = 'Trying to update scene exceptions failed with error: ' + error;
                sceneRefresh.inProgress = false;
            }).finally(() => {
                sceneRefresh.showSpinner = false;
            });
        },
        /**
         * Get total number current scene exceptions per source. Will request medusa, xem and anidb name exceptions.
         * @param {Object[]} exceptions - A list of exception types with their last updates.
         * @param {string} exceptions[].id - The name of the scene exception source.
         * @param {number} exceptions[].lastRefresh - The last update of the scene exception source as a timestamp.
         */
        updateExceptionData(exceptions) {
            const { sceneExceptions, sceneRefresh } = this;

            for (const type of ['local', 'xem', 'anidb']) {
                const data = exceptions.find(obj => obj.id === type);
                const exception = sceneExceptions.find(item => item.id === type);
                exception.lastRefresh = new Date(data.lastRefresh * 1000).toLocaleDateString();
            }

            sceneRefresh.inProgress = false;
        },
        forceBacklog() {
            this.client.api.put('search/backlog');
        },
        forceDaily() {
            this.client.api.put('search/daily');
        },
        forceFindPropers() {
            this.client.api.put('search/proper');
        },
        forceSubtitlesFinder() {
            this.client.api.put('search/subtitles');
        },
        toggleBacklog() {
            const { schedulerStatus } = this;
            this.client.api.put('search/backlog', { options: { paused: !schedulerStatus.backlogPaused } }); // eslint-disable-line no-undef
        },
        forceDownloadHandler() {
            this.client.api.post('system/operation', { type: 'FORCEADH' });
        },
        async searchRecommendedShows(source) {
            try {
                await this.client.api.post(`recommended/${source}`);
                this.$snotify.success(
                    'Started search for new recommended shows',
                    `Searching ${source}`
                );
            } catch (error) {
                if (error.response.status === 409) {
                    this.$snotify.error(
                        error.response.data.error,
                        'Error'
                    );
                }
            }
        },
        cleanScenExceptionCache() {
            const vm = this;
            $.confirm({
                title: 'Clear scene exception cache',
                text: 'Do you really want to clear the scene exception cache? Custom exception will be left untouched.',
                confirmButton: 'Yes',
                cancelButton: 'Cancel',
                dialogClass: 'modal-dialog',
                post: false,
                confirm() {
                    this.client.api.post('internal/deleteSceneExceptions')
                        .then(() => {
                            vm.sceneExceptionsDeleted = true;
                            setTimeout(() => {
                                vm.sceneExceptionsDeleted = false;
                            }, 3000);
                        });
                }
            });
        }
    },
    mounted() {
        // Initially load the exception types last updates on page load.
        const { updateExceptionData } = this;
        this.client.api.get('alias-source').then(response => {
            updateExceptionData(response.data);
        }).catch(error => {
            console.error('Trying to get scene exceptions failed with error: ' + error);
        });
    },
    watch: {
        queueItems() {
            const { getConfig } = this;
            getConfig('system');
        }
    }
};
</script>
<style scoped>
.recommended-list span {
    cursor: pointer;
    color: #337ab7;
    text-decoration: none;
}

.recommended-list span:focus,
.recommended-list span:hover {
    text-decoration: underline;
}

.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.5s;
}

.fade-enter,
.fade-leave-to {
    opacity: 0;
}
</style>
