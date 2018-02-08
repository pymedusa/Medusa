MEDUSA.manage.episodeStatuses = function() {
    $('.allCheck').on('click', function() {
        var seriesId = $(this).attr('data-indexer-id') + '-' + $(this).attr('data-series-id');
        $('.' + seriesId + '-epcheck').prop('checked', $(this).prop('checked'));
    });

    $('.get_more_eps').on('click', function() {
        var indexerId = $(this).attr('data-indexer-id');
        var indexerName = MEDUSA.config.indexers.indexerIdToName(indexerId);
        var seriesId = $(this).attr('data-series-id');
        var checked = $('#allCheck-' + indexerId + '-' + seriesId).prop('checked');
        var lastRow = $('tr#' + indexerId + '-' + seriesId);
        var clicked = $(this).data('clicked');
        var action = $(this).attr('value');

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
            }, function(data) {
                $.each(data, function(season, eps) {
                    $.each(eps, function(episode, name) {
                        lastRow.after($.makeEpisodeRow(indexerId, seriesId, season, episode, name, checked));
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
