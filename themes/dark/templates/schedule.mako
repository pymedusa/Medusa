<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    from medusa.helpers import anon_url
    from medusa.indexers.indexer_api import indexerApi
    from medusa.indexers.utils import indexer_id_to_name, mappings
    from medusa import sbdatetime
    import datetime
    import time
    import re
    import json
%>
<%block name="content">
<%namespace file="/inc_defs.mako" import="renderQualityPill"/>
<input type="hidden" id="background-series-slug" :value="randomSeries" />

<div class="row">
    <div class="col-md-12">
        <h1 class="header">{{header}}</h1>
    </div>
</div>

<div class="row">
    <div class="col-md-12">
        <div class="key pull-left">
        <template v-if="layout !== 'calendar'">
            <b>Key:</b>
            <span class="listing-key listing-overdue">Missed</span>
            <span class="listing-key listing-current">Today</span>
            <span class="listing-key listing-default">Soon</span>
            <span class="listing-key listing-toofar">Later</span>
        </template>
            <a class="btn btn-inline forceBacklog" :href="'webcal://' + medusaHost + ':' + medusaPort + '/calendar'">
            <i class="icon-calendar icon-white"></i>Subscribe</a>
        </div>

        <div class="pull-right">
            <div class="show-option">
                <span>View Paused:
                    <select name="viewpaused" class="form-control form-control-inline input-sm" onchange="location = this.options[this.selectedIndex].value;">
                        <option value="toggleScheduleDisplayPaused" :selected="!displayPaused">Hidden</option>
                        <option value="toggleScheduleDisplayPaused" :selected="displayPaused">Shown</option>
                    </select>
                </span>
            </div>
            <div class="show-option">
                <span>Layout:
                    <select name="layout" class="form-control form-control-inline input-sm">
                        <option value="poster" :selected="layout === 'poster'">Poster</option>
                        <option value="calendar" :selected="layout === 'calendar'">Calendar</option>
                        <option value="banner" :selected="layout === 'banner'">Banner</option>
                        <option value="list" :selected="layout === 'list'">List</option>
                    </select>
                </span>
            </div>
            <div v-if="layout === 'list'" class="show-option">
                <button id="popover" type="button" class="btn btn-inline">Select Columns <b class="caret"></b></button>
            </div>
            <div v-else class="show-option">
                <span>Sort By:
                    <select name="sort" class="form-control form-control-inline input-sm" onchange="location = this.options[this.selectedIndex].value;">
                        <option value="setScheduleSort/?sort=date" :selected="config.comingEpsSort === 'date'">Date</option>
                        <option value="setScheduleSort/?sort=network" :selected="config.comingEpsSort === 'network'">Network</option>
                        <option value="setScheduleSort/?sort=show" :selected="config.comingEpsSort === 'show'">Show</option>
                    </select>
                </span>
            </div>
        </div>
    </div>
</div>

