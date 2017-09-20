<%inherit file="/layouts/main.mako"/>
<%!
    import datetime
    import urllib
    import ntpath
    from medusa import app, helpers, subtitles, sbdatetime, network_timezones
    from medusa.common import SKIPPED, WANTED, UNAIRED, ARCHIVED, IGNORED, FAILED, DOWNLOADED
    from medusa.common import Quality, qualityPresets, statusStrings, Overview
    from medusa.helpers import anon_url
    from medusa.helper.common import pretty_file_size
    from medusa.indexers.indexer_api import indexerApi
    from medusa.indexers.indexer_config import mappings
%>
<%block name="scripts">
<script type="text/javascript" src="js/plot-tooltip.js?${sbPID}"></script>
<script type="text/javascript" src="js/rating-tooltip.js?${sbPID}"></script>
<script type="text/javascript" src="js/ajax-episode-search.js?${sbPID}"></script>
<script type="text/javascript" src="js/ajax-episode-subtitles.js?${sbPID}"></script>
</%block>
<%block name="content">
<%namespace file="/inc_defs.mako" import="renderQualityPill"/>
<input type="hidden" id="series-id" value="${show.indexerid}" />
<input type="hidden" id="series-slug" value="${show.slug}" />
<div class="clearfix"></div><!-- div.clearfix //-->
</div>
<div class="clearfix"></div>
<div id="content-col" class="col-lg-10 col-lg-offset-1 col-md-10 col-md-offset-1 col-sm-12 col-xs-12">

<%include file="/partials/showheader.mako"/>

