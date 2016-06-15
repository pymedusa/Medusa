<%!
    import sickbeard
    import calendar
    from sickbeard import sbdatetime
    from sickbeard import network_timezones
    from sickrage.helper.common import pretty_file_size
    import re
%>
<%namespace file="/inc_defs.mako" import="renderQualityPill"/>
<div class="loading-spinner"></div>
% for curShowlist in showlists:
    <% curListType = curShowlist[0] %>
    <% myShowList = list(curShowlist[1]) %>
    % if curListType == "Anime":
        <h1 class="header">Anime List</h1>
        <div class="loading-spinner"></div>
    % endif
<div id="${('container', 'container-anime')[curListType == 'Anime']}" class="show-grid clearfix">
    <div class="posterview">
    % for curLoadingShow in sickbeard.showQueueScheduler.action.loadingShowList:
        % if curLoadingShow.show is None:
            <div class="show-container" data-name="0" data-date="010101" data-network="0" data-progress="101">
                <img alt="" title="${curLoadingShow.show_name}" class="show-image" style="border-bottom: 1px solid rgb(17, 17, 17);" src="/images/poster.png" />
                <div class="show-details">
                    <div class="show-add">Loading... (${curLoadingShow.show_name})</div>
                </div>
            </div>
        % endif
    % endfor
    <% myShowList.sort(lambda x, y: cmp(x.name, y.name)) %>
    % for curShow in myShowList:
    <%
        cur_airs_next = ''
        cur_snatched = 0
        cur_downloaded = 0
        cur_total = 0
        download_stat_tip = ''
        display_status = curShow.status
        if None is not display_status:
            if re.search(r'(?i)(?:new|returning)\s*series', curShow.status):
                display_status = 'Continuing'
            elif re.search(r'(?i)(?:nded)', curShow.status):
                display_status = 'Ended'
        if curShow.indexerid in show_stat:
            cur_airs_next = show_stat[curShow.indexerid]['ep_airs_next']
            cur_snatched = show_stat[curShow.indexerid]['ep_snatched']
            if not cur_snatched:
                cur_snatched = 0
            cur_downloaded = show_stat[curShow.indexerid]['ep_downloaded']
            if not cur_downloaded:
                cur_downloaded = 0
            cur_total = show_stat[curShow.indexerid]['ep_total']
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
            data_date = calendar.timegm(sbdatetime.sbdatetime.convert_to_setting(network_timezones.parse_date_time(cur_airs_next, curShow.airs, curShow.network)).timetuple())
        elif None is not display_status:
            if 'nded' not in display_status and 1 == int(curShow.paused):
                data_date = '5000000500.0'
            elif 'ontinu' in display_status:
                data_date = '5000000000.0'
            elif 'nded' in display_status:
                data_date = '5000000100.0'
    %>
        <div class="show-container" id="show${curShow.indexerid}" data-name="${curShow.name}" data-date="${data_date}" data-network="${curShow.network}" data-progress="${progressbar_percent}">
            <div class="show-image">
                <a href="/home/displayShow?show=${curShow.indexerid}"><img alt="" class="show-image" src="/showPoster/?show=${curShow.indexerid}&amp;which=poster_thumb" /></a>
            </div>
            <div class="progressbar hidden-print" style="position:relative;" data-show-id="${curShow.indexerid}" data-progress-percentage="${progressbar_percent}"></div>
            <div class="show-title">
                ${curShow.name}
            </div>
            <div class="show-date">
    % if cur_airs_next:
        <% ldatetime = sbdatetime.sbdatetime.convert_to_setting(network_timezones.parse_date_time(cur_airs_next, curShow.airs, curShow.network)) %>
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
        display_status = curShow.status
        if None is not display_status:
            if 'nded' not in display_status and 1 == int(curShow.paused):
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
                            % if curShow.network:
                                <span title="${curShow.network}"><img class="show-network-image" src="/showPoster/?show=${curShow.indexerid}&amp;which=network" alt="${curShow.network}" title="${curShow.network}" /></span>
                            % else:
                                <span title="No Network"><img class="show-network-image" src="/images/network/nonetwork.png" alt="No Network" title="No Network" /></span>
                            % endif
                        </td>
                        <td class="show-table">
                            ${renderQualityPill(curShow.quality, showTitle=True, overrideClass="show-quality")}
                        </td>
                    </tr>
                </table>
            </div>
        </div>
    % endfor
    </div>
</div>
% endfor
