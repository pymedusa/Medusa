<template>

    <v-client-table v-if="episodes" :data="episodes" v-bind="{columns, options}" :ref="`tableSeason-${season}`" @sorted="sorted">
        <!-- <episode-row v-for="episode in episodesInverse(row)" :key="episode.episode" v-bind="{episode, show}"></episode-row> -->
        <div slot="content.hasNfo" slot-scope="{row}">
            <img :src="'images/' + (row.content.hasNfo ? 'nfo.gif' : 'nfo-no.gif')" :alt="(row.content.hasNfo ? 'Y' : 'N')" width="23" height="11" />
        </div>
        <div slot="content.hasTbn" slot-scope="{row}">
            <img :src="'images/' + (row.content.hasTbn ? 'tbn.gif' : 'tbn-no.gif')" :alt="(row.content.hasTbn ? 'Y' : 'N')" width="23" height="11" />
        </div>
        <div slot="episode" slot-scope="{row}">
            <span :title="row.location !== '' ? row.location : ''" :class="{addQTip: row.location !== ''}">{{row.episode}}</span>
        </div>
        <div slot="download" slot-scope="{row}">
            <app-link v-if="config.downloadUrl && row.file.location && ['Downloaded', 'Archived'].includes(row.status)" :href="config.downloadUrl + row.file.location">Download</app-link>
        </div>
    </v-client-table>
</template>
<script>

import { mapState } from 'vuex';
import { humanFileSize } from '../utils';
import EpisodeRow from './episode-row.vue';

export default {
    name: 'episode-table',
    props: {
        show: {
            type: Object
        },
        season: {
            type: Number
        },
        episodes: {
            type: Array
        }
    },
    data() {
        // episodeColumns = [
        //     'content.hasNfo', 'content.hasTbn', 'episode', 'absolute','scene', 'sceneAbsolute', 'title', 'fileName',
        //     'size', 'airDate', 'download', 'subtitles', 'status', 'search'
        // ];
        return {
            columns: [
                'content.hasNfo', 'content.hasTbn', 'episode', 'absoluteNumber', 'title', 'file.location',
                'file.size', 'airDate', 'download', 'subtitles', 'status', 'search'
            ],
            options: {
                headings: {
                    'content.hasNfo': 'nfo',
                    'content.hasTbn': 'tbn',
                    episode: 'Episode'
                },
                perPage: 1000,
                orderBy: {
                    column: 'episode',
                    ascending: false
                },
                dateColumns: ['airDate'],
                columnsDropdown: true,
                unqiueKey: 'episode',
                filterable: false,
                pagination:{
                    dropdown: false
                }
            }
        }
        
    },
    computed: {
        ...mapState({
            configLoaded: state => state.config.fanartBackground !== null,
            config: state => state.config            
        }),
    },
    methods: {
        humanFileSize,
        /**
         * Check if the season/episode combination exists in the scene numbering.
         */
        getSceneNumbering(episode) {
            const { show } = this;
            const { xemNumbering } = show;

            if (xemNumbering.length !== 0) {
                const mapped = xemNumbering.filter(x => {
                    return x.source.season === episode.season && x.source.episode === episode.episode;
                });
                if (mapped.length !== 0) {
                    return mapped[0].destination;
                }
            }
            return { season: 0, episode: 0 };
        },
        getSceneAbsoluteNumbering(episode) {
            const { show } = this;
            const { sceneAbsoluteNumbering, xemAbsoluteNumbering } = show;  
            const xemAbsolute = xemAbsoluteNumbering[episode.absoluteNumber];

            if (Object.keys(sceneAbsoluteNumbering).length > 0) {
                return sceneAbsoluteNumbering[episode.absoluteNumber];
            } else if (xemAbsolute) {
                return xemAbsolute;
            }
            return 0;
        },
        retryDownload(episode) {
            const { config } = this;
            return (config.failedDownloads.enabled && ['Snatched', 'Snatched (Proper)', 'Snatched (Best)', 'Downloaded'].includes(episode.status));
        },
        showSubtitleButton(episode) {
            const { config, show } = this;
            return (episode.season !== 0 && config.subtitles.enabled && show.config.subtitlesEnabled && !['Snatched', 'Snatched (Proper)', 'Snatched (Best)', 'Downloaded'].includes(episode.status));
        },
        totalSeasonEpisodeSize(season) {
            return season.episodes.filter(x => x.file && x.file.size > 0).reduce((a, b) => a + b.file.size, 0);
        },
        getSeasonExceptions(season) {
            const { show } = this;
            const { allSceneExceptions } = show;
            let bindData = { class: 'display: none' };

            // Map the indexer season to a xem mapped season.
            // check if the season exception also exists in the xem numbering table

            let xemSeasons = [];
            let foundInXem = false;
            if (show.xemNumbering.length > 0) {
                const xemResult = show.xemNumbering.filter(x => x.source.season === season);
                // Create an array with unique seasons
                xemSeasons = [...new Set(xemResult.map(item => item.destination.season))];
                foundInXem = Boolean(xemSeasons.length);
            }

            // Check if there is a season exception for this season
            if (allSceneExceptions[season]) {
                // if there is not a match on the xem table, display it as a medusa scene exception
                bindData = {
                    id: `xem-exception-season-${foundInXem ? xemSeasons[0] : season}`,
                    alt: foundInXem ? '[xem]' : '[medusa]',
                    src: foundInXem ? 'images/xem.png' : 'images/ico/favicon-16.png',
                    title: xemSeasons.reduce(function (a, b) {
                        return a = a.concat(allSceneExceptions[b]);
                    }, []).join(', '),
                }
            }

            return bindData;
        },
        sorted(event) {
            const { season } = this;
            this.$emit('episodeTableSorted', {
                ascending: event.ascending,
                column: event.column,
                ref: `tableSeason-${season}`
            });
        }
    }
};
</script>
<style>
.table {
    width: 100%;
    max-width: 100%;
    margin-bottom: 20px;
}
.table-striped>tbody>tr:nth-of-type(odd) {
    background-color: transparent;
}
.VueTables__child-row-toggler {
    width: 16px;
    height: 16px;
    line-height: 16px;
    display: block;
    margin: auto;
    text-align: center;
}
 
.VueTables__child-row-toggler--closed::before {
    content: "+";
}
 
.VueTables__child-row-toggler--open::before {
    content: "-";
}
.VueTables__table > .float-right {
    float: right;
}
.VueTables.episodes {
    display: inline-block;
}
.table-bordered, .table-bordered>tbody>tr>td, 
.table-bordered>tbody>tr>th, .table-bordered>tfoot>tr>td, 
.table-bordered>tfoot>tr>th, 
.table-bordered>thead>tr>td, .table-bordered>thead>tr>th {
    border: none;
}
.table>tbody>tr>td, .table>tbody>tr>th, .table>tfoot>tr>td, 
.table>tfoot>tr>th, .table>thead>tr>td, .table>thead>tr>th {
    border-top: none;
}
table.VueTables__table.table {
    background-color: inherit;
}
div.form-group.form-inline.float-right.VueTables__limit {
    display: none;
}

</style>
