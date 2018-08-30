<%!
    import operator
    from medusa import app, helpers, subtitles, network_timezones
    from medusa.common import SKIPPED, WANTED, ARCHIVED, IGNORED, FAILED, DOWNLOADED
    from medusa.common import Quality, qualityPresets, statusStrings, Overview
    from medusa.helper.common import pretty_file_size
    from medusa.indexers.indexer_api import indexerApi
%>

<%namespace file="/inc_defs.mako" import="renderQualityPill"/>

<div class="row">
    <div id="showtitle" class="col-lg-12" :data-showname="show.title">
        <div>
            <h1 class="title" :data-indexer-name="show.indexer" :data-series-id="show.id[show.indexer]" :id="'scene_exception_' + show.id[show.indexer]">
                <app-link :href="'home/displayShow?indexername=' + show.indexer + '&seriesid=' + show.id[show.indexer]" class="snatchTitle">{{ show.title }}</app-link>
            </h1>
        </div>

        <div v-if="$route.name === 'snatchSelection'" id="show-specials-and-seasons" class="pull-right">
            <span class="h2footer display-specials">
                Manual search for:<br>
                <app-link href="home/displayShow?indexername=${show.indexer_name}&seriesid=${show.series_id}" class="snatchTitle">{{ show.title }}</app-link> / Season {{ season }}<template v-if="episode"> Episode {{ episode }}</template>
            </span>
        </div>
        <template v-if="$route.name !== 'snatchSelection' && show.seasons && show.seasons.length >= 1">
            <div id="show-specials-and-seasons" class="pull-right">
                <span class="h2footer display-specials" v-if="show.seasons.find(({ season }) => season === 0)">
                    Display Specials: <a @click="toggleSpecials()" class="inner" style="cursor: pointer;">{{ config.layout.show.specials ? 'Hide' : 'Show' }}</a>
                </span>

                <div class="h2footer display-seasons clear">
                    <span>
                        <template v-if="show.seasons && show.seasons.length >= 13">
                            <select @change="jumpToSeason($event)" id="seasonJump" class="form-control input-sm" style="position: relative">
                                <option value="jump">Jump to Season</option>
                                <option v-for="season in show.seasons" :value="'#season-' + season.season" :data-season="season.season">
                                    Season {{ season.season === 0 ? 'Specials' : season.season }}
                                </option>
                            </select>
                        </template>
                        <template v-else-if="show.seasons && show.seasons.length >= 1">
                            Season:
                            <template v-for="(season, $index) in reverse(show.seasons)">
                                <app-link :href="'#season-' + season[0].season">{{ season[0].season === 0 ? 'Specials' : season[0].season }}</app-link>
                                <slot> </slot>
                                <span v-if="$index !== (show.seasons.length - 1)" class="separator">| </span>
                            </template>
                        </template>
                    </span>
                </div>
            </div>
        </template>
    </div> <!-- end show title -->
</div> <!-- end row showtitle-->

% if show_message:
<div class="row">
    <div class="alert alert-info">
        ${show_message}
    </div>
</div>
% endif

