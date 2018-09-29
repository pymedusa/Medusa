<%!
    from medusa import app
    from medusa import sbdatetime
    from medusa import network_timezones
    from medusa.helpers import remove_article
    from medusa.indexers.indexer_api import indexerApi
    from medusa.helper.common import pretty_file_size
    from medusa.scene_numbering import get_xem_numbering_for_show
%>
<template v-for="(shows, listTitle) in showLists">
    ## % if app.ANIME_SPLIT_HOME and app.ANIME_SPLIT_HOME_IN_TABS:
    ## <div id=${("seriesTabContent", "animeTabContent")[cur_list_type == "Anime"]}>
    ## % elif len(show_lists) > 1:
    ## <h1 class="header">${cur_list_type}</h1>
    ## % endif
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
        ##     ## <%
        ##     ##     def titler(x):
        ##     ##        return (remove_article(x), x)[not x or app.SORT_ARTICLE]

        ##     ##     my_show_list.sort(key=lambda x: titler(x.name).lower())
        ##     ## %>
        ##     ## % for cur_show in my_show_list:
        ##     ## <%
        ##     ##     cur_airs_next = ''
        ##     ##     cur_airs_prev = ''
        ##     ##     cur_snatched = 0
        ##     ##     cur_downloaded = 0
        ##     ##     cur_total = 0
        ##     ##     show_size = 0
        ##     ##     download_stat_tip = ''
        ##     ##     if (cur_show.indexer, cur_show.series_id) in show_stat:
        ##     ##         series = (cur_show.indexer, cur_show.series_id)
        ##     ##         cur_airs_next = show_stat[series]['ep_airs_next']
        ##     ##         cur_airs_prev = show_stat[series]['ep_airs_prev']
        ##     ##         cur_snatched = show_stat[series]['ep_snatched']
        ##     ##         if not cur_snatched:
        ##     ##             cur_snatched = 0
        ##     ##         cur_downloaded = show_stat[series]['ep_downloaded']
        ##     ##         if not cur_downloaded:
        ##     ##             cur_downloaded = 0
        ##     ##         cur_total = show_stat[series]['ep_total']
        ##     ##         if not cur_total:
        ##     ##             cur_total = 0
        ##     ##         show_size = show_stat[series]['show_size']
        ##     ##     download_stat = str(cur_downloaded)
        ##     ##     download_stat_tip = "Downloaded: " + str(cur_downloaded)
        ##     ##     if cur_snatched:
        ##     ##         download_stat = download_stat + "+" + str(cur_snatched)
        ##     ##         download_stat_tip = download_stat_tip + "&#013;" + "Snatched: " + str(cur_snatched)
        ##     ##     download_stat = download_stat + " / " + str(cur_total)
        ##     ##     download_stat_tip = download_stat_tip + "&#013;" + "Total: " + str(cur_total)
        ##     ##     nom = cur_downloaded
        ##     ##     if cur_total:
        ##     ##         den = cur_total
        ##     ##     else:
        ##     ##         den = 1
        ##     ##         download_stat_tip = "Unaired"
        ##     ##     progressbar_percent = nom * 100 / den
        ##     ## %>
                <tr v-for="show in shows">
                    <template v-if="show.stats.airs.next">
                        ## <%
                        ##     try:
                        ##         airDate = sbdatetime.sbdatetime.convert_to_setting(network_timezones.parse_date_time(cur_airs_next, cur_show.airs, cur_show.network))
                        ##         datetime = airDate.isoformat('T')
                        ##         text = sbdatetime.sbdatetime.sbfdate(airDate)
                        ##     except ValueError:
                        ##         datetime = ""
                        ##         text = ""
                        ## %>
                        <td align="center" class="nowrap">
                        ##     <time datetime="${datetime}" class="date">${text}</time>
                        </td>
                    </template>
                    <td v-else align="center" class="nowrap"></td>
                    <template v-if="show.stats.airs.prev">
                    ##     <%
                    ##         try:
                    ##             airDate = sbdatetime.sbdatetime.convert_to_setting(network_timezones.parse_date_time(cur_airs_prev, cur_show.airs, cur_show.network))
                    ##             datetime = airDate.isoformat('T')
                    ##             text = sbdatetime.sbdatetime.sbfdate(airDate)
                    ##         except ValueError:
                    ##             datetime = ""
                    ##             text = ""
                    ##     %>
                        <td align="center" class="nowrap">
                    ##         <time datetime="${datetime}" class="date">${text}</time>
                        </td>
                    </template>
                    <td v-else align="center" class="nowrap"></td>
                    <td>
                        <span style="display: none;">{{ show.title }}</span>
                        <div class="imgbanner banner">
                            <app-link :href="'home/displayShow?indexername=' + show.indexer + '&seriesid=' + show.id[show.indexer]">
                                <asset default="images/banner.png" :show-slug="show.indexer + show.id[show.indexer]" type="banner" class="banner" :alt="show.title" :title="show.title"></asset>
                            </app-link>
                        </div>
                    </td>
                    <td align="center">
                        <template v-if="show.network">
                            <span :title="show.network" class="hidden-print">
                                <asset default="images/network/nonetwork.png" :show-slug="show.indexer + show.id[show.indexer]" type="network" cls="show-network-image" :link="false" width="54" height="27" :alt="show.network" :title="show.network"></asset>
                            </span>
                            <span class="visible-print-inline">{{ show.network }}</span>
                        </template>
                        <template v-else>
                            <span title="No Network" class="hidden-print"><img id="network" width="54" height="27" src="images/network/nonetwork.png" alt="No Network" title="No Network" /></span>
                            <span class="visible-print-inline">No Network</span>
                        </template>
                    </td>
                    <td align="center">
                        <app-link v-if="show.id.imdb" :href="'http://www.imdb.com/title/' + show.id.imdb" :title="'http://www.imdb.com/title/' + show.id.imdb">
                            <img alt="[imdb]" height="16" width="16" src="images/imdb.png" />
                        </app-link>
                        <app-link v-if="show.id.trakt" :href="'https://trakt.tv/shows/' + show.id.trakt" :title="'https://trakt.tv/shows/' + show.id.trakt">
                            <img alt="[trakt]" height="16" width="16" src="images/trakt.png" />
                        </app-link>
                    ##     <app-link data-indexer-name="${indexerApi(cur_show.indexer).name}" href="${indexerApi(cur_show.indexer).config['show_url']}${cur_show.series_id}" title="${indexerApi(cur_show.indexer).config['show_url']}${cur_show.series_id}">
                    ##         <img alt="${indexerApi(cur_show.indexer).name}" height="16" width="16" src="images/${indexerApi(cur_show.indexer).config['icon']}" />
                    ##     </app-link>
                    </td>
                    <td align="center"><quality-pill :allowed="show.config.qualities.allowed" :preferred="show.config.qualities.preferred" show-title></quality-pill></td>
                    <td align="center">
                        <!-- This first span is used for sorting and is never displayed to user -->
                        <span style="display: none;">{{ show.stats.tooltip.text }}</span>
                        <progress-bar v-bind="{ ...show.stats.tooltip }"></progress-bar>
                        ## <div class="progressbar hidden-print" style="position:relative;" :data-show-id="show.id[show.indexer]" :data-progress-percentage="show.stats.tooltip.percentage" :data-progress-text="show.stats.tooltip.text" :data-progress-tip="show.stats.tooltip.tip"></div>
                        <span class="visible-print-inline">{{ show.stats.tooltip.text }}</span>
                    </td>
                    <td align="center" :data-show-size="show.stats.episodes.size">{{ prettyBytes(show.stats.episodes.size) }}</td>
                    <td align="center">
                        <img :src="'images/' + (show.config.paused && show.status === 'Continuing' ? 'Yes' : 'No') + '16.png'" :alt="show.config.paused && show.status === 'Continuing' ? 'Yes' : 'No'" width="16" height="16" />
                    </td>
                    <td align="center">{{ show.status }}</td>
                    <td align="center">
                    ##     <% have_xem = bool(get_xem_numbering_for_show(cur_show, refresh_data=False)) %>
                    ##     <img src="images/${('no16.png', 'yes16.png')[have_xem]}" alt="${('No', 'Yes')[have_xem]}" width="16" height="16" />
                    </td>
                </tr>
            </tbody>
        </table>
    </div> <!-- .horizontal-scroll -->
    ## % if app.ANIME_SPLIT_HOME and app.ANIME_SPLIT_HOME_IN_TABS:
    ## </div> <!-- #...TabContent -->
    ## % endif
</template>
