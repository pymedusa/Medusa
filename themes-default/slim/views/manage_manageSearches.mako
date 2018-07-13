<%inherit file="/layouts/main.mako"/>
<%!
    import json
    from medusa import app
%>
<%block name="scripts">
<script>
window.app = {};
window.app = new Vue({
    store,
    router,
    el: '#vue-wrap',
    data() {
        return {
            // Python conversions
            backlogPaused: ${json.dumps(backlogPaused)},
            backlogRunning: ${json.dumps(backlogRunning)},
            dailySearchStatus: ${json.dumps(dailySearchStatus)},
            findPropersStatus: ${json.dumps(findPropersStatus)},
            searchQueueLength: ${json.dumps(searchQueueLength)},
            forcedSearchQueueLength: ${json.dumps(forcedSearchQueueLength)},
            subtitlesFinderStatus: ${json.dumps(subtitlesFinderStatus)},

            backlogDays: ${json.dumps(app.BACKLOG_DAYS)},
            downloadPropers: ${json.dumps(app.DOWNLOAD_PROPERS)},

            // JS only
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
            }
        };
    },
    computed: {
        config() {
            return this.$store.state.config;
        },
        spinnerSrc() {
            const { config } = this;
            const { themeName } = config;
            const themeSpinner = themeName === 'dark' ? '-dark' : '';
            return 'images/loading32' + themeSpinner + '.gif';
        }
    },
    methods: {
        /**
         * Trigger the force refresh of all the exception types.
         */
        forceSceneExceptionRefresh() {
            const { updateExceptionData, sceneRefresh } = this;
            // Start a spinner.
            sceneRefresh.showSpinner = true;
            sceneRefresh.inProgress = true;
            sceneRefresh.message = 'Retrieving scene exceptions...';

            api.post('alias-source/all/operation', { type: 'REFRESH' }, {
                timeout: 60000
            }).then(() => {
                api.get('alias-source').then(response => {
                    updateExceptionData(response.data);
                }).catch(error => {
                    log.error('Trying to get scene exceptions failed with error: ' + error);
                    sceneRefresh.showSpinner = false;
                    sceneRefresh.inProgress = false;
                    sceneRefresh.message = 'Trying to get scene exceptions failed with error: ' + error;
                });

                sceneRefresh.message = 'Finished updating scene exceptions.';
            }).catch(error => {
                log.error('Trying to update scene exceptions failed with error: ' + error);
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
        goTo(url) {
            const base = document.getElementsByTagName('base')[0].getAttribute('href');
            window.location.href = base + 'manage/manageSearches/' + url;
        },
        toggleBacklog() {
            const { backlogPaused, goTo } = this;
            goTo('pauseBacklog?paused=' + String(Number(!backlogPaused)));
        }
    },
    mounted() {
        // Initially load the exception types last updates on page load.
        const { updateExceptionData } = this;
        api.get('alias-source').then(response => {
            updateExceptionData(response.data);
        }).catch(error => {
            log.error('Trying to get scene exceptions failed with error: ' + error);
        });
    }
});
</script>
</%block>
<%block name="content">
<h1 class="header">{{ $route.meta.header }}</h1>
<div class="align-left">
    <h3>Backlog Search:</h3>
    <h5>Note: Limited by backlog days setting: last {{ backlogDays }} days</h5>
    <button class="btn-medusa" @click="goTo('forceBacklog')">
        <i class="icon-exclamation-sign"></i> Force
    </button>
    <button class="btn-medusa" @click="toggleBacklog">
        <template v-if="backlogPaused"><i class="icon-play"></i> Unpause</template>
        <template v-else><i class="icon-paused"></i> Pause</template>
    </button>
    <template v-if="!backlogRunning">Not in progress</template>
    <template v-else>{{ backlogPaused ? 'Paused: ' : '' }}Currently running</template>
    <br>

    <h3>Daily Search:</h3>
    <button class="btn-medusa" @click="goTo('forceSearch')">
        <i class="icon-exclamation-sign"></i> Force
    </button>
    {{ dailySearchStatus ? 'In Progress' : 'Not in progress' }}<br>

    <h3>Propers Search:</h3>
    <button class="btn-medusa" :disabled="!downloadPropers" @click="goTo('forceFindPropers')">
        <i class="icon-exclamation-sign"></i> Force
    </button>
    <template v-if="!downloadPropers">Propers search disabled</template>
    <template v-else>{{ findPropersStatus ? 'In Progress' : 'Not in progress' }}</template>
    <br>

    <h3>Subtitle Search:</h3>
    <button class="btn-medusa" :disabled="!config.subtitles.enabled" @click="goTo('forceSubtitlesFinder')">
        <i class="icon-exclamation-sign"></i> Force
    </button>
    <template v-if="!config.subtitles.enabled">Subtitle search disabled</template>
    <template v-else>{{ subtitlesFinderStatus ? 'In Progress' : 'Not in progress' }}</template>
    <br>

    <h3>Scene Exceptions:</h3>
    <button class="btn-medusa" :disabled="sceneRefresh.inProgress" @click="forceSceneExceptionRefresh">
        <i class="icon-exclamation-sign"></i> Force
    </button>
    <span v-show="sceneRefresh.message">
        <img v-show="sceneRefresh.showSpinner" :src="spinnerSrc" height="16" width="16" />
        {{ sceneRefresh.message }}
    </span>
    <ul class="simpleList" v-if="!sceneRefresh.inProgress && sceneExceptions.every(item => item.lastRefresh)">
        <li v-for="item in sceneExceptions" :key="item.id">
            <app-link v-if="item.url" :href="item.url">Last updated {{ item.name }} exceptions</app-link>
            <template v-else>Last updated {{ item.name }} exceptions</template>
            {{ item.lastRefresh }}
        </li>
    </ul>

    <h3>Search Queue:</h3>
    <ul class="simpleList">
        <li>Backlog: <i>{{ searchQueueLength.backlog }} pending items</i>
        <li>Daily: <i>{{ searchQueueLength.daily }} pending items</i>
        <li>Forced: <i>{{ forcedSearchQueueLength.forced_search }} pending items</i>
        <li>Manual: <i>{{ forcedSearchQueueLength.manual_search }} pending items</i>
        <li>Failed: <i>{{ forcedSearchQueueLength.failed }} pending items</i>
    </ul>
</div>
</%block>
