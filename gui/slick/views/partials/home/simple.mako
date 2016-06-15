<%!
    import sickbeard
    import calendar
    from sickbeard import sbdatetime
    from sickbeard import network_timezones
    from sickrage.helper.common import pretty_file_size
    import re
%>
<%namespace file="/inc_defs.mako" import="renderQualityPill"/>
% for curShowlist in showlists:
    <% curListType = curShowlist[0] %>
    <% myShowList = list(curShowlist[1]) %>
    % if curListType == "Anime":
        <h1 class="header">Anime List</h1>
    % endif
<table id="showListTable${curListType}" class="tablesorter" cellspacing="1" border="0" cellpadding="0">
    <thead>
        <tr>
            <th class="nowrap">Next Ep</th>
            <th class="nowrap">Prev Ep</th>
            <th>Show</th>
            <th>Network</th>
            <th>Quality</th>
            <th>Downloads</th>
            <th>Size</th>
            <th>Active</th>
            <th>Status</th>
        </tr>
    </thead>
    <tfoot class="hidden-print">
        <tr>
            <th rowspan="1" colspan="1" align="center"><a href="/addShows/">Add ${('Show', 'Anime')[curListType == 'Anime']}</a></th>
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
    % if sickbeard.showQueueScheduler.action.loadingShowList:
        <tbody class="tablesorter-infoOnly">
        % for curLoadingShow in sickbeard.showQueueScheduler.action.loadingShowList:
            <% if curLoadingShow.show is not None and curLoadingShow.show in sickbeard.showList:
                continue
            %>
            <tr>
                <td align="center">(loading)</td>
                <td></td>
                <td>
                % if curLoadingShow.show is None:
                <span title="">Loading... (${curLoadingShow.show_name})</span>
                % else:
                <a href="displayShow?show=${curLoadingShow.show.indexerid}">${curLoadingShow.show.name}</a>
                % endif
                </td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
            </tr>
        % endfor
        </tbody>
    % endif
    <tbody>
    <% myShowList.sort(lambda x, y: cmp(x.name, y.name)) %>
    % for curShow in myShowList:
    <%
        cur_airs_next = ''
        cur_airs_prev = ''
        cur_snatched = 0
        cur_downloaded = 0
        cur_total = 0
        show_size = 0
        download_stat_tip = ''

        if curShow.indexerid in show_stat:
            cur_airs_next = show_stat[curShow.indexerid]['ep_airs_next']
            cur_airs_prev = show_stat[curShow.indexerid]['ep_airs_prev']

            cur_snatched = show_stat[curShow.indexerid]['ep_snatched']
            if not cur_snatched:
                cur_snatched = 0

            cur_downloaded = show_stat[curShow.indexerid]['ep_downloaded']
            if not cur_downloaded:
                cur_downloaded = 0

            cur_total = show_stat[curShow.indexerid]['ep_total']
            if not cur_total:
                cur_total = 0

            show_size = show_stat[curShow.indexerid]['show_size']

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
    %>
        <tr>
        % if cur_airs_next:
            <% airDate = sbdatetime.sbdatetime.convert_to_setting(network_timezones.parse_date_time(cur_airs_next, curShow.airs, curShow.network)) %>
            % try:
                <td align="center" class="nowrap">
                    <time datetime="${airDate.isoformat('T')}" class="date">${sbdatetime.sbdatetime.sbfdate(airDate)}</time>
                </td>
            % except ValueError:
                <td align="center" class="nowrap"></td>
            % endtry
        % else:
            <td align="center" class="nowrap"></td>
        % endif

        % if cur_airs_prev:
            <% airDate = sbdatetime.sbdatetime.convert_to_setting(network_timezones.parse_date_time(cur_airs_prev, curShow.airs, curShow.network)) %>
            % try:
                <td align="center" class="nowrap">
                    <time datetime="${airDate.isoformat('T')}" class="date">${sbdatetime.sbdatetime.sbfdate(airDate)}</time>
                </td>
            % except ValueError:
                <td align="center" class="nowrap"></td>
            % endtry
        % else:
            <td align="center" class="nowrap"></td>
        % endif

            <td class="tvShow"><a href="/home/displayShow?show=${curShow.indexerid}">${curShow.name}</a></td>

            <td>
                <span title="${curShow.network}">${curShow.network}</span>
            </td>

            <td align="center">${renderQualityPill(curShow.quality, showTitle=True)}</td>

            <td align="center">
                ## This first span is used for sorting and is never displayed to user
                <span style="display: none;">${download_stat}</span>
                <div class="progressbar hidden-print" style="position:relative;" data-show-id="${curShow.indexerid}" data-progress-percentage="${progressbar_percent}" data-progress-text="${download_stat}" data-progress-tip="${download_stat_tip}"></div>
                <span class="visible-print-inline">${download_stat}</span>
            </td>

            <td align="center" data-show-size="${show_size}">${pretty_file_size(show_size)}</td>

            <td align="center">
                <% paused = int(curShow.paused) == 0 and curShow.status == 'Continuing' %>
                <img src="/images/${('no16.png', 'yes16.png')[bool(paused)]}" alt="${('No', 'Yes')[bool(paused)]}" width="16" height="16" />
            </td>

            <td align="center">
            <%
                display_status = curShow.status
                if None is not display_status:
                    if re.search(r'(?i)(?:new|returning)\s*series', curShow.status):
                        display_status = 'Continuing'
                    elif re.search('(?i)(?:nded)', curShow.status):
                        display_status = 'Ended'
            %>
            ${display_status}
            </td>
        </tr>
    % endfor
    </tbody>
</table>
% endfor
