<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import common
    from medusa import app
%>
<%block name="scripts">
<script>
window.app = {};
const startVue = () => {
    window.app = new Vue({
        el: '#vue-wrap',
        metaInfo: {
            title: 'Episode Overview'
        },
        data() {
            return {
                header: 'Episode Overview'
            };
        }
    });
};
</script>
</%block>
<%block name="content">
<div id="content960">
<h1 class="header">{{header}}</h1>
% if not whichStatus or (whichStatus and not ep_counts):
% if whichStatus:
<h2>None of your episodes have status ${common.statusStrings[whichStatus]}</h2>
<br>
% endif
<form action="manage/episodeStatuses" method="get">
Manage episodes with status <select name="whichStatus" class="form-control form-control-inline input-sm">
% for cur_status in [common.SKIPPED, common.SNATCHED, common.WANTED, common.IGNORED] + common.Quality.DOWNLOADED + common.Quality.ARCHIVED:
    %if cur_status not in [common.ARCHIVED, common.DOWNLOADED]:
        <option value="${cur_status}">${common.statusStrings[cur_status]}</option>
    %endif
% endfor
</select>
<input class="btn-medusa btn-inline" type="submit" value="Manage" />
</form>
% else:
<form action="manage/changeEpisodeStatuses" method="post">
<input type="hidden" id="oldStatus" name="oldStatus" value="${whichStatus}" />
<h2>Shows containing ${common.statusStrings[whichStatus]} episodes</h2>
<br>
<%
    if int(whichStatus) in [common.IGNORED, common.SNATCHED, common.SNATCHED_PROPER, common.SNATCHED_BEST] + common.Quality.DOWNLOADED + common.Quality.ARCHIVED:
        row_class = "good"
    else:
        row_class = common.Overview.overviewStrings[int(whichStatus)]
%>
<input type="hidden" id="row_class" value="${row_class}" />
Set checked shows/episodes to <select name="newStatus" class="form-control form-control-inline input-sm">
<%
    statusList = [common.SKIPPED, common.WANTED, common.IGNORED] + common.Quality.DOWNLOADED + common.Quality.ARCHIVED
    # Do not allow setting to bare downloaded or archived!
    statusList.remove(common.DOWNLOADED)
    statusList.remove(common.ARCHIVED)
    if int(whichStatus) in statusList:
        statusList.remove(int(whichStatus))
    if int(whichStatus) in [common.SNATCHED, common.SNATCHED_PROPER, common.SNATCHED_BEST] + common.Quality.ARCHIVED + common.Quality.DOWNLOADED and app.USE_FAILED_DOWNLOADS:
        statusList.append(common.FAILED)
%>
% for cur_status in statusList:
<option value="${cur_status}">${common.statusStrings[cur_status]}</option>
% endfor
</select>
<input class="btn-medusa btn-inline" type="submit" value="Go" />
<div>
    <button type="button" class="btn-medusa btn-xs selectAllShows">Select all</button>
    <button type="button" class="btn-medusa btn-xs unselectAllShows">Clear all</button>
</div>
<br>
<table class="defaultTable manageTable" cellspacing="1" border="0" cellpadding="0">
    % for cur_series in sorted_show_ids:
    <% series_id = str(cur_series[0]) + '-' + str(cur_series[1]) %>
    <tr id="${series_id}">
        <th><input type="checkbox" class="allCheck" data-indexer-id="${cur_series[0]}" data-series-id="${cur_series[1]}" id="allCheck-${series_id}" name="${series_id}-all" checked="checked" /></th>
        <th colspan="2" style="width: 100%; text-align: left;"><app-link indexer-id="${cur_series[0]}" class="whitelink" href="home/displayShow?indexername=indexer-to-name&seriesid=${cur_series[1]}">${show_names[(cur_series[0], cur_series[1])]}</app-link> (${ep_counts[(cur_series[0], cur_series[1])]})
        <input type="button" data-indexer-id="${cur_series[0]}" data-series-id="${cur_series[1]}" class="pull-right get_more_eps btn" id="${series_id}" value="Expand" /></th>
    </tr>
    % endfor
    <tr><td style="padding:0;"></td><td style="padding:0;"></td><td style="padding:0;"></td></tr>
</table>
</form>
% endif
</div>
</%block>
