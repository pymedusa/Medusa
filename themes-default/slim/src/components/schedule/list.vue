<template>
    <div class="horizontal-scroll vgt-table-styling">
        <vue-good-table
            v-if="filteredSchedule.length > 0"
            :columns="columns"
            :rows="filteredSchedule"
            :class="{fanartOpacity: layout.fanartBackgroundOpacity}"
            :column-filter-options="{
                enabled: true
            }"
            :sort-options="{
                enabled: true,
                initialSortBy: getSortBy('localAirTime', 'asc')
            }"
            styleClass="vgt-table condensed schedule"
            :row-style-class="rowStyleClassFn"
            @on-sort-change="saveSorting"
        >
            <template slot="table-row" slot-scope="props">
                <span v-if="props.column.label == 'Airdate'" class="align-center">
                    {{props.row.localAirTime ? fuzzyParseDateTime(props.row.localAirTime) : ''}}
                </span>

                <span v-else-if="props.column.label == 'Show'" class="tv-show">
                    <app-link :href="`home/displayShow?showslug=${props.row.showSlug}`">{{ props.row.showName }}</app-link>
                </span>

                <span v-else-if="props.column.label === 'Runtime'" class="align-center">
                    {{props.row.runtime}}min
                </span>

                <span v-else-if="props.column.label === 'Quality'" class="align-center">
                    <quality-pill :quality="props.row.quality" show-title />
                </span>

                <span v-else-if="props.column.label === 'Indexers'" class="align-center indexer-image">
                    <app-link v-if="props.row.externals.imdb_id" :href="`https://www.imdb.com/title/${props.row.externals.imdb_id}`"
                              :title="`https://www.imdb.com/title/${props.row.externals.imdb_id}`">
                        <img alt="[imdb]" height="16" width="16" src="images/imdb16.png" style="margin-top: -1px; vertical-align:middle;">
                    </app-link>

                    <app-link v-if="props.row.externals.tvdb_id" :href="`https://www.thetvdb.com/dereferrer/series/${props.row.externals.tvdb_id}`"
                              :title="`https://www.thetvdb.com/dereferrer/series/${props.row.externals.tvdb_id}`">
                        <img alt="[tvdb]" height="16" width="16" src="images/thetvdb16.png" style="margin-top: -1px; vertical-align:middle;">
                    </app-link>

                    <app-link v-if="props.row.externals.trakt_id" :href="`https://trakt.tv/shows/${props.row.externals.trakt_id}`"
                              :title="`https://trakt.tv/shows/${props.row.externals.trakt_id}`">
                        <img alt="[trakt]" height="16" width="16" src="images/trakt.png">
                    </app-link>

                    <app-link v-if="props.row.externals.tmdb_id" :href="`https://www.themoviedb.org/tv/${props.row.externals.tmdb_id}`"
                              :title="`https://www.themoviedb.org/tv/${props.row.externals.tmdb_id}`">
                        <img alt="[tmdb]" height="16" width="16" src="images/tmdb16.png" style="margin-top: -1px; vertical-align:middle;">
                    </app-link>

                    <app-link v-if="props.row.externals.tvmaze_id" :href="`https://www.tvmaze.com/shows/${props.row.externals.tvmaze_id}`"
                              :title="`https://www.tvmaze.com/shows/${props.row.externals.tvmaze_id}`">
                        <img alt="[tvmaze]" height="16" width="16" src="images/tvmaze16.png" style="margin-top: -1px; vertical-align:middle;">
                    </app-link>
                </span>

                <span v-else-if="props.column.label === 'Search'" class="align-center">
                    <search searchType="backlog" :showSlug="props.row.showSlug" :episode="{
                        episode: props.row.episode, season: props.row.season, slug: props.row.episodeSlug
                    }" />
                    <search searchType="manual" :showSlug="props.row.showSlug" :episode="{
                        episode: props.row.episode, season: props.row.season, slug: props.row.episodeSlug
                    }" />
                </span>

                <span v-else>
                    {{props.formattedRow[props.column.field]}}
                </span>
            </template>
        </vue-good-table>

    </div> <!-- .horizontal-scroll -->
</template>
<script>
import { mapGetters, mapState } from 'vuex';
import { AppLink, QualityPill, Search } from '../helpers';
import { VueGoodTable } from 'vue-good-table';
import { manageCookieMixin } from '../../mixins/manage-cookie';

export default {
    name: 'list',
    components: {
        AppLink,
        QualityPill,
        Search,
        VueGoodTable
    },
    mixins: [
        manageCookieMixin('schedule')
    ],
    data() {
        const { getCookie } = this;

        return {
            columns: [{
                label: 'Airdate',
                field: 'localAirTime',
                dateInputFormat: 'yyyy-MM-dd\'T\'HH:mm:ssXXX', // E.g. 07-09-2017 19:16:25
                dateOutputFormat: 'yyyy-MM-dd HH:mm:ss',
                type: 'date',
                hidden: getCookie('Airdate')
            }, {
                label: 'Show',
                field: 'showName',
                hidden: getCookie('Show')
            }, {
                label: 'Next Ep',
                field: 'episodeSlug',
                hidden: getCookie('Next Ep')
            }, {
                label: 'Next Ep Name',
                field: 'epName',
                hidden: getCookie('Next Ep Name')
            }, {
                label: 'Network',
                field: 'network',
                tdClass: 'span-center',
                hidden: getCookie('Network')
            }, {
                label: 'Runtime',
                field: 'runtime',
                hidden: getCookie('Runtime')
            }, {
                label: 'Quality',
                field: 'quality',
                hidden: getCookie('Quality')
            }, {
                label: 'Indexers',
                field: 'indexers',
                sortable: false,
                hidden: getCookie('Indexers')
            }, {
                label: 'Search',
                field: 'search',
                sortable: false,
                hidden: getCookie('Search')
            }]
        };
    },
    computed: {
        ...mapState({
            layout: state => state.config.layout,
            consts: state => state.config.consts,
            displayPaused: state => state.config.layout.comingEps.displayPaused
        }),
        ...mapGetters([
            'getScheduleFlattened',
            'fuzzyParseDateTime'
        ]),
        filteredSchedule() {
            const { displayPaused, getScheduleFlattened } = this;
            return getScheduleFlattened.filter(item => !item.paused || displayPaused);
        }
    },
    methods: {
        rowStyleClassFn(row) {
            return row.class;
        }
    }
};
</script>

<style scoped>
</style>
