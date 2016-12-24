<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    from medusa.helpers import anon_url
    from medusa.indexers.indexer_api import indexerApi
%>
<%block name="scripts">
<script type="text/javascript" src="js/lib/jquery.bookmarkscroll.js?${sbPID}"></script>
<script type="text/javascript" src="js/plot-tooltip.js?${sbPID}"></script>
<script type="text/javascript" src="js/rating-tooltip.js?${sbPID}"></script>
<script type="text/javascript" src="js/ajax-episode-subtitles.js?${sbPID}"></script>
</%block>
<%block name="content">
<%namespace file="/inc_defs.mako" import="renderQualityPill"/>
<input type="hidden" id="showID" value="${show.indexerid}" />
<div class="clearfix"></div><!-- div.clearfix //-->

% if show_message:
    <div class="alert alert-info">
        ${show_message}
    </div><!-- .alert .alert-info //-->
% endif

<%include file="/partials/showheader.mako"/>

<div class="row">
    <div class="col-md-12">
        <input class="btn manualSearchButton" type="button" id="reloadResults" value="Reload Results" data-force-search="0" />
        <input class="btn manualSearchButton" type="button" id="reloadResultsForceSearch" value="Force Search" data-force-search="1" />
        <div id="searchNotification"></div><!-- #searchNotification //-->
        <div class="pull-right clearfix" id="filterControls">
            <button id="popover" type="button" class="btn top-5 bottom-5">Select Columns <b class="caret"></b></button>
            <button id="btnReset" type="button" class="btn top-5 bottom-5">Reset Sort</button>
        </div><!-- #filterControls //-->
        <div class="clearfix"></div><!-- .clearfix //-->
        <div id="wrapper" data-history-toggle="hide">
            <div id="container">
            % if episode_history:
                <table id="history" class="${"displayShowTableFanArt tablesorterFanArt" if app.FANART_BACKGROUND else "displayShowTable"} display_show tablesorter tablesorter-default hasSaveSort hasStickyHeaders" cellspacing="1" border="0" cellpadding="0">
                    <tbody class="tablesorter-no-sort" aria-live="polite" aria-relevant="all">
                        <tr style="height: 60px;" role="row">
                            <th style="vertical-align: bottom; width: auto;" colspan="10" class="row-seasonheader ${"displayShowTableFanArt" if app.FANART_BACKGROUND else "displayShowTable"}">
                                <h3 style="display: inline;">
                                    History
                                </h3>
                                <button id="showhistory" type="button" class="btn top-5 bottom-5 pull-right" data-toggle="collapse" data-target="#historydata">
                                    Show History
                                </button>
                            </th>
                        </tr>
                    </tbody>
                    <tbody class="tablesorter-no-sort" aria-live="polite" aria-relevant="all">
                        <tr>
                            <th width="15%">Date</th>
                            <th width="18%">Status</th>
                            <th width="15%">Provider/Group</th>
                            <th width="52%">Release</th>
                        </tr>
                    </tbody>
                    <tbody class="toggle collapse" aria-live="polite" aria-relevant="all" id="historydata">
                        % for item in episode_history:
                            <tr class="${item['status_color_style']}">
                            <td align="center" style="width: auto;">
                                ${item['action_date']}
                            </td>
                            <td  align="center" style="width: auto;">
                            ${item['status_name']} ${renderQualityPill(item['quality'])}
                            </td>
                            <td align="center" style="width: auto;">
                                    % if item['provider_img_link']:
                                        <img src="${item['provider_img_link']}" width="16" height="16" alt="${item['provider_name']}" title="${item['provider_name']}"/> ${item["provider_name"]}
                                    % else:
                                        ${item['provider_name']}
                                    % endif
                            </td>
                            <td style="width: auto;">
                            ${item['resource_file']}
                            </td>
                            </tr>
                        % endfor
                    </tbody>
                </table>
            % endif
            <!-- add provider meta data -->
                <meta data-last-prov-updates='${provider_results["last_prov_updates"]}' data-show="${show.indexerid}" data-season="${season}" data-episode="${episode}" data-manual-search-type="${manual_search_type}">
                <table id="showTableSeason" class="${"displayShowTableFanArt tablesorterFanArt" if app.FANART_BACKGROUND else "displayShowTable"} display_show tablesorter tablesorter-default hasSaveSort hasStickyHeaders" cellspacing="1" border="0" cellpadding="0">
                    <!-- @TODO: Change this first thead to a caption with CSS styling -->
                    <tbody class="tablesorter-no-sort" aria-live="polite" aria-relevant="all">
                        <tr style="height: 60px;" role="row">
                            <th style="vertical-align: bottom; width: auto;" colspan="10" class="row-seasonheader ${"displayShowTableFanArt" if app.FANART_BACKGROUND else "displayShowTable"}">
                                <h3 style="display: inline;">
                                    Season ${season}
                                % if manual_search_type != 'season':
                                    Episode ${episode}
                                % endif
                                </h3>
                            </th>
                        </tr>
                    </tbody>
                </table>
                <table id="showTable" class="${"displayShowTableFanArt tablesorterFanArt" if app.FANART_BACKGROUND else "displayShowTable"} display_show tablesorter tablesorter-default hasSaveSort hasStickyHeaders" cellspacing="1" border="0" cellpadding="0">
                    <thead aria-live="polite" aria-relevant="all">
                        <tr>
                            <th data-priority="critical" class="col-name">Release</th>
                            <th>Group</th>
                            <th>Provider</th>
                            <th>Quality</th>
                            <th>Seeds</th>
                            <th>Peers</th>
                            <th>Size</th>
                            <th>Type</th>
                            <th>Updated</th>
                            <th>Published</th>
                            <th data-priority="critical" class="col-search">Snatch</th>
                        </tr>
                    </thead>
                    <tbody aria-live="polite" aria-relevant="all">
                    % for hItem in provider_results['found_items']:
                        <tr id='${hItem["name"]}' class="skipped season-${season} seasonstyle ${hItem['status_highlight']}" role="row">
                            <td class="tvShow">
                                <span class="break-word ${hItem['name_highlight']}">
                                    ${hItem["name"]}
                                </span>
                            </td>
                            <td class="col-group">
                                <span class="break-word ${hItem['rg_highlight']}">
                                    ${hItem['release_group']}
                                </span>
                            </td>
                            <td class="col-provider">
                                <img src="${hItem["provider_img_link"]}" width="16" height="16" style="vertical-align:middle;" style="cursor: help;" alt="${hItem["provider"]}" title="${hItem["provider"]}"/>
                                ${hItem["provider"]}
                            </td>
                            <td align="center">${renderQualityPill(int(hItem["quality"]))}
                            % if hItem["proper_tags"]:
                                <img src="images/info32.png" width="16" height="16" style="vertical-align:middle;" title="${hItem["proper_tags"]}"/>
                            % endif
                            </td>
                            <td align="center">
                                <span class="${hItem['seed_highlight']}">
                                    ${hItem["seeders"]}
                                </span>
                            </td>
                            <td align="center">
                                <span class="${hItem['leech_highlight']}">
                                    ${hItem["leechers"]}
                                </span>
                            </td>
                            <td class="col-size">${hItem["pretty_size"]}</td>
                            <td align="center">${hItem["provider_type"]}</td>
                            <td class="col-date">${hItem["time"]}</td>
                            <td class="col-date">${hItem["pubdate"]}</td>
                            <td class="col-search"><a class="epManualSearch" id="${str(show.indexerid)}x${season}x${episode}" name="${str(show.indexerid)}x${season}x${episode}" href='home/pickManualSearch?provider=${hItem["provider_id"]}&amp;rowid=${hItem["rowid"]}&amp;manual_search_type=${manual_search_type}'><img src="images/download.png" width="16" height="16" alt="search" title="Download selected episode" /></a></td>
                        </tr>
                    % endfor
                    </tbody>
                </table>
            </div><!-- #container //-->
        </div><!-- #wrapper //-->
    </div><!-- col -->
</div><!-- row -->
</%block>
