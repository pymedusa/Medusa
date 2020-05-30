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
                                styleClass="vgt-table condensed"
                />
            </div>
        </div>
    </div>
</template>
<script>

import { mapActions, mapState } from 'vuex';
import { VueGoodTable } from 'vue-good-table';
import { StateSwitch } from './helpers';

import { episodeToSlug, humanFileSize } from '../utils/core';

export default {
    name: 'show-results',
    components: {
        VueGoodTable,
        StateSwitch
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
                label: 'Date Added',
                field: 'dateAdded',
                type: 'date',
                dateInputFormat: 'yyyy-MM-dd\'T\'HH:mm:ss', //e.g. 07-09-2017 19:16:25
                dateOutputFormat: 'yyyy/MM/dd HH:mm:ss'
            },
            {
                label: 'Date Published',
                field: 'pubdate',
                type: 'date',
                sortable: true,
                dateInputFormat: 'yyyy-MM-dd\'T\'HH:mm:ssXXX',
                dateOutputFormat: 'yyyy-MM-dd\'T\'HH:mm:ssXXX'
            },
            {
                label: 'Provider',
                field: 'provider.name'
            },
            {
                label: 'Size',
                field: 'size',
                formatFn: humanFileSize,
                type: 'number'
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
            providers: state => state.provider.providers
        }),
        combinedResults() {
            const { providers } = this;
            let results = [];

            for (const provider of Object.values(providers).filter(provider => provider.config.enabled)) {
                if (provider.cache && provider.cache.length > 0) {
                    results = [...results, ...provider.cache];
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
            const { episode, getProviderCacheResults, season } = this;
            const unwatch = this.$watch('show.id.slug', showSlug => {
                // Use apiv2 to get latest provider cache results
                getProviderCacheResults({ showSlug, season, episode });
                unwatch();
            });
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
            const { show } = this;
            let data = {};

            if (episodes) {
                data = {
                    showSlug: show.id.slug,
                    episodes,
                    options: {}
                };
            }

            this.loading = true;
            this.loadingMessage = `Manual searching providers for episode ${episodes.join(' ,')}`;
            api.put('search/manual', data) // eslint-disable-line no-undef
                .then(() => {
                    console.info(`started search for show: ${show.id.slug} episode: ${episodes[0]}`);
                    this.loadingMessage = `started search for show: ${show.id.slug} episode: ${episodes[0]}`;
                }).catch(error => {
                    console.error(String(error));
                });
        }
    }
};
</script>
<style scoped>

</style>
