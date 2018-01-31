MEDUSA.manage.subtitleMissed = function() {
    $('.allCheck').on('click', function() {
        var seriesId = $(this).attr('data-indexer-id') + '-' + $(this).attr('data-series-id');
        $('.' + seriesId + '-epcheck').prop('checked', $(this).prop('checked'));
    });

    $('.get_more_eps').on('click', function() {
        var indexerId = $(this).attr('data-indexer-id');
        var seriesId = $(this).attr('data-series-id');
        var checked = $('#allCheck-' + indexerId + '-' + seriesId).prop('checked');
        var lastRow = $('tr#' + indexerId + '-' + seriesId);
        var clicked = $(this).data('clicked');
        var action = $(this).attr('value');

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
            }, function(data) {
                $.each(data, function(season, eps) {
                    $.each(eps, function(episode, data) {
                        lastRow.after($.makeSubtitleRow(indexerId, seriesId, season, episode, data.name, data.subtitles, checked));
                    });
                });
            });
            $(this).data('clicked', 1);
            $(this).prop('value', 'Collapse');
        }
    });

    // Selects all visible episode checkboxes.
    $('.selectAllShows').on('click', function() {
        $('.allCheck').each(function() {
            this.checked = true;
        });
        $('input[class*="-epcheck"]').each(function() {
            this.checked = true;
        });
    });

    // Clears all visible episode checkboxes and the season selectors
    $('.unselectAllShows').on('click', function() {
        $('.allCheck').each(function() {
            this.checked = false;
        });
        $('input[class*="-epcheck"]').each(function() {
            this.checked = false;
        });
    });
};
