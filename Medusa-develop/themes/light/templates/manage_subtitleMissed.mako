<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import subtitles
    import datetime
    from medusa import app
    from medusa import common
%>
<%block name="scripts">
<script>
window.app = {};
window.app = new Vue({
    store,
    router,
    el: '#vue-wrap',
    mounted() {
        $.makeSubtitleRow = function(indexerId, seriesId, season, episode, name, subtitles, checked) { // eslint-disable-line max-params
            let row = '';
            const series = indexerId + '-' + seriesId;

            row += '<tr class="good show-' + series + '">';
            row += '<td align="center"><input type="checkbox" class="' + series + '-epcheck" name="' + series + '-' + 's' + season + 'e' + episode + '"' + (checked ? ' checked' : '') + '></td>';
            row += '<td style="width: 2%;">' + season + 'x' + episode + '</td>';
            if (subtitles.length > 0) {
                row += '<td style="width: 8%;">';
                subtitles = subtitles.split(',');
                for (const i in subtitles) {
                    if ({}.hasOwnProperty.call(subtitles, i)) {
                        row += '<img src="images/subtitles/flags/' + subtitles[i] + '.png" width="16" height="11" alt="' + subtitles[i] + '" />&nbsp;';
                    }
                }
                row += '</td>';
            } else {
                row += '<td style="width: 8%;">No subtitles</td>';
            }
            row += '<td>' + name + '</td>';
            row += '</tr>';

            return row;
        };

        $('.allCheck').on('click', function() {
            const seriesId = $(this).attr('data-indexer-id') + '-' + $(this).attr('data-series-id');
            $('.' + seriesId + '-epcheck').prop('checked', $(this).prop('checked'));
        });

        $('.get_more_eps').on('click', function() {
            const indexerId = $(this).attr('data-indexer-id');
            const seriesId = $(this).attr('data-series-id');
            const checked = $('#allCheck-' + indexerId + '-' + seriesId).prop('checked');
            const lastRow = $('tr#' + indexerId + '-' + seriesId);
            const clicked = $(this).data('clicked');
            const action = $(this).attr('value');

            if (clicked) {
                if (action === 'Collapse') {
                    $('table tr').filter('.show-' + indexerId + '-' + seriesId).hide();
                    $(this).prop('value', 'Expand');
                } else if (action === 'Expand') {
                    $('table tr').filter('.show-' + indexerId + '-' + seriesId).show();
                    $(this).prop('value', 'Collapse');
                }
            } else {
                $.getJSON('manage/showSubtitleMissed', {
                    indexer: indexerId, // eslint-disable-line camelcase
                    seriesid: seriesId, // eslint-disable-line camelcase
                    whichSubs: $('#selectSubLang').val()
                }, data => {
                    $.each(data, (season, eps) => {
                        $.each(eps, (episode, data) => {
                            lastRow.after($.makeSubtitleRow(indexerId, seriesId, season, episode, data.name, data.subtitles, checked));
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
    <% subsLanguage = subtitles.name_from_code(whichSubs) if whichSubs and whichSubs != 'all' else 'All' %>
    <% wanted_languages = subtitles.wanted_languages() %>
    <% label = 'all wanted' if subsLanguage == 'All' else str(subsLanguage) + ' (' + str(subtitles.from_code(whichSubs)) + ')' %>
    % if not whichSubs or (whichSubs and not ep_counts):
        % if whichSubs:
        <h2>All of your episodes have ${label} subtitles.</h2>
        <br>
        % endif
        <form action="manage/subtitleMissed" method="get">
            % if app.SUBTITLES_MULTI:
                Manage episodes without <select name="whichSubs" class="form-control form-control-inline input-sm">
                <option value="all">All</option>
                % for sub_code in wanted_languages:
                    <option ${'selected="selected"' if sub_code == whichSubs else ''} value="${sub_code}">${subtitles.name_from_code(sub_code)} (${subtitles.from_code(sub_code)})</option>
                % endfor
                </select>
            % else:
                Manage episodes without <select name="whichSubs" class="form-control form-control-inline input-sm">
                % if not wanted_languages:
                    <option value="all">All</option>
                % else:
                    % for index, sub_code in enumerate(wanted_languages):
                        % if index == 0:
                            <option value="und">${subtitles.name_from_code(sub_code)} (${subtitles.from_code(sub_code)})</option>
                        % endif
                    % endfor
                % endif
                </select>
            % endif
            <input class="btn-medusa" type="submit" value="Manage" />
        </form>
    % else:
        ##Strange that this is used by js but is an input outside of any form?
        <input type="hidden" id="selectSubLang" name="selectSubLang" value="${whichSubs}" />
        <form action="manage/downloadSubtitleMissed" method="post">
            % if app.SUBTITLES_MULTI:
                <% sub_code = '({0}) '.format(whichSubs) if not whichSubs == 'all' else '' %>
                <h2>Episodes without ${label} subtitles.</h2>
            % else:
                % for index, sub_code in enumerate(wanted_languages):
                    % if index == 0:
                        <h2>Episodes without ${subtitles.name_from_code(sub_code)} (undefined) subtitles.</h2>
                    % endif
                % endfor
            % endif
            <br>
            Download missed subtitles for selected episodes <input class="btn-medusa btn-inline" type="submit" value="Go" />
            <div>
                <button type="button" class="btn-medusa btn-xs selectAllShows">Select all</button>
                <button type="button" class="btn-medusa btn-xs unselectAllShows">Clear all</button>
            </div>
            <br>
            <table class="defaultTable manageTable" cellspacing="1" border="0" cellpadding="0">
            % for cur_series in sorted_show_ids:
                <% series_id = str(cur_series[0]) + '-' + str(cur_series[1]) %>
                <tr id="${series_id}">
                    <th style="width: 1%;"><input type="checkbox" class="allCheck" data-indexer-id="${cur_series[0]}" data-series-id="${cur_series[1]}" id="allCheck-${series_id}" name="${series_id}-all"checked="checked" /></th>
                    <th colspan="3" style="text-align: left;"><app-link indexer-id="${cur_series[0]}" class="whitelink" href="home/displayShow?indexername=indexer-to-name&seriesid=${cur_series[1]}">
                    ${show_names[(cur_series[0], cur_series[1])]}</app-link> (${ep_counts[(cur_series[0], cur_series[1])]}) <input type="button" class="pull-right get_more_eps btn-medusa" data-indexer-id="${cur_series[0]}" data-series-id="${cur_series[1]}" id="${series_id}" value="Expand" /></th>
                </tr>
            % endfor
            </table>
        </form>
    % endif
    </div>
</%block>
