<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    from medusa.helpers import anon_url
    from medusa.indexers.indexer_api import indexerApi
    from medusa.indexers.indexer_config import mappings
    from medusa import sbdatetime
    from random import choice
    import datetime
    import time
    import re
%>
<%block name="scripts">
<script type="text/javascript" src="js/ajax-episode-search.js?${sbPID}"></script>
<script type="text/javascript" src="js/plot-tooltip.js?${sbPID}"></script>
</%block>

<%block name="content">
<%namespace file="/inc_defs.mako" import="renderQualityPill"/>
<input type="hidden" id="series-id" value="${choice(results)['showid'] if results else ''}" />
<input type="hidden" id="series-slug" value="${choice(results)['series_slug'] if results else ''}" />
<div class="row">
    <div class="col-md-12">
        <h1 class="header">${header}</h1>
    </div>
</div>

<div class="row">
    <div class="col-md-12">
        <div class="key pull-left">
        % if 'calendar' != layout:
            <b>Key:</b>
            <span class="listing-key listing-overdue">Missed</span>
            <span class="listing-key listing-current">Today</span>
            <span class="listing-key listing-default">Soon</span>
            <span class="listing-key listing-toofar">Later</span>
        % endif
            <a class="btn btn-inline forceBacklog" href="webcal://${sbHost}:${sbHttpPort}/calendar">
            <i class="icon-calendar icon-white"></i>Subscribe</a>
        </div>

        <div class="pull-right">
            <div class="show-option">
                <span>View Paused:
                    <select name="viewpaused" class="form-control form-control-inline input-sm" onchange="location = this.options[this.selectedIndex].value;">
                        <option value="toggleScheduleDisplayPaused" ${'selected="selected"' if not bool(app.COMING_EPS_DISPLAY_PAUSED) else ''}>Hidden</option>
                        <option value="toggleScheduleDisplayPaused" ${'selected="selected"' if app.COMING_EPS_DISPLAY_PAUSED else ''}>Shown</option>
                    </select>
                </span>
            </div>
            <div class="show-option">
                <span>Layout:
                    <select name="layout" class="form-control form-control-inline input-sm">
                        <option value="poster" ${'selected="selected"' if app.COMING_EPS_LAYOUT == 'poster' else ''} >Poster</option>
                        <option value="calendar" ${'selected="selected"' if app.COMING_EPS_LAYOUT == 'calendar' else ''} >Calendar</option>
                        <option value="banner" ${'selected="selected"' if app.COMING_EPS_LAYOUT == 'banner' else ''} >Banner</option>
                        <option value="list" ${'selected="selected"' if app.COMING_EPS_LAYOUT == 'list' else ''} >List</option>
                    </select>
                </span>
            </div>
            % if layout == 'list':
            <div class="show-option">
                <button id="popover" type="button" class="btn btn-inline">Select Columns <b class="caret"></b></button>
            </div>
            % else:
            <div class="show-option">
                <span>Sort By:
                    <select name="sort" class="form-control form-control-inline input-sm" onchange="location = this.options[this.selectedIndex].value;">
                        <option value="setScheduleSort/?sort=date" ${'selected="selected"' if app.COMING_EPS_SORT == 'date' else ''} >Date</option>
                        <option value="setScheduleSort/?sort=network" ${'selected="selected"' if app.COMING_EPS_SORT == 'network' else ''} >Network</option>
                        <option value="setScheduleSort/?sort=show" ${'selected="selected"' if app.COMING_EPS_SORT == 'show' else ''} >Show</option>
                    </select>
                </span>
            </div>
            % endif
        </div>
    </div>
</div>

