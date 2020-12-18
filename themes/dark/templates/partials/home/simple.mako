<%!
    from medusa import app
    from medusa import sbdatetime
    from medusa import network_timezones
    from medusa.helpers import remove_article
    from medusa.indexers.api import indexerApi
    from medusa.helper.common import pretty_file_size
    from medusa.scene_numbering import get_xem_numbering_for_show
%>
% for cur_show_list in show_lists:
    <% cur_list_type = cur_show_list[0] %>
    <% my_show_list = list(cur_show_list[1]) %>
    % if app.ANIME_SPLIT_HOME and app.ANIME_SPLIT_HOME_IN_TABS:
    <div id=${("seriesTabContent", "animeTabContent")[cur_list_type == "Anime"]}>
    % elif len(show_lists) > 1:
    <h1 class="header">${cur_list_type}</h1>
    % endif
    <div class="horizontal-scroll">
        <table id="showListTable${cur_list_type}" class="tablesorter ${'fanartOpacity' if app.FANART_BACKGROUND else ''}" cellspacing="1" border="0" cellpadding="0">
            <thead>
                <tr>
                    <th class="min-cell-width nowrap">Next Ep</th>
                    <th class="min-cell-width nowrap">Prev Ep</th>
                    <th>Show</th>
                    <th class="min-cell-width nowrap">Network</th>
                    <th class="min-cell-width nowrap">Indexer</th>
                    <th class="min-cell-width nowrap">Quality</th>
                    <th class="min-cell-width nowrap"> Downloads</th>
                    <th style="width: 100px">Size</th>
                    <th class="min-cell-width nowrap">Active</th>
                    <th class="min-cell-width nowrap">Status</th>
                    <th class="min-cell-width nowrap">XEM</th>
                </tr>
            </thead>
            <tfoot class="hidden-print shadow">
                <tr>
                    <th rowspan="1" colspan="1" align="center"><app-link href="addShows/">Add ${('Show', 'Anime')[cur_list_type == 'Anime']}</app-link></th>
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
            % if app.show_queue_scheduler.action.loadingShowList:
                <tbody class="tablesorter-infoOnly">
                % for cur_loading_show in app.show_queue_scheduler.action.loadingShowList:
                    <% if cur_loading_show.show is not None and cur_loading_show.show in app.showList:
                        continue
                    %>
                    <tr>
                        <td align="center">(loading)</td>
                        <td></td>
                        <td>
                        % if cur_loading_show.show is None:
                        <span title="">Loading... (${cur_loading_show.show_name})</span>
                        % else:
                        <app-link href="home/displayShow?indexername=${cur_loading_show.series.indexer_name}&seriesid=${cur_loading_show.series.series_id}">${cur_loading_show.show.name | h}</app-link>
                        % endif
                        </td>
                        <td></td>
                        <td></td>
                        <td></td>
                        <td></td>
                        <td></td>
                    </tr>
                % endfor
                </tbody>
            % endif
            <tbody>
            <%
                def titler(x):
                    return (remove_article(x), x)[not x or app.SORT_ARTICLE]

                my_show_list.sort(key=lambda x: titler(x.name).lower())
            %>
            % for cur_show in my_show_list:
            <%
                cur_airs_next = ''
                cur_airs_prev = ''
                cur_snatched = 0
                cur_downloaded = 0
                cur_total = 0
                show_size = 0
                download_stat_tip = ''
                if (cur_show.indexer, cur_show.series_id) in show_stat:
                    series = (cur_show.indexer, cur_show.series_id)
                    cur_airs_next = show_stat[series]['ep_airs_next']
                    cur_airs_prev = show_stat[series]['ep_airs_prev']
                    cur_snatched = show_stat[series]['ep_snatched']
                    if not cur_snatched:
                        cur_snatched = 0
                    cur_downloaded = show_stat[series]['ep_downloaded']
                    if not cur_downloaded:
                        cur_downloaded = 0
                    cur_total = show_stat[series]['ep_total']
                    if not cur_total:
                        cur_total = 0
                    show_size = show_stat[series]['show_size']
                download_stat = str(cur_downloaded)
                download_stat_tip = "Downloaded: " + str(cur_downloaded)
                if cur_snatched:
                    download_stat = download_stat + "+" + str(cur_snatched)
                    download_stat_tip = download_stat_tip + "&#013;" + "Snatched: " + str(cur_snatched)
                download_stat = download_stat + " / " + str(cur_total)
                download_stat_tip = download_stat_tip + "&#013;" + "Total: " + str(cur_total)
                nom = cur_downloaded
                if cur_total:
                    den = cur_total
                else:
                    den = 1
                    download_stat_tip = "Unaired"
                progressbar_percent = nom * 100 // den
            %>
                <tr>
                % if cur_airs_next:
                    <% airDate = sbdatetime.sbdatetime.convert_to_setting(network_timezones.parse_date_time(cur_airs_next, cur_show.airs, cur_show.network)) %>
                    % try:
                        <td align="center" class="nowrap triggerhighlight">
                            <time datetime="${airDate.isoformat('T')}" class="date">${sbdatetime.sbdatetime.sbfdate(airDate)}</time>
                        </td>
                    % except ValueError:
                        <td align="center" class="nowrap triggerhighlight"></td>
                    % endtry
                % else:
                    <td align="center" class="nowrap triggerhighlight"></td>
                % endif
                % if cur_airs_prev:
                    <% airDate = sbdatetime.sbdatetime.convert_to_setting(network_timezones.parse_date_time(cur_airs_prev, cur_show.airs, cur_show.network)) %>
                    % try:
                        <td align="center" class="nowrap triggerhighlight">
                            <time datetime="${airDate.isoformat('T')}" class="date">${sbdatetime.sbdatetime.sbfdate(airDate)}</time>
                        </td>
                    % except ValueError:
                        <td align="center" class="nowrap triggerhighlight"></td>
                    % endtry
                % else:
                    <td align="center" class="nowrap triggerhighlight"></td>
                % endif
                    <td class="tvShow triggerhighlight"><app-link href="home/displayShow?indexername=${cur_show.indexer_name}&seriesid=${cur_show.series_id}">${cur_show.name | h}</app-link></td>
                    <td class="triggerhighlight">
                        <span title="${cur_show.network}">${cur_show.network}</span>
                    </td>
                    <td align="center" class="triggerhighlight">
                        % if cur_show.imdb_id:
                            <app-link href="http://www.imdb.com/title/${cur_show.imdb_id}" title="http://www.imdb.com/title/${cur_show.imdb_id}">
                                <img alt="[imdb]" height="16" width="16" src="images/imdb.png" />
                            </app-link>
                        % endif
                        % if cur_show.externals.get('trakt_id'):
                            <app-link href="https://trakt.tv/shows/${cur_show.externals.get('trakt_id')}" title="https://trakt.tv/shows/${cur_show.externals.get('trakt_id')}">
                                <img alt="[trakt]" height="16" width="16" src="images/trakt.png" />
                            </app-link>
                        % endif
                        <app-link data-indexer-name="${indexerApi(cur_show.indexer).name}" href="${indexerApi(cur_show.indexer).config['show_url']}${cur_show.series_id}" title="${indexerApi(cur_show.indexer).config['show_url']}${cur_show.series_id}">
                            <img alt="${indexerApi(cur_show.indexer).name}" height="16" width="16" src="images/${indexerApi(cur_show.indexer).config['icon']}" />
                        </app-link>
                    </td>
                    <td class="triggerhighlight" align="center"><quality-pill :quality="${cur_show.quality}" show-title></quality-pill></td>
                    <td class="triggerhighlight" align="center">
                        ## This first span is used for sorting and is never displayed to user
                        <span style="display: none;">${download_stat}</span>
                        <div class="progressbar hidden-print" style="position:relative;" data-indexer-name="${cur_show.indexer_name}" data-show-id="${cur_show.series_id}" data-progress-percentage="${progressbar_percent}" data-progress-text="${download_stat}" data-progress-tip="${download_stat_tip}"></div>
                        <span class="visible-print-inline">${download_stat}</span>
                    </td>
                    <td class="triggerhighlight" align="center" data-show-size="${show_size}">${pretty_file_size(show_size)}</td>
                    <td class="triggerhighlight" align="center">
                        <% paused = int(cur_show.paused) == 0 and cur_show.status == 'Continuing' %>
                        <img src="images/${('no16.png', 'yes16.png')[bool(paused)]}" alt="${('No', 'Yes')[bool(paused)]}" width="16" height="16" />
                    </td>
                    <td align="center" class="triggerhighlight">
                    ${cur_show.status}
                    </td>
                    <td align="center" class="triggerhighlight">
                        <% have_xem = bool(get_xem_numbering_for_show(cur_show, refresh_data=False)) %>
                        <img src="images/${('no16.png', 'yes16.png')[have_xem]}" alt="${('No', 'Yes')[have_xem]}" width="16" height="16" />
                    </td>
                </tr>
            % endfor
            </tbody>
        </table>
    </div> <!-- .horizontal-scroll -->
    % if app.ANIME_SPLIT_HOME and app.ANIME_SPLIT_HOME_IN_TABS:
    </div> <!-- #...TabContent -->
    % endif
% endfor
