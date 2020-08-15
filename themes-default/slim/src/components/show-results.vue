<template>
    <div class="show-results-wrapper">
        <div class="row horizontal-scroll" :class="{ fanartBackground: layout.fanartBackground }">
            <div class="col-md-12 top-15">
                <div class="button-row">
                    <input class="btn-medusa manualSearchButton top-5 bottom-5" type="button"  value="Refresh Results" @click="getProviderResults">
                    <input class="btn-medusa manualSearchButton top-5 bottom-5" type="button"  value="Force Search" @click="forceSearch">
                    <template v-if="loading">
                        <state-switch state="loading" />
                        <span>{{loadingMessage}}</span>
                    </template>
                </div>
                <vue-good-table v-show="show.id.slug"
                                ref="vgt-show-results"
                                :columns="columns"
                                :rows="combinedResults"
                                :search-options="{
                                    enabled: false
                                }"
                                :sort-options="{
                                    enabled: true,
                                    initialSortBy: getSortBy('quality', 'desc')
                                }"
                                :column-filter-options="{
                                    enabled: true
                                }"
                                :row-style-class="rowStyleClassFn"
                                styleClass="vgt-table condensed"
                                @on-sort-change="saveSorting"
                >
                    <template slot="table-row" slot-scope="props">
                        <span v-if="props.column.label === 'Provider'" class="align-center">
                            <img :src="`images/providers/${props.row.provider.imageName}`"
                                 :alt="props.row.provider.name" width="16" class="addQTip"
                                 :title="props.row.provider.name"
                                 onError="this.onerror=null;this.src='images/providers/missing.png';"
                            >
                        </span>

                        <span v-else-if="props.column.label === 'Quality'" class="align-center">
                            <quality-pill v-if="props.row.quality !== 0" :quality="props.row.quality" />
                        </span>

                        <span v-else-if="props.column.label === 'Seeds'" class="align-center">
                            {{props.row.seeders !== -1 ? props.row.seeders : '-'}}
                        </span>

                        <span v-else-if="props.column.label === 'Peers'" class="align-center">
                            {{props.row.leechers !== -1 ? props.row.leechers : '-'}}
                        </span>

                        <span v-else-if="props.column.label === 'Added'" class="align-center">
                            {{props.row.dateAdded ? fuzzyParseDateTime(props.row.dateAdded) : ''}}
                        </span>

                        <span v-else-if="props.column.label === 'Published'" class="align-center">
                            {{props.row.pubdate ? fuzzyParseDateTime(props.row.pubdate) : ''}}
                        </span>

                        <span v-else-if="props.column.label === 'Updated'" class="align-center">
                            {{props.row.time ? fuzzyParseDateTime(props.row.time) : ''}}
                        </span>

                        <span v-else-if="props.column.label == 'Snatch'">
                            <img src="images/download.png" width="16" height="16" alt="snatch" title="Download selected episode" :data-identifier="props.row.identifier" @click="snatchResult($event, props.row)">
                        </span>

                        <span v-else>
                            {{props.formattedRow[props.column.field]}}
                        </span>
                    </template>

                </vue-good-table>
            </div>
        </div>
    </div>
</template>
<script>

import { apiRoute } from '../api';
import { mapActions, mapGetters, mapState } from 'vuex';
import { VueGoodTable } from 'vue-good-table';
import { manageCookieMixin } from '../mixins/manage-cookie';
import { StateSwitch } from './helpers';
import QualityPill from './helpers/quality-pill.vue';
import { episodeToSlug, humanFileSize } from '../utils/core';
import { addQTip } from '../utils/jquery';

