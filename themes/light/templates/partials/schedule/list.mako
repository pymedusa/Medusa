<%!
    import datetime

    from medusa import app, sbdatetime
    from medusa.indexers.api import indexerApi
    from medusa.indexers.utils import indexer_id_to_name
%>
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
    else:
        cur_ep_enddate = cur_result['localtime']
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
                <plot-info description="${cur_result['description'] | h}" show-slug="${indexer_id_to_name(cur_indexer) + str(cur_result['showid'])}" season="${str(cur_result['season'])}" episode="${str(cur_result['episode'])}"></plot-info>
                ${cur_result['name']}
            </td>
            <td align="center" class="triggerhighlight">
                ${cur_result['network']}
            </td>
            <td align="center" class="triggerhighlight">
            ${run_time}min
            </td>
            <td align="center" class="triggerhighlight">
                <quality-pill :quality="${cur_result['quality']}" show-title></quality-pill>
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