<div id="row-show-summary" class="row">
    <div id="col-show-summary" class="col-md-12">
        <div class="show-poster-container">
            <div class="row">
                <div class="image-flex-container col-md-12">
                    <asset default="images/poster.png" :show-slug="show.id.slug" type="posterThumb" cls="show-image shadow" :link="true"></asset>
                </div>
            </div>
        </div>

        <div class="ver-spacer"></div>

        <div class="show-info-container">
            <div class="row">
                <div class="pull-right col-lg-3 col-md-3 hidden-sm hidden-xs">
                    <asset default="images/banner.png" :show-slug="show.id.slug" type="banner" cls="show-banner pull-right shadow" :link="true"></asset>
                </div>
                <div id="show-rating" class="pull-left col-lg-9 col-md-9 col-sm-12 col-xs-12">
                    <span v-if="show.rating.imdb && show.rating.imdb.rating"
                        class="imdbstars"
                        :qtip-content="show.rating.imdb.rating + ' / 10 Stars<br> ' + show.rating.imdb.votes + ' Votes'"
                    >
                        <span :style="{ width: (Number(show.rating.imdb.rating) * 12) + '%' }"></span>
                    </span>
                    <template v-if="!show.rating.imdb">
                        <span v-if="show.year && show.year.start">({{ show.year.start }}) - {{ show.runtime }} minutes - </span>
                    </template>
                    <template v-else>
                        <template v-if="show.country_codes && show.country_codes.length >= 1 ">
                            <img v-for="country in show.country_codes" src="images/blank.png" :class="['country-flag', 'flag-' + country]" width="16" height="11" style="margin-left: 3px; vertical-align:middle;" />
                        </template>
                        <span>
                        % if show.imdb_info.get('year'):
                            (${show.imdb_info['year']}) -
                        % endif
                            ${show.imdb_info.get('runtimes') or show.runtime} minutes
                        </span>
                        <app-link :href="'http://www.imdb.com/title/' + show.id.imdb" :title="'http://www.imdb.com/title/' + show.id.imdb">
                            <img alt="[imdb]" height="16" width="16" src="images/imdb.png" style="margin-top: -1px; vertical-align:middle;"/>
                        </app-link>
                    </template>
                    <app-link v-if="show.id.trakt" :href="'https://trakt.tv/shows/' + show.id.trakt" :title="'https://trakt.tv/shows/' + show.id.trakt">
                        <img alt="[trakt]" height="16" width="16" src="images/trakt.png" />
                    </app-link>
                    <app-link href="${indexerApi(show.indexer).config['show_url']}${show.indexerid}" title="${indexerApi(show.indexer).config["show_url"] + str(show.indexerid)}">
                        <img alt="${indexerApi(show.indexer).name | h}" height="16" width="16" src="images/${indexerApi(show.indexer).config["icon"]}" style="margin-top: -1px; vertical-align:middle;"/>
                    </app-link>
                 % if xem_numbering or xem_absolute_numbering:
                     <app-link href="http://thexem.de/search?q=${show.name | h}" title="http://thexem.de/search?q-${show.name | h}">
                         <img alt="[xem]" height="16" width="16" src="images/xem.png" style="margin-top: -1px; vertical-align:middle;"/>
                     </app-link>
                 % endif
                    ##  @TODO: Is this meant to use show.title for title but show.id[show.indexer] for href?
                    <app-link :href="'https://fanart.tv/series/' + show.id[show.indexer]" :title="'https://fanart.tv/series/' + show.title"><img alt="[fanart.tv]" height="16" width="16" src="images/fanart.tv.png" class="fanart"/></app-link>
                 </div>
                 <div id="tags" class="pull-left col-lg-9 col-md-9 col-sm-12 col-xs-12">
                     <ul class="tags">
                         % if show.imdb_info.get('genres'):
                             % for imdbgenre in show.imdb_info['genres'].replace('Sci-Fi', 'Science-Fiction').split('|'):
                                 <app-link href="http://www.imdb.com/search/title?count=100&title_type=tv_series&genres=${imdbgenre.lower()}" title="View other popular ${imdbgenre} shows on IMDB."><li>${imdbgenre}</li></app-link>
                             % endfor
                         % elif show.genre:
                             % for genre in show.genre.strip('|').split('|'):
                                 <app-link href="http://trakt.tv/shows/popular/?genres=${genre.lower()}" title="View other popular ${genre} shows on trakt.tv."><li>${genre}</li></app-link>
                             % endfor
                         % endif
                     </ul>
                 </div>
            </div>

            <div class="row">
                <!-- Show Summary -->
                <div id="summary" class="col-md-12">
                    <div id="show-summary" class="${'summaryFanArt' if app.FANART_BACKGROUND else ''} col-lg-9 col-md-8 col-sm-8 col-xs-12">
                        <table class="summaryTable pull-left">
                            <tr v-if="show.plot">
                                <td colspan="2" style="padding-bottom: 15px;">
                                    <truncate @toggle="reflowLayout()" :length="250" clamp="show more..." less="show less..." :text="show.plot"></truncate>
                                </td>
                            </tr>

                            <% allowed_qualities, preferred_qualities = Quality.split_quality(int(show.quality)) %>
                                <tr><td class="showLegend">Quality: </td><td>
                            % if show.quality in qualityPresets:
                                ${renderQualityPill(show.quality)}
                            % else:
                                % if allowed_qualities:
                                    <i>Allowed:</i> ${', '.join([capture(renderQualityPill, x) for x in sorted(allowed_qualities)])}${'<br>' if preferred_qualities else ''}
                                % endif
                                % if preferred_qualities:
                                    <i>Preferred:</i> ${', '.join([capture(renderQualityPill, x) for x in sorted(preferred_qualities)])}
                                % endif
                            % endif
                                </td></tr>
                                <tr v-if="show.network && show.airs"><td class="showLegend">Originally Airs: </td><td>{{ show.airs }} ${"" if network_timezones.test_timeformat(show.airs) else "<font color='#FF0000'><b>(invalid Timeformat)</b></font>"} on {{ show.network }}</td></tr>
                                <tr v-else-if="show.network"><td class="showLegend">Originally Airs: </td><td>{{ show.network }}</td></tr>
                                <tr v-else-if="show.airs"><td class="showLegend">Originally Airs: </td><td>{{ show.airs }} ${"" if network_timezones.test_timeformat(show.airs) else "<font color='#FF0000'><b>(invalid Timeformat)</b></font>"}</td></tr>
                                <tr><td class="showLegend">Show Status: </td><td>{{ show.status }}</td></tr>
                                <tr><td class="showLegend">Default EP Status: </td><td>${statusStrings[show.default_ep_status]}</td></tr>
                            % if showLoc[1]:
                                <tr><td class="showLegend">Location: </td><td>${showLoc[0]}</td></tr>
                            % else:
                                <tr><td class="showLegend"><span style="color: rgb(255, 0, 0);">Location: </span></td><td><span style="color: rgb(255, 0, 0);">${showLoc[0]}</span> (Missing)</td></tr>
                            % endif
                            % if all_scene_exceptions:
                                <tr><td class="showLegend" style="vertical-align: top;">Scene Name:</td><td>${all_scene_exceptions}</td></tr>
                            % endif
                            % if show.show_words().required_words:
                                <tr><td class="showLegend" style="vertical-align: top;">Required Words: </td><td><span class="break-word ${'' if (action == "displayShow") else 'required'}">${', '.join(show.show_words().required_words)}</span></td></tr>
                            % endif
                            % if show.show_words().ignored_words:
                                <tr><td class="showLegend" style="vertical-align: top;">Ignored Words: </td><td><span class="break-word ${'' if (action == "displayShow") else 'ignored'}">${', '.join(show.show_words().ignored_words)}</span></td></tr>
                            % endif
                            % if show.show_words().preferred_words:
                                <tr><td class="showLegend" style="vertical-align: top;">Preferred Words: </td><td><span class="break-word ${'' if (action == "displayShow") else 'preferred'}">${', '.join(show.show_words().preferred_words)}</span></td></tr>
                            % endif
                            % if show.show_words().undesired_words:
                                <tr><td class="showLegend" style="vertical-align: top;">Undesired Words: </td><td><span class="break-word ${'' if (action == "displayShow") else 'undesired'}">${', '.join(show.show_words().undesired_words)}</span></td></tr>
                            % endif
                            % if bwl and bwl.whitelist:
                                <tr>
                                    <td class="showLegend">Wanted Group${"s" if len(bwl.whitelist) > 1 else ""}:</td>
                                    <td>${', '.join(bwl.whitelist)}</td>
                                </tr>
                            % endif
                            % if bwl and bwl.blacklist:
                                <tr>
                                    <td class="showLegend">Unwanted Group${"s" if len(bwl.blacklist) > 1 else ""}:</td>
                                    <td>${', '.join(bwl.blacklist)}</td>
                                </tr>
                            % endif
                            <tr><td class="showLegend">Size:</td><td>${pretty_file_size(helpers.get_size(showLoc[0]))}</td></tr>
                        </table><!-- Option table right -->
                    </div>

                    <!-- Option table right -->
                    <div id="show-status" class="col-lg-3 col-md-4 col-sm-4 col-xs-12 pull-xs-left">
                        <table class="pull-xs-left pull-md-right pull-sm-right pull-lg-right">
                            <% info_flag = subtitles.code_from_code(show.lang) if show.lang else '' %>
                            <tr><td class="showLegend">Info Language:</td><td><img src="images/subtitles/flags/${info_flag}.png" width="16" height="11" alt="${show.lang}" title="${show.lang}" onError="this.onerror=null;this.src='images/flags/unknown.png';"/></td></tr>
                            % if app.USE_SUBTITLES:
                            <tr><td v-if="config.subtitles.enabled" class="showLegend">Subtitles: </td><td><img src="images/${("no16.png", "yes16.png")[bool(show.subtitles)]}" alt="${("N", "Y")[bool(show.subtitles)]}" width="16" height="16" /></td></tr>
                            % endif
                            <tr><td class="showLegend">Season Folders: </td><td><img src="images/${("no16.png", "yes16.png")[bool(show.season_folders or app.NAMING_FORCE_FOLDERS)]}" alt="${("N", "Y")[bool(show.season_folders or app.NAMING_FORCE_FOLDERS)]}" width="16" height="16" /></td></tr>
                            <tr><td class="showLegend">Paused: </td><td><img src="images/${("no16.png", "yes16.png")[bool(show.paused)]}" alt="${("N", "Y")[bool(show.paused)]}" width="16" height="16" /></td></tr>
                            <tr><td class="showLegend">Air-by-Date: </td><td><img src="images/${("no16.png", "yes16.png")[bool(show.air_by_date)]}" alt="${("N", "Y")[bool(show.air_by_date)]}" width="16" height="16" /></td></tr>
                            <tr><td class="showLegend">Sports: </td><td><img src="images/${("no16.png", "yes16.png")[bool(show.is_sports)]}" alt="${("N", "Y")[bool(show.is_sports)]}" width="16" height="16" /></td></tr>
                            <tr><td class="showLegend">Anime: </td><td><img src="images/${("no16.png", "yes16.png")[bool(show.is_anime)]}" alt="${("N", "Y")[bool(show.is_anime)]}" width="16" height="16" /></td></tr>
                            <tr><td class="showLegend">DVD Order: </td><td><img src="images/${("no16.png", "yes16.png")[bool(show.dvd_order)]}" alt="${("N", "Y")[bool(show.dvd_order)]}" width="16" height="16" /></td></tr>
                            <tr><td class="showLegend">Scene Numbering: </td><td><img src="images/${("no16.png", "yes16.png")[bool(show.scene)]}" alt="${("N", "Y")[bool(show.scene)]}" width="16" height="16" /></td></tr>
                        </table>
                     </div> <!-- end of show-status -->
                </div> <!-- end of summary -->
            </div> <!-- end of row -->
        </div> <!-- show-info-container -->
    </div> <!-- end of col -->