<div class="horizontal-scroll">
% if 'list' == layout:
<!-- start list view //-->
<% show_div = 'listing-default' %>
<table id="showListTable" class="${'fanartOpacity' if app.FANART_BACKGROUND else ''} defaultTable tablesorter seasonstyle" cellspacing="1" border="0" cellpadding="0">
    <thead>
        <tr>
            <th>Airdate (${('local', 'network')[app.TIMEZONE_DISPLAY == 'network']})</th>
            <th>Ends</th>
            <th>Show</th>
            <th>Next Ep</th>
            <th>Next Ep Name</th>
            <th>Network</th>
            <th>Run time</th>
            <th>Quality</th>
            <th>Indexers</th>
            <th>Search</th>
        </tr>
    </thead>
    <tbody style="text-shadow:none;">
% for cur_result in results:
<%
    cur_indexer = int(cur_result['indexer'])
    run_time = cur_result['runtime']
    if bool(cur_result['paused']) and not app.COMING_EPS_DISPLAY_PAUSED:
        continue
    cur_ep_airdate = cur_result['localtime'].date()
    if run_time:
        cur_ep_enddate = cur_result['localtime'] + datetime.timedelta(minutes = run_time)
        if cur_ep_enddate < today:
            show_div = 'listing-overdue'
        elif cur_ep_airdate >= next_week.date():
            show_div = 'listing-toofar'
        elif cur_ep_airdate >= today.date() and cur_ep_airdate < next_week.date():
            if cur_ep_airdate == today.date():
                show_div = 'listing-current'
            else:
                show_div = 'listing-default'
%>
        <tr class="${show_div}">
            <td align="center" nowrap="nowrap" class="triggerhighlight">
                <% airDate = sbdatetime.sbdatetime.convert_to_setting(cur_result['localtime']) %>
                <time datetime="${airDate.isoformat('T')}" class="date">${sbdatetime.sbdatetime.sbfdatetime(airDate)}</time>
            </td>
            <td align="center" nowrap="nowrap" class="triggerhighlight">
                <% ends = sbdatetime.sbdatetime.convert_to_setting(cur_ep_enddate) %>
                <time datetime="${ends.isoformat('T')}" class="date">${sbdatetime.sbdatetime.sbfdatetime(ends)}</time>
            </td>
            <td class="tvShow triggerhighlight" nowrap="nowrap"><a href="home/displayShow?show=${cur_result['showid']}">${cur_result['show_name']}</a>
% if bool(cur_result['paused']):
                <span class="pause">[paused]</span>
% endif
            </td>
            <td nowrap="nowrap" align="center" class="triggerhighlight">
                ${'S%02iE%02i' % (int(cur_result['season']), int(cur_result['episode']))}
            </td>
            <td class="triggerhighlight">
% if cur_result['description']:
                <img alt="" src="images/info32.png" height="16" width="16" class="plotInfo" id="plot_info_${str(mappings.get(cur_indexer).replace('_id', '')) + str(cur_result['showid'])}_${str(cur_result["season"])}_${str(cur_result["episode"])}" />
% else:
                <img alt="" src="images/info32.png" width="16" height="16" class="plotInfoNone"  />
% endif
                ${cur_result['name']}
            </td>
            <td align="center" class="triggerhighlight">
                ${cur_result['network']}
            </td>
            <td align="center" class="triggerhighlight">
            ${run_time}min
            </td>
            <td align="center" class="triggerhighlight">
                ${renderQualityPill(cur_result['quality'], showTitle=True)}
            </td>
            <td align="center" style="vertical-align: middle;" class="triggerhighlight">
            % if cur_result['imdb_id']:
                <a href="${anon_url('http://www.imdb.com/title/', cur_result['imdb_id'])}" rel="noreferrer" onclick="window.open(this.href, '_blank'); return false" title="http://www.imdb.com/title/${cur_result['imdb_id']}">
                    <img alt="[imdb]" height="16" width="16" src="images/imdb.png" />
                </a>
            % endif
                <a href="${anon_url(indexerApi(cur_indexer).config['show_url'], cur_result['showid'])}" data-indexer-name="${indexerApi(cur_indexer).name}"
                    rel="noreferrer" onclick="window.open(this.href, '_blank'); return false" title="${indexerApi(cur_indexer).config['show_url']}${cur_result['showid']}">
                    <img alt="${indexerApi(cur_indexer).name}" height="16" width="16" src="images/${indexerApi(cur_indexer).config['icon']}" />
                </a>
            </td>
            <td align="center" class="triggerhighlight">
            <a class="epSearch" id="forceUpdate-${cur_result['showid']}x${cur_result['season']}x${cur_result['episode']}" name="forceUpdate-${cur_result['showid']}x${cur_result['season']}x${cur_result['episode']}" href="home/searchEpisode?show=${cur_result['showid']}&amp;season=${cur_result['season']}&amp;episode=${cur_result['episode']}"><img data-ep-search src="images/search16.png" width="16" height="16" alt="search" title="Forced Search" /></a>
            <a class="epManualSearch" id="forcedSearch-${cur_result['showid']}x${cur_result['season']}x${cur_result['episode']}" name="forcedSearch-${cur_result['showid']}x${cur_result['season']}x${cur_result['episode']}" href="home/snatchSelection?show=${cur_result['showid']}&amp;season=${cur_result['season']}&amp;episode=${cur_result['episode']}&amp;manual_search_type=episode"><img data-ep-manual-search src="images/manualsearch.png" width="16" height="16" alt="search" title="Manual Search" /></a>
            </td>
        </tr>
