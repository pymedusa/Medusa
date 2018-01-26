MEDUSA.manage.init = function() {
    $.makeEpisodeRow = function(indexerId, seriesId, season, episode, name, checked) { // eslint-disable-line max-params
        let row = '';
        const series = indexerId + '-' + seriesId;

        row += ' <tr class="' + $('#row_class').val() + ' show-' + series + '">';
        row += '  <td class="tableleft" align="center"><input type="checkbox" class="' + series + '-epcheck" name="' + series + '-' + season + 'x' + episode + '"' + (checked ? ' checked' : '') + '></td>';
        row += '  <td>' + season + 'x' + episode + '</td>';
        row += '  <td class="tableright" style="width: 100%">' + name + '</td>';
        row += ' </tr>';

        return row;
    };

    $.makeSubtitleRow = function(indexerId, seriesId, season, episode, name, subtitles, checked) { // eslint-disable-line max-params
        let row = '';
        const series = indexerId + '-' + seriesId;

        row += '<tr class="good show-' + series + '">';
        row += '<td align="center"><input type="checkbox" class="' + series + '-epcheck" name="' + series + '-' + season + 'x' + episode + '"' + (checked ? ' checked' : '') + '></td>';
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
};
