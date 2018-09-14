MEDUSA.manage.init = function() {
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
};