<div class="horizontal-scroll">
<!-- start list view //-->
<table v-if="layout === 'list'" id="showListTable" :class="(fanartBackground ? 'fanartOpacity ' : '') + 'defaultTable tablesorter seasonstyle'" cellspacing="1" border="0" cellpadding="0">
    <thead>
        <tr>
            <th>Airdate ({{timezoneDisplay}})</th>
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
        <tr v-for="episode in episodes" v-if="!displayPaused || displayPaused && !episode.paused" :class="showDiv(episode, 'listing-default')">
            <td align="center" nowrap="nowrap" class="triggerhighlight">
                ## <% airDate = sbdatetime.sbdatetime.convert_to_setting(cur_result['localtime']) %>
                ## <time datetime="${airDate.isoformat('T')}" class="date">${sbdatetime.sbdatetime.sbfdatetime(airDate)}</time>
                <time :datetime="episode.localtime" class="date">{{episode.localtime}}</time>
            </td>
            <td align="center" nowrap="nowrap" class="triggerhighlight">
                ## <% ends = sbdatetime.sbdatetime.convert_to_setting(cur_ep_enddate) %>
                ## <time datetime="${ends.isoformat('T')}" class="date">${sbdatetime.sbdatetime.sbfdatetime(ends)}</time>
            </td>
            <td class="tvShow triggerhighlight" nowrap="nowrap">
                <a :href="'home/displayShow?indexername=' + indexerIdToName(episode.indexer) + '&seriesid=' + episode.show_id">{{episode.show_name}}</a>
                <a>{{episode.show_name}}</a>
                <span v-if="episode.paused" class="pause">[paused]</span>
            </td>
            <td nowrap="nowrap" align="center" class="triggerhighlight">
                S{{episode.season | pad}}E{{episode.episode | pad}}
            </td>
            <td class="triggerhighlight">
                <img
                    v-if="episode.description"
                    alt=""
                    src="images/info32.png"
                    height="16"
                    width="16"
                    class="plotInfo"
                    :id="'plot_info_' + indexerIdToName(episode.indexer) + episodeSlug(episode)"
                />
                <img v-else alt="" src="images/info32.png" width="16" height="16" class="plotInfoNone"  />
                {{episode.name}}
            </td>
            <td align="center" class="triggerhighlight">
                {{episode.network}}
            </td>
            <td align="center" class="triggerhighlight">
            ## ${run_time}min
            </td>
            <td align="center" class="triggerhighlight">
                ## ${renderQualityPill(cur_result['quality'], showTitle=True)}
            </td>
            <td align="center" style="vertical-align: middle;" class="triggerhighlight">
            <template v-if="episode.imdb_id">
                <a @click.prevent="anonRedirect('http://www.imdb.com/title/' + episode.imdb_id)" rel="noreferrer" :title="'http://www.imdb.com/title/' + episode.imdb_id">
                    <img alt="[imdb]" height="16" width="16" src="images/imdb.png" />
                </a>
            </template>
                <a
                    @click.prevent="anonRedirect(indexerById(episode.indexer).show_url + episode.showid)"
                    :data-indexer-name="indexerById(episode.indexer).name"
                    rel="noreferrer"
                    onclick="window.open(this.href, '_blank'); return false"
                    :title="indexerById(episode.indexer).show_url + episode.showid"
                >
                    <img :alt="indexerById(episode.indexer).name" height="16" width="16" :src="'images/' + indexerById(episode.indexer).icon" />
                </a>
            </td>
            <td align="center" class="triggerhighlight">
            <a
                class="epSearch"
                :id="'forceUpdate-' + episode.indexer + 'x' + episode.showid + 'x' + episode.season + 'x' + episode.episode"
                :name="'forceUpdate-' + episode.showid + 'x' + episode.season + 'x' + episode.episode"
                :href="'home/searchEpisode?indexername=' + indexerIdToName(episode.indexer) + '&seriesid=' + episode.showid + '&season=' + episode.season + '&episode=' + episode.episode"
            >
                <img data-ep-search src="images/search16.png" width="16" height="16" alt="search" title="Forced Search" />
            </a>
            <a
                class="epManualSearch"
                :id="'forcedSearch-' + episode.indexer + 'x' + episode.showid + 'x' + episode.season + 'x' + episode.episode"
                :name="'forcedSearch-' + episode.showid + 'x' + episode.season + 'x' + episode.episode"
                :href="'home/searchEpisode?indexername=' + indexerIdToName(episode.indexer) + '&seriesid=' + episode.showid + '&season=' + episode.season + '&episode=' + episode.episode + 'manual_search_type=episode'"
            >
                    <img data-ep-manual-search src="images/manualsearch.png" width="16" height="16" alt="search" title="Manual Search" />
            </a>
            </td>
        </tr>
    </tbody>
    <tfoot>
        <tr class="shadow border-bottom">
            <th rowspan="1" colspan="10" align="center">&nbsp;</th>
        </tr>
    </tfoot>
</table>
<!-- end list view //-->
<template v-if="['banner', 'poster'].indexOf(layout) >= 0">
<!-- start non list view //-->
<%
    cur_segment = None
    too_late_header = False
    missed_header = False
    today_header = False