export default {
    name: 'show-results',
    components: {
        VueGoodTable,
        StateSwitch,
        QualityPill
    },
    mixins: [
        manageCookieMixin('showResults')
    ],
    props: {
        show: {
            type: Object,
            required: true
        },
        season: {
            type: Number,
            required: true
        },
        episode: {
            type: Number,
            required: false
        },
        searchType: {
            type: String,
            default: 'episode'
        }
    },
    data() {
        const { getCookie } = this;
        return {
            columns: [{
                label: 'Release',
                field: 'release',
                tdClass: 'release',
                hidden: getCookie('Release')
            },
            {
                label: 'Group',
                field: 'releaseGroup',
                hidden: getCookie('Group')
            },
            {
                label: 'Provider',
                field: 'provider.name',
                hidden: getCookie('Provider')
            },
            {
                label: 'Quality',
                field: 'quality',
                type: 'number',
                hidden: getCookie('Quality')
            },
            {
                label: 'Seeds',
                field: 'seeders',
                type: 'number',
                hidden: getCookie('Seeds')
            },
            {
                label: 'Peers',
                field: 'leechers',
                type: 'number',
                hidden: getCookie('Peers')
            },
            {
                label: 'Size',
                field: 'size',
                formatFn: humanFileSize,
                type: 'number',
                hidden: getCookie('Size')
            },
            {
                label: 'Added',
                field: 'dateAdded',
                type: 'date',
                sortable: true,
                dateInputFormat: 'yyyy-MM-dd\'T\'HH:mm:ss', // E.g. 07-09-2017 19:16:25
                dateOutputFormat: 'yyyy/MM/dd HH:mm:ss',
                hidden: getCookie('Added')
            },
            {
                label: 'Published',
                field: 'pubdate',
                type: 'date',
                sortable: true,
                dateInputFormat: 'yyyy-MM-dd\'T\'HH:mm:ssXXX',
                dateOutputFormat: 'yyyy-MM-dd HH:mm:ss',
                hidden: getCookie('Published')
            },
            {
                label: 'Updated',
                field: 'time',
                type: 'date',
                sortable: true,
                dateInputFormat: 'yyyy-MM-dd\'T\'HH:mm:ss',
                dateOutputFormat: 'yyyy/MM/dd HH:mm:ss',
                hidden: getCookie('Updated')
            },
            {
                label: 'Snatch',
                field: 'snatch',
                sortable: false
            }],
            loading: false,
            loadingMessage: ''
        };
    },
    async mounted() {
        const { forceSearch, getProviders, getProviderCacheResults, show, season, episode } = this;
        await getProviders();

        const result = await getProviderCacheResults({ showSlug: show.id.slug, season, episode });

        // TODO: put a modal in between
        if (result.providersSearched > 0 && result.totalSearchResults.length === 0) {
            forceSearch();
        }

        addQTip();
    },
    computed: {
        ...mapState({
            config: state => state.config.general,
            layout: state => state.config.layout,
            search: state => state.config.search,
            providers: state => state.provider.providers,
            queueitems: state => state.search.queueitems,
            history: state => state.history.episodeHistory
        }),
        ...mapGetters({
            fuzzyParseDateTime: 'fuzzyParseDateTime',
            effectiveIgnored: 'effectiveIgnored',
            effectiveRequired: 'effectiveRequired'
        }),
        combinedResults() {
            const { episode, episodeHistory, providers, season, show } = this;
            let results = [];

            const getLastHistoryStatus = result => {
                const sortedHistory = episodeHistory.sort(item => item.actionDate).reverse();
                for (const historyRow of sortedHistory) {
                    if (historyRow.resource === result.release && historyRow.size === result.size) {
                        return historyRow.statusName.toLocaleLowerCase();
                    }
                }
                return 'skipped';
            };

            for (const provider of Object.values(providers).filter(provider => provider.config.enabled)) {
                if (provider.cache && provider.cache.length > 0) {
                    results = [...results, ...provider.cache.filter(
                        searchResult => {
                            if (episode) {
                                return searchResult.showSlug === show.id.slug &&
                                       searchResult.season === season &&
                                       searchResult.episodes.includes(episode);
                            }
                            return searchResult.showSlug === show.id.slug &&
                                   searchResult.season === season &&
                                   searchResult.seasonPack;
                        }
                    ).map(result => {
                        return { ...result, status: getLastHistoryStatus(result) };
                    })];
                }
            }
            return results;
        },
        /**
         * Helper to get the current episode or season slug.
         * @returns {string} episode slug.
         */
        episodeSlug() {
            const { season, episode } = this;
            return episodeToSlug(season, episode);
        },
        /**
         * Helper to check if showSlug and season/episode slug exist.
         * @returns {array} history for episode or empty array.
         */
        episodeHistory() {
            const { episodeSlug, history, show } = this;
            if (!history[show.id.slug] || !history[show.id.slug][episodeSlug]) {
                return [];
            }
            return history[show.id.slug][episodeSlug];
        }
    },
    methods: {
        humanFileSize,
        ...mapActions({
            getProviders: 'getProviders',
            getProviderCacheResults: 'getProviderCacheResults',
            getShowEpisodeHistory: 'getShowEpisodeHistory'
        }),
        close() {
            this.$emit('close');
            // Destroy the vue listeners, etc
            this.$destroy();
            // Remove the element from the DOM
            this.$el.remove();
        },
        getProviderResults() {
            const { episode, getProviderCacheResults, season, show } = this;
            getProviderCacheResults({ showSlug: show.id.slug, season, episode });
        },
        forceSearch() {
            const { episode, episodeSlug, season, show } = this;
            let data = {};

            data = {
                showSlug: show.id.slug,
                options: {},
                [episode ? 'episodes' : 'season']: [episodeSlug]
            };

            this.loading = true;
            this.loadingMessage = 'Queue search...';
            api.put('search/manual', data) // eslint-disable-line no-undef
                .then(() => {
                    console.info(`Queued search for show: ${show.id.slug} season: ${season}, episode: ${episode}`);
                    this.loadingMessage = 'Queued search...';
                }).catch(error => {
                    console.error(String(error));
                });
        },
        rowStyleClassFn(row) {
            const { effectiveIgnored, effectiveRequired, search, show } = this;
            const classes = [row.status || 'skipped'];

            const getReleaseNameClasses = name => {
                const classes = [];

                if (effectiveIgnored(show).map(word => {
                    return name.toLowerCase().includes(word.toLowerCase());
                }).filter(x => x === true).length > 0) {
                    classes.push('global-ignored');
                }

                if (effectiveRequired(show).map(word => {
                    return name.toLowerCase().includes(word.toLowerCase());
                }).filter(x => x === true).length > 0) {
                    classes.push('global-required');
                }

                if (search.filters.undesired.map(word => {
                    return name.toLowerCase().includes(word.toLowerCase());
                }).filter(x => x === true).length > 0) {
                    classes.push('global-undesired');
                }

                return classes;
            };

            return [...classes, ...getReleaseNameClasses(row.release)].join(' ');
        },
        async snatchResult(evt, result) {
            const { layout } = this;
            evt.target.src = `images/loading16-${layout.themeName}.gif`;
            try {
                const response = await apiRoute('home/pickManualSearch', { params: { provider: result.provider.id, identifier: result.identifier } });
                if (response.data.result === 'success') {
                    evt.target.src = 'images/save.png';
                } else {
                    evt.target.src = 'images/no16.png';
                }
            } catch (error) {
                console.error(String(error));
                evt.target.src = 'images/no16.png';
            }
        }
    },
    watch: {
        queueitems: {
            async handler(queue) {
                // Check for manual searches
                const queueForThisEpisode = queue.filter(q => ['MANUAL-SEARCH'].includes(q.name) && q.segment.length && q.segment.find(
                    ep => ep.season === this.season && ep.episode === this.episode
                ));

                const [last] = queueForThisEpisode.slice(-1);
                if (last) {
                    const searchStatus = last.success === null ? 'running' : 'finished';

                    if (searchStatus === 'running') {
                        this.loading = true;
                        this.loadingMessage = 'Started searching providers...';
                    } else {
                        this.loadingMessage = 'Finished manual search';
                        setTimeout(() => {
                            this.loading = false;
                            this.loadingMessage = '';
                        }, 5000);
                    }
                }

                // Check for snach selection
                const snatchedForThisEpisode = queue.filter(q => q.name === 'SNATCH-RESULT' && q.segment.length && q.segment.find(
                    ep => ep.season === this.season && ep.episode === this.episode
                ));

                const [lastSnatch] = snatchedForThisEpisode.slice(-1);
                if (lastSnatch && lastSnatch.success === true) {
                    const { getProviderCacheResults, getShowEpisodeHistory, show, season, episode, episodeSlug } = this;

                    // Something changed, let's get a new batch of provider results.
                    await getShowEpisodeHistory({ showSlug: show.id.slug, episodeSlug });
                    await getProviderCacheResults({ showSlug: show.id.slug, season, episode });
                }

                // Update qTip
                addQTip();
            },
            deep: true,
            immediate: false
        }
    }
};
</script>
<style scoped>
</style>
