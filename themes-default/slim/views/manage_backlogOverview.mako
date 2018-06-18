<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    from medusa import sbdatetime
    from medusa.common import ARCHIVED, DOWNLOADED, Overview, Quality, qualityPresets, statusStrings
    from medusa.helpers import remove_article
%>
<%block name="scripts">
<script>
window.app = {};
const startVue = () => {
    window.app = new Vue({
        el: '#vue-wrap',
        metaInfo: {
            title: 'Backlog Overview'
        },
        data() {
            return {
                header: 'Backlog Overview'
            };
        }
    });
};
</script>
</%block>
<%block name="content">
<%namespace file="/inc_defs.mako" import="renderQualityPill"/>

<div class="row">
<div id="content-col" class="col-md-12">
    <div class="col-md-12">
        <h1 class="header">{{header}}</h1>
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
            <select id="backlog_period" class="form-control-inline input-sm-custom">
                <option value="all" ${'selected="selected"' if app.BACKLOG_PERIOD == 'all' else ''}>All</option>
                <option value="one_day" ${'selected="selected"' if app.BACKLOG_PERIOD == 'one_day' else ''}>Last 24h</option>
                <option value="three_days" ${'selected="selected"' if app.BACKLOG_PERIOD == 'three_days' else ''}>Last 3 days</option>
                <option value="one_week" ${'selected="selected"' if app.BACKLOG_PERIOD == 'one_week' else ''}>Last 7 days</option>
                <option value="one_month" ${'selected="selected"' if app.BACKLOG_PERIOD == 'one_month' else ''}>Last 30 days</option>
            </select>
        </div>
        <div class="show-option pull-left">Status:
            <select id="backlog_status" class="form-control-inline input-sm-custom">
                <option value="all" ${'selected="selected"' if app.BACKLOG_STATUS == 'all' else ''}>All</option>
                <option value="quality" ${'selected="selected"' if app.BACKLOG_STATUS == 'quality' else ''}>Quality</option>
                <option value="wanted" ${'selected="selected"' if app.BACKLOG_STATUS == 'wanted' else ''}>Wanted</option>
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
                                    &nbsp;&nbsp;&nbsp;&nbsp;<i>Quality:</i>&nbsp;&nbsp;${renderQualityPill(cur_show.quality)}
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
                                    <app-link class="btn-medusa btn-inline editShow" href="manage/editShow?indexername=${cur_show.indexer_name}&seriesid=${cur_show.series_id}"><i class="icon-play-circle icon-white"></i> Edit Show</app-link>
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
                               <i>Allowed:</i>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ${' '.join([capture(renderQualityPill, x) for x in sorted(allowed_qualities)])}${'<br>' if preferred_qualities else ''}
                            </div>
                        % endif
                        % if preferred_qualities:
                            <div class="col-md-12 align-left">
                               <i>Preferred:</i>&nbsp;&nbsp; ${' '.join([capture(renderQualityPill, x) for x in sorted(preferred_qualities)])}
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
                                ${statusStrings[old_status]} ${renderQualityPill(old_quality)}
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
                                <app-link class="epArchive" id="${str(cur_show.indexer)}x${str(cur_show.series_id)}x${str(cur_result['season'])}x${str(cur_result['episode'])}" name="${str(cur_show.series_id)}x${str(cur_result['season'])}x${str(cur_result['episode'])}" href="home/setStatus?indexername=${cur_show.indexer_name}&seriesid=${cur_show.series_id}&eps=${cur_result['season']}x${cur_result['episode']}&status=${ARCHIVED}&direct=1"><img data-ep-archive src="images/archive.png" width="16" height="16" alt="search" title="Archive episode" /></app-link>
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
