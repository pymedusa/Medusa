<template>
    <div class="horizontal-scroll">
        <vue-good-table v-if="shows.length > 0"
            :columns="columns"
            :rows="shows"
            :search-options="{
                enabled: true,
                trigger: 'enter',
                skipDiacritics: false,
                placeholder: 'Search',
            }"
            :sort-options="{
                enabled: true,
                initialSortBy: { field: 'title', type: 'asc' }
            }"
            :column-filter-options="{
                enabled: true
            }">

                <template slot="table-row" slot-scope="props">
                    <span v-if="props.column.label == 'Show'">
                        <app-link :href="`home/displayShow?indexername=${props.row.indexer}&seriesid=${props.row.id[props.row.indexer]}`">{{ props.row.title }}</app-link>
                    </span>

                    <span v-else-if="props.column.label == 'Network'">
                        <span class="align-center">{{ props.row.network }}</span>
                    </span>

                    <span v-else-if="props.column.label == 'Indexer'" class="align-center">
                        <app-link v-if="props.row.id.imdb" :href="'http://www.imdb.com/title/' + props.row.id.imdb" :title="`http://www.imdb.com/title/${props.row.id.imdb}`">
                            <img alt="[imdb]" height="16" width="16" src="images/imdb.png" />
                        </app-link>
                        <app-link v-if="props.row.id.trakt" :href="'https://trakt.tv/shows/' + props.row.id.trakt" :title="`https://trakt.tv/shows/${props.row.id.trakt}`">
                            <img alt="[trakt]" height="16" width="16" src="images/trakt.png" />
                        </app-link>
                        <app-link v-if="showIndexerUrl && indexerConfig[props.row.indexer].icon" :href="showIndexerUrl(props.row)" :title="showIndexerUrl(props.row)">
                            <img :alt="indexerConfig[props.row.indexer].name" height="16" width="16" :src="'images/' + indexerConfig[props.row.indexer].icon" style="margin-top: -1px; vertical-align:middle;">
                        </app-link>
                    </span>

                    <span v-else-if="props.column.label == 'Quality'" class="align-center">
                        <quality-pill :allowed="props.row.config.qualities.allowed" :preferred="props.row.config.qualities.preferred" show-title></quality-pill>
                    </span>

                    <span v-else-if="props.column.label == 'Downloads'">
                        <progress-bar v-bind="props.row.stats.tooltip"></progress-bar>
                    </span>

                    <span v-else-if="props.column.label == 'Size'" class="align-center">
                        {{ prettyBytes(props.row.stats.episodes.size) }}
                    </span>

                    <span v-else-if="props.column.label == 'Active'" class="align-center">
                       <img :src="'images/' + (!props.row.config.paused && props.row.status === 'Continuing' ? 'Yes' : 'No') + '16.png'" :alt="!props.row.config.paused && props.row.status === 'Continuing' ? 'Yes' : 'No'" width="16" height="16" />
                    </span>

                    <span v-else-if="props.column.label == 'Xem'" class="align-center">
                        <img :src="`images/${props.row.xemNumbering.length !== 0  ? 'yes16.png' : 'no16.png'}`" :alt="props.row.xemNumbering.length !== 0  ? 'yes' : 'no'" width="16" height="16" />
                    </span>

                    <span v-else class="align-center">
                        {{props.formattedRow[props.column.field]}}
                    </span>
                </template>


        </vue-good-table>

    </div> <!-- .horizontal-scroll -->
</template>
<script>
import pretty from 'pretty-bytes';

import { mapGetters, mapState } from 'vuex';
import { AppLink } from '../helpers';
import { ProgressBar } from '../helpers';
import { QualityPill } from '../helpers';
import { Asset } from '../helpers';
import { VueGoodTable } from 'vue-good-table';

