MEDUSA.manage.episodeStatuses = function() {
    $('.allCheck').on('click', function() {
        const seriesId = $(this).attr('data-indexer-id') + '-' + $(this).attr('data-series-id');
        $('.' + seriesId + '-epcheck').prop('checked', $(this).prop('checked'));
    });

    $('.get_more_eps').on('click', function() {
        const indexerId = $(this).attr('data-indexer-id');
        const indexerName = MEDUSA.config.indexers.indexerIdToName(indexerId);
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
};
