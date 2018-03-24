<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    from medusa.indexers.indexer_api import indexerApi
    from medusa.indexers.utils import indexer_id_to_name, mappings
    from medusa import sbdatetime
    from random import choice
    import datetime
    import time
    import re
%>
<%block name="scripts">
<script type="text/javascript" src="js/ajax-episode-search.js?${sbPID}"></script>
<script type="text/javascript" src="js/plot-tooltip.js?${sbPID}"></script>
<script>
let app;
const startVue = () => {
    app = new Vue({
        el: '#vue-wrap',
        data() {
            return {};
        },
        mounted() {
            if ($.isMeta({ layout: 'schedule' }, ['list'])) {
                const sortCodes = {
                    date: 0,
                    show: 2,
                    network: 5
                };
                const sort = MEDUSA.config.comingEpsSort;
                const sortList = (sort in sortCodes) ? [[sortCodes[sort], 0]] : [[0, 0]];

                $('#showListTable:has(tbody tr)').tablesorter({
                    widgets: ['stickyHeaders', 'filter', 'columnSelector', 'saveSort'],
                    sortList,
                    textExtraction: {
                        0: node => $(node).find('time').attr('datetime'),
                        1: node => $(node).find('time').attr('datetime'),
                        7: node => $(node).find('span').text().toLowerCase(),
                        8: node => $(node).find('a[data-indexer-name]').attr('data-indexer-name')
                    },
                    headers: {
                        0: { sorter: 'realISODate' },
                        1: { sorter: 'realISODate' },
                        2: { sorter: 'loadingNames' },
                        4: { sorter: 'loadingNames' },
                        7: { sorter: 'quality' },
                        8: { sorter: 'text' },
                        9: { sorter: false }
                    },
                    widgetOptions: {
                        filter_columnFilters: true, // eslint-disable-line camelcase
                        filter_hideFilters: true, // eslint-disable-line camelcase
                        filter_saveFilters: true, // eslint-disable-line camelcase
                        columnSelector_mediaquery: false // eslint-disable-line camelcase
                    }
                });

                $.ajaxEpSearch();
            }

            if ($.isMeta({ layout: 'schedule' }, ['banner', 'poster'])) {
                $.ajaxEpSearch({
                    size: 16,
                    loadingImage: 'loading16' + MEDUSA.config.themeSpinner + '.gif'
                });
                $('.ep_summary').hide();
                $('.ep_summaryTrigger').on('click', function() {
                    $(this).next('.ep_summary').slideToggle('normal', function() {
                        $(this).prev('.ep_summaryTrigger').prop('src', function(i, src) {
                            return $(this).next('.ep_summary').is(':visible') ? src.replace('plus', 'minus') : src.replace('minus', 'plus');
                        });
                    });
                });
            }

            $('#popover').popover({
                placement: 'bottom',
                html: true, // Required if content has HTML
                content: '<div id="popover-target"></div>'
            }).on('shown.bs.popover', () => { // Bootstrap popover event triggered when the popover opens
                // call this function to copy the column selection code into the popover
                $.tablesorter.columnSelector.attachTo($('#showListTable'), '#popover-target');
            });

            $('.show-option select[name="layout"]').on('change', function() {
                api.patch('config/main', {
                    layout: {
                        schedule: $(this).val()
                    }
                }).then(response => {
                    log.info(response);
                    window.location.reload();
                }).catch(err => {
                    log.info(err);
                });
            });
        }
    });
};
</script>
</%block>

