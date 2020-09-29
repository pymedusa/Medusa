<template>
    <div>
        <div class="col-md-12 pull-right">
            <div class="logging-filter-control pull-right">
                <!-- Toggle auto update -->
                <div class="show-option">
                    <button @click="autoUpdate = !autoUpdate" type="button" class="btn-medusa btn-inline">
                        <i :class="`glyphicon glyphicon-${autoUpdate ? 'pause' : 'play'}`" />
                        {{ autoUpdate ? 'Pause' : 'Resume' }}
                    </button>
                </div>
                <!-- Select Loglevel -->
                <div class="show-option">
                    <span>Logging level:
                        <select v-model="minLevel" @change="fetchLogsDebounced()" class="form-control form-control-inline input-sm">
                            <option v-for="level in levels" :key="level" :value="level.toUpperCase()">{{ level }}</option>
                        </select>
                    </span>
                </div>
                <div class="show-option">
                    <!-- Filter log -->
                    <span>Filter log by:
                        <select v-model="threadFilter" @change="fetchLogsDebounced()" class="form-control form-control-inline input-sm">
                            <option value="" v-once>&lt;No Filter&gt;</option>
                            <option v-for="filter in filters" :key="filter.value" :value="filter.value">{{ filter.title }}</option>
                        </select>
                    </span>
                </div>
                <div class="show-option">
                    <!-- Select period -->
                    <span>Period:
                        <select v-model="periodFilter" @change="fetchLogsDebounced()" class="form-control form-control-inline input-sm">
                            <option value="all">All</option>
                            <option value="one_day">Last 24h</option>
                            <option value="three_days">Last 3 days</option>
                            <option value="one_week">Last 7 days</option>
                        </select>
                    </span>
                </div>
                <div class="show-option">
                    <!-- Search Log -->
                    <span>Search log by:
                        <input
                            v-model="searchQuery" @keyup="fetchLogsDebounced()" @keypress.enter="fetchLogsDebounced.flush()"
                            type="text" placeholder="clear to reset" class="form-control form-control-inline input-sm"
                        >
                    </span>
                </div>
            </div>
        </div>

        <pre class="col-md-12" :class="{ fanartOpacity: layout.fanartBackground }"><!--
            --><div class="notepad"><!--
                --><app-link :href="rawViewLink"><!--
                    --><img src="images/notepad.png"><!--
                --></app-link><!--
            --></div><!--
            --><div v-for="(line, index) in logLines" :key="`line-${index}`"><!--
                -->{{ line | formatLine }}<!--
            --></div><!--
        --></pre>

        <backstretch :slug="config.randomShowSlug" />
    </div>
</template>

<script>
import debounce from 'lodash/debounce';
import { mapState } from 'vuex';

import { api, apiKey } from '../api';
import { AppLink } from './helpers';
import Backstretch from './backstretch.vue';

