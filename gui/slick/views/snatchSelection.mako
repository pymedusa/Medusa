<%inherit file="/layouts/main.mako"/>
<%!
    from datetime import datetime
    import urllib
    import ntpath
    import os.path
    import sickbeard
    import time
    from sickbeard import subtitles, sbdatetime, network_timezones, helpers
    import sickbeard.helpers
    from sickbeard.common import SKIPPED, WANTED, UNAIRED, ARCHIVED, IGNORED, FAILED, DOWNLOADED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST
    from sickbeard.common import Quality, qualityPresets, statusStrings, Overview
    from sickbeard.helpers import anon_url
    from sickbeard.show_name_helpers import containsAtLeastOneWord, filterBadReleases
    from sickrage.helper.common import pretty_file_size, episode_num
    from sickbeard.sbdatetime import sbdatetime
    from sickrage.show.History import History
    from sickbeard.failed_history import prepareFailedName
    from sickrage.providers.GenericProvider import GenericProvider
    from sickbeard import providers
    from sickrage.helper.encoding import ek
%>
<%block name="scripts">
<script type="text/javascript" src="/js/lib/jquery.bookmarkscroll.js?${sbPID}"></script>
<script type="text/javascript" src="/js/plotTooltip.js?${sbPID}"></script>
<script type="text/javascript" src="/js/ratingTooltip.js?${sbPID}"></script>
<script type="text/javascript" src="/js/ajaxEpSubtitles.js?${sbPID}"></script>
</%block>
<%block name="content">
<%namespace file="/inc_defs.mako" import="renderQualityPill"/>
<input type="hidden" id="srRoot" value="" />
    <div class="clearfix"></div><!-- div.clearfix //-->
    <div id="showtitle" data-showname="${show.name}">
        <h1 class="title" id="scene_exception_${show.indexerid}">
            <a href="/home/displayShow?show=${show.indexerid}">
                ${show.name}
            </a>
        </h1>
    </div><!-- #showtitle //-->
    <div class="clearfix"></div><!-- div.clearfix //-->
% if show_message:
    <div class="alert alert-info">
        ${show_message}
    </div><!-- .alert .alert-info //-->
