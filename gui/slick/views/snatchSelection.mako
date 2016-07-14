<%inherit file="/layouts/main.mako"/>
<%!
    import datetime
    import urllib
    import ntpath
    import os.path
    import sickbeard
    import time
    from sickbeard import subtitles, sbdatetime, network_timezones, helpers, show_name_helpers
    import sickbeard.helpers

    from sickbeard.common import SKIPPED, WANTED, UNAIRED, ARCHIVED, IGNORED, FAILED, DOWNLOADED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST
    from sickbeard.common import Quality, qualityPresets, statusStrings, Overview
    from sickbeard.helpers import anon_url
    from sickrage.helper.common import pretty_file_size
    from sickbeard.sbdatetime import sbdatetime
    from sickrage.show.History import History
    from sickbeard.failed_history import prepareFailedName
    from sickrage.providers.GenericProvider import GenericProvider
    from sickbeard import providers

    from sickrage.helper.encoding import ek
%>
<%block name="scripts">
<script type="text/javascript" src="${srRoot}/js/lib/jquery.bookmarkscroll.js?${sbPID}"></script>
<script type="text/javascript" src="${srRoot}/js/plotTooltip.js?${sbPID}"></script>
<script type="text/javascript" src="${srRoot}/js/ratingTooltip.js?${sbPID}"></script>
<script type="text/javascript" src="${srRoot}/js/ajaxEpSubtitles.js?${sbPID}"></script>
</%block>
<%block name="content">
<%namespace file="/inc_defs.mako" import="renderQualityPill"/>
<input type="hidden" id="srRoot" value="${srRoot}" />

    <div class="clearfix"></div>

    <div id="showtitle" data-showname="${show.name}">
        <h1 class="title" id="scene_exception_${show.indexerid}"> <a href="${srRoot}/home/displayShow?show=${show.indexerid}">${show.name}</h1>
    </div>


    <div class="clearfix"></div>

% if show_message:
    <div class="alert alert-info">
        ${show_message}
    </div>
% endif

        <div id="posterCol">
            <a href="${srRoot}/showPoster/?show=${show.indexerid}&amp;which=poster" rel="dialog" title="View Poster for ${show.name}"><img src="${srRoot}/showPoster/?show=${show.indexerid}&amp;which=poster_thumb" class="tvshowImg" alt=""/></a>
        </div>

        <div id="showCol">

            <div id="showinfo">
% if 'rating' in show.imdb_info:
    <% rating_tip = str(show.imdb_info['rating']) + " / 10" + " Stars" + "<br>" + str(show.imdb_info['votes']) + " Votes" %>
    <span class="imdbstars" qtip-content="${rating_tip}">${show.imdb_info['rating']}</span>
% endif

% if not show.imdbid:
    <span>(${show.startyear}) - ${show.runtime} minutes - </span>
% else:
    % if 'country_codes' in show.imdb_info:
        % for country in show.imdb_info['country_codes'].split('|'):
                <img src="${srRoot}/images/blank.png" class="country-flag flag-${country}" width="16" height="11" style="margin-left: 3px; vertical-align:middle;" />
        % endfor
    % endif
                <span>
    % if show.imdb_info.get('year'):
                    (${show.imdb_info['year']}) -
    % endif
                    ${show.imdb_info.get('runtimes') or show.runtime} minutes
                </span>

                <a href="${anon_url('http://www.imdb.com/title/', show.imdbid)}" rel="noreferrer" onclick="window.open(this.href, '_blank'); return false;" title="http://www.imdb.com/title/${show.imdbid}">
                    <img alt="[imdb]" height="16" width="16" src="${srRoot}/images/imdb.png" style="margin-top: -1px; vertical-align:middle;"/>
                </a>
% endif

                <a href="${anon_url(sickbeard.indexerApi(show.indexer).config['show_url'], show.indexerid)}" onclick="window.open(this.href, '_blank'); return false;" title="${sickbeard.indexerApi(show.indexer).config["show_url"] + str(show.indexerid)}">
                    <img alt="${sickbeard.indexerApi(show.indexer).name}" height="16" width="16" src="${srRoot}/images/${sickbeard.indexerApi(show.indexer).config["icon"]}" style="margin-top: -1px; vertical-align:middle;"/>
                </a>

% if xem_numbering or xem_absolute_numbering:
                <a href="${anon_url('http://thexem.de/search?q=', show.name)}" rel="noreferrer" onclick="window.open(this.href, '_blank'); return false;" title="http://thexem.de/search?q-${show.name}">
                    <img alt="[xem]" height="16" width="16" src="${srRoot}/images/xem.png" style="margin-top: -1px; vertical-align:middle;"/>
                </a>