<div class="row">
    <div class="col-md-12 horizontal-scroll">
        <table id="${'animeTable' if show.is_anime else 'showTable'}" class="${'displayShowTableFanArt tablesorterFanArt' if app.FANART_BACKGROUND else 'displayShowTable'} display_show" cellspacing="0" border="0" cellpadding="0">
            <% cur_season = -1 %>
            <% odd = 0 %>
            <% epCount = 0 %>
            <% epSize = 0 %>
            <% epList = [] %>

            % for epResult in sql_results:
                <%
                epStr = str(epResult["season"]) + "x" + str(epResult["episode"])
                if not epStr in ep_cats:
                    continue
                if not app.DISPLAY_SHOW_SPECIALS and int(epResult["season"]) == 0:
                    continue
                scene = False
                scene_anime = False
                if not show.air_by_date and not show.is_sports and not show.is_anime and show.is_scene:
                    scene = True
                elif not show.air_by_date and not show.is_sports and show.is_anime and show.is_scene:
                    scene_anime = True
                (dfltSeas, dfltEpis, dfltAbsolute) = (0, 0, 0)
                if (epResult["season"], epResult["episode"]) in xem_numbering:
                    (dfltSeas, dfltEpis) = xem_numbering[(epResult["season"], epResult["episode"])]
                if epResult["absolute_number"] in xem_absolute_numbering:
                    dfltAbsolute = xem_absolute_numbering[epResult["absolute_number"]]
                if epResult["absolute_number"] in scene_absolute_numbering:
                    scAbsolute = scene_absolute_numbering[epResult["absolute_number"]]
                    dfltAbsNumbering = False
                else:
                    scAbsolute = dfltAbsolute
                    dfltAbsNumbering = True
                if (epResult["season"], epResult["episode"]) in scene_numbering:
                    (scSeas, scEpis) = scene_numbering[(epResult["season"], epResult["episode"])]
                    dfltEpNumbering = False
                else:
                    (scSeas, scEpis) = (dfltSeas, dfltEpis)
                    dfltEpNumbering = True
                epLoc = epResult["location"]
                if epLoc and show._location and epLoc.lower().startswith(show._location.lower()):
                    epLoc = epLoc[len(show._location)+1:]
                %>
                % if int(epResult["season"]) != cur_season:
                    % if cur_season == -1:
            <thead>
                <tr class="seasoncols" style="display:none;">
                        <th data-sorter="false" data-priority="critical" class="col-checkbox"><input type="checkbox" class="seasonCheck"/></th>
                        <th data-sorter="false" class="col-metadata">NFO</th>
                        <th data-sorter="false" class="col-metadata">TBN</th>
                        <th data-sorter="false" class="col-ep">Episode</th>
                        <th data-sorter="false" ${("class=\"col-ep columnSelector-false\"", "class=\"col-ep\"")[bool(show.is_anime)]}>Absolute</th>
                        <th data-sorter="false" ${("class=\"col-ep columnSelector-false\"", "class=\"col-ep\"")[bool(scene)]}>Scene</th>
                        <th data-sorter="false" ${("class=\"col-ep columnSelector-false\"", "class=\"col-ep\"")[bool(scene_anime)]}>Scene Absolute</th>
                        <th data-sorter="false" class="col-name">Name</th>
                        <th data-sorter="false" class="col-name columnSelector-false">File Name</th>
                        <th data-sorter="false" class="col-ep columnSelector-false">Size</th>
                        <th data-sorter="false" class="col-airdate">Airdate</th>
                        <th data-sorter="false" ${("class=\"col-ep columnSelector-false\"", "class=\"col-ep\"")[bool(app.DOWNLOAD_URL)]}>Download</th>
                        <th data-sorter="false" ${("class=\"col-ep columnSelector-false\"", "class=\"col-ep\"")[bool(app.USE_SUBTITLES)]}>Subtitles</th>
                        <th data-sorter="false" class="col-status">Status</th>
                        <th data-sorter="false" class="col-search">Search</th>
                </tr>
            </thead>
            <tbody class="tablesorter-no-sort">
                <tr>
                    <th class="row-seasonheader ${'displayShowTable' if app.FANART_BACKGROUND else 'displayShowTableFanArt'}" colspan="15" style="vertical-align: bottom; width: auto;">
                        <h3 style="display: inline;"><a name="season-${epResult["season"]}"></a>${"Season " + str(epResult["season"]) if int(epResult["season"]) > 0 else "Specials"}
                        % if not any([i for i in sql_results if epResult['season'] == i['season'] and int(i['status']) == 1]):
                        <a class="epManualSearch" href="home/snatchSelection?show=${show.indexerid}&amp;season=${epResult["season"]}&amp;episode=1&amp;manual_search_type=season"><img data-ep-manual-search src="images/manualsearch${'-white' if app.THEME_NAME == 'dark' else ''}.png" width="16" height="16" alt="search" title="Manual Search" /></a>
                        % endif
                        </h3>
                        <div class="season-scene-exception" data-season=${str(epResult["season"]) if int(epResult["season"]) > 0 else "Specials"}></div>
                        <div class="pull-right"> <!-- column select and hide/show episodes -->
                            % if not app.DISPLAY_ALL_SEASONS:
                                <button id="showseason-${epResult['season']}" type="button" class="btn pull-right" data-toggle="collapse" data-target="#collapseSeason-${epResult['season']}">Hide Episodes</button>
                            % endif
                            <button id="popover" type="button" class="btn pull-right">Select Columns <b class="caret"></b></button>
                        </div> <!-- end column select and hide/show episodes -->
                    </th>
                </tr>
            </tbody>
            <tbody class="tablesorter-no-sort">
                <tr id="season-${epResult["season"]}-cols" class="seasoncols">
                    <th class="col-checkbox"><input type="checkbox" class="seasonCheck" id="${epResult["season"]}" /></th>
                    <th class="col-metadata">NFO</th>
                    <th class="col-metadata">TBN</th>
                    <th class="col-ep">Episode</th>
                    <th class="col-ep">Absolute</th>
                    <th class="col-ep">Scene</th>
                    <th class="col-ep">Scene Absolute</th>
                    <th class="col-name hidden-xs">Name</th>
                    <th class="col-name hidden-xs">File Name</th>
                    <th class="col-ep">Size</th>
                    <th class="col-airdate">Airdate</th>
                    <th class="col-ep">Download</th>
                    <th class="col-ep">Subtitles</th>
                    <th class="col-status">Status</th>
                    <th class="col-search">Search</th>
                </tr>
                    % else:
                <tr id="season-${epResult["season"]}-footer" class="seasoncols border-bottom shadow">
                    <th class="col-footer" colspan=15 align=left>Season contains ${epCount} episodes with total filesize: ${pretty_file_size(epSize)}</th>
                </tr>
                <% epCount = 0 %>
                <% epSize = 0 %>
                <% epList = [] %>
            </tbody>
            <tbody class="tablesorter-no-sort">
                <tr>
                    <th class="row-seasonheader ${'displayShowTableFanArt' if app.FANART_BACKGROUND else 'displayShowTable'}" colspan="15" style="vertical-align: bottom; width: auto;">
                        <h3 style="display: inline;"><a name="season-${epResult["season"]}"></a>${"Season " + str(epResult["season"]) if int(epResult["season"]) else "Specials"}
                        % if not any([i for i in sql_results if epResult['season'] == i['season'] and int(i['status']) == 1]):
                        <a class="epManualSearch" href="home/snatchSelection?show=${show.indexerid}&amp;season=${epResult["season"]}&amp;episode=1&amp;manual_search_type=season"><img data-ep-manual-search src="images/manualsearch${'-white' if app.THEME_NAME == 'dark' else ''}.png" width="16" height="16" alt="search" title="Manual Search" /></a>
                        % endif
                        </h3>
                        <div class="season-scene-exception" data-season=${str(epResult["season"])}></div>
                        <div class="pull-right"> <!-- hide/show episodes -->
                            % if not app.DISPLAY_ALL_SEASONS:
                                <button id="showseason-${epResult['season']}" type="button" class="btn pull-right" data-toggle="collapse" data-target="#collapseSeason-${epResult['season']}">Show Episodes</button>
                            % endif
                        </div> <!-- end hide/show episodes -->
                    </th>
                </tr>
            </tbody>
            <tbody class="tablesorter-no-sort">
                <tr id="season-${epResult["season"]}-cols" class="seasoncols ${'' if app.DISPLAY_ALL_SEASONS else 'shadow'}">
                    <th class="col-checkbox"><input type="checkbox" class="seasonCheck" id="${epResult["season"]}" /></th>
                    <th class="col-metadata">NFO</th>
                    <th class="col-metadata">TBN</th>
                    <th class="col-ep">Episode</th>
                    <th class="col-ep">Absolute</th>
                    <th class="col-ep">Scene</th>
                    <th class="col-ep">Scene Absolute</th>
                    <th class="col-name hidden-xs">Name</th>
                    <th class="col-name hidden-xs">File Name</th>
                    <th class="col-ep">Size</th>
                    <th class="col-airdate">Airdate</th>
                    <th class="col-ep">Download</th>
                    <th class="col-ep">Subtitles</th>
                    <th class="col-status">Status</th>
                    <th class="col-search">Search</th>
                </tr>
                    % endif
            </tbody>
                % if not app.DISPLAY_ALL_SEASONS:
                <tbody class="toggle collapse${("", " in")[cur_season == -1]}" id="collapseSeason-${epResult['season']}">
                % else:
                <tbody>
                % endif
                <% cur_season = int(epResult["season"]) %>
                % endif
                <tr class="${Overview.overviewStrings[ep_cats[epStr]]} season-${cur_season} seasonstyle" id="${'S' + str(epResult["season"]) + 'E' + str(epResult["episode"])}">
                    <td class="col-checkbox triggerhighlight">
                        % if int(epResult["status"]) != UNAIRED:
                            <input type="checkbox" class="epCheck" id="${str(epResult["season"])+'x'+str(epResult["episode"])}" name="${str(epResult["season"]) +"x"+str(epResult["episode"])}" />
                        % endif
                    </td>
                    <td align="center" class="triggerhighlight"><img src="images/${("nfo-no.gif", "nfo.gif")[epResult["hasnfo"]]}" alt="${("N", "Y")[epResult["hasnfo"]]}" width="23" height="11" /></td>
                    <td align="center" class="triggerhighlight"><img src="images/${("tbn-no.gif", "tbn.gif")[epResult["hastbn"]]}" alt="${("N", "Y")[epResult["hastbn"]]}" width="23" height="11" /></td>
                    <td align="center" class="triggerhighlight">
                    <%
                        text = str(epResult['episode'])
                        if epLoc != '' and epLoc is not None:
                            text = '<span title="' + epLoc + '" class="addQTip">' + text + "</span>"
                            epCount += 1
                            if not epLoc in epList:
                                epSize += epResult["file_size"]
                                epList.append(epLoc)
                    %>
                        ${text}
                    </td>
                    <td align="center" class="triggerhighlight">${epResult["absolute_number"]}</td>
                    <td align="center" class="triggerhighlight">
                        <input type="text" placeholder="${str(dfltSeas) + 'x' + str(dfltEpis)}" size="6" maxlength="8"
                            class="sceneSeasonXEpisode form-control input-scene" data-for-season="${epResult["season"]}" data-for-episode="${epResult["episode"]}"
                            id="sceneSeasonXEpisode_${show.indexerid}_${str(epResult["season"])}_${str(epResult["episode"])}"
                            title="Change this value if scene numbering differs from the indexer episode numbering. Generally used for non-anime shows."
                            % if dfltEpNumbering:
                                value=""
                            % else:
                                value="${str(scSeas)}x${str(scEpis)}"
                            % endif
                                style="padding: 0; text-align: center; max-width: 60px;"/>
                    </td>
                    <td align="center" class="triggerhighlight">
                        <input type="text" placeholder="${str(dfltAbsolute)}" size="6" maxlength="8"
                            class="sceneAbsolute form-control input-scene" data-for-absolute="${epResult["absolute_number"]}"
                            id="sceneAbsolute_${show.indexerid}${"_"+str(epResult["absolute_number"])}"
                            title="Change this value if scene absolute numbering differs from the indexer absolute numbering. Generally used for anime shows."
                            % if dfltAbsNumbering:
                                value=""
                            % else:
                                value="${str(scAbsolute)}"
                            % endif
                                style="padding: 0; text-align: center; max-width: 60px;"/>
                    </td>
                    <td class="col-name hidden-xs triggerhighlight">
                    % if epResult["description"] != "" and epResult["description"] is not None:
                        <img src="images/info32.png" width="16" height="16" class="plotInfo" alt="" id="plot_info_${show.indexer_slug}_${str(epResult["season"])}_${str(epResult["episode"])}" />
                    % else:
                        <img src="images/info32.png" width="16" height="16" class="plotInfoNone" alt="" />
                    % endif
                    ${epResult["name"]}
                    </td>
                    <td class="col-name hidden-xs triggerhighlight">${epLoc if Quality.split_composite_status(int(epResult['status'])).status in [DOWNLOADED, ARCHIVED] else ''}</td>
                    <td class="col-ep triggerhighlight">
                        % if epResult["file_size"] and Quality.split_composite_status(int(epResult['status'])).status in [DOWNLOADED, ARCHIVED]:
                            ${pretty_file_size(epResult["file_size"])}
                        % endif
                    </td>
                    <td class="col-airdate triggerhighlight">
                        % if int(epResult['airdate']) != 1:
                            ## Lets do this exactly like ComingEpisodes and History
                            ## Avoid issues with dateutil's _isdst on Windows but still provide air dates
                            <% airDate = datetime.datetime.fromordinal(epResult['airdate']) %>
                            % if airDate.year >= 1970 or show.network:
                                <% airDate = sbdatetime.sbdatetime.convert_to_setting(network_timezones.parse_date_time(epResult['airdate'], show.airs, show.network)) %>
                            % endif
                            <time datetime="${airDate.isoformat('T')}" class="date">${sbdatetime.sbdatetime.sbfdatetime(airDate)}</time>
                        % else:
                            Never
                        % endif
                    </td>
                    <td class="triggerhighlight">
                        % if app.DOWNLOAD_URL and epResult['location'] and Quality.split_composite_status(int(epResult['status'])).status in [DOWNLOADED, ARCHIVED]:
                            <%
                                filename = epResult['location']
                                for rootDir in app.ROOT_DIRS:
                                    if rootDir.startswith('/'):
                                        filename = filename.replace(rootDir, "")
                                filename = app.DOWNLOAD_URL + urllib.quote(filename.encode('utf8'))
                            %>
                            <a href="${filename}">Download</a>
                        % endif
                    </td>
                    <td class="col-subtitles triggerhighlight" align="center">
                    % for flag in (epResult["subtitles"] or '').split(','):
                        % if flag.strip() and Quality.split_composite_status(int(epResult['status'])).status in [DOWNLOADED, ARCHIVED]:
                            % if flag != 'und':
                                <a class=epRedownloadSubtitle href="home/searchEpisodeSubtitles?show=${show.indexerid}&amp;season=${epResult['season']}&amp;episode=${epResult['episode']}&amp;lang=${flag}">
                                    <img src="images/subtitles/flags/${flag}.png" width="16" height="11" alt="${flag}" onError="this.onerror=null;this.src='images/flags/unknown.png';"/>
                                </a>
                            % else:
                                <img src="images/subtitles/flags/${flag}.png" width="16" height="11" alt="${subtitles.name_from_code(flag)}" onError="this.onerror=null;this.src='images/flags/unknown.png';" />
                            % endif
                        % endif
                    % endfor
                    </td>
                        <% cur_status, cur_quality = Quality.split_composite_status(int(epResult["status"])) %>
                        % if cur_quality != Quality.NONE:
                            <td class="col-status triggerhighlight">${statusStrings[cur_status]} ${renderQualityPill(cur_quality)}</td>
                        % else:
                            <td class="col-status triggerhighlight">${statusStrings[cur_status]}</td>
                        % endif
                    <td class="col-search triggerhighlight">
                        % if int(epResult["season"]) != 0:
                            % if (int(epResult["status"]) in Quality.SNATCHED + Quality.SNATCHED_PROPER + Quality.SNATCHED_BEST + Quality.DOWNLOADED ) and app.USE_FAILED_DOWNLOADS:
                                <a class="epRetry" id="${str(show.indexerid)}x${str(epResult["season"])}x${str(epResult["episode"])}" name="${str(show.indexerid)}x${str(epResult["season"])}x${str(epResult["episode"])}" href="home/retryEpisode?show=${show.indexerid}&amp;season=${epResult["season"]}&amp;episode=${epResult["episode"]}"><img data-ep-search src="images/search16.png" height="16" alt="retry" title="Retry Download" /></a>
                            % else:
                                <a class="epSearch" id="${str(show.indexerid)}x${str(epResult["season"])}x${str(epResult["episode"])}" name="${str(show.indexerid)}x${str(epResult["season"])}x${str(epResult["episode"])}" href="home/searchEpisode?show=${show.indexerid}&amp;season=${epResult["season"]}&amp;episode=${epResult["episode"]}"><img data-ep-search src="images/search16.png" width="16" height="16" alt="search" title="Forced Search" /></a>
                            % endif
                            <a class="epManualSearch" id="${str(show.indexerid)}x${str(epResult["season"])}x${str(epResult["episode"])}" name="${str(show.indexerid)}x${str(epResult["season"])}x${str(epResult["episode"])}" href="home/snatchSelection?show=${show.indexerid}&amp;season=${epResult["season"]}&amp;episode=${epResult["episode"]}"><img data-ep-manual-search src="images/manualsearch.png" width="16" height="16" alt="search" title="Manual Search" /></a>
                        % else:
                            <a class="epManualSearch" id="${str(show.indexerid)}x${str(epResult["season"])}x${str(epResult["episode"])}" name="${str(show.indexerid)}x${str(epResult["season"])}x${str(epResult["episode"])}" href="home/snatchSelection?show=${show.indexerid}&amp;season=${epResult["season"]}&amp;episode=${epResult["episode"]}"><img data-ep-manual-search src="images/manualsearch.png" width="16" height="16" alt="search" title="Manual Search" /></a>
                        % endif
                        % if int(epResult["status"]) not in Quality.SNATCHED + Quality.SNATCHED_PROPER and app.USE_SUBTITLES and show.subtitles and epResult["location"]:
                            <a class="epSubtitlesSearch" href="home/searchEpisodeSubtitles?show=${show.indexerid}&amp;season=${epResult["season"]}&amp;episode=${epResult["episode"]}"><img src="images/closed_captioning.png" height="16" alt="search subtitles" title="Search Subtitles" /></a>
                        % endif
                    </td>
                </tr>
            % endfor
            % if sql_results:
                <tr id="season-${epResult["season"]}-footer" class="seasoncols border-bottom shadow">
                    <th class="col-footer" colspan=15 align=left>Season contains ${epCount} episodes with total filesize: ${pretty_file_size(epSize)}</th>
                </tr>
            % endif
            </tbody>
            <tbody class="tablesorter-no-sort"><tr><th class="row-seasonheader" colspan=15></th></tr></tbody>
        </table>
    </div> <!-- end of col -->