export default {
    name: 'logs',
    components: {
        AppLink,
        Backstretch
    },
    data() {
        return {
            minLevel: 'INFO',
            threadFilter: '',
            periodFilter: 'one_day',
            searchQuery: '',
            logLines: [],
            autoUpdate: true,
            autoUpdateTimer: null,
            filters: [
                { value: 'BACKLOG', title: 'Backlog' },
                { value: 'CHECKVERSION', title: 'Check Version' },
                { value: 'DAILYSEARCHER', title: 'Daily Searcher' },
                { value: 'ERROR', title: 'Error' },
                { value: 'EVENT', title: 'Event' },
                { value: 'FINDPROPERS', title: 'Find Propers' },
                { value: 'FINDSUBTITLES', title: 'Find Subtitles' },
                { value: 'MAIN', title: 'Main' },
                { value: 'POSTPROCESSOR', title: 'PostProcessor' },
                { value: 'SEARCHQUEUE', title: 'Search Queue (All)' },
                { value: 'SEARCHQUEUE-BACKLOG', title: 'Search Queue (Backlog)' },
                { value: 'SEARCHQUEUE-DAILY-SEARCH', title: 'Search Queue (Daily Searcher)' },
                { value: 'SEARCHQUEUE-FORCED', title: 'Search Queue (Forced)' },
                { value: 'SEARCHQUEUE-MANUAL', title: 'Search Queue (Manual)' },
                { value: 'SEARCHQUEUE-RETRY', title: 'Search Queue (Retry/Failed)' },
                { value: 'SEARCHQUEUE-RSS', title: 'Search Queue (RSS)' },
                { value: 'SHOWQUEUE', title: 'Show Queue (All)' },
                { value: 'SHOWQUEUE-REFRESH', title: 'Show Queue (Refresh)' },
                { value: 'SHOWQUEUE-SEASON-UPDATE', title: 'Show Season Queue (Update)' },
                { value: 'SHOWQUEUE-UPDATE', title: 'Show Queue (Update)' },
                { value: 'SHOWUPDATER', title: 'Show Updater' },
                { value: 'EPISODEUPDATER', title: 'Episode Updater' },
                { value: 'Thread', title: 'Thread' },
                { value: 'TORNADO', title: 'Tornado' },
                { value: 'TORRENTCHECKER', title: 'Torrent Checker' },
                { value: 'TRAKTCHECKER', title: 'Trakt Checker' }
            ]
        };
    },
    filters: {
        formatLine(line) {
            let result = '';
            result += line.timestamp.replace('T', ' ').replace('Z', '');
            result += ` ${line.level}`;
            result += `\t${line.thread}`;
            if (line.threadId) {
                result += `-${line.threadId}`;
            }
            result += ' :: ';
            if (line.extra) {
                result += `${line.extra} :: `;
            }
            if (line.commit) {
                result += `[${line.commit}] `;
            }
            result += line.message;
            if (line.traceback) {
                result += line.traceback
                    .reduce((str, tbLine) => str.concat('\n', tbLine), '');
            }
            return result;
        }
    },
    computed: {
        ...mapState({
            config: state => state.config.general,
            layout: state => state.config.layout
        }),
        rawViewLink() {
            const qs = new URLSearchParams();
            qs.set('level', this.minLevel);
            qs.set('thread', this.threadFilter);
            qs.set('period', this.periodFilter);
            qs.set('query', this.searchQuery);
            qs.set('limit', 1000);
            qs.set('api_key', apiKey);
            qs.set('raw', 'true');
            return `${api.defaults.baseURL}log?${qs}`;
        },
        levels() {
            const { debug, dbDebug, loggingLevels } = this.config.logs;
            return Object.entries(loggingLevels)
                .sort((a, b) => a[1] - b[1]) // Sort by level in ascending order
                .reduce((result, level) => {
                    const key = level[0];
                    if ((key === 'debug' && !debug) ||
                        (key === 'db' && !dbDebug)) {
                        return result;
                    }
                    const levelName = key.length <= 2 ? key.toUpperCase() : key.charAt(0).toUpperCase() + key.slice(1);
                    return result.concat(levelName);
                }, []);
        }
    },
    mounted() {
        const { query } = this.$route;
        // Map values from URL query
        this.minLevel = query.minLevel === undefined ? this.minLevel : query.minLevel;
        this.threadFilter = query.threadFilter === undefined ? this.threadFilter : query.threadFilter;
        this.periodFilter = query.periodFilter === undefined ? this.periodFilter : query.periodFilter;
        this.searchQuery = query.searchQuery === undefined ? this.searchQuery : query.searchQuery;

        if (this.autoUpdate) {
            this.autoUpdateTask();
        } else {
            this.fetchLogs(false, true);
        }
        this.fetchLogsDebounced = debounce(this.fetchLogs, 500);
    },
    destroyed() {
        if (this.autoUpdateTimer) {
            clearTimeout(this.autoUpdateTimer);
        }
    },
    methods: {
        async fetchLogs(pushState = true, cursor = true) {
            const {
                minLevel,
                threadFilter,
                periodFilter,
                searchQuery
            } = this;

            if (cursor) {
                document.body.style.cursor = 'wait';
            }
            const params = {
                level: minLevel,
                thread: threadFilter,
                period: periodFilter,
                query: searchQuery,
                limit: 1000
            };
            try {
                const resp = await api.get('log', { params });
                this.logLines = resp.data;
                return true;
            } catch (error) {
                console.error(error);
                return false;
            } finally {
                if (cursor) {
                    document.body.style.cursor = 'default';
                }
                if (pushState) {
                    this.$router.push({
                        query: {
                            minLevel,
                            threadFilter,
                            periodFilter,
                            searchQuery
                        }
                    });
                }
            }
        },
        async autoUpdateTask(errors = 0) {
            if (this.autoUpdate) {
                const result = await this.fetchLogs(false, false);
                // Increment if false
                errors += Number(!result);
                // Stop after 5 network errors
                if (errors < 5) {
                    this.autoUpdateTimer = setTimeout(this.autoUpdateTask, 1500, errors);
                } else {
                    this.autoUpdate = false;
                    this.autoUpdateTimer = null;
                }
            } else {
                this.autoUpdateTimer = null;
            }
        }
    },
    watch: {
        autoUpdate() {
            this.autoUpdateTask();
        }
    }
};
</script>

<style scoped>
pre {
    overflow: auto;
    word-wrap: normal;
    white-space: pre;
    min-height: 65px;
}

div.notepad {
    position: absolute;
    right: 15px;
    opacity: 0.1;
    zoom: 1;
    -webkit-filter: grayscale(100%);
    filter: grayscale(100%);
    -webkit-transition: opacity 0.5s; /* Safari */
    transition: opacity 0.5s;
}

div.notepad:hover {
    opacity: 0.4;
}

div.notepad img {
    width: 50px;
}

.logging-filter-control {
    padding-top: 24px;
}
</style>
