<%inherit file="/layouts/main.mako"/>
<%!
    from medusa.common import Overview, statusStrings, SKIPPED, WANTED, ARCHIVED, IGNORED, FAILED, DOWNLOADED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST
    from medusa import app
%>
<%block name="scripts">
<script>
const { mapGetters } = window.Vuex;

window.app = {};
window.app = new Vue({
    store,
    router,
    el: '#vue-wrap',
    data() {
        return {
        };
    },
    computed: mapGetters(['indexerIdToName']),
    mounted() {
        $.makeEpisodeRow = function(indexerId, seriesId, season, episode, name, checked) { // eslint-disable-line max-params
            let row = '';
            const series = indexerId + '-' + seriesId;

            row += ' <tr class="' + $('#row_class').val() + ' show-' + series + '">';
            row += '  <td class="tableleft" align="center"><input type="checkbox" class="' + series + '-epcheck" name="' + series + '-s' + season + 'e' + episode + '"' + (checked ? ' checked' : '') + '></td>';
            row += '  <td>' + season + 'x' + episode + '</td>';
            row += '  <td class="tableright" style="width: 100%">' + name + '</td>';
            row += ' </tr>';

            return row;
        };

        const { indexerIdToName } = this;

        $('.allCheck').on('click', function() {
            const seriesId = $(this).attr('data-indexer-id') + '-' + $(this).attr('data-series-id');
            $('.' + seriesId + '-epcheck').prop('checked', $(this).prop('checked'));
        });

        $('.get_more_eps').on('click', function() {
            const indexerId = $(this).attr('data-indexer-id');
            const indexerName = indexerIdToName(indexerId);
            const seriesId = $(this).attr('data-series-id');
            const checked = $('#allCheck-' + indexerId + '-' + seriesId).prop('checked');
            const lastRow = $('tr#' + indexerId + '-' + seriesId);
            const clicked = $(this).data('clicked');
            const action = $(this).attr('value');

            if (clicked) {
                if (action.toLowerCase() === 'collapse') {
                    $('table tr').filter('.show-' + indexerId + '-' + seriesId).hide();
                    $(this).prop('value', 'Expand');
                } else if (action.toLowerCase() === 'expand') {
                    $('table tr').filter('.show-' + indexerId + '-' + seriesId).show();
                    $(this).prop('value', 'Collapse');
                }
            } else {
                $.getJSON('manage/showEpisodeStatuses', {
                    indexername: indexerName,
                    seriesid: seriesId, // eslint-disable-line camelcase
                    whichStatus: $('#oldStatus').val()
                }, data => {
                    $.each(data, (season, eps) => {
                        $.each(eps, (episode, name) => {
                            lastRow.after($.makeEpisodeRow(indexerId, seriesId, season, episode, name, checked));
                        });
                    });
                });
                $(this).data('clicked', 1);
                $(this).prop('value', 'Collapse');
            }
        });

        // Selects all visible episode checkboxes.
        $('.selectAllShows').on('click', () => {
            $('.allCheck').each(function() {
                this.checked = true;
            });
            $('input[class*="-epcheck"]').each(function() {
                this.checked = true;
            });
        });

        // Clears all visible episode checkboxes and the season selectors
        $('.unselectAllShows').on('click', () => {
            $('.allCheck').each(function() {
                this.checked = false;
            });
            $('input[class*="-epcheck"]').each(function() {
                this.checked = false;
            });
        });
    }
});
</script>
</%block>
<%block name="content">
<div id="content960">
<h1 class="header">{{ $route.meta.header }}</h1>
% if not whichStatus or (whichStatus and not ep_counts):
    % if whichStatus:
        <h2>None of your episodes have status ${statusStrings[int(whichStatus)]}</h2>
        <br>
    % endif
    <form action="manage/episodeStatuses" method="get">
    Manage episodes with status <select name="whichStatus" class="form-control form-control-inline input-sm">
    % for cur_status in (WANTED, SKIPPED, IGNORED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, DOWNLOADED, ARCHIVED):
        <option value="${cur_status}">${statusStrings[cur_status]}</option>
    % endfor
    </select>
    <input class="btn-medusa btn-inline" type="submit" value="Manage" />
    </form>
% else:
    <form action="manage/changeEpisodeStatuses" method="post">
    <input type="hidden" id="oldStatus" name="oldStatus" value="${whichStatus}" />
    <h2>Shows containing ${statusStrings[int(whichStatus)]} episodes</h2>
    <br>
    <%
        if int(whichStatus) in (IGNORED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, DOWNLOADED, ARCHIVED):
            row_class = "good"
        else:
            row_class = Overview.overviewStrings[int(whichStatus)]
    %>
    <input type="hidden" id="row_class" value="${row_class}" />
    Set checked shows/episodes to <select name="newStatus" class="form-control form-control-inline input-sm">
    <%
        statusList = [WANTED, SKIPPED, IGNORED, DOWNLOADED]
        if int(whichStatus) == DOWNLOADED:
            statusList.append(ARCHIVED)
        if app.USE_FAILED_DOWNLOADS and int(whichStatus) in (SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, DOWNLOADED, ARCHIVED):
            statusList.append(FAILED)
        if int(whichStatus) in statusList:
            statusList.remove(int(whichStatus))
    %>
    % for cur_status in statusList:
        <option value="${cur_status}">${statusStrings[cur_status]}</option>
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
            <input type="button" data-indexer-id="${cur_series[0]}" data-series-id="${cur_series[1]}" class="pull-right get_more_eps btn-medusa" id="${series_id}" value="Expand" /></th>
        </tr>
        % endfor
        <tr><td style="padding:0;"></td><td style="padding:0;"></td><td style="padding:0;"></td></tr>
    </table>
    </form>
% endif
</div>
</%block>