</div> <!-- end of row row-show-summary-->

<div id="row-show-episodes-controls" class="row">
    <div id="col-show-episodes-controls" class="col-md-12">
    % if (action == "displayShow"):
        <div class="row key"> <!-- Checkbox filter controls -->
            <div class="col-lg-12" id="checkboxControls">
                <div id="key-padding" class="pull-left top-5">
                    <% total_snatched = ep_counts[Overview.SNATCHED] + ep_counts[Overview.SNATCHED_PROPER] + ep_counts[Overview.SNATCHED_BEST] %>
                    <label for="wanted"><span class="wanted"><input type="checkbox" id="wanted" checked="checked" /> Wanted: <b>${ep_counts[Overview.WANTED]}</b></span></label>
                    <label for="qual"><span class="qual"><input type="checkbox" id="qual" checked="checked" /> Allowed: <b>${ep_counts[Overview.QUAL]}</b></span></label>
                    <label for="good"><span class="good"><input type="checkbox" id="good" checked="checked" /> Preferred: <b>${ep_counts[Overview.GOOD]}</b></span></label>
                    <label for="skipped"><span class="skipped"><input type="checkbox" id="skipped" checked="checked" /> Skipped: <b>${ep_counts[Overview.SKIPPED]}</b></span></label>
                    <label for="snatched"><span class="snatched"><input type="checkbox" id="snatched" checked="checked" /> Snatched: <b>${total_snatched}</b></span></label>
                    <button class="btn-medusa seriesCheck">Select Episodes</button>
                    <button class="btn-medusa clearAll">Clear</button>
                </div>
                <div class="pull-lg-right top-5">
                    <select id="statusSelect" class="form-control form-control-inline input-sm-custom input-sm-smallfont">
                        <option selected value="">Change status to:</option>
                        <% statuses = [WANTED, SKIPPED, IGNORED, DOWNLOADED, ARCHIVED] %>
                        % if app.USE_FAILED_DOWNLOADS:
                            <% statuses.append(FAILED) %>
                        % endif
                        % for cur_status in statuses:
                            <option value="${cur_status}">${statusStrings[cur_status]}</option>
                        % endfor
                    </select>
                    <select id="qualitySelect" class="form-control form-control-inline input-sm-custom input-sm-smallfont">
                        <option selected value="">Change quality to:</option>
                        <% qualities = sorted(Quality.qualityStrings.items(), key=operator.itemgetter(0)) %>
                        % for quality, name in qualities:
                            % if quality not in (Quality.NA, Quality.UNKNOWN):
                                <option value="${quality}">${name}</option>
                            % endif
                        % endfor
                    </select>
                    <input type="hidden" id="series-slug" value="${show.slug}" />
                    <input type="hidden" id="series-id" value="${show.indexerid}" />
                    <input type="hidden" id="indexer" value="${show.indexer}" />
                    <input class="btn-medusa" type="button" id="changeStatus" value="Go" />
                </div>
            </div> <!-- checkboxControls -->
        </div> <!-- end of row -->
    % else:
        <div></div>
    % endif
    </div> <!-- end of col -->
</div> <!-- end of row -->
