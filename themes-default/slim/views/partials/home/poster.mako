<%!
    import calendar
    import re

    from medusa import app
    from medusa import sbdatetime
    from medusa import network_timezones
    from medusa.helpers import remove_article
    from medusa.helper.common import pretty_file_size
    from medusa.scene_numbering import get_xem_numbering_for_show
%>
<div class="loading-spinner"></div>

<div id="poster-container">
% for cur_show_list in show_lists:
    <% cur_list_type = cur_show_list[0] %>
    <% my_show_list = list(cur_show_list[1]) %>
    % if app.ANIME_SPLIT_HOME and app.ANIME_SPLIT_HOME_IN_TABS:
    <div id=${("seriesTabContent", "animeTabContent")[cur_list_type == "Anime"]}>
    % endif
    <div id="${'container-' + cur_list_type.lower()}" class="show-grid clearfix" data-list="${cur_list_type}">
        % if not (app.ANIME_SPLIT_HOME and app.ANIME_SPLIT_HOME_IN_TABS):
            % if len(show_lists) > 1:
            <div class="showListTitle ${cur_list_type.lower()}">
                <button type="button" class="nav-show-list move-show-list" data-move-target="${'container-' + cur_list_type.lower()}">
                    <span class="icon-bar"></span>
                    <span class="icon-bar"></span>
                    <span class="icon-bar"></span>
                </button>
                <h2 class="header">${cur_list_type}</h2>
                <div class="loading-spinner"></div>
            </div>
            % endif
        % endif
        <div class="posterview">
        % for cur_loading_show in app.show_queue_scheduler.action.loadingShowList:
            % if cur_loading_show.show is None:
                <div class="show-container" data-name="0" data-date="010101" data-network="0" data-progress="101">
                    <img alt="" title="${cur_loading_show.show_name}" class="show-image" style="border-bottom: 1px solid rgb(17, 17, 17);" src="images/poster.png" />
                    <div class="show-details">
                        <div class="show-add">Loading... (${cur_loading_show.show_name})</div>
                    </div>
                </div>
            % endif
        % endfor
        <%
            def titler(x):
                return (remove_article(x), x)[not x or app.SORT_ARTICLE]

            my_show_list.sort(key=lambda x: titler(x.name).lower())
        %>
        % for cur_show in my_show_list:
        <%
            cur_airs_next = ''
            cur_snatched = 0
            cur_downloaded = 0
            cur_total = 0
            download_stat_tip = ''
            display_status = cur_show.status
            if None is not display_status:
                if re.search(r'(?i)(?:new|returning)\s*series', cur_show.status):
                    display_status = 'Continuing'
                elif re.search(r'(?i)(?:nded)', cur_show.status):
                    display_status = 'Ended'
            if (cur_show.indexer, cur_show.series_id) in show_stat:
                series = (cur_show.indexer, cur_show.series_id)
                cur_airs_next = show_stat[series]['ep_airs_next']
                cur_snatched = show_stat[series]['ep_snatched']
                if not cur_snatched:
                    cur_snatched = 0
                cur_downloaded = show_stat[series]['ep_downloaded']
                if not cur_downloaded:
                    cur_downloaded = 0
                cur_total = show_stat[series]['ep_total']
                if not cur_total:
                    cur_total = 0
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
            data_date = '6000000000.0'
            if cur_airs_next:
                data_date = calendar.timegm(sbdatetime.sbdatetime.convert_to_setting(network_timezones.parse_date_time(cur_airs_next, cur_show.airs, cur_show.network)).timetuple())
            elif None is not display_status:
                if 'nded' not in display_status and 1 == int(cur_show.paused):
                    data_date = '5000000500.0'
                elif 'ontinu' in display_status:
                    data_date = '5000000000.0'
                elif 'nded' in display_status:
                    data_date = '5000000100.0'
        %>
            <div class="show-container" id="show${cur_show.indexerid}" data-name="${cur_show.name | h}" data-date="${data_date}" data-network="${cur_show.network}" data-progress="${progressbar_percent}" data-indexer="${cur_show.indexer}">
                <div class="aligner">
                    <div class="background-image">
                        <img src="images/poster-back-dark.png"/>
                    </div>
                    <div class="poster-overlay">
                        <app-link href="home/displayShow?indexername=${cur_show.indexer_name}&seriesid=${cur_show.indexerid}">
                            <asset default-src="images/poster.png" show-slug="${cur_show.slug}" type="posterThumb" cls="show-image" :link="false"></asset>
                        </app-link>
                    </div>
                </div>
                <div class="show-poster-footer row">
                    <div class="col-md-12">
                        <div class="progressbar hidden-print" style="position:relative;" data-show-id="${cur_show.indexerid}" data-progress-percentage="${progressbar_percent}"></div>
                        <div class="show-title">
                            <div class="ellipsis">${cur_show.name | h}</div>
                            % if get_xem_numbering_for_show(cur_show, refresh_data=False):
                                <div class="xem">
                                    <img src="images/xem.png" width="16" height="16" />
                                </div>
                            % endif
                        </div>
                        <div class="show-date">
                % if cur_airs_next:
                    <% ldatetime = sbdatetime.sbdatetime.convert_to_setting(network_timezones.parse_date_time(cur_airs_next, cur_show.airs, cur_show.network)) %>
                    <%
                        try:
                            out = str(sbdatetime.sbdatetime.sbfdate(ldatetime))
                        except ValueError:
                            out = 'Invalid date'
                            pass
                    %>
                        ${out}
                % else:
                    <%
                    output_html = '?'
                    display_status = cur_show.status
                    if None is not display_status:
                        if 'nded' not in display_status and 1 == int(cur_show.paused):
                          output_html = 'Paused'
                        elif display_status:
                            output_html = display_status
                    %>
                    ${output_html}
                % endif
                        </div>
                        <div class="show-details">
                            <table class="show-details ${'fanartOpacity' if app.FANART_BACKGROUND else ''}" width="100%" cellspacing="1" border="0" cellpadding="0">
                                <tr>
                                    <td class="show-table">
                                        <span class="show-dlstats" title="${download_stat_tip}">${download_stat}</span>
                                    </td>
                                    <td class="show-table">
                                    % if cur_show.network:
                                        <span title="${cur_show.network}">
                                            <asset default-src="images/network/nonetwork.png" show-slug="${cur_show.slug}" type="network" cls="show-network-image" :link="false" alt="${cur_show.network}" title="${cur_show.network}"></asset>
                                        </span>
                                    % else:
                                        <span title="No Network"><img class="show-network-image" src="images/network/nonetwork.png" alt="No Network" title="No Network" /></span>
                                    % endif
                                    </td>
                                    <td class="show-table">
                                        <quality-pill :quality="${cur_show.quality}" show-title :override="{ class: 'show-quality' }"></quality-pill>
                                    </td>
                                </tr>
                            </table>
                        </div>
                    </div> <!-- col -->
                </div> <!-- show-poster-footer -->
            </div> <!-- show container -->
        % endfor
        </div>
    </div>
    % if app.ANIME_SPLIT_HOME and app.ANIME_SPLIT_HOME_IN_TABS:
    </div> <!-- #...TabContent -->
    % endif
% endfor
</div>
