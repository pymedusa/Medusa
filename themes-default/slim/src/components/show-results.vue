<template>
    <div class="show-results-wrapper">
        <div class="row horizontal-scroll">
            <div class="col-md-12 top-15">
                <div class="button-row">
                    <input class="btn-medusa manualSearchButton top-5 bottom-5" type="button"  value="Refresh Results" @click="getProviderResults">
                    <input class="btn-medusa manualSearchButton top-5 bottom-5" type="button"  value="Force Search" @click="forceSearch">
                    <template v-if="loading">
                        <state-switch state="loading" />
                        <span>{{loadingMessage}}</span>
                    </template>
                </div>
                <vue-good-table
                    v-show="show.id.slug"
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
                    :pagination-options="{
                        enabled: true,
                        perPage: paginationPerPage,
                        perPageDropdown: [...perPageDropdown, -1],
                        perPageDropdownEnabled: false,
                        infoFn: paginationInfo
                    }"
                    @on-per-page-change="updatePaginationPerPage($event.currentPerPage)"
                    @on-sort-change="saveSorting"
                >
                    <template slot="table-actions-bottom">
                        <table-page-size :value="paginationPerPage" :options="perPageDropdown" @input="updatePaginationPerPage" />
                    </template><template slot="table-row" slot-scope="props">
                        <span v-if="props.column.label === 'Provider'" class="align-center">
                            <img :src="`images/providers/${props.row.provider.imageName}`"
                                 :alt="props.row.provider.name" width="16"
                                 :title="props.row.provider.name"
                                 v-tooltip.right="props.row.provider.name"
                                 onError="this.onerror=null;this.src='images/providers/missing.png';"
                            >
                        </span>

                        <span v-else-if="props.column.label === 'Group'" class="align-center release-group">
                            {{props.row.releaseGroup}}
                            <manage-whitelist v-if="show.config.anime && props.row.releaseGroup" :show="show" :releaseGroup="props.row.releaseGroup" />
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

                    <div id="no-result" slot="emptystate">
                        No search results available
                    </div>
                </vue-good-table>
            </div>
        </div>
    </div>
</template>
<script>

import { cloneDeep, isEqual } from 'lodash';
import { mapActions, mapGetters, mapState } from 'vuex';
import { VueGoodTable } from 'vue-good-table';
import { manageCookieMixin } from '../mixins/manage-cookie';
import { StateSwitch } from './helpers';
import QualityPill from './helpers/quality-pill.vue';
import { episodeToSlug, humanFileSize } from '../utils/core';
import { VTooltip } from 'v-tooltip';
import ManageWhitelist from './show-results/manage-whitelist.vue';
import TablePageSize, { formatPaginationInfo } from './helpers/table-page-size.vue';