%>

<template v-if="config.comingEpsSort === 'show'">
    <br><br>
</template>
## <%
##     cur_indexer = int(cur_result['indexer'])
##     if bool(cur_result['paused']) and not app.COMING_EPS_DISPLAY_PAUSED:
##         continue
##     run_time = cur_result['runtime']
##     cur_ep_airdate = cur_result['localtime'].date()
##     if run_time:
##         cur_ep_enddate = cur_result['localtime'] + datetime.timedelta(minutes = run_time)
##     else:
##         cur_ep_enddate = cur_result['localtime']
## %>
##     % if app.COMING_EPS_SORT == 'network':
##         <% show_network = ('no network', cur_result['network'])[bool(cur_result['network'])] %>
##         % if cur_segment != show_network:
##             <div>
##                 <h2 class="${'fanartOpacity' if app.FANART_BACKGROUND else ''} network">${show_network}</h2>
##             <% cur_segment = cur_result['network'] %>
##         % endif
##         % if cur_ep_enddate < today:
##             <% show_div = 'ep_listing listing-overdue' %>
##         % elif cur_ep_airdate >= next_week.date():
##             <% show_div = 'ep_listing listing-toofar' %>
##         % elif cur_ep_enddate >= today and cur_ep_airdate < next_week.date():
##             % if cur_ep_airdate == today.date():
##                 <% show_div = 'ep_listing listing-current' %>
##             % else:
##                 <% show_div = 'ep_listing listing-default' %>
##             % endif
##         % endif
##     % elif app.COMING_EPS_SORT == 'date':
##         % if cur_segment != cur_ep_airdate:
##             % if cur_ep_enddate < today and cur_ep_airdate != today.date() and not missed_header:
##                 <h2 class="${'fanartOpacity' if app.FANART_BACKGROUND else ''} day">Missed</h2>
##                 <% missed_header = True %>
##             % elif cur_ep_airdate >= next_week.date() and not too_late_header:
##                 <h2 class="${'fanartOpacity' if app.FANART_BACKGROUND else ''} day">Later</h2>
##                 <% too_late_header = True %>
##             % elif cur_ep_enddate >= today and cur_ep_airdate < next_week.date():
##                 % if cur_ep_airdate == today.date():
##                     <h2 class="${'fanartOpacity' if app.FANART_BACKGROUND else ''} day">${datetime.date.fromordinal(cur_ep_airdate.toordinal()).strftime('%A').decode(app.SYS_ENCODING).capitalize()}<span style="font-size: 14px; vertical-align: top;">[Today]</span></h2>
##                     <% today_header = True %>
##                 % else:
##                     <h2 class="${'fanartOpacity' if app.FANART_BACKGROUND else ''} day">${datetime.date.fromordinal(cur_ep_airdate.toordinal()).strftime('%A').decode(app.SYS_ENCODING).capitalize()}</h2>
##                 % endif
##             % endif
##             <% cur_segment = cur_ep_airdate %>
##         % endif
##         % if cur_ep_airdate == today.date() and not today_header:
##             <div>
##             <h2 class="${'fanartOpacity' if app.FANART_BACKGROUND else ''} day">${datetime.date.fromordinal(cur_ep_airdate.toordinal()).strftime('%A').decode(app.SYS_ENCODING).capitalize()} <span style="font-size: 14px; vertical-align: top;">[Today]</span></h2>
##             <% today_header = True %>
##         % endif
##         % if cur_ep_enddate < today:
##             <% show_div = 'ep_listing listing-overdue' %>
##         % elif cur_ep_airdate >= next_week.date():
##             <% show_div = 'ep_listing listing-toofar' %>
##         % elif cur_ep_enddate >= today and cur_ep_airdate < next_week.date():
##             % if cur_ep_airdate == today.date():
##                 <% show_div = 'ep_listing listing-current' %>
##             % else:
##                 <% show_div = 'ep_listing listing-default'%>
##             % endif
##         % endif
##     % elif app.COMING_EPS_SORT == 'show':
##         % if cur_ep_enddate < today:
##             <% show_div = 'ep_listing listing-overdue listingradius' %>
##         % elif cur_ep_airdate >= next_week.date():
##             <% show_div = 'ep_listing listing-toofar listingradius' %>
##         % elif cur_ep_enddate >= today and cur_ep_airdate < next_week.date():
##             % if cur_ep_airdate == today.date():
##                 <% show_div = 'ep_listing listing-current listingradius' %>
##             % else:
##                 <% show_div = 'ep_listing listing-default listingradius' %>
##             % endif
##         % endif
##     % endif
<template v-for="episode in episodes">
<h2 :class="(fanartBackground ? 'fanartOpacity ' : '') + ' day'">{{getWeekDay(episode.localtime)}} <span style="font-size: 14px; vertical-align: top;">[Today]</span></h2>
<div :class="(fanartBackground ? 'fanartOpacity ' : '') + showDiv(episode, 'listing-default')" :id="'listing-' + episode.showid">
    <div class="tvshowDiv">
        <table width="100%" border="0" cellpadding="0" cellspacing="0">
        <tr>
            <th :class="layout !== 'poster' ? 'nobg' : ''" :rowspan="layout === 'poster' ? 2 : ''" valign="top">
                <a :href="'home/displayShow?indexername=' + indexerIdToName(episode.indexer) + '&seriesid=' + episode.showid">
                    <img alt="" :class="layout === 'banner' ? 'bannerThumb' : 'posterThumb'" :series="episode.series_slug" :asset="layout === 'poster' ? 'posterThumb' : layout"/>
                </a>
            </th>
            ## The fuck is the template below for? It seems to break the episode's next_episode div
