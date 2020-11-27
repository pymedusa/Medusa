<%!
    import datetime
    import time
    import re

    from medusa import app
    from medusa.indexers.utils import indexer_id_to_name
    from medusa.sbdatetime import sbdatetime
%>

<% dates = [today.date() + datetime.timedelta(days = i) for i in range(7)] %>
<% tbl_day = 0 %>

<div class="calendarWrapper">
    % for day in dates:
    <% tbl_day += 1 %>
        <table class="${'fanartOpacity' if app.FANART_BACKGROUND else ''} defaultTable tablesorter calendarTable ${'cal-%s' % (('even', 'odd')[bool(tbl_day % 2)])}" cellspacing="0" border="0" cellpadding="0">
        <thead><tr><th>${sbdatetime.sbftime(dt=day, t_preset='%A').capitalize()}</th></tr></thead>
        <tbody>
        <% day_has_show = False %>
        % for cur_result in results:
            % if bool(cur_result['paused']) and not app.COMING_EPS_DISPLAY_PAUSED:
                <% continue %>
            % endif
            <% cur_indexer = int(cur_result['indexer']) %>
            <% run_time = cur_result['runtime'] %>
            <% airday = cur_result['localtime'].date() %>
            % if airday == day:
                % try:
                    <% day_has_show = True %>
                    <% airtime = sbdatetime.fromtimestamp(time.mktime(cur_result['localtime'].timetuple())).sbftime() %>
                    % if app.TRIM_ZERO:
                        <% airtime = re.sub(r'0(\d:\d\d)', r'\1', airtime, 0, re.IGNORECASE | re.MULTILINE) %>
                    % endif
                % except OverflowError:
                    <% airtime = "Invalid" %>
                % endtry
                <tr>
                    <td class="calendarShow">
                        <div class="poster">
                            <app-link title="${cur_result['show_name'] | h}" href="home/displayShow?indexername=${indexer_id_to_name(cur_result['indexer'])}&seriesid=${cur_result['showid']}">
                                <asset default-src="images/poster.png" show-slug="${cur_result['series_slug']}" type="posterThumb" :link="false"></asset>
                            </app-link>
                        </div>
                        <div class="text">
                            <span class="airtime">
                                ${airtime} on ${cur_result["network"]}
                            </span>
                            <span class="episode-title" title="${cur_result['name'] | h}">
                                ${'S%02iE%02i' % (int(cur_result['season']), int(cur_result['episode']))} - ${cur_result['name']}
                            </span>
                        </div>
                    </td> <!-- end ${cur_result['show_name']} -->
                </tr>
            % endif
        % endfor
        % if not day_has_show:
            <tr><td class="calendarShow"><span class="show-status">No shows for this day</span></td></tr>
        % endif
        </tbody>
        </table>
    % endfor
<!-- end calender view //-->
</div>