% endfor
    </tbody>
    <tfoot>
        <tr class="shadow border-bottom">
            <th rowspan="1" colspan="10" align="center">&nbsp</th>
        </tr>
    </tfoot>
</table>
<!-- end list view //-->
% elif layout in ['banner', 'poster']:
<!-- start non list view //-->
<%
    cur_segment = None
    too_late_header = False
    missed_header = False
    today_header = False
    show_div = 'ep_listing listing-default'
%>

% if app.COMING_EPS_SORT == 'show':
    <br><br>
% endif
% for cur_result in results:
<%
    cur_indexer = int(cur_result['indexer'])
    if bool(cur_result['paused']) and not app.COMING_EPS_DISPLAY_PAUSED:
        continue
    run_time = cur_result['runtime']
    cur_ep_airdate = cur_result['localtime'].date()
    if run_time:
        cur_ep_enddate = cur_result['localtime'] + datetime.timedelta(minutes = run_time)
    else:
        cur_ep_enddate = cur_result['localtime']
%>
    % if app.COMING_EPS_SORT == 'network':
        <% show_network = ('no network', cur_result['network'])[bool(cur_result['network'])] %>
        % if cur_segment != show_network:
            <div>
                <h2 class="${'fanartOpacity' if app.FANART_BACKGROUND else ''} network">${show_network}</h2>
            <% cur_segment = cur_result['network'] %>
        % endif
        % if cur_ep_enddate < today:
            <% show_div = 'ep_listing listing-overdue' %>
        % elif cur_ep_airdate >= next_week.date():
            <% show_div = 'ep_listing listing-toofar' %>
        % elif cur_ep_enddate >= today and cur_ep_airdate < next_week.date():
            % if cur_ep_airdate == today.date():
                <% show_div = 'ep_listing listing-current' %>
            % else:
                <% show_div = 'ep_listing listing-default' %>
            % endif
        % endif
    % elif app.COMING_EPS_SORT == 'date':
        % if cur_segment != cur_ep_airdate:
            % if cur_ep_enddate < today and cur_ep_airdate != today.date() and not missed_header:
                <h2 class="${'fanartOpacity' if app.FANART_BACKGROUND else ''} day">Missed</h2>
                <% missed_header = True %>
            % elif cur_ep_airdate >= next_week.date() and not too_late_header:
                <h2 class="${'fanartOpacity' if app.FANART_BACKGROUND else ''} day">Later</h2>
                <% too_late_header = True %>
            % elif cur_ep_enddate >= today and cur_ep_airdate < next_week.date():
                % if cur_ep_airdate == today.date():
                    <h2 class="${'fanartOpacity' if app.FANART_BACKGROUND else ''} day">${datetime.date.fromordinal(cur_ep_airdate.toordinal()).strftime('%A').decode(app.SYS_ENCODING).capitalize()}<span style="font-size: 14px; vertical-align: top;">[Today]</span></h2>
                    <% today_header = True %>
                % else:
                    <h2 class="${'fanartOpacity' if app.FANART_BACKGROUND else ''} day">${datetime.date.fromordinal(cur_ep_airdate.toordinal()).strftime('%A').decode(app.SYS_ENCODING).capitalize()}</h2>
                % endif
            % endif
            <% cur_segment = cur_ep_airdate %>
        % endif
        % if cur_ep_airdate == today.date() and not today_header:
            <div>
            <h2 class="${'fanartOpacity' if app.FANART_BACKGROUND else ''} day">${datetime.date.fromordinal(cur_ep_airdate.toordinal()).strftime('%A').decode(app.SYS_ENCODING).capitalize()} <span style="font-size: 14px; vertical-align: top;">[Today]</span></h2>
            <% today_header = True %>
        % endif
        % if cur_ep_enddate < today:
            <% show_div = 'ep_listing listing-overdue' %>
        % elif cur_ep_airdate >= next_week.date():
            <% show_div = 'ep_listing listing-toofar' %>
        % elif cur_ep_enddate >= today and cur_ep_airdate < next_week.date():
            % if cur_ep_airdate == today.date():
                <% show_div = 'ep_listing listing-current' %>
            % else:
                <% show_div = 'ep_listing listing-default'%>
            % endif
        % endif
    % elif app.COMING_EPS_SORT == 'show':
        % if cur_ep_enddate < today:
            <% show_div = 'ep_listing listing-overdue listingradius' %>
        % elif cur_ep_airdate >= next_week.date():
            <% show_div = 'ep_listing listing-toofar listingradius' %>
        % elif cur_ep_enddate >= today and cur_ep_airdate < next_week.date():
            % if cur_ep_airdate == today.date():
                <% show_div = 'ep_listing listing-current listingradius' %>
            % else:
                <% show_div = 'ep_listing listing-default listingradius' %>
            % endif
        % endif
    % endif