export default {
    name: 'simple',
    components: {
        Asset,
        AppLink,
        ProgressBar,
        QualityPill,
        VueGoodTable
    },
    props: {
        layout: {
            validator: val => val === null || typeof val === 'string',
            required: true
        },
        shows: {
            type: Array,
            required: true
        },
        listTitle: {
            type: String
        },
        header: {
            type: Boolean
        }
    },
    data() {
        return {
            columns: [{
                label: 'Next Ep',
                field: row => this.parseNextDateFn(row),
                sortable: false
            }, {
                label: 'Prev Ep',
                field: row => this.parsePrevDateFn(row),
                sortable: false
            }, {
                label: 'Show',
                field: 'title'
            }, {
                label: 'Network',
                field: 'network'
            }, {
                label: 'Indexer',
                field: 'id'
            }, {
                label: 'Quality',
                field: 'quality'
            }, {
                label: 'Downloads',
                field: 'stats.tooltip.text'
            }, {
                label: 'Size',
                field: 'size'
            }, {
                label: 'Active',
                field: 'config.paused'
            }, {
                label: 'Status',
                field: 'status'
            }, {
                label: 'Xem',
                field: 'status'
            }]
        }
    },
    computed: {
        ...mapState({
            config: state => state.config,
            indexerConfig: state => state.indexers.indexers,
            sortArticle: state => state.layout.sortArticle 
        }),
        ...mapGetters({
            fuzzyParseDateTime: 'fuzzyParseDateTime'
        }),
        sortedShows() {
            const { show, sortArticle } = this;
            const removeArticle = str => sortArticle ? str.replace(/^((?:A(?!\s+to)n?)|The)\s/i, '') : str;
            return shows.concat().sort((a, b) => removeArticle(a.title).toLowerCase().localeCompare(removeArticle(b.title).toLowerCase()));
        }
    },
    methods: {
        prettyBytes: bytes => pretty(bytes),
        showIndexerUrl(show) {
            const { indexerConfig } = this;
            if (!show.indexer) {
                return;
            }

            const id = show.id[show.indexer];
            const indexerUrl = indexerConfig[show.indexer].showUrl;

            return `${indexerUrl}${id}`;
        },
        parsePrevDateFn(row) {
            const { fuzzyParseDateTime } = this;
            if (row.prevAirDate) {
                console.log(`Calculating time for show ${row.title} prev date: ${row.prevAirDate}`);
                return fuzzyParseDateTime(row.prevAirDate)
            } else {
                return ''
            }
        },
        parseNextDateFn(row) {
            const { fuzzyParseDateTime } = this;
            if (row.nextAirDate) {
                console.log(`Calculating time for show ${row.title} next date: ${row.nextAirDate}`);
                return fuzzyParseDateTime(row.nextAirDate)
            } else {
                return ''
            }
        }
    }
};
</script>
<style>
.vgt-table {
    width: 100%;
    margin-right: auto;
    margin-left: auto;
    color: rgb(0, 0, 0);
    text-align: left;
    background-color: rgb(221, 221, 221);
    border-spacing: 0;
}

.vgt-table th,
.vgt-table td {
    padding: 4px;
    border-top: rgb(255, 255, 255) 1px solid;
    border-left: rgb(255, 255, 255) 1px solid;
    vertical-align: middle;
}

/* remove extra border from left edge */
.vgt-table th:first-child,
.vgt-table td:first-child {
    border-left: none;
}

.vgt-table th {
    color: rgb(255, 255, 255);
    text-align: center;
    text-shadow: -1px -1px 0 rgba(0, 0, 0, 0.3);
    background-color: rgb(51, 51, 51);
    border-collapse: collapse;
    font-weight: normal;
}

.vgt-table span.break-word {
    word-wrap: break-word;
}

