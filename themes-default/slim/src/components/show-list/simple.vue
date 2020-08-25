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
                            initialSortBy: getSortBy()
                        }"
                        :column-filter-options="{
                            enabled: true
                        }"
                        :class="{fanartOpacity: stateLayout.fanartBackground}"
                        @on-sort-change="saveSorting"
        >

            <template slot="table-actions-header">
                <!-- Only show the list title when not in tabs -->
                <div v-if="!stateLayout.splitHomeInTabs && (showsInLists && showsInLists.length > 1)" class="show-list-title listTitle">
                    <button type="button" class="nav-show-list move-show-list">
                        <span class="icon-bar" />
                        <span class="icon-bar" />
                        <span class="icon-bar" />
                    </button>
                    <h3 class="header">{{listTitle}}</h3>
                </div>
            </template>

            <template slot="table-row" slot-scope="props">
                <span v-if="props.column.label == 'Next Ep'" class="align-center">
                    {{props.row.nextAirDate ? fuzzyParseDateTime(props.row.nextAirDate) : ''}}
                </span>

                <span v-else-if="props.column.label === 'Prev Ep'" class="align-center">
                    {{props.row.prevAirDate ? fuzzyParseDateTime(props.row.prevAirDate) : ''}}
                </span>

                <span v-else-if="props.column.label === 'Show'" class="tvShow">
                    <app-link :href="`home/displayShow?indexername=${props.row.indexer}&seriesid=${props.row.id[props.row.indexer]}`">{{ props.row.title }}</app-link>
                </span>

                <span v-else-if="props.column.label === 'Network'" class="align-center">
                    <span class="align-center">{{ props.row.network }}</span>
                </span>

                <span v-else-if="props.column.label === 'Indexer'" class="align-center indexer-image">
                    <app-link v-if="props.row.id.imdb" :href="'http://www.imdb.com/title/' + props.row.id.imdb" :title="`http://www.imdb.com/title/${props.row.id.imdb}`">
                        <img alt="[imdb]" height="16" width="16" src="images/imdb.png">
                    </app-link>
                    <app-link v-if="props.row.id.trakt" :href="'https://trakt.tv/shows/' + props.row.id.trakt" :title="`https://trakt.tv/shows/${props.row.id.trakt}`">
                        <img alt="[trakt]" height="16" width="16" src="images/trakt.png">
                    </app-link>
                    <app-link v-if="showIndexerUrl && indexerConfig[props.row.indexer].icon" :href="showIndexerUrl(props.row)" :title="showIndexerUrl(props.row)">
                        <img :alt="indexerConfig[props.row.indexer].name" height="16" width="16" :src="'images/' + indexerConfig[props.row.indexer].icon" style="margin-top: -1px; vertical-align:middle;">
                    </app-link>
                </span>

                <span v-else-if="props.column.label === 'Quality'" class="align-center">
                    <quality-pill :allowed="props.row.config.qualities.allowed" :preferred="props.row.config.qualities.preferred" show-title />
                </span>

                <span v-else-if="props.column.label === 'Downloads'">
                    <progress-bar v-bind="props.row.stats.tooltip" />
                </span>

                <span v-else-if="props.column.label === 'Size'" class="align-center">
                    {{ prettyBytes(props.row.stats.episodes.size) }}
                </span>

                <span v-else-if="props.column.label === 'Active'" class="align-center">
                    <img :src="`images/${props.row.config && !props.row.config.paused && props.row.status === 'Continuing' ? 'yes' : 'no'}16.png`" :alt="props.row.config && !props.row.config.paused && props.row.status === 'Continuing' ? 'yes' : 'no'" width="16" height="16">
                </span>

                <span v-else-if="props.column.label === 'Xem'" class="align-center">
                    <img :src="`images/${props.row.xemNumbering && props.row.xemNumbering.length !== 0 ? 'yes' : 'no'}16.png`" :alt="props.row.xemNumbering && props.row.xemNumbering.length !== 0 ? 'yes' : 'no'" width="16" height="16">
                </span>

                <span v-else class="align-center">
                    {{props.formattedRow[props.column.field]}}
                </span>
            </template>
        </vue-good-table>

    </div> <!-- .horizontal-scroll -->
</template>
<script>
import { AppLink, ProgressBar, QualityPill } from '../helpers';
import { VueGoodTable } from 'vue-good-table';
import { manageCookieMixin } from '../../mixins/manage-cookie';
import { showlistTableMixin } from '../../mixins/show-list';

export default {
    name: 'simple',
    components: {
        AppLink,
        ProgressBar,
        QualityPill,
        VueGoodTable
    },
    mixins: [
        manageCookieMixin('home-simple'),
        showlistTableMixin
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
    }
};
</script>

<style>
</style>
