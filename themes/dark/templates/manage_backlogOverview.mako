<%inherit file="/layouts/main.mako"/>
<%!
    import json

    from medusa import app
    from medusa import sbdatetime
    from medusa.common import ARCHIVED, DOWNLOADED, Overview, Quality, qualityPresets, statusStrings
    from medusa.helpers import remove_article
%>
<%block name="scripts">
<script>
const { mapState } = window.Vuex;

window.app = {};
window.app = new Vue({
    store,
    router,
    el: '#vue-wrap',
    data() {
        return {
        };
    },
    // TODO: Replace with Object spread (`...mapState`)
    computed: Object.assign(mapState({
        layout: state => state.config.layout
    }),
    {
        period: {
            get() {
                return this.layout.backlogOverview.period;
            },
            set(value) {
                const { $store } = this;
                return $store.dispatch('setBacklogOverview', { key: 'period', value })
                       .then(setTimeout(() => location.reload(), 500));
            }
        },
        status: {
            get() {
                return this.layout.backlogOverview.status;
            },
            set(value) {
                const { $store } = this;
                return $store.dispatch('setBacklogOverview', { key: 'status', value })
                       .then(setTimeout(() => location.reload(), 500));
            }
        }
    }),
    methods: {
    },
    mounted() {
        checkForcedSearch();

        function checkForcedSearch() {
            let pollInterval = 5000;
            const searchStatusUrl = 'home/getManualSearchStatus';
            const indexerName = $('#indexer-name').val();
            const seriesId = $('#series-id').val();
            const url = seriesId === undefined ? searchStatusUrl : searchStatusUrl + '?indexername=' + indexerName + '&seriesid=' + seriesId;
            $.ajax({
                url,
                error() {
                    pollInterval = 30000;
                },
                type: 'GET',
                dataType: 'JSON',
                complete() {
                    setTimeout(checkForcedSearch, pollInterval);
                },
                timeout: 15000 // Timeout every 15 secs
            }).done(data => {
                if (data.episodes) {
                    pollInterval = 5000;
                } else {
                    pollInterval = 15000;
                }
                updateForcedSearch(data);
            });
        }

        function updateForcedSearch(data) {
            $.each(data.episodes, (name, ep) => {
                const el = $('a[id=' + ep.show.indexer + 'x' + ep.show.series_id + 'x' + ep.episode.season + 'x' + ep.episode.episode + ']');
                const img = el.children('img[data-ep-search]');
                const episodeStatus = ep.episode.status.toLowerCase();
                const episodeSearchStatus = ep.search.status.toLowerCase();
                if (el) {
                    if (episodeSearchStatus === 'searching' || episodeSearchStatus === 'queued') {
                        // El=$('td#' + ep.season + 'x' + ep.episode + '.search img');
                        img.prop('src', 'images/loading16.gif');
                    } else if (episodeSearchStatus === 'finished') {
                        // El=$('td#' + ep.season + 'x' + ep.episode + '.search img');
                        if (episodeStatus.indexOf('snatched') >= 0) {
                            img.prop('src', 'images/yes16.png');
                            setTimeout(() => {
                                img.parent().parent().parent().remove();
                            }, 3000);
                        } else {
                            img.prop('src', 'images/search16.png');
                        }
                    }
                }
            });
        }

        $('#pickShow').on('change', function() {
            const id = $(this).val();
            if (id) {
                $('html,body').animate({ scrollTop: $('#show-' + id).offset().top - 25 }, 'slow');
            }
        });

        $('.forceBacklog').on('click', function() {
            $.get($(this).attr('href'));
            $(this).text('Searching...');
            return false;
        });

        $('.epArchive').on('click', function(event) {
            event.preventDefault();
            const img = $(this).children('img[data-ep-archive]');
            img.prop('title', 'Archiving');
            img.prop('alt', 'Archiving');
            img.prop('src', 'images/loading16.gif');
            const url = $(this).prop('href');
            $.getJSON(url, data => {
                // If they failed then just put the red X
                if (data.result.toLowerCase() === 'success') {
                    img.prop('src', 'images/yes16.png');
                    setTimeout(() => {
                        img.parent().parent().parent().remove();
                    }, 3000);
                } else {
                    img.prop('src', 'images/no16.png');
                }
                return false;
            });
        });

        $('.epSearch').on('click', function(event) {
            event.preventDefault();
            const img = $(this).children('img[data-ep-search]');
            img.prop('title', 'Searching');
            img.prop('alt', 'Searching');
            img.prop('src', 'images/loading16.gif');
            const url = $(this).prop('href');
            $.getJSON(url, data => {
                // If they failed then just put the red X
                if (data.result.toLowerCase() === 'failed') {
                    img.prop('src', 'images/no16.png');
                }
                return false;
            });
        });
    }
});
</script>
</%block>
<%block name="content">
<div class="row">
<div id="content-col" class="col-md-12">
    <div class="col-md-12">
        <h1 class="header">{{ $route.meta.header }}</h1>
    </div>