export default {
    name: 'show-results',
    components: {
        VueGoodTable,
        StateSwitch,
        QualityPill,
        ManageWhitelist,
        TablePageSize
    },
    directives: {
        tooltip: VTooltip
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
        const perPageDropdown = [25, 50, 100, 250, 500];
        const getPaginationPerPage = () => {
            const rows = getCookie('pagination-perPage');
            if (!rows) {
                return 50;
            }

            if (rows !== -1 && !perPageDropdown.includes(rows)) {
                return 500;
            }
            return rows;
        };
        return {
            columns: [{
                label: 'Release',
                field: 'release',
                tdClass: 'release',
                filterOptions: {
                    enabled: true
                },
                hidden: getCookie('Release')
            },
            {
                label: 'Group',
                field: 'releaseGroup',
                filterOptions: {
                    enabled: true
                },
                width: '0',
                hidden: getCookie('Group')
            },
            {
                label: 'Provider',
                field: 'provider.name',
                filterOptions: {
                    enabled: true
                },
                width: '8rem',
                hidden: getCookie('Provider')
            },
            {
                label: 'Quality',
                field: 'quality',
                type: 'number',
                filterOptions: {
                    customFilter: true
                },
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
                formatFn: bytes => humanFileSize(bytes),
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
            loadingMessage: '',
            perPageDropdown,
            paginationPerPage: getPaginationPerPage()
        };
    },
    created() {
        this.resultsActive = false;
        // Keep only an identity token in the store, never the component itself.
        this.resultsOwner = {};
        this.resultsRequestGeneration = 0;
        this.loadingTimeout = null;
    },
    mounted() {
        return this.activateResults();
    },
    activated() {
        return this.activateResults();
    },
    deactivated() {
        this.stopResults();
    },
    beforeDestroy() {
        this.stopResults();
    },
    computed: {
        ...mapState({
            config: state => state.config.general,
            layout: state => state.config.layout,
            search: state => state.config.search,
            providers: state => state.provider.providers,
            queueitems: state => state.queue.queueitems,
            history: state => state.history.episodeHistory,
            client: state => state.auth.client
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
                const sortedHistory = episodeHistory.slice().sort(item => item.actionDate).reverse();
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
        hasInactiveParent() {
            // Cached route parents can render new children while they are inactive.
            for (let parent = this; parent; parent = parent.$parent) {
                if (parent._inactive) {
                    return true;
                }
            }
            return false;
        },
        isResultsActive() {
            return this.resultsActive && !this._isDestroyed && !this.hasInactiveParent();
        },
        activateResults() {
            if (this.resultsActive || this.hasInactiveParent()) {
                return;
            }
            this.resultsActive = true;
            this.$store.commit('claimProviderCache', {
                owner: this.resultsOwner, showSlug: this.show.id.slug, season: this.season, episode: this.episode
            });
            return this.loadInitialResults();
        },
        stopResults() {
            this.resultsActive = false;
            ++this.resultsRequestGeneration;
            this.$store.commit('releaseProviderCache', this.resultsOwner);
            clearTimeout(this.loadingTimeout);
            this.loadingTimeout = null;
            this.loading = false;
            this.loadingMessage = '';
        },
        createResultsRequest() {
            const { season, episode } = this;
            const showSlug = this.show.id.slug;
            const generation = ++this.resultsRequestGeneration;
            clearTimeout(this.loadingTimeout);
            this.loadingTimeout = null;
            return {
                owner: this.resultsOwner, showSlug, season, episode,
                isCurrent: () => this.isResultsActive() && generation === this.resultsRequestGeneration &&
                    this.show.id.slug === showSlug && this.season === season && this.episode === episode
            };
        },
        async loadInitialResults() {
            const request = this.createResultsRequest();
            await this.getProviders();
            if (!request.isCurrent()) {
                return;
            }
            const result = await this.getProviderCacheResults(request);
            if (request.isCurrent() && !result.cancelled && result.providersSearched > 0 &&
                result.totalSearchResults.length === 0 && this.combinedResults.length === 0) {
                this.forceSearch();
            }
        },
        finishLoading(request, delay) {
            clearTimeout(this.loadingTimeout);
            this.loadingTimeout = setTimeout(() => {
                this.loadingTimeout = null;
                if (request.isCurrent()) {
                    this.loading = false;
                    this.loadingMessage = '';
                }
            }, delay);
        },
        close() {
            this.$emit('close');
            // Destroy the vue listeners, etc
            this.$destroy();
            // Remove the element from the DOM
            this.$el.remove();
        },
        async getProviderResults() {
            if (!this.isResultsActive()) {
                return;
            }
            const request = this.createResultsRequest();
            this.loading = true;
            this.loadingMessage = 'Refreshing results from cache';
            const result = await this.getProviderCacheResults(request);
            if (request.isCurrent()) {
                this.finishLoading(request, result.cancelled ? 0 : 1000);
            }
        },
        forceSearch() {
            if (!this.isResultsActive()) {
                return;
            }
            const request = this.createResultsRequest();
            const { episode, episodeSlug, season, show } = this;
            let data = {};

            data = {
                showSlug: show.id.slug,
                options: {},
                [episode ? 'episodes' : 'season']: [episodeSlug]
            };

            this.loading = true;
            this.loadingMessage = 'Queue search...';
            return this.client.api.put('search/manual', data) // eslint-disable-line no-undef
                .then(() => {
                    if (request.isCurrent()) {
                        console.info(`Queued search for show: ${show.id.slug} season: ${season}, episode: ${episode}`);
                        this.loadingMessage = 'Queued search...';
                    }
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
                const response = await this.client.apiRoute('home/pickManualSearch', { params: { provider: result.provider.id, identifier: result.identifier } });
                if (response.data.result === 'success') {
                    evt.target.src = 'images/save.png';
                } else {
                    evt.target.src = 'images/no16.png';
                }
            } catch (error) {
                console.error(String(error));
                evt.target.src = 'images/no16.png';
            }
        },
        updatePaginationPerPage(rows) {
            const { setCookie } = this;
            if (this.paginationPerPage === rows) {
                return;
            }
            this.paginationPerPage = rows;
            setCookie('pagination-perPage', rows);
        },
        paginationInfo(info) {
            return formatPaginationInfo(info, this.paginationPerPage);
        }
    },
    watch: {
        combinedResults() {
            const table = this.$refs['vgt-show-results'];
            if (!this.isResultsActive() || !table || table.currentPage <= 1) {
                return;
            }

            const page = table.currentPage;
            const controls = cloneDeep({ filters: table.columnFilters, sorts: table.sorts, perPage: table.currentPerPage });
            this.$nextTick(() => {
                if (!this.isResultsActive() || this.$refs['vgt-show-results'] !== table || !isEqual(controls, {
                    filters: table.columnFilters, sorts: table.sorts, perPage: table.currentPerPage
                })) {
                    return;
                }

                const maxPage = table.currentPerPage > 0 ? Math.max(1, Math.ceil(table.totalRowCount / table.currentPerPage)) : 1;
                const currentPage = Math.min(page, maxPage);
                if (table.currentPage !== currentPage) {
                    table.changePage(currentPage);
                }
            });
        },
        queueitems: {
            async handler(queue) {
                if (!this.isResultsActive()) {
                    return;
                }
                const matchesScope = item => item.show && item.show.id.slug === this.show.id.slug &&
                    item.segment.some(ep => ep.season === this.season && (this.episode === undefined || ep.episode === this.episode));
                // Check for manual searches
                const queueForThisEpisode = queue.filter(q => q.name === 'MANUAL-SEARCH' && matchesScope(q));

                const [last] = queueForThisEpisode.slice(-1);
                if (last) {
                    const generation = this.resultsRequestGeneration;
                    const request = { isCurrent: () => this.isResultsActive() && generation === this.resultsRequestGeneration };
                    const searchStatus = last.success === null ? 'running' : 'finished';

                    if (searchStatus === 'running') {
                        clearTimeout(this.loadingTimeout);
                        this.loading = true;
                        this.loadingMessage = 'Started searching providers...';
                    } else {
                        this.loadingMessage = 'Finished manual search';
                        this.finishLoading(request, 5000);
                    }
                }

                // Check for snach selection
                const snatchedForThisEpisode = queue.filter(q => q.name === 'SNATCH-RESULT' && matchesScope(q));

                const [lastSnatch] = snatchedForThisEpisode.slice(-1);
                if (lastSnatch && lastSnatch.success === true) {
                    const request = this.createResultsRequest();
                    const { getProviderCacheResults, getShowEpisodeHistory, show, episodeSlug } = this;
                    if (last && last.success !== null) {
                        // A failed history fetch must not keep a completed search's spinner alive.
                        this.finishLoading(request, 5000);
                    }

                    // Something changed, let's get a new batch of provider results.
                    await getShowEpisodeHistory({ showSlug: show.id.slug, episodeSlug });
                    if (request.isCurrent()) {
                        await getProviderCacheResults(request);
                        if (request.isCurrent() && (!last || last.success !== null)) {
                            this.finishLoading(request, 1000);
                        }
                    }
                }
            },
            deep: true,
            immediate: false
        }
    }
};
</script>
<style scoped>
.show-results-wrapper >>> tbody {
    color: rgb(0, 0, 0);
}

#no-result {
    color: rgb(255, 255, 255);
}

.release-group {
    position: relative;
}
</style>
