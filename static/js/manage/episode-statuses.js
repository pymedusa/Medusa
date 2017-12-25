MEDUSA.manage.episodeStatuses = function() {
    $('.allCheck').on('click', function() {
        var seriesId = $(this).attr('id').split('-')[1];
        $('.' + seriesId + '-epcheck').prop('checked', $(this).prop('checked'));
    });

    $('.get_more_eps').on('click', function() {
        var indexerName = MEDUSA.config.indexer.indexerIdToName($(this).attr('data-indexer-to-name'));
        var seriesId = $(this).attr('id');
        var checked = $('#allCheck-' + seriesId).prop('checked');
        var lastRow = $('tr#' + seriesId);
        var clicked = $(this).data('clicked');
        var action = $(this).attr('value');

        if (clicked) {
            if (action.toLowerCase() === 'collapse') {
                $('table tr').filter('.show-' + seriesId).hide();
                $(this).prop('value', 'Expand');
            } else if (action.toLowerCase() === 'expand') {
                $('table tr').filter('.show-' + seriesId).show();
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
                        lastRow.after($.makeEpisodeRow(seriesId, season, episode, name, checked));
                    });
                });
            });
            $(this).data('clicked', 1);
            $(this).prop('value', 'Collapse');
        }
    });

    // selects all visible episode checkboxes.
    $('.selectAllShows').on('click', function() {
        $('.allCheck').each(function() {
            this.checked = true;
        });
        $('input[class*="-epcheck"]').each(function() {
            this.checked = true;
        });
    });

    // clears all visible episode checkboxes and the season selectors
    $('.unselectAllShows').on('click', function() {
        $('.allCheck').each(function() {
            this.checked = false;
        });
        $('input[class*="-epcheck"]').each(function() {
            this.checked = false;
        });
    });
};
