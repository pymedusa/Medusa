const MEDUSA = require('../../core');

MEDUSA.manage.init = function() {
    $.makeEpisodeRow = function(indexerId, season, episode, name, checked) { // eslint-disable-line max-params
        return `
            <tr class="${$('#row_class').val()} show-${indexerId}">
            <td class="tableleft" align="center">
                <input type="checkbox" class="${indexerId}-epcheck" name="${indexerId}-${season}x${episode}" ${checked ? ' checked' : ''}></td>
            <td>${season}x${episode}</td>
            <td class="tableright" style="width: 100%">${name}</td>
            </tr>
        `;
    };

    $.makeSubtitleRow = function(indexerId, season, episode, name, subtitles, checked) { // eslint-disable-line max-params
        let row = '';
        row += '<tr class="good show-' + indexerId + '">';
        row += '<td align="center"><input type="checkbox" class="' + indexerId + '-epcheck" name="' + indexerId + '-' + season + 'x' + episode + '"' + (checked ? ' checked' : '') + '></td>';
        row += '<td style="width: 2%;">' + season + 'x' + episode + '</td>';
        if (subtitles.length > 0) {
            row += '<td style="width: 8%;">';
            subtitles = subtitles.split(',');
            subtitles.forEach(subtitle => {
                row += '<img src="images/subtitles/flags/' + subtitle + '.png" width="16" height="11" alt="' + subtitle + '" />&nbsp;';
            });
            row += '</td>';
        } else {
            row += '<td style="width: 8%;">No subtitles</td>';
        }
        row += '<td>' + name + '</td>';
        row += '</tr>';

        return row;
    };
};
