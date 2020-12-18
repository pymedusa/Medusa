<%!
    import datetime

    from medusa import app
    from medusa.indexers.api import indexerApi
    from medusa.indexers.utils import indexer_id_to_name
    from medusa.sbdatetime import sbdatetime
%>
<!-- start banner view //-->
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
            </div>
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
                    <h2 class="${'fanartOpacity' if app.FANART_BACKGROUND else ''} day">${sbdatetime.sbftime(dt=cur_ep_airdate, t_preset='%A').capitalize()}<span style="font-size: 14px; vertical-align: top;">[Today]</span></h2>
                    <% today_header = True %>
                % else:
                    <h2 class="${'fanartOpacity' if app.FANART_BACKGROUND else ''} day">${sbdatetime.sbftime(dt=cur_ep_airdate, t_preset='%A').capitalize()}</h2>
                % endif
            % endif
            <% cur_segment = cur_ep_airdate %>
        % endif
        % if cur_ep_airdate == today.date() and not today_header:
            <div>
            <h2 class="${'fanartOpacity' if app.FANART_BACKGROUND else ''} day">${sbdatetime.sbftime(dt=cur_ep_airdate, t_preset='%A').capitalize()} <span style="font-size: 14px; vertical-align: top;">[Today]</span></h2>
            </div>
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
            <th class="nobg" valign="top">
                <app-link href="home/displayShow?indexername=${indexer_id_to_name(cur_result['indexer'])}&seriesid=${cur_result['showid']}">
                    <asset default-src="images/banner.png" show-slug="${cur_result['series_slug']}" type="banner" cls="bannerThumb" :link="false"></asset>
                </app-link>
            </th>
        </tr>
        <tr>
            <td class="next_episode">
                <div class="clearfix">
                    <span class="tvshowTitle">
                        <app-link href="home/displayShow?indexername=${indexer_id_to_name(cur_result['indexer'])}&seriesid=${cur_result['showid']}">
                            ${cur_result['show_name']}${('', ' <span class="pause">[paused]</span>')[bool(cur_result['paused'])]}
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
                    <span class="title">Airs: </span><span class="airdate">${sbdatetime.sbfdatetime(cur_result['localtime'])}</span>${('', '<span> on %s</span>' % cur_result['network'])[bool(cur_result['network'])]}
                </div>
                <div class="clearfix">
                    <span class="title">Quality:</span>
                    <quality-pill :quality="${cur_result['quality']}" show-title></quality-pill>
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
<!-- end banner view //-->