## <template v-if="layout === 'banner'">
        </tr>
        <tr>
## </template>
            <td class="next_episode">
                <div class="clearfix">
                    <span class="tvshowTitle">
                        <a :href="'home/displayShow?indexername=' + indexerIdToName(episode.indexer) + '&seriesid=' + episode.showid">
                        <template v-if="episode.paused">
                            <span class="pause">[paused]</span>
                        </template>
                        </a>
                    </span>
                    <span class="tvshowTitleIcons">
                        <a @click.prevent="anonRedirect('http://www.imdb.com/title/' + episode.imdb_id)" rel="noreferrer" :title="'http://www.imdb.com/title/' + episode.imdb_id">
                            <img alt="[imdb]" height="16" width="16" src="images/imdb.png" />
                        </a>
                        ## <a href="${anon_url(indexerApi(cur_indexer).config['show_url'], cur_result['showid'])}" rel="noreferrer" onclick="window.open(this.href, '_blank'); return false" title="${indexerApi(cur_indexer).config['show_url']}"><img alt="${indexerApi(cur_indexer).name}" height="16" width="16" src="images/${indexerApi(cur_indexer).config['icon']}" /></a>
                        ## <a class="epSearch" id="forceUpdate-${cur_result['indexer']}x${cur_result['showid']}x${cur_result['season']}x${cur_result['episode']}" name="forceUpdate-${cur_result['showid']}x${cur_result['season']}x${cur_result['episode']}" href="home/searchEpisode?indexername=${indexer_id_to_name(cur_result['indexer'])}&seriesid=${cur_result['showid']}&amp;season=${cur_result['season']}&amp;episode=${cur_result['episode']}"><img data-ep-search src="images/search16.png" width="16" height="16" alt="search" title="Forced Search" /></a>
                        <a
                            class="epManualSearch"
                            :id="'forcedSearch-' + episode.indexer + 'x' + episodeSlug(episode, 'x')"
                            :name="'forcedSearch-' + episode.indexer + 'x' + episodeSlug(episode, 'x')"
                            :href="'home/snatchSelection?indexername=' + indexerIdToName(episode.indexer) + '&seriesid=' + episode.seriesid + '&season=' + episode.season + '&episode=' + episode.episode + '&manual_search_type=episode'"
                        >
                            <img data-ep-manual-search src="images/manualsearch.png" width="16" height="16" alt="search" title="Manual Search" />
                        </a>
                    </span>
                </div>
                <span class="title">Next Episode:</span> <span>S{{episode.season | pad}}E{{episode.episode | pad}} - {{episode.name}}</span>
                <div class="clearfix">
                    <span class="title">Airs: </span>
                    ## <span class="airdate">${sbdatetime.sbdatetime.sbfdatetime(cur_result['localtime'])}</span>
                    <span v-if="episode.network"> on {{episode.network}}</span>
                </div>
                <div class="clearfix">
                    <span class="title">Quality:</span>
                    ## ${renderQualityPill(cur_result['quality'], showTitle=True)}
                </div>
            ##</td>
        ##</tr>
        ##<tr>
            ##<td style="vertical-align: top;">
                <div>
                <template v-if="episode.description">
                    <span class="title" style="vertical-align:middle;">Plot:</span>
                    <img class="ep_summaryTrigger" src="images/plus.png" height="16" width="16" alt="" title="Toggle Summary" />
                    <div class="ep_summary">{{episode.description}}</div>
                </template>
                <template v-else>
                    <span class="title ep_summaryTriggerNone" style="vertical-align:middle;">Plot:</span>
                    <img class="ep_summaryTriggerNone" src="images/plus.png" height="16" width="16" alt="" />
                </template>
                </div>
            </td>
        </tr>
        </table>
    </div>
