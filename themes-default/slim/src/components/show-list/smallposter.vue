<template>
    <div class="horizontal-scroll">
        <vue-good-table v-if="shows.length > 0"
                        :columns="columns"
                        :rows="shows"
                        :search-options="{
                            enabled: false
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
                    <div class="imgsmallposter small">
                        <app-link :href="`home/displayShow?indexername=${props.row.indexer}&seriesid=${props.row.id[props.row.indexer]}`" :title="props.row.title">
                            <asset default="images/poster.png" :show-slug="props.row.id.slug" type="posterThumb" cls="small" :alt="props.row.title" :title="props.row.title" :link="false"/>
                        </app-link>
                        <app-link :href="`home/displayShow?indexername=${props.row.indexer}&seriesid=${props.row.id[props.row.indexer]}`" style="vertical-align: middle;">{{ props.row.title }}</app-link>
                    </div>
                </span>

                <span v-else-if="props.column.label == 'Network'">
                    <template v-if="props.row.network">
                        <span :title="props.row.network" class="hidden-print">
                            <asset default="images/network/nonetwork.png" :show-slug="props.row.indexer + props.row.id[props.row.indexer]" type="network" cls="show-network-image" :link="false" width="54" height="27" :alt="props.row.network" :title="props.row.network"></asset>
                        </span>
                        <span class="visible-print-inline">{{ props.row.network }}</span>
                    </template>
                    <template v-else>
                        <span title="No Network" class="hidden-print"><img id="network" width="54" height="27" src="images/network/nonetwork.png" alt="No Network" title="No Network" /></span>
                        <span class="visible-print-inline">No Network</span>
                    </template>
                </span>

                <span v-else-if="props.column.label == 'Indexer'" class="align-center">
                    <app-link v-if="props.row.id.imdb" :href="`http://www.imdb.com/title/${props.row.id.imdb}`" :title="`http://www.imdb.com/title/${props.row.id.imdb}`">
                        <img alt="[imdb]" height="16" width="16" src="images/imdb.png" />
                    </app-link>
                    <app-link v-if="props.row.id.trakt" :href="`https://trakt.tv/shows/${props.row.id.trakt}`" :title="`https://trakt.tv/shows/${props.row.id.trakt}`">
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
                    <img :src="`images/${props.formattedRow[props.column.field]}16.png`" :alt="props.formattedRow[props.column.field]" width="16" height="16" />
                </span>

                <span v-else-if="props.column.label == 'Xem'" class="align-center">
                    <img :src="`images/${props.formattedRow[props.column.field]}16.png`" :alt="props.formattedRow[props.column.field]" width="16" height="16" />
                </span>

                <span v-else class="align-center">
                    {{props.formattedRow[props.column.field]}}
                </span>
            </template>
        </vue-good-table>

    </div> <!-- .horizontal-scroll -->
</template>
<script>
import { mapGetters, mapState } from 'vuex';
import pretty from 'pretty-bytes';
import { Asset } from '../helpers';
import { AppLink } from '../helpers';
import { ProgressBar } from '../helpers';
import { QualityPill } from '../helpers';
import { VueGoodTable } from 'vue-good-table';
import { manageCookieMixin } from '../../utils/core';

export default {
    name: 'smallposter',
    components: {
        Asset,
        AppLink,
        ProgressBar,
        QualityPill,
        VueGoodTable
    },
    mixins: [
        manageCookieMixin('home-hide-field')
    ],
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
        const { getCookie } = this;
        return {
            columns: [{
                label: 'Next Ep',
                field: row => this.parseNextDateFn(row),
                sortable: true,
                sortFn: this.sortDateNext,
                hidden: getCookie('Next Ep')
            }, {
                label: 'Prev Ep',
                field: row => this.parsePrevDateFn(row),
                sortable: true,
                sortFn: this.sortDatePrev,
                hidden: getCookie('Prev Ep')
            }, {
                label: 'Show',
                field: 'title',
                hidden: getCookie('Show')
            }, {
                label: 'Network',
                field: 'network',
                hidden: getCookie('Network')
            }, {
                label: 'Indexer',
                field: 'indexer',
                hidden: getCookie('Indexer')
            }, {
                label: 'Quality',
                field: 'quality',
                sortable: false,
                hidden: getCookie('Quality')
            }, {
                label: 'Downloads',
                field: 'stats.tooltip.text',
                hidden: getCookie('Downloads')
            }, {
                label: 'Size',
                field: 'stats.episodes.size',
                hidden: getCookie('Size')
            }, {
                label: 'Active',
                field: this.fealdFnActive,
                hidden: getCookie('Active')
            }, {
                label: 'Status',
                field: 'status',
                hidden: getCookie('Status')
            }, {
                label: 'Xem',
                field: this.fealdFnXem,
                hidden: getCookie('Xem')
            }]
        };
    },
    computed: {
        ...mapState({
            config: state => state.config,
            indexerConfig: state => state.indexers.indexers,
            sortArticle: state => state.layout.sortArticle
        }),
        ...mapGetters({
            fuzzyParseDateTime: 'fuzzyParseDateTime'
        })
        // ,
        // sortedShows() {
        //     const { show, sortArticle } = this;
        //     const removeArticle = str => sortArticle ? str.replace(/^((?:A(?!\s+to)n?)|The)\s/i, '') : str;
        //     return shows.concat().sort((a, b) => removeArticle(a.title).toLowerCase().localeCompare(removeArticle(b.title).toLowerCase()));
        // }
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
                return fuzzyParseDateTime(row.prevAirDate);
            }
            return '';
        },
        parseNextDateFn(row) {
            const { fuzzyParseDateTime } = this;
            if (row.nextAirDate) {
                console.log(`Calculating time for show ${row.title} next date: ${row.nextAirDate}`);
                return fuzzyParseDateTime(row.nextAirDate);
            }
            return '';
        },
        sortDateNext(x, y, col, rowX, rowY) {
            // rowX - row object for row1
            // rowY - row object for row2
            return (!rowX.nextAirDate && rowX.nextAirDate < rowY.nextAirDate ? -1 : (rowX.nextAirDate > rowY.nextAirDate ? 1 : 0));
        },
        sortDatePrev(x, y, col, rowX, rowY) {
            // rowX - row object for row1
            // rowY - row object for row2
            return (rowX.prevAirDate < rowY.prevAirDate ? -1 : (rowX.prevAirDate > rowY.prevAirDate ? 1 : 0));
        },
        fealdFnXem(row) {
            if (row.xemNumbering && row.xemNumbering.length !== 0) {
                return 'yes';
            }
            return 'no';
        },
        fealdFnActive(row) {
            if (row.config && row.config.paused && row.status === 'Continuing') {
                return 'yes';
            }
            return 'no';
        }
    }
};
</script>

<style>
</style>