</div>

<div class="row">
    <div class="col-md-12">
<%
    def titler(x):
        return (remove_article(x), x)[not x or app.SORT_ARTICLE]

    totalWanted = totalQual = 0
    backLogShows = sorted([x for x in app.showList if x.paused == 0 and
                           showCounts[(x.indexer, x.series_id)][Overview.QUAL] +
                           showCounts[(x.indexer, x.series_id)][Overview.WANTED]],
                          key=lambda x: titler(x.name).lower())
    for cur_show in backLogShows:
        totalWanted += showCounts[(cur_show.indexer, cur_show.series_id)][Overview.WANTED]
        totalQual += showCounts[(cur_show.indexer, cur_show.series_id)][Overview.QUAL]
%>
        <div class="show-option pull-left">Jump to Show:
            <select id="pickShow" class="form-control-inline input-sm-custom">
            % for cur_show in backLogShows:
                <option value="${cur_show.indexer_name}${cur_show.series_id}">${cur_show.name}</option>
            % endfor
            </select>
        </div>
        <div class="show-option pull-left">Period:
            <select v-model="period" id="backlog_period" class="form-control-inline input-sm-custom">
                <option value="all" :selected="period === 'all'">All</option>
                <option value="one_day" :selected="period === 'one_day'">Last 24h</option>
                <option value="three_days" :selected="period === 'three_days'">Last 3 days</option>
                <option value="one_week" :selected="period === 'one_week'">Last 7 days</option>
                <option value="one_month" :selected="period === 'one_month'">Last 30 days</option>
            </select>
        </div>
        <div class="show-option pull-left">Status:
            <select v-model="status" id="backlog_status" class="form-control-inline input-sm-custom">
                <option value="all" :selected="status === 'all'">All</option>
                <option value="quality" :selected="status === 'quality'">Quality</option>
                <option value="wanted" :selected="status === 'wanted'">Wanted</option>
            </select>
        </div>

        <div id="status-summary" class="pull-right">
            <div class="h2footer pull-right">
                % if totalWanted > 0:
                <span class="listing-key wanted">Wanted: <b>${totalWanted}</b></span>
                % endif
                % if totalQual > 0:
                <span class="listing-key qual">Quality: <b>${totalQual}</b></span>
                % endif
            </div>
        </div> <!-- status-summary -->
    </div> <!-- end of col -->