</div> <!-- row -->

<!--Begin - Bootstrap Modals-->
<div id="forcedSearchModalFailed" class="modal fade">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                <h4 class="modal-title">Forced Search</h4>
            </div>
            <div class="modal-body">
                <p>Do you want to mark this episode as failed?</p>
                <p class="text-warning"><small>The episode release name will be added to the failed history, preventing it to be downloaded again.</small></p>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-danger" data-dismiss="modal">No</button>
                <button type="button" class="btn btn-success" data-dismiss="modal">Yes</button>
            </div>
        </div>
    </div>
</div>
<div id="forcedSearchModalQuality" class="modal fade">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                <h4 class="modal-title">Forced Search</h4>
            </div>
            <div class="modal-body">
                <p>Do you want to include the current episode quality in the search?</p>
                <p class="text-warning"><small>Choosing No will ignore any releases with the same episode quality as the one currently downloaded/snatched.</small></p>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-danger" data-dismiss="modal">No</button>
                <button type="button" class="btn btn-success" data-dismiss="modal">Yes</button>
            </div>
        </div>
    </div>
</div>
<div id="confirmSubtitleReDownloadModal" class="modal fade">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                <h4 class="modal-title">Re-download subtitle</h4>
            </div>
            <div class="modal-body">
                <p>Do you want to re-download the subtitle for this language?</p>
                <p class="text-warning"><small>It will overwrite your current subtitle</small></p>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-danger" data-dismiss="modal">No</button>
                <button type="button" class="btn btn-success" data-dismiss="modal">Yes</button>
            </div>
        </div>
    </div>
</div>
<div id="askmanualSubtitleSearchModal" class="modal fade">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                <h4 class="modal-title">Subtitle search</h4>
            </div>
            <div class="modal-body">
                <p>Do you want to manually pick subtitles or let us choose it for you?</p>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-info" data-dismiss="modal">Auto</button>
                <button type="button" class="btn btn-success" data-dismiss="modal">Manual</button>
            </div>
        </div>
    </div>
</div>

<%include file="subtitle_modal.mako"/>
<!--End - Bootstrap Modal-->
</%block>