% endif
            </div>

            <div id="tags">
                <ul class="tags">
                    % if show.imdb_info.get('genres'):
                        % for imdbgenre in show.imdb_info['genres'].replace('Sci-Fi','Science-Fiction').split('|'):
                            <a href="${anon_url('http://www.imdb.com/search/title?count=100&title_type=tv_series&genres=', imdbgenre.lower())}" target="_blank" title="View other popular ${imdbgenre} shows on IMDB."><li>${imdbgenre}</li></a>
                        % endfor
                    % elif show.genre:
                        % for genre in show.genre[1:-1].split('|'):
                            <a href="${anon_url('http://trakt.tv/shows/popular/?genres=', genre.lower())}" target="_blank" title="View other popular ${genre} shows on trakt.tv."><li>${genre}</li></a>
                        % endfor
                    % endif
                </ul>
            </div>

            <div id="summary">
                <table class="summaryTable pull-left">
                <% anyQualities, bestQualities = Quality.splitQuality(int(show.quality)) %>
                    <tr><td class="showLegend">Quality: </td><td>
                % if show.quality in qualityPresets:
                    ${renderQualityPill(show.quality)}
                % else:
                % if anyQualities:
                    <i>Allowed:</i> ${", ".join([capture(renderQualityPill, x) for x in sorted(anyQualities)])}${("", "<br>")[bool(bestQualities)]}
                % endif
                % if bestQualities:
                    <i>Preferred:</i> ${", ".join([capture(renderQualityPill, x) for x in sorted(bestQualities)])}
                % endif
                % endif

                % if show.network and show.airs:
                    <tr><td class="showLegend">Originally Airs: </td><td>${show.airs} ${("<font color='#FF0000'><b>(invalid Timeformat)</b></font> ", "")[network_timezones.test_timeformat(show.airs)]} on ${show.network}</td></tr>
                % elif show.network:
                    <tr><td class="showLegend">Originally Airs: </td><td>${show.network}</td></tr>
                % elif show.airs:
                    <tr><td class="showLegend">Originally Airs: </td><td>${show.airs} ${("<font color='#FF0000'><b>(invalid Timeformat)</b></font>", "")[network_timezones.test_timeformat(show.airs)]}</td></tr>
                % endif
                    <tr><td class="showLegend">Show Status: </td><td>${show.status}</td></tr>
                    <tr><td class="showLegend">Default EP Status: </td><td>${statusStrings[show.default_ep_status]}</td></tr>
                % if showLoc[1]:
                    <tr><td class="showLegend">Location: </td><td>${showLoc[0]}</td></tr>
                % else:
                    <tr><td class="showLegend"><span style="color: red;">Location: </span></td><td><span style="color: red;">${showLoc[0]}</span> (Missing)</td></tr>
                % endif
                % if show.exceptions:
                    <tr><td class="showLegend" style="vertical-align: top;">Scene Name:</td><td>${(show.name, " | ".join(show.exceptions))[show.exceptions != 0]}</td></tr>
                % endif

                % if require_words:
                    <tr><td class="showLegend" style="vertical-align: top;">Required Words: </td><td><span class="break-word"><font color="green">${require_words}</font></span></td></tr>
                % endif
                % if ignore_words:
                    <tr><td class="showLegend" style="vertical-align: top;">Ignored Words: </td><td><span class="break-word"><font color="red">${ignore_words}</font></span></td></tr>
                % endif
                % if preferred_words:
                    <tr><td class="showLegend" style="vertical-align: top;">Preferred Words: </td><td><span class="break-word"><font color="blue">${preferred_words}</font></span></td></tr>
                % endif
                % if undesired_words:
                    <tr><td class="showLegend" style="vertical-align: top;">Undesired Words: </td><td><span class="break-word"><font color="orange">${undesired_words}</font></span></td></tr>
                % endif
                % if bwl and bwl.whitelist:
                    <tr>
                        <td class="showLegend">Wanted Group${("", "s")[len(bwl.whitelist) > 1]}:</td>
                        <td>${', '.join(bwl.whitelist)}</td>
                    </tr>
                % endif
                % if bwl and bwl.blacklist:
                    <tr>
                        <td class="showLegend">Unwanted Group${("", "s")[len(bwl.blacklist) > 1]}:</td>
                        <td>${', '.join(bwl.blacklist)}</td>
                    </tr>
                % endif

                <tr><td class="showLegend">Size:</td><td>${pretty_file_size(sickbeard.helpers.get_size(showLoc[0]))}</td></tr>

                </table>

                <table style="width:180px; float: right; vertical-align: middle; height: 100%;">
                    <% info_flag = subtitles.code_from_code(show.lang) if show.lang else '' %>
                    <tr><td class="showLegend">Info Language:</td><td><img src="${srRoot}/images/subtitles/flags/${info_flag}.png" width="16" height="11" alt="${show.lang}" title="${show.lang}" onError="this.onerror=null;this.src='${srRoot}/images/flags/unknown.png';"/></td></tr>
                    % if sickbeard.USE_SUBTITLES:
                    <tr><td class="showLegend">Subtitles: </td><td><img src="${srRoot}/images/${("no16.png", "yes16.png")[bool(show.subtitles)]}" alt="${("N", "Y")[bool(show.subtitles)]}" width="16" height="16" /></td></tr>
                    % endif
                    <tr><td class="showLegend">Season Folders: </td><td><img src="${srRoot}/images/${("no16.png", "yes16.png")[bool(not show.flatten_folders or sickbeard.NAMING_FORCE_FOLDERS)]}" alt="${("N", "Y")[bool(not show.flatten_folders or sickbeard.NAMING_FORCE_FOLDERS)]}" width="16" height="16" /></td></tr>
                    <tr><td class="showLegend">Paused: </td><td><img src="${srRoot}/images/${("no16.png", "yes16.png")[bool(show.paused)]}" alt="${("N", "Y")[bool(show.paused)]}" width="16" height="16" /></td></tr>
                    <tr><td class="showLegend">Air-by-Date: </td><td><img src="${srRoot}/images/${("no16.png", "yes16.png")[bool(show.air_by_date)]}" alt="${("N", "Y")[bool(show.air_by_date)]}" width="16" height="16" /></td></tr>
                    <tr><td class="showLegend">Sports: </td><td><img src="${srRoot}/images/${("no16.png", "yes16.png")[bool(show.is_sports)]}" alt="${("N", "Y")[bool(show.is_sports)]}" width="16" height="16" /></td></tr>
                    <tr><td class="showLegend">Anime: </td><td><img src="${srRoot}/images/${("no16.png", "yes16.png")[bool(show.is_anime)]}" alt="${("N", "Y")[bool(show.is_anime)]}" width="16" height="16" /></td></tr>
                    <tr><td class="showLegend">DVD Order: </td><td><img src="${srRoot}/images/${("no16.png", "yes16.png")[bool(show.dvdorder)]}" alt="${("N", "Y")[bool(show.dvdorder)]}" width="16" height="16" /></td></tr>
                    <tr><td class="showLegend">Scene Numbering: </td><td><img src="${srRoot}/images/${("no16.png", "yes16.png")[bool(show.scene)]}" alt="${("N", "Y")[bool(show.scene)]}" width="16" height="16" /></td></tr>
                </table>
            </div>
        </div>

    <input class="btn manualSearchButton" type="button" id="reloadResults" value="Reload Results" data-force-search="0" />
    <input class="btn manualSearchButton" type="button" id="reloadResultsForceSearch" value="Force Search" data-force-search="1" />
    <div id="searchNotification"></div>

    <div class="clearfix"></div>
    <div id="wrapper" data-history-toggle="hide">
    <div id="container">

    % if episode_history:
        <table id="history" class="displayShowTable display_show tablesorter tablesorter-default hasSaveSort hasStickyHeaders" cellspacing="1" border="0" cellpadding="0">

                <tbody class="tablesorter-no-sort" aria-live="polite" aria-relevant="all">
                <tr style="height: 60px;" role="row">
                    <th style="vertical-align: bottom; width: auto;" colspan="10" class="row-seasonheader displayShowTable">
                    <h3 style="display: inline;"><a name="history" style="position: absolute; font-size: 1px; visibility: hidden;">.</a>History</h3>
                     <button id="showhistory" type="button" class="btn btn-xs pull-right" data-toggle="collapse" data-target="#historydata">Show History</button>
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
                    <% status, quality = Quality.splitCompositeStatus(item['action']) %>
                    % if status == DOWNLOADED:
                        <tr style="background-color:#C3E3C8;!important">
                    % elif status in (SNATCHED, SNATCHED_PROPER, SNATCHED_BEST):
                        <tr style="background-color:#EBC1EA;!important">
                    % elif status == FAILED:
                        <tr style="background-color:#FF9999;!important">
                    % endif

                    <td align="center" style="width: auto;">
                        <% action_date = sbdatetime.sbfdatetime(datetime.datetime.strptime(str(item['date']), History.date_format), show_seconds=True) %>
                        ${action_date}
                    </td>
                    <td  align="center" style="width: auto;">
                    ${statusStrings[status]} ${renderQualityPill(quality)}
                    </td>
                    <td align="center" style="width: auto;">
                        <% provider = providers.getProviderClass(GenericProvider.make_id(item["provider"])) %>
                        % if provider is not None:
                            <img src="${srRoot}/images/providers/${provider.image_name()}" width="16" height="16" alt="${provider.name}" title="${provider.name}"/> ${item["provider"]}
                        % else:
                            ${item['provider'] if item['provider'] != "-1" else 'Unknown'}
                        % endif
                    </td>
                    <td style="width: auto;">
                    ${os.path.basename(item['resource'])}
                    </td>
                    </tr>
                % endfor
            </tbody>
        </table>
    % endif

    <!-- @TODO: Change this to use the REST API -->
    <!-- add provider meta data -->
    <meta data-last-prov-updates='${provider_results["last_prov_updates"]}' data-show="${show.indexerid}" data-season="${season}" 
    data-episode="${episode}" data-manual-search-type="${manual_search_type}">
        <table id="showTable" class="displayShowTable display_show tablesorter tablesorter-default hasSaveSort hasStickyHeaders" cellspacing="1" border="0" cellpadding="0">
            <tbody class="tablesorter-no-sort" aria-live="polite" aria-relevant="all">
            <tr style="height: 60px;" role="row">
                <th style="vertical-align: bottom; width: auto;" colspan="10" class="row-seasonheader displayShowTable">
                    % if manual_search_type == 'season':
                        <h3 style="display: inline;"><a name="season-${season}" style="position: absolute; font-size: 1px; visibility: hidden;">.</a>Season ${season}</h3>
                    % else:
                        <h3 style="display: inline;"><a name="season-${season}" style="position: absolute; font-size: 1px; visibility: hidden;">.</a>Season ${season} Episode ${episode}</h3>
                    % endif
                </th>
            </tr>
            </tbody>

            <tbody class="tablesorter-no-sort" aria-live="polite" aria-relevant="all">
                <tr>
                    <th class="col-name">Release</th>
                    <th>Group</th>
                    <th>Provider</th>
                    <th>Quality</th>
                    <th>Seeds</th>
                    <th>Peers</th>
                    <th>Size</th>
                    <th>Type</th>
                    <th>Date</th>
                    <th class="col-search">Snatch</th>
                </tr>
            </tbody>

            <tbody aria-live="polite" aria-relevant="all">
            % for hItem in provider_results['found_items']:

                <%
                if manual_search_type == 'season' and 'E00' in hItem["name"]:
                    continue

                release_group_ignore = False
                release_group_require = False
                release_group_preferred = False
                release_group_undesired = False
                name_ignore = False
                name_require = False
                name_undesired = False
                name_preferred = False
                below_minseed = False
                below_minleech = False

                release_group = hItem["release_group"]
                if release_group and ignore_words and release_group.lower() in ignore_words.lower().split(','):
                    release_group_ignore = True
                elif release_group and require_words and release_group.lower() in require_words.lower().split(','):
                    release_group_require = True
                elif release_group and preferred_words and release_group.lower() in preferred_words.lower().split(','):
                    release_group_preferred = True
                elif release_group and undesired_words and release_group.lower() in undesired_words.lower().split(','):
                    release_group_undesired = True

                if hItem["name"] and require_words and show_name_helpers.containsAtLeastOneWord(hItem["name"], require_words):
                    name_require = True
                if hItem["name"] and ignore_words and show_name_helpers.containsAtLeastOneWord(hItem["name"], ignore_words):
                    name_ignore = True
                if hItem["name"] and not show_name_helpers.filterBadReleases(hItem["name"], False):
                    name_ignore = True
                if hItem["name"] and undesired_words and show_name_helpers.containsAtLeastOneWord(hItem["name"], undesired_words):
                    name_undesired = True
                if hItem["name"] and preferred_words and show_name_helpers.containsAtLeastOneWord(hItem["name"], preferred_words):
                    name_preferred = True

                if hItem["provider_minseed"] and int(hItem["seeders"]) > -1 and int(hItem["seeders"]) < int(hItem["provider_minseed"]):
                    below_minseed = True
                if hItem["provider_minleech"] and int(hItem["leechers"]) > -1 and int(hItem["leechers"]) < int(hItem["provider_minleech"]):
                    below_minleech = True

                %>
                % if any([i for i in episode_history if prepareFailedName(str(hItem["name"])) in i['resource'] and (hItem['release_group'] == i['provider'] or  hItem['provider'] == i['provider']) and Quality.splitCompositeStatus(i['action']).status == FAILED]):
                    <tr style="text-decoration:line-through;!important" id="S${season}E${episode} ${hItem["name"]}" class="skipped season-${season} seasonstyle" role="row">
                % elif any([i for i in episode_history if Quality.splitCompositeStatus(i['action']).status in (SNATCHED, SNATCHED_PROPER, SNATCHED_BEST) and hItem["name"] in i['resource'] and hItem['provider'] == i['provider']]):
                    <tr style="background-color:#EBC1EA;!important" id="S${season}E${episode} ${hItem["name"]}" class="skipped season-${season} seasonstyle" role="row">
                % else:
                    <tr id="S${season}E${episode} ${hItem["name"]}" class="skipped season-${season} seasonstyle" role="row">
                % endif
                    % if name_ignore:
                        <td class="tvShow"><span class="break-word"><font color="red">${hItem["name"]}</font></span></td>
                    % elif name_require:
                        <td class="tvShow"><span class="break-word"><font color="green">${hItem["name"]}</font></span></td>
                    % elif name_undesired:
                        <td class="tvShow"><span class="break-word"><font color="orange">${hItem["name"]}</font></span></td>
                    % elif name_preferred:
                        <td class="tvShow"><span class="break-word"><font color="blue">${hItem["name"]}</font></span></td>
                    % else:
                        <td class="tvShow"><span class="break-word">${hItem["name"]}</span></td>
                    % endif
                    % if release_group_ignore:
                        <td class="col-group"><span class="break-word"><font color="red">${release_group}</font></span></td>
                    % elif release_group_require:
                        <td class="col-group"><span class="break-word"><font color="green">${release_group}</font></span></td>
                    % elif release_group_preferred:
                        <td class="col-group"><span class="break-word"><font color="blue">${release_group}</font></span></td>
                    % elif release_group_undesired:
                        <td class="col-group"><span class="break-word"><font color="orange">${release_group}</font></span></td>
                    % else:
                        <td class="col-group"><span class="break-word">${release_group}</span></td>
                    % endif
                    <td class="col-provider">
                        % if hItem["provider_image"]:
                            <img src="${srRoot}/images/providers/${hItem["provider_image"]}" width="16" height="16" style="vertical-align:middle;" alt="${hItem["provider"]}" style="cursor: help;" title="${hItem["provider"]}"/> ${hItem["provider"]}
                        % else:
                            <img src="${srRoot}/images/providers/missing.png" width="16" height="16" style="vertical-align:middle;" alt="missing provider" title="missing provider"/> ${hItem["provider"]}
                        % endif
                    </td>
                    <td align="center">${renderQualityPill(int(hItem["quality"]))}</td>
                    
                    % if below_minseed:
                        <td align="center"><font color="red">${hItem["seeders"] if hItem["seeders"] > -1 else '-'}</font></td>
                    % else:
                        <td align="center">${hItem["seeders"] if hItem["seeders"] > -1 else '-'}</td>
                    % endif
                    % if below_minleech:
                        <td align="center"><font color="red">${hItem["leechers"] if hItem["leechers"] > -1 else '-'}</font></td>
                    % else:
                        <td align="center">${hItem["leechers"] if hItem["leechers"] > -1 else '-'}</td>
                    % endif
                    <td class="col-size">${pretty_file_size(hItem["size"]) if hItem["size"] > -1 else 'N/A'}</td>
                    <td align="center">${hItem["provider_type"]}</td>
                    <td class="col-date">${datetime.datetime.fromtimestamp(hItem["time"]).strftime(sickbeard.DATE_PRESET+" "+sickbeard.TIME_PRESET)}</td>
                    <td class="col-search"><a class="epManualSearch" id="${str(show.indexerid)}x${season}x${episode}" name="${str(show.indexerid)}x${season}x${episode}" href="${srRoot}/home/pickManualSearch?provider=${hItem["provider_id"]}&amp;rowid=${hItem["rowid"]}&amp;manual_search_type=${manual_search_type}"><img src="${srRoot}/images/download.png" width="16" height="16" alt="search" title="Download selected episode" /></a></td>
                </tr>
            % endfor
            </tbody>
        </table>
    </div>
    </div>
</%block>