<div class="${'fanartOpacity' if app.FANART_BACKGROUND else ''} ${show_div}" id="listing-${cur_result['showid']}">
    <div class="tvshowDiv">
        <table width="100%" border="0" cellpadding="0" cellspacing="0">
        <tr>
            <th ${('class="nobg"', 'rowspan="2"')[layout == 'poster']} valign="top">
                <a href="home/displayShow?show=${cur_result['showid']}">
                    <img alt="" class="${('posterThumb', 'bannerThumb')[layout == 'banner']}" series="${cur_result['series_slug']}" asset="${(layout, 'posterThumb')[layout == 'poster']}"/>
                </a>
            </th>
% if 'banner' == layout:
        </tr>
        <tr>
% endif
            <td class="next_episode">
                <div class="clearfix">
                    <span class="tvshowTitle">
                        <a href="home/displayShow?show=${cur_result['showid']}">${cur_result['show_name']}
                            ${('', '<span class="pause">[paused]</span>')[bool(cur_result['paused'])]}
                        </a>
                    </span>
                    <span class="tvshowTitleIcons">
% if cur_result['imdb_id']:
                        <a href="${anon_url('http://www.imdb.com/title/', cur_result['imdb_id'])}" rel="noreferrer" onclick="window.open(this.href, '_blank'); return false" title="http://www.imdb.com/title/${cur_result['imdb_id']}">
                            <img alt="[imdb]" height="16" width="16" src="images/imdb.png" />
                        </a>
