<template>
    <div id="snatch-selection-template">
        <vue-snotify />
        <backstretch v-if="show.id.slug" :slug="show.id.slug" />

        <show-header type="snatch-selection"
                     ref="show-header"
                     :show-id="id"
                     :show-indexer="indexer"
                     :manual-search-type="manualSearchType"
                     @update-overview-status="filterByOverviewStatus = $event"
        />

        <show-history v-show="show" class="show-history vgt-table-styling" v-bind="{ show, season, episode }" :key="`history-${show.id.slug}-${season}-${episode || ''}`" />

        <show-results v-show="show" class="table-layout vgt-table-styling" v-bind="{ show, season, episode }" :key="`results-${show.id.slug}-${season}-${episode || ''}`" />

    </div>
</template>

<script>
import { mapState, mapGetters, mapActions } from 'vuex';
import ShowHeader from './show-header.vue';
import ShowHistory from './show-history.vue';
import ShowResults from './show-results.vue';
import Backstretch from './backstretch.vue';

export default {
    name: 'snatch-selection',
    template: '#snatch-selection-template',
    components: {
        Backstretch,
        ShowHeader,
        ShowHistory,
        ShowResults
    },
    metaInfo() {
        if (!this.show || !this.show.title) {
            return {
                title: 'Medusa'
            };
        }
        const { title } = this.show;
        return {
            title,
            titleTemplate: '%s | Medusa'
        };
    },
    computed: {
        ...mapState({
            shows: state => state.shows.shows,
            config: state => state.config.general,
            search: state => state.config.search,
            history: state => state.history
        }),
        ...mapGetters({
            show: 'getCurrentShow',
            effectiveIgnored: 'effectiveIgnored',
            effectiveRequired: 'effectiveRequired',
            getShowHistoryBySlug: 'getShowHistoryBySlug',
            getEpisode: 'getEpisode'
        }),
        indexer() {
            return this.$route.query.indexername;
        },
        id() {
            return Number(this.$route.query.seriesid);
        },
        season() {
            return Number(this.$route.query.season);
        },
        episode() {
            if (this.$route.query.manual_search_type === 'season') {
                return;
            }
            return Number(this.$route.query.episode);
        },
        manualSearchType() {
            return this.$route.query.manual_search_type;
        }
    },
    methods: {
        ...mapActions({
            getShow: 'getShow', // Map `this.getShow()` to `this.$store.dispatch('getShow')`
            getHistory: 'getHistory'
        }),
        // TODO: Move this to show-results!
        getReleaseNameClasses(name) {
            const { effectiveIgnored, effectiveRequired, search, show } = this;
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

            return classes.join(' ');
        }
    },
    mounted() {
        const {
            indexer,
            id,
            show,
            getShow,
            $store
        } = this;

        // Let's tell the store which show we currently want as current.
        $store.commit('currentShow', {
            indexer,
            id
        });

        // We need the show info, so let's get it.
        if (!show || !show.id.slug) {
            getShow({ id, indexer, detailed: false });
        }
    }
};
</script>

<style scoped src="../style/vgt-table.css">
.vgt-table-styling >>> .align-center {
    display: flex;
    justify-content: center;
}

.vgt-table-styling >>> .indexer-image :not(:last-child) {
    margin-right: 5px;
}

.vgt-table-styling >>> .button-row {
    width: 100%;
    display: inline-block;
}

.vgt-table-styling >>> .fanartBackground {
    clear: both;
    opacity: 0.9;
}

.vgt-table-styling >>> .fanartBackground table {
    table-layout: auto;
    width: 100%;
    border-collapse: collapse;
    border-spacing: 0;
    text-align: center;
    border: none;
    empty-cells: show;
    color: rgb(0, 0, 0) !important;
}

.vgt-table-styling >>> .fanartBackground > table th.vgt-row-header {
    border: none !important;
    background-color: transparent !important;
    color: rgb(255, 255, 255) !important;
    padding-top: 15px !important;
    text-align: left !important;
}

.vgt-table-styling >>> .fanartBackground td.col-search {
    text-align: center;
}

.vgt-table-styling >>> .skipped {
    background-color: rgb(190, 222, 237);
}

.vgt-table-styling >>> .snatched {
    background-color: rgb(235, 193, 234);
}

.vgt-table-styling >>> .downloaded {
    background-color: rgb(255, 218, 138);
}

.vgt-table-styling >>> .failed {
    background-color: rgb(255, 153, 153);
}

.vgt-table-styling >>> .subtitled {
    background-color: rgb(190, 222, 237);
}

.vgt-table-styling >>> .global-ignored td.release span {
    color: red;
}

.vgt-table-styling >>> .show-ignored td.release span {
    color: red;
    font-style: italic;
}

.vgt-table-styling >>> .global-required td.release span {
    color: green;
}

.vgt-table-styling >>> .show-required td.release span {
    color: green;
    font-style: italic;
}

.vgt-table-styling >>> .global-undesired td.release span {
    color: orange;
}

.show-history {
    margin-bottom: 10px;
}
</style>
