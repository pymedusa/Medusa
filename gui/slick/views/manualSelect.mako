<%inherit file="/layouts/main.mako"/>
<%!
    import datetime
    import urllib
    import ntpath
    import os.path
    import sickbeard
    from sickbeard import providers, subtitles, sbdatetime, network_timezones, helpers
    import sickbeard.helpers

    from sickbeard.common import SKIPPED, WANTED, UNAIRED, ARCHIVED, IGNORED, FAILED, DOWNLOADED
    from sickbeard.common import Quality, qualityPresets, statusStrings, Overview
    from sickbeard.helpers import anon_url
    from sickrage.helper.common import pretty_file_size

    from sickrage.helper.encoding import ek
    from sickrage.providers.GenericProvider import GenericProvider
%>
<%block name="scripts">
<script type="text/javascript" src="${srRoot}/js/lib/jquery.bookmarkscroll.js?${sbPID}"></script>
<script type="text/javascript" src="${srRoot}/js/plotTooltip.js?${sbPID}"></script>
<script type="text/javascript" src="${srRoot}/js/sceneExceptionsTooltip.js?${sbPID}"></script>
<script type="text/javascript" src="${srRoot}/js/ratingTooltip.js?${sbPID}"></script>
<script type="text/javascript" src="${srRoot}/js/ajaxEpSubtitles.js?${sbPID}"></script>
</%block>
<%block name="content">
<%namespace file="/inc_defs.mako" import="renderQualityPill"/>
<input type="hidden" id="srRoot" value="${srRoot}" />

    <div class="clearfix"></div>

    <div id="showtitle" data-showname="${show.name}">
        <h1 class="title" id="scene_exception_${show.indexerid}">${show.name}</h1>
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

<% _show = show %>
% if not show.imdbid:
    <span>(${show.startyear}) - ${show.runtime} minutes - </span>
% else:
    % if 'country_codes' in show.imdb_info:
        % for country in show.imdb_info['country_codes'].split('|'):
                <img src="${srRoot}/images/blank.png" class="country-flag flag-${country}" width="16" height="11" style="margin-left: 3px; vertical-align:middle;" />
        % endfor
    % endif
    <span>
    % if 'year' in show.imdb_info and show.imdb_info['year']:
                (${show.imdb_info['year']}) -
    % endif
                ${show.imdb_info['runtimes']} minutes</span>

                <a href="${anon_url('http://www.imdb.com/title/', _show.imdbid)}" rel="noreferrer" onclick="window.open(this.href, '_blank'); return false;" title="http://www.imdb.com/title/${show.imdbid}"><img alt="[imdb]" height="16" width="16" src="${srRoot}/images/imdb.png" style="margin-top: -1px; vertical-align:middle;"/></a>
% endif
                <a href="${anon_url(sickbeard.indexerApi(_show.indexer).config['show_url'], _show.indexerid)}" onclick="window.open(this.href, '_blank'); return false;" title="${sickbeard.indexerApi(show.indexer).config["show_url"] + str(show.indexerid)}"><img alt="${sickbeard.indexerApi(show.indexer).name}" height="16" width="16" src="${srRoot}/images/${sickbeard.indexerApi(show.indexer).config["icon"]}" style="margin-top: -1px; vertical-align:middle;"/></a>
% if xem_numbering or xem_absolute_numbering:
                <a href="${anon_url('http://thexem.de/search?q=', _show.name)}" rel="noreferrer" onclick="window.open(this.href, '_blank'); return false;" title="http://thexem.de/search?q-${show.name}"><img alt="[xem]" height="16" width="16" src="${srRoot}/images/xem.png" style="margin-top: -1px; vertical-align:middle;"/></a>
