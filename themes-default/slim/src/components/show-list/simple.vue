<template>
    <div class="horizontal-scroll">
        <table :id="'showListTable' + listTitle.charAt(0).toUpperCase() + listTitle.substr(1)" :class="['tablesorter', { fanartOpacity: config.fanartBackground }]" cellspacing="1" border="0" cellpadding="0">
            <thead>
                <tr>
                    <th class="nowrap">Next Ep</th>
                    <th class="nowrap">Prev Ep</th>
                    <th>Show</th>
                    <th>Network</th>
                    <th>Indexer</th>
                    <th>Quality</th>
                    <th>Downloads</th>
                    <th>Size</th>
                    <th>Active</th>
                    <th>Status</th>
                    <th>XEM</th>
                </tr>
            </thead>
            <tfoot class="hidden-print">
                <tr>
                    <th rowspan="1" colspan="1" align="center"><app-link href="addShows/">Add {{ listTitle.charAt(0).toUpperCase() + listTitle.substr(1) }}</app-link></th>
                    <th>&nbsp;</th>
                    <th>&nbsp;</th>
                    <th>&nbsp;</th>
                    <th>&nbsp;</th>
                    <th>&nbsp;</th>
                    <th>&nbsp;</th>
                    <th>&nbsp;</th>
                    <th>&nbsp;</th>
                    <th>&nbsp;</th>
                    <th>&nbsp;</th>
                </tr>
            </tfoot>
            <tbody>
                <tr v-for="show in sortedShows" :key="show.title">
                    <template v-if="show.stats.airs.next">
                        <!-- <%
                            try:
                                airDate = sbdatetime.sbdatetime.convert_to_setting(network_timezones.parse_date_time(cur_airs_next, cur_show.airs, cur_show.network))
                                datetime = airDate.isoformat('T')
                                text = sbdatetime.sbdatetime.sbfdate(airDate)
                            except ValueError:
                                datetime = ""
                                text = ""
                        %> -->
                        <td align="center" class="nowrap">
                            <!-- <time datetime="${datetime}" class="date">${text}</time> -->
                        </td>
                    </template>
                    <td v-else align="center" class="nowrap"></td>
                    <template v-if="show.stats.airs.prev">
                        <!-- <%
                            try:
                                airDate = sbdatetime.sbdatetime.convert_to_setting(network_timezones.parse_date_time(cur_airs_prev, cur_show.airs, cur_show.network))
                                datetime = airDate.isoformat('T')
                                text = sbdatetime.sbdatetime.sbfdate(airDate)
                            except ValueError:
                                datetime = ""
                                text = ""
                        %> -->
                        <td align="center" class="nowrap">
                            <!-- <time datetime="${datetime}" class="date">${text}</time> -->
                        </td>
                    </template>
                    <td v-else align="center" class="nowrap"></td>
                    <td>
                        <span style="display: none;">{{ show.title }}</span>
                        <app-link :href="'home/displayShow?indexername=' + show.indexer + '&seriesid=' + show.id[show.indexer]">{{ show.title }}</app-link>
                    </td>
                    <td align="center">
                        <template>
                            <span :title="show.network" class="hidden-print">{{ show.network }}</span>
                            <span class="visible-print-inline">{{ show.network }}</span>
                        </template>
                    </td>
                    <td align="center">
                        <app-link v-if="show.id.imdb" :href="'http://www.imdb.com/title/' + show.id.imdb" :title="'http://www.imdb.com/title/' + show.id.imdb">
                            <img alt="[imdb]" height="16" width="16" src="images/imdb.png" />
                        </app-link>
                        <app-link v-if="show.id.trakt" :href="'https://trakt.tv/shows/' + show.id.trakt" :title="'https://trakt.tv/shows/' + show.id.trakt">
                            <img alt="[trakt]" height="16" width="16" src="images/trakt.png" />
                        </app-link>
                        <!-- <app-link data-indexer-name="${indexerApi(cur_show.indexer).name}" href="${indexerApi(cur_show.indexer).config['show_url']}${cur_show.series_id}" title="${indexerApi(cur_show.indexer).config['show_url']}${cur_show.series_id}">
                            <img alt="${indexerApi(cur_show.indexer).name}" height="16" width="16" src="images/${indexerApi(cur_show.indexer).config['icon']}" />
                        </app-link> -->
                    </td>
                    <td align="center"><quality-pill :allowed="show.config.qualities.allowed" :preferred="show.config.qualities.preferred" show-title></quality-pill></td>
                    <td align="center">
                        <!-- This first span is used for sorting and is never displayed to user -->
                        <span style="display: none;">{{ show.stats.tooltip.text }}</span>
                        <progress-bar v-bind="show.stats.tooltip"></progress-bar>
                        <span class="visible-print-inline">{{ show.stats.tooltip.text }}</span>
                    </td>
                    <td align="center" :data-show-size="show.stats.episodes.size">{{ prettyBytes(show.stats.episodes.size) }}</td>
                    <td align="center">
                        <img :src="'images/' + (show.config.paused && show.status === 'Continuing' ? 'Yes' : 'No') + '16.png'" :alt="show.config.paused && show.status === 'Continuing' ? 'Yes' : 'No'" width="16" height="16" />
                    </td>
                    <td align="center">{{ show.status }}</td>
                    <td align="center">
                        <!-- <% have_xem = bool(get_xem_numbering_for_show(cur_show, refresh_data=False)) %>
                        <img src="images/${('no16.png', 'yes16.png')[have_xem]}" alt="${('No', 'Yes')[have_xem]}" width="16" height="16" /> -->
                    </td>
                </tr>
            </tbody>
        </table>
    </div> <!-- .horizontal-scroll -->
</template>
<script>
import pretty from 'pretty-bytes';
import { Asset } from '../helpers';
import { AppLink } from '../helpers';
import { ProgressBar } from '../helpers';
import { QualityPill } from '../helpers';

export default {
    name: 'simple',
    components: {
        Asset,
        AppLink,
        ProgressBar,
        QualityPill
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
        },
        sortArticle: {
            type: Boolean
        }
    },
    computed: {
        sortedShows() {
            const removeArticle = str => this.sortArticle ? str.replace(/^((?:A(?!\s+to)n?)|The)\s/i, '') : str;
            return this.shows.sort((a, b) => removeArticle(a.title).toLowerCase().localeCompare(removeArticle(b.title).toLowerCase()));
        }
    },
    methods: {
        prettyBytes: bytes => pretty(bytes)
    }
};
</script>