% endif
    <div id="posterCol">
        <a href="/showPoster/?show=${show.indexerid}&amp;which=poster" rel="dialog" title="View Poster for ${show.name}">
            <img src="/showPoster/?show=${show.indexerid}&amp;which=poster_thumb" class="tvshowImg" alt=""/>
        </a>
    </div><!-- #posterCol //-->
    <div id="showCol">
        <div id="showinfo">
            % if 'rating' in show.imdb_info:
                <% rating_tip = "{x} / 10 Stars<br />{y} Votes".format(x=show.imdb_info['rating'], y=show.imdb_info['votes']) %>
            <span class="imdbstars" qtip-content="${rating_tip}">
                    ${show.imdb_info['rating']}
            </span><!-- .imdbstars //-->
            % endif
            % if not show.imdbid:
                <span>
                    (${show.startyear}) - ${show.runtime} minutes -
                </span>
            % else:
                % if 'country_codes' in show.imdb_info:
                    % for country in show.imdb_info['country_codes'].split('|'):
                <img src="/images/blank.png" class="country-flag flag-${country}" width="16" height="11" style="margin-left: 3px; vertical-align:middle;" />
                    % endfor
                % endif
                <span>
                % if show.imdb_info.get('year'):
                    (${show.imdb_info['year']}) -
                % endif
                    ${show.imdb_info.get('runtimes') or show.runtime} minutes
                </span>
                <a href="${anon_url('http://www.imdb.com/title/', show.imdbid)}" rel="noreferrer" onclick="window.open(this.href, '_blank'); return false;" title="http://www.imdb.com/title/${show.imdbid}">
                    <img alt="[imdb]" height="16" width="16" src="/images/imdb.png" style="margin-top: -1px; vertical-align:middle;"/>
                </a>
            % endif
                <a href="${anon_url(sickbeard.indexerApi(show.indexer).config['show_url'], show.indexerid)}" onclick="window.open(this.href, '_blank'); return false;" title="${sickbeard.indexerApi(show.indexer).config["show_url"] + str(show.indexerid)}">
                    <img alt="${sickbeard.indexerApi(show.indexer).name}" height="16" width="16" src="/images/${sickbeard.indexerApi(show.indexer).config["icon"]}" style="margin-top: -1px; vertical-align:middle;"/>
                </a>
            % if xem_numbering or xem_absolute_numbering:
                <a href="${anon_url('http://thexem.de/search?q=', show.name)}" rel="noreferrer" onclick="window.open(this.href, '_blank'); return false;" title="http://thexem.de/search?q-${show.name}">
                    <img alt="[xem]" height="16" width="16" src="/images/xem.png" style="margin-top: -1px; vertical-align:middle;"/>
                </a>
            % endif
        </div><!-- #showinfo //-->
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
        </div><!-- #tags //-->
        <div id="summary">
            <table class="summaryTable pull-left">
                <% allowed_qualities, preferred_qualities = Quality.splitQuality(int(show.quality)) %>
                <tr>
                    <td class="showLegend">
                        Quality:
                    </td>
                    <td>
                    % if show.quality in qualityPresets:
                        ${renderQualityPill(show.quality)}
                    % else:
                        % if allowed_qualities:
                        <i>Allowed:</i> ${", ".join([capture(renderQualityPill, x) for x in sorted(allowed_qualities)])}${("", "<br />")[bool(preferred_qualities)]}
                        % endif
                        % if preferred_qualities:
                        <i>Preferred:</i> ${", ".join([capture(renderQualityPill, x) for x in sorted(preferred_qualities)])}
                        % endif
                    % endif
                    </td>
                </tr><!-- Row: Qualities //-->
                <tr>
                    <td class="showLegend">
                        Originally Airs:
                    </td>
                    <td>
                        % if show.airs:
                        ${show.airs}
                            % if not network_timezones.test_timeformat(show.airs):
                        <strong class="warning">(invalid Timeformat)</strong>
                            % endif
                        % endif
                        % if show.network:
                            % if show.airs:
                        on
                            % endif
                        ${show.network}
                        % endif
                    </td>
                </tr><!-- Row: Airing //-->
                <tr>
                    <td class="showLegend">
                        Show Status:
                    </td>
                    <td>
                        ${show.status}
                    </td>
                </tr><!-- Row: Show Status //-->
                <tr>
                    <td class="showLegend">
                        Default EP Status:
                    </td>
                    <td>
                        ${statusStrings[show.default_ep_status]}
                    </td>
                </tr><!-- Row: Ep Status //-->
            % if showLoc[1]:
                <tr>
                    <td class="showLegend">
                        Location:
                    </td>
                    <td>
                        ${showLoc[0]}
                    </td>
                </tr><!-- Row: Location //-->
            % else:
                <tr>
                    <td class="showLegend">
                        <span style="color: rgb(255, 0, 0);">
                            Location:
                        </span>
                    </td>
                    <td>
                        <span style="color: rgb(255, 0, 0);">
                            ${showLoc[0]}
                        </span>
                        (Missing)
                    </td>
                </tr><!-- Row: Location (Missing) //-->
            % endif
            % if show.exceptions:
                <tr>
                    <td class="showLegend" style="vertical-align: top;">
                        Scene Name:
                    </td>
                    <td>
                        ${(show.name, " | ".join(show.exceptions))[show.exceptions != 0]}
                    </td>
                </tr><!-- Row: Scene exceptions //-->
            % endif
            % if require_words:
                <tr>
                    <td class="showLegend" style="vertical-align: top;">
                        Required Words:
                    </td>
                    <td>
                        <span class="break-word required">
                            ${require_words}
                        </span>
                    </td>
                </tr><!-- Row: Required words //-->
            % endif
            % if ignore_words:
                <tr>
                    <td class="showLegend" style="vertical-align: top;">
                        Ignored Words:
                    </td>
                    <td>
                        <span class="break-word ignored">
                                ${ignore_words}
                        </span>
                    </td>
                </tr><!-- Row: Ignored words //-->
            % endif
            % if preferred_words:
                <tr>
                    <td class="showLegend" style="vertical-align: top;">
                        Preferred Words:
                    </td>
                    <td>
                        <span class="break-word preferred">
                            ${preferred_words}
                        </span>
                    </td>
                </tr><!-- Row: Preferred words //-->
            % endif
            % if undesired_words:
                <tr>
                    <td class="showLegend" style="vertical-align: top;">
                        Undesired Words:
                    </td>
                    <td>
                        <span class="break-word undesired">
                            ${undesired_words}
                        </span>
                    </td>
                </tr><!-- Row: Undesired words //-->
            % endif
            % if bwl and bwl.whitelist:
                <tr>
                    <td class="showLegend">
                        Wanted Group${'s' if len(bwl.whitelist) > 1 else ''}:
                    </td>
                    <td>
                        ${', '.join(bwl.whitelist)}
                    </td>
                </tr><!-- Row: Whitelist //-->
            % endif
            % if bwl and bwl.blacklist:
                <tr>
                    <td class="showLegend">
                        Unwanted Group${'s' if len(bwl.blacklist) > 1 else ''}:
                    </td>
                    <td>${', '.join(bwl.blacklist)}</td>
                </tr><!-- Row: Blacklist //-->
            % endif
                <tr>
                    <td class="showLegend">
                        Size:
                    </td>
                    <td>
                        ${pretty_file_size(sickbeard.helpers.get_size(showLoc[0]))}
                    </td>
                </tr><!-- Row: Size //-->
            </table><!-- Table: Summary //-->
            <table style="width:180px; float: right; vertical-align: middle; height: 100%;">
                <%
                    info_flag = subtitles.code_from_code(show.lang) if show.lang else ''
                    yes_img = '<img src="/images/yes16.png" alt="Y" width="16" height="16" />'
                    no_img = '<img src="/images/no16.png" alt="N" width="16" height="16" />'
                %>
                <tr>
                    <td class="showLegend">
                        Info Language:
                    </td>
                    <td>
                        <img src="/images/subtitles/flags/${info_flag}.png" width="16" height="11" alt="${show.lang}" title="${show.lang}" onError="this.onerror=null;this.src='/images/flags/unknown.png';"/>
                    </td>
                </tr><!-- Row: Language //-->
                % if sickbeard.USE_SUBTITLES:
                <tr>
                    <td class="showLegend">
                        Subtitles:
                    </td>
                    <td>
                        ${yes_img if show.subtitles else no_img}
                    </td>
                </tr><!-- Row: Subtitles //-->
                % endif
                <tr>
                    <td class="showLegend">
                        Season Folders:
                    </td>
                    <td>
                        ${yes_img if not show.flatten_folders or sickbeard.NAMING_FORCE_FOLDERS else no_img}
                    </td>
                </tr><!-- Row: Season Folders //-->
                <tr>
                    <td class="showLegend">
                        Paused:
                    </td>
                    <td>
                        ${yes_img if show.paused else no_img}
                    </td>
                </tr><!-- Row: Paused //-->
                <tr>
                    <td class="showLegend">
                        Air-by-Date:
                    </td>
                    <td>
                        ${yes_img if show.air_by_date else no_img}
                    </td>
                </tr><!-- Row: Air by Date //-->
                <tr>
                    <td class="showLegend">
                        Sports:
                    </td>
                    <td>
                        ${yes_img if show.is_sports else no_img}
                    </td>
                </tr><!-- Row: Sports //-->
                <tr>
                    <td class="showLegend">
                        Anime:
                    </td>
                    <td>
                        ${yes_img if show.is_anime else no_img}
                    </td>
                </tr><!-- Row: Anime //-->
                <tr>
                    <td class="showLegend">
                        DVD Order:
                    </td>
                    <td>
                        ${yes_img if show.dvdorder else no_img}
                    </td>
                </tr><!-- Row: DVD Order //-->
                <tr>
                    <td class="showLegend">
                        Scene Numbering:
                    </td>
                    <td>
                        ${yes_img if show.scene else no_img}
                    </td>
                </tr><!-- Row: Scene Numbering //-->
            </table><!-- Table: Configuration //-->
        </div><!-- #summary //-->
    </div><!-- #showCol //-->
    <input class="btn manualSearchButton" type="button" id="reloadResults" value="Reload Results" data-force-search="0" />
    <input class="btn manualSearchButton" type="button" id="reloadResultsForceSearch" value="Force Search" data-force-search="1" />
    <div id="searchNotification"></div><!-- #searchNotification //-->
    <div class="clearfix"></div><!-- .clearfix //-->
    <div id="wrapper" data-history-toggle="hide">
        <div id="container">
        % if episode_history:
            <table id="history" class="displayShowTable display_show tablesorter tablesorter-default hasSaveSort hasStickyHeaders" cellspacing="1" border="0" cellpadding="0">
                <tbody class="tablesorter-no-sort" aria-live="polite" aria-relevant="all">
                    <tr style="height: 60px;" role="row">
                        <th style="vertical-align: bottom; width: auto;" colspan="10" class="row-seasonheader displayShowTable">
                            <h3 style="display: inline;">
                                History
                            </h3>
                            <button id="showhistory" type="button" class="btn btn-xs pull-right" data-toggle="collapse" data-target="#historydata">
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
                        <% status, quality = Quality.splitCompositeStatus(item['action']) %>
                        % if status == DOWNLOADED:
                    <tr style="background-color:rgb(195, 227, 200);!important">
                        % elif status in (SNATCHED, SNATCHED_PROPER, SNATCHED_BEST):
                            <tr style="background-color:rgb(235, 193, 234);!important">
                        % elif status == FAILED:
                            <tr style="background-color:rgb(255, 153, 153);!important">
                        % endif
                    </td>
                    <td align="center">${renderQualityPill(int(hItem["quality"]))}
                        % if hItem["proper_tags"]:
                            <img src="${srRoot}/images/info32.png" width="16" height="16" style="vertical-align:middle;" title="${hItem["proper_tags"].replace('|', ', ')}"/>
                        % endif
                    </td>
                    
                    % if below_minseed:
                        <td align="center"><font color="red">${hItem["seeders"] if hItem["seeders"] > -1 else '-'}</font></td>
                    % else:
                        <td align="center">${hItem["seeders"] if hItem["seeders"] > -1 else '-'}</td>
                    % endif
                % endfor
                </tbody>
            </table>
        </div><!-- #container //-->
    </div><!-- #wrapper //-->
</%block>
