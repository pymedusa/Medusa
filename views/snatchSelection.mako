<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    from medusa.helpers import anon_url
%>
<%block name="scripts">
<script type="text/javascript" src="js/plot-tooltip.js?${sbPID}"></script>
<script type="text/javascript" src="js/rating-tooltip.js?${sbPID}"></script>
<script type="text/javascript" src="js/ajax-episode-subtitles.js?${sbPID}"></script>
</%block>
<%block name="content">
<%namespace file="/inc_defs.mako" import="renderQualityPill"/>
<input type="hidden" id="showID" value="${show.indexerid}" />
<div class="clearfix"></div><!-- div.clearfix //-->

<%include file="/partials/showheader.mako"/>

<div class="row">
    <div class="col-md-12">
        <div class="clearfix"></div><!-- .clearfix //-->
        <div id="wrapper" data-history-toggle="hide">
            <div id="container">
            % if episode_history:
                <table id="snatchhistory" class="${"displayShowTableFanArt tablesorterFanArt" if app.FANART_BACKGROUND else "displayShowTable"} display_show tablesorter tablesorter-default" cellspacing="1" border="0" cellpadding="0">
                    <tbody class="tablesorter-no-sort" aria-live="polite" aria-relevant="all">
                        <tr role="row">
                            <th colspan="5" class="row-seasonheader">
                                <h3>
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
                            <th>Date</th>
                            <th>Status</th>
                            <th>Provider/Group</th>
                            <th>Release</th>
                            <th>Size</th>
                        </tr>
                    </tbody>
                    <tbody class="toggle collapse" aria-live="polite" aria-relevant="all" id="historydata">
                        % for item in episode_history:
                            <tr class="${item['status_color_style']}">
                                <td>
                                    ${item['action_date']}
                                </td>
                                <td>
                                ${item['status_name']} ${renderQualityPill(item['quality'])}
                                </td>
                                <td>
                                        % if item['provider_img_link']:
                                            <img src="${item['provider_img_link']}" width="16" height="16" alt="${item['provider_name']}" title="${item['provider_name']}"/> ${item["provider_name"]}
                                        % else:
                                            ${item['provider_name']}
                                        % endif
                                </td>
                                <td>
                                ${item['resource_file']}
                                </td>
                                <td class="col-size">
                                ${item['resource_size']}
                                </td>
                            </tr>
                        % endfor
                        <tr id="history-footer" class="tablesorter-no-sort border-bottom shadow">
                            <th class="tablesorter-no-sort" colspan=4></th>
                        </tr>
                    </tbody>
                    <tbody class="tablesorter-no-sort"><tr><th class="row-seasonheader" colspan=4></td></tr></tbody>
                </table>
            % endif
            <!-- add provider meta data -->
                <div id='manualSearchMeta'>
                    <meta data-last-prov-updates='${provider_results["last_prov_updates"]}' data-show="${show.indexerid}" data-season="${season}" data-episode="${episode}" data-manual-search-type="${manual_search_type}">
                </div>
                <div class="col-md-12 bottom-15">
                    <div class="col-md-8 left-30">
                    <input class="btn manualSearchButton" type="button" id="reloadResults" value="Reload Results" data-force-search="0" />
                    <input class="btn manualSearchButton" type="button" id="reloadResultsForceSearch" value="Force Search" data-force-search="1" />
                    <div id="searchNotification"></div><!-- #searchNotification //-->
                    </div>
                    <div class="pull-right clearfix col-md-4 right-30" id="filterControls">
                        <div class="pull-right">
                            <button id="popover" type="button" class="btn">Select Columns <b class="caret"></b></button>
                            <button id="btnReset" type="button" class="btn">Reset Sort</button>
                        </div>
                    </div><!-- #filterControls //-->
                </div>
                <table id="srchresults" class="${"displayShowTableFanArt tablesorterFanArt" if app.FANART_BACKGROUND else "displayShowTable"} display_show tablesorter tablesorter-default hasSaveSort hasStickyHeaders" cellspacing="1" border="0" cellpadding="0">
                    <thead>
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
                    <tbody id="manualSearchTbody" aria-live="polite" aria-relevant="all">
                    % for hItem in provider_results['found_items']:
                        <tr id='${hItem["name"]}' class="skipped season-${season} seasonstyle ${hItem['status_highlight']}" role="row">
                            <td class="release-name-ellipses triggerhighlight">
                                <span data-qtip-my="top left" data-qtip-at="bottom left" title='${hItem["name"]}' class="break-word ${hItem['name_highlight']} addQTip">${hItem["name"]}</span>
                            </td>
                            <td class="col-group break-word triggerhighlight">
                                <span class="break-word ${hItem['rg_highlight']}">${hItem['release_group']}</span>
                            </td>
                            <td class="col-provider triggerhighlight">
                                <span title="${hItem["provider"]}" class="addQTip">
                                    <img src="${hItem["provider_img_link"]}" width="16" height="16" class="vMiddle curHelp" alt="${hItem["provider"]}" title="${hItem["provider"]}"/>
                                </span>
                            </td>
                            <td class="triggerhighlight">${renderQualityPill(int(hItem["quality"]))}
                            % if hItem["proper_tags"]:
                                <img src="images/info32.png" width="16" height="16" class="vMmiddle" title="${hItem["proper_tags"]}"/>
                            % endif
                            </td>
                            <td class="triggerhighlight">
                                <span class="${hItem['seed_highlight']}">${hItem["seeders"]}</span>
                            </td>
                            <td class="triggerhighlight">
                                <span class="${hItem['leech_highlight']}">${hItem["leechers"]}</span>
                            </td>
                            <td class="col-size triggerhighlight">${hItem["pretty_size"]}</td>
                            <td class="triggerhighlight">${hItem["provider_type"]}</tdclass>
                            <td class="col-date triggerhighlight">
                                <span data-qtip-my="top middle" data-qtip-at="bottom middle" title='${hItem["time"]}' class="addQTip"><time datetime="${hItem['time'].isoformat('T')}" class="date">${hItem["time"]}</time></span>
                            </td>
                            <td class="col-date triggerhighlight">${hItem["pubdate"]}</td>
                            <td class="col-search triggerhighlight"><a class="epManualSearch" id="${str(show.indexerid)}x${season}x${episode}" name="${str(show.indexerid)}x${season}x${episode}" href='home/pickManualSearch?provider=${hItem["provider_id"]}&amp;rowid=${hItem["rowid"]}&amp;manual_search_type=${manual_search_type}'><img src="images/download.png" width="16" height="16" alt="search" title="Download selected episode" /></a></td>
                        </tr>
                    % endfor
                    </tbody>
                    <tbody class="tablesorter-no-sort">
                    <tr id="search-footer" class="tablesorter-no-sort border-bottom shadow">
                        <th class="tablesorter-no-sort" colspan=11></td>
                    </tr>
                    <tr><th class="row-seasonheader" colspan=11></th></tr></tbody>
                </table>
            </div><!-- #container //-->
        </div><!-- #wrapper //-->
    </div><!-- col -->
</div><!-- row -->
</%block>
