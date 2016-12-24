<%!
    from medusa import app
    import calendar
    from medusa import sbdatetime
    from medusa import network_timezones
    from medusa.helper.common import pretty_file_size
    import re
%>
<%namespace file="/inc_defs.mako" import="renderQualityPill"/>
<div class="loading-spinner"></div>
% for cur_show_list in showlists:
    <% cur_list_type = cur_show_list[0] %>
    <% my_show_list = list(cur_show_list[1]) %>
    % if cur_list_type == "Anime":
        <h1 class="header">Anime List</h1>
        <div class="loading-spinner"></div>
    % endif
<div id="${('container', 'container-anime')[cur_list_type == 'Anime']}" class="show-grid clearfix">
    <div class="posterview">
    % for cur_loading_show in app.showQueueScheduler.action.loadingShowList:
        % if cur_loading_show.show is None:
            <div class="show-container" data-name="0" data-date="010101" data-network="0" data-progress="101">
                <img alt="" title="${cur_loading_show.show_name}" class="show-image" style="border-bottom: 1px solid rgb(17, 17, 17);" src="images/poster.png" />
                <div class="show-details">
                    <div class="show-add">Loading... (${cur_loading_show.show_name})</div>
                </div>
            </div>
        % endif
    % endfor
    <% my_show_list.sort(lambda x, y: cmp(x.name, y.name)) %>
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
        if cur_show.indexerid in show_stat:
            cur_airs_next = show_stat[cur_show.indexerid]['ep_airs_next']
            cur_snatched = show_stat[cur_show.indexerid]['ep_snatched']
            if not cur_snatched:
                cur_snatched = 0
            cur_downloaded = show_stat[cur_show.indexerid]['ep_downloaded']
            if not cur_downloaded:
                cur_downloaded = 0
            cur_total = show_stat[cur_show.indexerid]['ep_total']
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
        progressbar_percent = nom * 100 / den
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
        <div class="show-container" id="show${cur_show.indexerid}" data-name="${cur_show.name}" data-date="${data_date}" data-network="${cur_show.network}" data-progress="${progressbar_percent}" data-indexer="${cur_show.indexer}">
            <div class="aligner">
                <div class="background-image">
                    <img src="images/poster-back-dark.png"/>
                </div>

                <div class="poster-overlay">
                    <a href="home/displayShow?show=${cur_show.indexerid}"><img alt="" class="show-image" src="showPoster/?show=${cur_show.indexerid}&amp;which=poster_thumb" /></a>
                </div>
            </div>

            <div class="progressbar hidden-print" style="position:relative;" data-show-id="${cur_show.indexerid}" data-progress-percentage="${progressbar_percent}"></div>
            <div class="show-title">
                ${cur_show.name}
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
                <table class="show-details" width="100%" cellspacing="1" border="0" cellpadding="0">
                    <tr>
                        <td class="show-table">
                            <span class="show-dlstats" title="${download_stat_tip}">${download_stat}</span>
                        </td>
                        <td class="show-table">
                            % if cur_show.network:
                                <span title="${cur_show.network}"><img class="show-network-image" src="showPoster/?show=${cur_show.indexerid}&amp;which=network" alt="${cur_show.network}" title="${cur_show.network}" /></span>
                            % else:
                                <span title="No Network"><img class="show-network-image" src="images/network/nonetwork.png" alt="No Network" title="No Network" /></span>
                            % endif
                        </td>
                        <td class="show-table">
                            ${renderQualityPill(cur_show.quality, showTitle=True, overrideClass="show-quality")}
                        </td>
                    </tr>
                </table>
            </div>
        </div>
    % endfor
    </div>
</div>
% endfor