</div> <!-- end of row -->

    <div class="row">
        <div class="col-md-12 horizontal-scroll">
            <table class="defaultTable" cellspacing="0" border="0" cellpadding="0">
            % for cur_show in backLogShows:
                % if not showCounts[(cur_show.indexer, cur_show.series_id)][Overview.WANTED] + showCounts[(cur_show.indexer, cur_show.series_id)][Overview.QUAL]:
                    <% continue %>
                % endif
                <tr class="seasonheader" id="show-${cur_show.indexer_name}${cur_show.series_id}">
                    <td class="row-seasonheader" colspan="5" style="vertical-align: bottom; width: auto;">
                        <div class="col-md-12">
                            <div class="col-md-6 left-30">
                                <h3 style="display: inline;"><app-link href="home/displayShow?indexername=${cur_show.indexer_name}&seriesid=${cur_show.series_id}">${cur_show.name}</app-link></h3>
                                 % if cur_show.quality in qualityPresets:
                                    &nbsp;&nbsp;&nbsp;&nbsp;<i>Quality:</i>&nbsp;&nbsp;<quality-pill :quality="${cur_show.quality}"></quality-pill>
                                 % endif
                            </div>
                            <div class="col-md-6 pull-right right-30">
                                <div class="top-5 bottom-5 pull-right">
                                    % if showCounts[(cur_show.indexer, cur_show.series_id)][Overview.WANTED] > 0:
                                    <span class="listing-key wanted">Wanted: <b>${showCounts[(cur_show.indexer, cur_show.series_id)][Overview.WANTED]}</b></span>
                                    % endif
                                    % if showCounts[(cur_show.indexer, cur_show.series_id)][Overview.QUAL] > 0:
                                    <span class="listing-key qual">Quality: <b>${showCounts[(cur_show.indexer, cur_show.series_id)][Overview.QUAL]}</b></span>
                                    % endif
                                    <app-link class="btn-medusa btn-inline forceBacklog" href="manage/backlogShow?indexername=${cur_show.indexer_name}&seriesid=${cur_show.series_id}"><i class="icon-play-circle icon-white"></i> Force Backlog</app-link>
                                    <app-link class="btn-medusa btn-inline editShow" href="home/editShow?indexername=${cur_show.indexer_name}&seriesid=${cur_show.series_id}"><i class="icon-play-circle icon-white"></i> Edit Show</app-link>
                                </div>
                            </div>
                        </div>
                    </td>
                </tr>
                % if not cur_show.quality in qualityPresets:
                <% allowed_qualities, preferred_qualities = Quality.split_quality(int(cur_show.quality)) %>
                <tr>
                    <td colspan="5" class="backlog-quality">
                        <div class="col-md-12 left-30">
                        % if allowed_qualities:
                            <div class="col-md-12 align-left">
                                <% allowed_as_json = json.dumps(sorted(allowed_qualities)) %>
                                <i>Allowed:</i>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                                <template v-for="curQuality in ${allowed_as_json}">
                                    &nbsp;<quality-pill :quality="curQuality" :key="'${cur_show.indexer_name}${cur_show.series_id}-allowed-' + curQuality"></quality-pill>
                                </template>
                                ${'<br>' if preferred_qualities else ''}
                            </div>
                        % endif
                        % if preferred_qualities:
                            <div class="col-md-12 align-left">
                                <% preferred_as_json = json.dumps(sorted(preferred_qualities)) %>
                                <i>Preferred:</i>&nbsp;&nbsp;
                                <template v-for="curQuality in ${preferred_as_json}">
                                    &nbsp;<quality-pill :quality="curQuality" :key="'${cur_show.indexer_name}${cur_show.series_id}-preferred-' + curQuality"></quality-pill>
                                </template>
                           </div>
                        % endif
                        </div>
                    </td>
                </tr>
                % endif
                <tr class="seasoncols">
                    <th>Episode</th>
                    <th>Status / Quality</th>
                    <th>Episode Title</th>
                    <th class="nowrap">Airdate</th>
                    <th>Actions</th>
                </tr>
                % for cur_result in showSQLResults[(cur_show.indexer, cur_show.series_id)]:
                    <%
                        old_status = cur_result['status']
                        old_quality = cur_result['quality']
                    %>
                    <tr class="seasonstyle ${Overview.overviewStrings[showCats[(cur_show.indexer, cur_show.series_id)][cur_result['episode_string']]]}">
                        <td class="tableleft" align="center">${cur_result['episode_string']}</td>
                        <td class="col-status">
                            % if old_quality != Quality.NA:
                                ${statusStrings[old_status]} <quality-pill :quality="${old_quality}"></quality-pill>
                            % else:
                                ${statusStrings[old_status]}
                            % endif
                        </td>
                        <td class="tableright" align="center" class="nowrap">
                            ${cur_result["name"]}
                        </td>
                        <td>
                            <% show = cur_show %>
                            % if cur_result['airdate']:
                                <time datetime="${cur_result['airdate'].isoformat('T')}" class="date">${sbdatetime.sbdatetime.sbfdatetime(cur_result['airdate'])}</time>
                            % else:
                                Never
                            % endif
                        </td>
                        <td class="col-search">
                            <app-link class="epSearch" id="${str(cur_show.indexer)}x${str(cur_show.series_id)}x${str(cur_result['season'])}x${str(cur_result['episode'])}" name="${str(cur_show.series_id)}x${str(cur_result['season'])}x${str(cur_result['episode'])}" href="home/searchEpisode?indexername=${cur_show.indexer_name}&amp;seriesid=${cur_show.series_id}&amp;season=${cur_result['season']}&amp;episode=${cur_result['episode']}"><img data-ep-search src="images/search16.png" width="16" height="16" alt="search" title="Forced Search" /></app-link>
                            <app-link class="epManualSearch" id="${str(cur_show.indexer)}x${str(cur_show.series_id)}x${str(cur_result['season'])}x${str(cur_result['episode'])}" name="${str(cur_show.series_id)}x${str(cur_result['season'])}x${str(cur_result['episode'])}" href="home/snatchSelection?indexername=${cur_show.indexer_name}&amp;seriesid=${cur_show.series_id}&amp;season=${cur_result['season']}&amp;episode=${cur_result['episode']}"><img data-ep-manual-search src="images/manualsearch.png" width="16" height="16" alt="search" title="Manual Search" /></app-link>
                            % if old_status == DOWNLOADED:
                                <app-link class="epArchive" id="${str(cur_show.indexer)}x${str(cur_show.series_id)}x${str(cur_result['season'])}x${str(cur_result['episode'])}" name="${str(cur_show.series_id)}x${str(cur_result['season'])}x${str(cur_result['episode'])}" href="home/setStatus?indexername=${cur_show.indexer_name}&seriesid=${cur_show.series_id}&eps=s${cur_result['season']}e${cur_result['episode']}&status=${ARCHIVED}&direct=1"><img data-ep-archive src="images/archive.png" width="16" height="16" alt="search" title="Archive episode" /></app-link>
                            % endif
                        </td>
                    </tr>
                % endfor
            % endfor
            </table>
        </div> <!-- end of col-12 -->
    </div> <!-- end of row -->
</div>
</%block>
