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
import { manageCookieMixin } from '../../utils/core';

export default {
    name: 'simple',
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
                sortable: false,
                hidden: getCookie('Next Ep')
            }, {
                label: 'Prev Ep',
                field: row => this.parsePrevDateFn(row),
                sortable: false,
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
                field: 'id',
                hidden: getCookie('Indexer')
            }, {
                label: 'Quality',
                field: 'quality',
                hidden: getCookie('Quality')
            }, {
                label: 'Downloads',
                field: 'stats.tooltip.text',
                hidden: getCookie('Downloads')
            }, {
                label: 'Size',
                field: 'size',
                hidden: getCookie('Size')
            }, {
                label: 'Active',
                field: 'config.paused',
                hidden: getCookie('Active')
            }, {
                label: 'Status',
                field: 'status',
                hidden: getCookie('Status')
            }, {
                label: 'Xem',
                field: 'status',
                hidden: getCookie('Xem')
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
</style>