</div>
</template>
</template>
<!-- end non list view //-->
<template v-if="layout === 'calendar'">
<div class="calendarWrapper">
    <table
        v-for="(date, index) in dates"
        :class="(config.fanartBackground ? 'fanartOpacity' : '') + 'defaultTable tablesorter calendarTable' + ' cal-' + (index % 2 ? 'even' : 'odd')"
        cellspacing="0"
        border="0"
        cellpadding="0"
    >
        <thead><tr><th>{{isDateSame(date) ? 'Today' : getWeekDay(date)}}</th></tr></thead>
        <tbody>
            <tr v-for="episode in episodes" v-if="(!displayPaused || displayPaused && !episode.paused) && isDateSame(episode.localtime, date)">
                <td class="calendarShow">
                    <div class="poster">
                        <a
                            :title="episode.show_name"
                            :href="'home/displayShow?indexername=' + indexerIdToName(episode.indexer) + '&seriesid=' + episode.showid"
                        >
                            <img alt="" :series="episode.series_slug" asset="posterThumb" />
                        </a>
                    </div>
                    <div class="text">
                        <span class="airtime">
                            ## ${airtime} on {{episode.network}}
                        </span>
                        <span class="episode-title" :title="episode.name">
                            S{{episode.season | pad}}E{{episode.episode | pad}} - {{episode.name}}
                        </span>
                    </div>
                </td>
            </tr>
            <tr v-if="episodesPerDate(date) === 0">
                <td class="calendarShow"><span class="show-status">No shows for this day</span></td>
            </tr>
        </tbody>
    </table>
</div>
<!-- end calender view //-->
</template>
</div>
<div class="clearfix"></div>
</div>
</div>
</%block>
<%block name="scripts">
<%!
    from medusa.indexers.indexer_config import indexerConfig
%>
<%
    def myconverter(o):
        if isinstance(o, datetime.datetime):
            return o.__str__()

    ## Use this to convert python dict to JSON
    episodes = json.dumps(results, default = myconverter)
    indexers = indexerConfig
    for indexer in indexers:
        if 'api_params' in indexers[indexer]:
            del indexers[indexer]['api_params']
    indexers = json.dumps(indexerConfig, default = myconverter)