% endif
            </div>

            <div id="tags">
                <ul class="tags">
                    % if ('genres' not in show.imdb_info or not show.imdb_info['genres']) and show.genre:
                        % for genre in show.genre[1:-1].split('|'):
                            <a href="${anon_url('http://trakt.tv/shows/popular/?genres=', genre.lower())}" target="_blank" title="View other popular ${genre} shows on trakt.tv."><li>${genre}</li></a>
                        % endfor
                    % elif 'genres' in show.imdb_info and show.imdb_info['genres']:
                        % for imdbgenre in show.imdb_info['genres'].replace('Sci-Fi','Science-Fiction').split('|'):
                            <a href="${anon_url('http://www.imdb.com/search/title?count=100&title_type=tv_series&genres=', imdbgenre.lower())}" target="_blank" title="View other popular ${imdbgenre} shows on IMDB."><li>${imdbgenre}</li></a>
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
                    <tr><td class="showLegend">Scene Name:</td><td></td></tr>

                % if show.rls_require_words:
                    <tr><td class="showLegend">Required Words: </td><td>${show.rls_require_words}</td></tr>
                % endif
                % if show.rls_ignore_words:
                    <tr><td class="showLegend">Ignored Words: </td><td>${show.rls_ignore_words}</td></tr>
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
                    <tr><td class="showLegend">Season Folders: </td><td><img src="${srRoot}/images/${("no16.png", "yes16.png")[bool(not show.flatten_folders or sickbeard.NAMING_FORCE_FOLDERS)]}" alt=="${("N", "Y")[bool(not show.flatten_folders or sickbeard.NAMING_FORCE_FOLDERS)]}" width="16" height="16" /></td></tr>
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
    
    <div class="clearfix"></div>
    <div id="wrapper">
    <div id="container">
    
    <!-- @TODO: Change this to use the REST API -->
    <!-- add provider meta data -->
    <meta data-last-prov-updates="${last_prov_updates}" data-show="${show.indexerid}" data-season="${season}" data-episode="${episode}">
    
        <table id="showTable" class="displayShowTable display_show tablesorter tablesorter-default hasSaveSort hasStickyHeaders" cellspacing="1" border="0" cellpadding="0">
            <tbody class="tablesorter-no-sort" aria-live="polite" aria-relevant="all">
            <tr style="height: 60px;" role="row">
                <th style="vertical-align: bottom; width: auto;" colspan="10" class="row-seasonheader displayShowTable">
                    <h3 style="display: inline;"><a name="season-${season}" style="position: absolute; font-size: 1px; visibility: hidden;">.</a>Season ${season} Episode ${episode}</h3>
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
                    <th class="col-status">Status</th>
                    <th class="col-search">Download</th>
                </tr>
            </tbody>

            <tbody aria-live="polite" aria-relevant="all">
            % for hItem in sql_results:
                <% provider_img = providers.getProviderClass(GenericProvider.make_id(hItem["provider"])) %>
                <tr id="S${season}E${episode} ${hItem["name"]}" class="skipped season-${season} seasonstyle" role="row">
                    <td class="tvShow" class="col-name" width="35%">${hItem["name"]}</td>
                    <td align="center">${helpers.remove_non_release_groups(hItem["release_group"])}</td>
                    <td align="center">
                        % if provider_img is not None:
                            <img src="${srRoot}/images/providers/${provider_img.image_name()}" width="16" height="16" style="vertical-align:middle;" alt="${hItem["provider"]}" style="cursor: help;" title="${hItem["provider"]}"/> ${hItem["provider"]}
                        % else:
                            <img src="${srRoot}/images/providers/missing.png" width="16" height="16" style="vertical-align:middle;" alt="missing provider" title="missing provider"/> ${hItem["provider"]}
                        % endif
                    </td>
                    <td align="center">${renderQualityPill(int(hItem["quality"]))}</td>
                    <td align="center">${hItem["seeders"] if hItem["seeders"] > -1 else 'N/A'}</td>
                    <td align="center">${hItem["leechers"] if hItem["leechers"] > -1 else 'N/A'}</td>
                    <td align="center">${pretty_file_size(hItem["size"]) if hItem["size"] > -1 else 'N/A'}</td>
                    <td align="center">${provider_img.provider_type.title()}</td>
                    <td align="center">${datetime.datetime.fromtimestamp(hItem["time"]).strftime(sickbeard.DATE_PRESET+" "+sickbeard.TIME_PRESET)}</td>
                    <td align="center" class="col-status">Ignored</td>
                    <td align="center" class="col-search" width="5%"><a class="epManualSnatch" id="${str(show.indexerid)}x${season}x${episode}" name="${str(show.indexerid)}x${season}x${episode}" href="${srRoot}/home/manualSnatchSelect?provider=${hItem["provider_id"]}&amp;rowid=${hItem["rowid"]}&show=${show.indexerid}&amp;season=${season}&amp;episode=${episode}"><img src="${srRoot}/images/download.png" width="16" height="16" alt="search" title="Download selected episode" /></a></td>
                </tr>
            % endfor
            </tbody>
        </table>
    </div>
    </div>
</%block>