<%block name="content">
<%namespace file="/inc_defs.mako" import="renderQualityPill"/>
<% random_series = choice(results) if results else '' %>
<input type="hidden" id="background-series-slug" value="${choice(results)['series_slug'] if results else ''}" />

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
            <app-link class="btn btn-inline forceBacklog" href="webcal://${sbHost}:${sbHttpPort}/calendar">
            <i class="icon-calendar icon-white"></i>Subscribe</app-link>
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
            <td class="tvShow triggerhighlight" nowrap="nowrap"><app-link href="home/displayShow?indexername=${indexer_id_to_name(cur_result['indexer'])}&seriesid=${cur_result['showid']}">${cur_result['show_name']}</app-link>
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
                <app-link href="http://www.imdb.com/title/${cur_result['imdb_id']}" title="http://www.imdb.com/title/${cur_result['imdb_id']}">
                    <img alt="[imdb]" height="16" width="16" src="images/imdb.png" />
                </app-link>
            % endif
                <app-link href="${indexerApi(cur_indexer).config['show_url']}${cur_result['showid']}" data-indexer-name="${indexerApi(cur_indexer).name}"
                    title="${indexerApi(cur_indexer).config['show_url']}${cur_result['showid']}">
                    <img alt="${indexerApi(cur_indexer).name}" height="16" width="16" src="images/${indexerApi(cur_indexer).config['icon']}" />
                </app-link>
            </td>
            <td align="center" class="triggerhighlight">
            <app-link class="epSearch" id="forceUpdate-${cur_result['indexer']}x${cur_result['showid']}x${cur_result['season']}x${cur_result['episode']}" name="forceUpdate-${cur_result['showid']}x${cur_result['season']}x${cur_result['episode']}"
                href="home/searchEpisode?indexername=${indexer_id_to_name(cur_result['indexer'])}&seriesid=${cur_result['showid']}&amp;season=${cur_result['season']}&amp;episode=${cur_result['episode']}"><img data-ep-search src="images/search16.png" width="16" height="16" alt="search" title="Forced Search" /></app-link>
            <app-link class="epManualSearch" id="forcedSearch-${cur_result['indexer']}x${cur_result['showid']}x${cur_result['season']}x${cur_result['episode']}" name="forcedSearch-${cur_result['showid']}x${cur_result['season']}x${cur_result['episode']}"
                href="home/snatchSelection?indexername=${indexer_id_to_name(cur_result['indexer'])}&seriesid=${cur_result['showid']}&amp;season=${cur_result['season']}&amp;episode=${cur_result['episode']}&amp;manual_search_type=episode"><img data-ep-manual-search src="images/manualsearch.png" width="16" height="16" alt="search" title="Manual Search" /></app-link>
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
                <app-link href="home/displayShow?indexername=${indexer_id_to_name(cur_result['indexer'])}&seriesid=${cur_result['showid']}">
                    <img alt="" class="${('posterThumb', 'bannerThumb')[layout == 'banner']}" series="${cur_result['series_slug']}" asset="${(layout, 'posterThumb')[layout == 'poster']}"/>
                </app-link>
            </th>
% if 'banner' == layout:
        </tr>
        <tr>
% endif
            <td class="next_episode">
                <div class="clearfix">
                    <span class="tvshowTitle">
                        <app-link href="home/displayShow?indexername=${indexer_id_to_name(cur_result['indexer'])}&seriesid=${cur_result['showid']}}">
                            ${('', '<span class="pause">[paused]</span>')[bool(cur_result['paused'])]}
                        </app-link>
                    </span>
                    <span class="tvshowTitleIcons">
% if cur_result['imdb_id']:
                        <app-link href="http://www.imdb.com/title/${cur_result['imdb_id']}" title="http://www.imdb.com/title/${cur_result['imdb_id']}">
                            <img alt="[imdb]" height="16" width="16" src="images/imdb.png" />
                        </app-link>
% endif
                        <app-link href="${indexerApi(cur_indexer).config['show_url']}${cur_result['showid']}" title="${indexerApi(cur_indexer).config['show_url']}"><img alt="${indexerApi(cur_indexer).name}" height="16" width="16" src="images/${indexerApi(cur_indexer).config['icon']}" /></app-link>
                        <app-link class="epSearch" id="forceUpdate-${cur_result['indexer']}x${cur_result['showid']}x${cur_result['season']}x${cur_result['episode']}" name="forceUpdate-${cur_result['showid']}x${cur_result['season']}x${cur_result['episode']}" href="home/searchEpisode?indexername=${indexer_id_to_name(cur_result['indexer'])}&seriesid=${cur_result['showid']}&amp;season=${cur_result['season']}&amp;episode=${cur_result['episode']}"><img data-ep-search src="images/search16.png" width="16" height="16" alt="search" title="Forced Search" /></app-link>
                        <app-link class="epManualSearch" id="forcedSearch-${cur_result['indexer']}x${cur_result['showid']}x${cur_result['season']}x${cur_result['episode']}" name="forcedSearch-${cur_result['showid']}x${cur_result['season']}x${cur_result['episode']}" href="home/snatchSelection?indexername=${indexer_id_to_name(cur_result['indexer'])}&seriesid=${cur_result['showid']}&amp;season=${cur_result['season']}&amp;episode=${cur_result['episode']}&amp;manual_search_type=episode"><img data-ep-manual-search src="images/manualsearch.png" width="16" height="16" alt="search" title="Manual Search" /></app-link>
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
                            <app-link title="${cur_result['show_name']}" href="home/displayShow?indexername=${indexer_id_to_name(cur_result['indexer'])}&seriesid=${cur_result['showid']}"><img alt="" series="${cur_result['series_slug']}" asset="posterThumb" /></app-link>
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