%>
<script src="js/ajax-episode-search.js"></script>
<script src="js/plot-tooltip.js"></script>
<script src="js/lib/vue.js"></script>
<script src="js/lib/axios.min.js"></script>
<script>
let app;
const startVue = () => {
    app = new Vue({
        el: '#vue-wrap',
        data() {
            const episodes = ${episodes};
            episodes.map(episode => {
                episode.paused = episode.paused === 1;
                return episode;
            });
            return {
                config: MEDUSA.config,
                header: '${header}',
                layout: '${layout}',
                episodes: episodes,
                displayPaused: '${app.COMING_EPS_DISPLAY_PAUSED}' === 'True',
                indexers: ${indexers},
                timezoneDisplay: '${app.TIMEZONE_DISPLAY}',
                medusaHost: '${sbHost}',
                medusaPort: '${sbHttpPort}'
            };
        },
        computed: {
            randomSeries() {
                return this.episodes.length >=1 ? this.episodes[Math.floor(Math.random() * this.episodes.length)]['series_slug'] : '';
            },
            dates() {
                const dates = [];
                for (let i = 0; i < 7; i++) {
                    const now = new Date();
                    dates.push(now.setDate(now.getDate() + i));
                }
                return dates;
            },
            seriesByDate() {
                const dates = this.dates;
                const episodes = this.episodes;
                const later = [];
                dates.map(date => {
                    const episodesToReturn = [];
                    episodes.forEach(episode => {
                        if (this.isDateSame(date, episode.localtime)) {
                            if (episodesToReturn.indexOf(episode) === -1) {
                                return true;
                            }
                        }
                        if (new Date(episode.localtime) >= new Date().setDate(new Date().getDate() + 7)) {
                            if (later.indexOf(episode) === -1) {
                                // Not from a date we need so push to later
                                later.push(episode);
                                return false;
                            }
                        }
                    });
                    return episodesToReturn;
                });
                dates.push(later);
                return dates;
            }
        },
        methods: {
            anonRedirect: function(url) {
                window.open(this.config.anonRedirect + url, '_blank');
            },
            showDiv: function(episode, defaultShowDiv) {
                var millisecondsPerMinute = 60000;
                var millisecondsPerWeek = millisecondsPerMinute * 60 * 24 * 7;
                var today = new Date();
                var nextWeek = new Date(today + millisecondsPerWeek);
                var cur_indexer = Number(episode.indexer);
                var run_time = episode.runtime;
                var cur_ep_airdate = new Date(episode.localtime);
                // @TODO: Not sure what the default should be
                var show_div = defaultShowDiv || '';
                if (run_time) {
                    cur_ep_enddate = new Date(new Date(episode.localtime).valueOf() - (run_time * millisecondsPerMinute));
                    if (cur_ep_enddate < today) {
                        show_div = 'listing-overdue';
                    } else if (cur_ep_airdate >= nextWeek) {
                        show_div = 'listing-toofar';
                    } else if (cur_ep_airdate >= today && cur_ep_airdate < nextWeek) {
                        if (cur_ep_airdate === today) {
                            show_div = 'listing-current';
                        } else {
                            show_div = 'listing-default';
                        }
                    }
                }
                return 'ep_listing ' + show_div;
            },
            indexerIdToName: function(indexer) {
                return this.indexers[indexer].identifier;
            },
            indexerById: function(indexer) {
                return this.indexers[indexer];
            },
            episodeSlug: function(episode, spacer) {
                spacer = spacer || '_';
                return episode.showid + spacer + episode.season + spacer + episode.episode;
            },
            isDateSame: function(oldDate, newDate) {
                if (!newDate) {
                    newDate = new Date();
                }
                return (new Date(oldDate)).setHours(0, 0, 0, 0) === (new Date(newDate)).setHours(0, 0, 0, 0);
            },
            episodesPerDate: function(date) {
                return this.episodes.filter(episode => this.isDateSame(episode.localtime, date)).length;
            },
            getWeekDay: function(date) {
                const weekdays = [
                    'Sunday',
                    'Monday',
                    'Tuesday',
                    'Wednesday',
                    'Thursday',
                    'Friday',
                    'Saturday'
                ];
                return weekdays[new Date(date).getDay()];
            }
        },
        filters: {
            pad: function(n) {
                return (n < 10) ? ('0' + n) : n;
            }
        }
    });
    $('[v-cloak]').removeAttr('v-cloak');
};
</script>
</%block>
