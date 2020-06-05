<template>
    <div class="show-results-wrapper">
        <div class="row">
            <div class="col-md-12 top-15 displayShow horizontal-scroll" :class="{ fanartBackground: config.fanartBackground }">
                <div class="button-row">
                    <input class="btn-medusa manualSearchButton top-5 bottom-5" type="button"  value="Refresh Results" @click="refreshResults">
                    <input class="btn-medusa manualSearchButton top-5 bottom-5" type="button"  value="Force Search" @click="forceSearch">
                    <template v-if="loading">
                        <state-switch state="loading" />
                        <span>{{loadingMessage}}</span>
                    </template>
                </div>
                <vue-good-table v-show="show.id.slug"
                                :columns="columns"
                                :rows="combinedResults"
                                :search-options="{
                                    enabled: false
                                }"
                                :sort-options="{
                                    enabled: true,
                                    initialSortBy: { field: 'pubdate', type: 'desc' }
                                }"
                                :row-style-class="rowStyleClassFn"
                                styleClass="vgt-table condensed"
                >
                    <template slot="table-row" slot-scope="props">
                        <span v-if="props.column.label === 'Provider'" class="align-center">
                            <img :src="`images/providers/${props.row.provider.imageName}`" :alt="props.row.provider.name" width="16">
                        </span>

                        <span v-else-if="props.column.label === 'Quality'" class="align-center">
                            <quality-pill v-if="props.row.quality !== 0" :quality="props.row.quality" />
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

import { mapActions, mapGetters, mapState } from 'vuex';
import { VueGoodTable } from 'vue-good-table';
import { StateSwitch } from './helpers';
import QualityPill from './helpers/quality-pill.vue';
import { episodeToSlug, humanFileSize } from '../utils/core';

export default {
    name: 'show-results',
    components: {
        VueGoodTable,
        StateSwitch,
        QualityPill
    },
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
        return {
            columns: [{
                label: 'Release',
                field: 'release'
            },
            {
                label: 'Group',
                field: 'releaseGroup'
            },
            {
                label: 'Provider',
                field: 'provider.name'
            },
            {
                label: 'Quality',
                field: 'quality'
            },
            {
                label: 'Seeds',
                field: 'seeders',
                type: 'number'
            },
            {
                label: 'Peers',
                field: 'leechers',
                type: 'number'
            },
            {
                label: 'Size',
                field: 'size',
                formatFn: humanFileSize,
                type: 'number'
            },
            {
                label: 'Added',
                field: 'dateAdded',
                type: 'date',
                sortable: true,
                dateInputFormat: 'yyyy-MM-dd\'T\'HH:mm:ss', //e.g. 07-09-2017 19:16:25
                dateOutputFormat: 'yyyy/MM/dd HH:mm:ss'
            },
            {
                label: 'Published',
                field: 'pubdate',
                type: 'date',
                sortable: true,
                dateInputFormat: 'yyyy-MM-dd\'T\'HH:mm:ssXXX',
                dateOutputFormat: 'yyyy-MM-dd HH:mm:ss'
            },
            {
                label: 'Updated',
                field: 'time',
                type: 'date',
                sortable: true,
                dateInputFormat: 'yyyy-MM-dd\'T\'HH:mm:ss',
                dateOutputFormat: 'yyyy/MM/dd HH:mm:ss'
            }],
            loading: false,
            loadingMessage: ''
        };
    },
    mounted() {
        const { getProviders, getProviderResults } = this;
        getProviders()
            .then(() => {
                // We need to get the providers, before we know which providers to query.
                getProviderResults();
            });
    },
    computed: {
        ...mapState({
            config: state => state.config,
            providers: state => state.provider.providers,
            queueitems: state => state.search.queueitems
        }),
        ...mapGetters({
            fuzzyParseDateTime: 'fuzzyParseDateTime'
        }),
        combinedResults() {
            const { episode, providers, season, show } = this;
            let results = [];

            for (const provider of Object.values(providers).filter(provider => provider.config.enabled)) {
                if (provider.cache && provider.cache.length > 0) {
                    results = [...results, ...provider.cache.filter(
                        searchResult =>
                            searchResult.showSlug === show.id.slug &&
                            searchResult.season === season &&
                            searchResult.episodes.includes(episode))];
                }
            }
            return results;
        }
    },
    methods: {
        humanFileSize,
        ...mapActions({
            getProviders: 'getProviders',
            getProviderCacheResults: 'getProviderCacheResults'
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
            // const unwatch = this.$watch('show.id.slug', showSlug => {
            // Use apiv2 to get latest provider cache results
            getProviderCacheResults({ showSlug: show.id.slug, season, episode });
            //     unwatch();
            // });
        },
        refreshResults() {
            const { episode, getProviderCacheResults, season, show } = this;
            getProviderCacheResults({ showSlug: show.id.slug, season, episode });
        },
        forceSearch() {
            // Start a new manual search
            const { episode, season, search } = this;
            search([episodeToSlug(season, episode)]);
        },
        search(episodes) {
            const { episode, season, show } = this;
            let data = {};

            if (episodes) {
                data = {
                    showSlug: show.id.slug,
                    episodes,
                    options: {}
                };
            }

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
            const classes = [];
            return classes;
        }
    },
    watch: {
        queueitems: {
            handler(queue) {
                const queueForThisEpisode = queue.filter(q => q.segment.length && q.segment.find(
                    ep => ep.season === this.season && ep.episode === this.episode
                ));

                const [last] = queueForThisEpisode.slice(-1);
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
            },
            deep: true,
            immediate: false
        }
    }
};
</script>
<style scoped>

</style>
