<template>
    <div id="snatch-selection-template" class="snatch-selection-template">
        <vue-snotify />
        <backstretch v-if="show.id.slug" :slug="show.id.slug" />

        <show-header type="snatch-selection"
                     ref="show-header"
                     :show-id="id"
                     :show-indexer="indexer"
                     :manual-search-type="manualSearchType"
                     @update-overview-status="filterByOverviewStatus = $event"
        />

        <show-history v-show="show" class="show-history" v-bind="{ show, season, episode }" :key="`history-${show.id.slug}-${season}-${episode || ''}`" />

        <show-results v-show="show" class="table-layout" v-bind="{ show, season, episode }" :key="`results-${show.id.slug}-${season}-${episode || ''}`" />

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

<style scoped>
/** Use this as table styling for all table layouts */
.snatch-selection-template >>> .vgt-table {
    width: 100%;
    margin-right: auto;
    margin-left: auto;
    text-align: left;
    border-spacing: 0;
}

.snatch-selection-template >>> .vgt-table th,
.snatch-selection-template >>> .vgt-table td {
    padding: 4px;
    vertical-align: middle;
}

/* remove extra border from left edge */
.snatch-selection-template >>> .vgt-table th:first-child,
.snatch-selection-template >>> .vgt-table td:first-child {
    border-left: none;
}

.snatch-selection-template >>> .vgt-table th {
    text-align: center;
    border-collapse: collapse;
    font-weight: normal;
}

.snatch-selection-template >>> .vgt-table span.break-word {
    word-wrap: break-word;
}

.snatch-selection-template >>> .vgt-table thead th.sorting.sorting-asc {
    background-position-x: right;
    background-position-y: bottom;
}

.snatch-selection-template >>> .vgt-table thead th.sorting {
    background-repeat: no-repeat;
}

.snatch-selection-template >>> .vgt-table thead th {
    padding: 4px;
    cursor: default;
}

.snatch-selection-template >>> .vgt-table input.tablesorter-filter {
    width: 98%;
    height: auto;
    -webkit-box-sizing: border-box;
    -moz-box-sizing: border-box;
    box-sizing: border-box;
}

.snatch-selection-template >>> .vgt-table tr.tablesorter-filter-row,
.snatch-selection-template >>> .vgt-table tr.tablesorter-filter-row td {
    text-align: center;
}

/* optional disabled input styling */
.snatch-selection-template >>> .vgt-table input.tablesorter-filter-row .disabled {
    display: none;
}

.tablesorter-header-inner {
    padding: 0 2px;
    text-align: center;
}

.snatch-selection-template >>> .vgt-table tfoot tr {
    text-align: center;
    border-collapse: collapse;
}

.snatch-selection-template >>> .vgt-table tfoot a {
    text-decoration: none;
}

.snatch-selection-template >>> .vgt-table th.vgt-row-header {
    text-align: left;
}

.snatch-selection-template >>> .vgt-table .season-header {
    display: inline;
    margin-left: 5px;
}

.snatch-selection-template >>> .vgt-table tr.spacer {
    height: 25px;
}

.snatch-selection-template >>> .vgt-dropdown-menu {
    position: absolute;
    z-index: 1000;
    float: left;
    min-width: 160px;
    padding: 5px 0;
    margin: 2px 0 0;
    font-size: 14px;
    text-align: left;
    list-style: none;
    background-clip: padding-box;
    border-radius: 4px;
}

.snatch-selection-template >>> .vgt-dropdown-menu > li > span {
    display: block;
    padding: 3px 20px;
    clear: both;
    font-weight: 400;
    line-height: 1.42857143;
    white-space: nowrap;
}

.snatch-selection-template >>> .align-center {
    display: flex;
    justify-content: center;
}

.snatch-selection-template >>> .indexer-image :not(:last-child) {
    margin-right: 5px;
}

.snatch-selection-template >>> .button-row {
    width: 100%;
    display: inline-block;
}

.snatch-selection-template >>> .fanartBackground {
    clear: both;
    opacity: 0.9;
}

.snatch-selection-template >>> .fanartBackground table {
    table-layout: auto;
    width: 100%;
    border-collapse: collapse;
    border-spacing: 0;
    text-align: center;
    border: none;
    empty-cells: show;
    color: rgb(0, 0, 0) !important;
}

.snatch-selection-template >>> .fanartBackground > table th.vgt-row-header {
    border: none !important;
    background-color: transparent !important;
    color: rgb(255, 255, 255) !important;
    padding-top: 15px !important;
    text-align: left !important;
}

.snatch-selection-template >>> .fanartBackground td.col-search {
    text-align: center;
}

.snatch-selection-template >>> .skipped {
    background-color: rgb(190, 222, 237);
}

.snatch-selection-template >>> .snatched {
    background-color: rgb(235, 193, 234);
}

.snatch-selection-template >>> .downloaded {
    background-color: rgb(255, 218, 138);
}

.snatch-selection-template >>> .failed {
    background-color: rgb(255, 153, 153);
}

.snatch-selection-template >>> .subtitled {
    background-color: rgb(190, 222, 237);
}

.snatch-selection-template >>> .global-ignored td.release span {
    color: red;
}

.snatch-selection-template >>> .show-ignored td.release span {
    color: red;
    font-style: italic;
}

.snatch-selection-template >>> .global-required td.release span {
    color: green;
}

.snatch-selection-template >>> .show-required td.release span {
    color: green;
    font-style: italic;
}

.snatch-selection-template >>> .global-undesired td.release span {
    color: orange;
}

.show-history {
    margin-bottom: 10px;
}
</style>