.vgt-table thead th.sorting.sorting-desc {
    background-color: rgb(85, 85, 85);
    background-image: url(data:image/gif;base64,R0lGODlhFQAEAIAAAP///////yH5BAEAAAEALAAAAAAVAAQAAAINjB+gC+jP2ptn0WskLQA7);
}

.vgt-table thead th.sorting.sorting-asc {
    background-color: rgb(85, 85, 85);
    background-image: url(data:image/gif;base64,R0lGODlhFQAEAIAAAP///////yH5BAEAAAEALAAAAAAVAAQAAAINjI8Bya2wnINUMopZAQA7);
    background-position-x: right;
    background-position-y: bottom;
}

.vgt-table thead th.sorting {
    background-repeat: no-repeat;
}

.vgt-table thead th {
    background-image: none;
    padding: 4px;
    cursor: default;
}

.vgt-table input.tablesorter-filter {
    width: 98%;
    height: auto;
    -webkit-box-sizing: border-box;
    -moz-box-sizing: border-box;
    box-sizing: border-box;
}

.vgt-table tr.tablesorter-filter-row,
.vgt-table tr.tablesorter-filter-row td {
    text-align: center;
}

/* optional disabled input styling */
.vgt-table input.tablesorter-filter-row .disabled {
    display: none;
}

.tablesorter-header-inner {
    padding: 0 2px;
    text-align: center;
}

.vgt-table tfoot tr {
    color: rgb(255, 255, 255);
    text-align: center;
    text-shadow: -1px -1px 0 rgba(0, 0, 0, 0.3);
    background-color: rgb(51, 51, 51);
    border-collapse: collapse;
}

.vgt-table tfoot a {
    color: rgb(255, 255, 255);
    text-decoration: none;
}

.vgt-table th.vgt-row-header {
    text-align: left;
}

.vgt-table .season-header {
    display: inline;
    margin-left: 5px;
}

.vgt-table tr.spacer {
    height: 25px;
}

.unaired {
    background-color: rgb(245, 241, 228);
}

.skipped {
    background-color: rgb(190, 222, 237);
}

.preferred {
    background-color: rgb(195, 227, 200);
}

.archived {
    background-color: rgb(195, 227, 200);
}

.allowed {
    background-color: rgb(255, 218, 138);
}

.wanted {
    background-color: rgb(255, 176, 176);
}

.snatched {
    background-color: rgb(235, 193, 234);
}

.downloaded {
    background-color: rgb(195, 227, 200);
}

.failed {
    background-color: rgb(255, 153, 153);
}

span.unaired {
    color: rgb(88, 75, 32);
}

span.skipped {
    color: rgb(29, 80, 104);
}

span.preffered {
    color: rgb(41, 87, 48);
}

span.allowed {
    color: rgb(118, 81, 0);
}

span.wanted {
    color: rgb(137, 0, 0);
}

span.snatched {
    color: rgb(101, 33, 100);
}

span.unaired b,
span.skipped b,
span.preferred b,
span.allowed b,
span.wanted b,
span.snatched b {
    color: rgb(0, 0, 0);
    font-weight: 800;
}

td.col-footer {
    text-align: left !important;
}

.vgt-wrap__footer {
    color: rgb(255, 255, 255);
    padding: 1em;
    background-color: rgb(51, 51, 51);
    margin-bottom: 1em;
    display: flex;
    justify-content: space-between;
}

.footer__row-count,
.footer__navigation__page-info {
    display: inline;
}

.footer__row-count__label {
    margin-right: 1em;
}

.vgt-wrap__footer .footer__navigation {
    font-size: 14px;
}

.vgt-pull-right {
    float: right !important;
}

.vgt-wrap__footer .footer__navigation__page-btn .chevron {
    width: 24px;
    height: 24px;
    border-radius: 15%;
    position: relative;
    margin: 0 8px;
}

.vgt-wrap__footer .footer__navigation__info,
.vgt-wrap__footer .footer__navigation__page-info {
    display: inline-flex;
    color: #909399;
    margin: 0 16px;
    margin-top: 0;
    margin-right: 16px;
    margin-bottom: 0;
    margin-left: 16px;
}

.select-info span {
    margin-left: 5px;
    line-height: 40px;
}

/** Style the modal. This should be saved somewhere, where we create one modal template with slots, and style that. */
.modal-container {
    border: 1px solid rgb(17, 17, 17);
    box-shadow: 0 0 12px 0 rgba(0, 0, 0, 0.175);
    border-radius: 0;
}

.modal-header {
    padding: 9px 15px;
    border-bottom: none;
    border-radius: 0;
    background-color: rgb(55, 55, 55);
}

.modal-content {
    background: rgb(34, 34, 34);
    border-radius: 0;
    border: 1px solid rgba(0, 0, 0, 0.2);
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.5);
    color: white;
}

.modal-body {
    background: rgb(34, 34, 34);
    overflow-y: auto;
}

.modal-footer {
    border-top: none;
    text-align: center;
}

.subtitles > div {
    float: left;
}

.subtitles > div:not(:last-child) {
    margin-right: 2px;
}

.align-center {
    display: flex;
    justify-content: center;
}
</style>