% endif
                        <a href="${anon_url(indexerApi(cur_indexer).config['show_url'], cur_result['showid'])}" rel="noreferrer" onclick="window.open(this.href, '_blank'); return false" title="${indexerApi(cur_indexer).config['show_url']}"><img alt="${indexerApi(cur_indexer).name}" height="16" width="16" src="images/${indexerApi(cur_indexer).config['icon']}" /></a>
                        <a class="epSearch" id="forceUpdate-${cur_result['showid']}x${cur_result['season']}x${cur_result['episode']}" name="forceUpdate-${cur_result['showid']}x${cur_result['season']}x${cur_result['episode']}" href="home/searchEpisode?show=${cur_result['showid']}&amp;season=${cur_result['season']}&amp;episode=${cur_result['episode']}"><img data-ep-search src="images/search16.png" width="16" height="16" alt="search" title="Forced Search" /></a>
                        <a class="epManualSearch" id="forcedSearch-${cur_result['showid']}x${cur_result['season']}x${cur_result['episode']}" name="forcedSearch-${cur_result['showid']}x${cur_result['season']}x${cur_result['episode']}" href="home/snatchSelection?show=${cur_result['showid']}&amp;season=${cur_result['season']}&amp;episode=${cur_result['episode']}&amp;manual_search_type=episode"><img data-ep-manual-search src="images/manualsearch.png" width="16" height="16" alt="search" title="Manual Search" /></a>
                    </span>
                </div>
                <span class="title">Next Episode:</span> <span>${'S%02iE%02i' % (int(cur_result['season']), int(cur_result['episode']))} - ${cur_result['name']}</span>
                <div class="clearfix">
                    <span class="title">Airs: </span><span class="airdate">${sbdatetime.sbdatetime.sbfdatetime(cur_result['localtime'])}</span>${('', '<span> on %s</span>' % cur_result['network'])[bool(cur_result['network'])]}
                </div>
                <div class="clearfix">
                    <span class="title">Quality:</span>
                    ${renderQualityPill(cur_result['quality'], showTitle=True)}
                </div>
            ##</td>
        ##</tr>
        ##<tr>
            ##<td style="vertical-align: top;">
                <div>
% if cur_result['description']:
                        <span class="title" style="vertical-align:middle;">Plot:</span>
                        <img class="ep_summaryTrigger" src="images/plus.png" height="16" width="16" alt="" title="Toggle Summary" /><div class="ep_summary">${cur_result['description']}</div>
% else:
                        <span class="title ep_summaryTriggerNone" style="vertical-align:middle;">Plot:</span>
                        <img class="ep_summaryTriggerNone" src="images/plus.png" height="16" width="16" alt="" />
% endif
                </div>
            </td>
        </tr>
        </table>
    </div>
</div>
<!-- end ${cur_result['show_name']} //-->
% endfor
<!-- end non list view //-->
% endif
% if 'calendar' == layout:
<% dates = [today.date() + datetime.timedelta(days = i) for i in range(7)] %>
<% tbl_day = 0 %>

<div class="calendarWrapper">
    % for day in dates:
    <% tbl_day += 1 %>
        <table class="${'fanartOpacity' if app.FANART_BACKGROUND else ''} defaultTable tablesorter calendarTable ${'cal-%s' % (('even', 'odd')[bool(tbl_day % 2)])}" cellspacing="0" border="0" cellpadding="0">
        <thead><tr><th>${day.strftime('%A').decode(app.SYS_ENCODING).capitalize()}</th></tr></thead>
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
                    <% airtime = sbdatetime.sbdatetime.fromtimestamp(time.mktime(cur_result['localtime'].timetuple())).sbftime().decode(app.SYS_ENCODING) %>
                    % if app.TRIM_ZERO:
                        <% airtime = re.sub(r'0(\d:\d\d)', r'\1', airtime, 0, re.IGNORECASE | re.MULTILINE) %>
                    % endif
                % except OverflowError:
                    <% airtime = "Invalid" %>
                % endtry
                <tr>
                    <td class="calendarShow">
                        <div class="poster">
                            <a title="${cur_result['show_name']}" href="home/displayShow?show=${cur_result['showid']}"><img alt="" series="${cur_result['series_slug']}" asset="posterThumb" /></a>
                        </div>
                        <div class="text">
                            <span class="airtime">
                                ${airtime} on ${cur_result["network"]}
                            </span>
                            <span class="episode-title" title="${cur_result['name']}">
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
% endif
</div>
<div class="clearfix"></div>
</div>
</div>
</%block>
