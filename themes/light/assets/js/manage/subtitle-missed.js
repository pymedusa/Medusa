MEDUSA.manage.subtitleMissed = function() {
    $('.allCheck').on('click', function() {
        const showId = $(this).attr('data-indexer-id') + '-' + $(this).attr('data-show-id');
        $('.' + showId + '-epcheck').prop('checked', $(this).prop('checked'));
    });

    $('.get_more_eps').on('click', function() {
        const indexerId = $(this).attr('data-indexer-id');
        const showId = $(this).attr('data-show-id');
        const checked = $('#allCheck-' + indexerId + '-' + showId).prop('checked');
        const lastRow = $('tr#' + indexerId + '-' + showId);
        const clicked = $(this).data('clicked');
        const action = $(this).attr('value');

        if (clicked) {
            if (action === 'Collapse') {
                $('table tr').filter('.show-' + indexerId + '-' + showId).hide();
                $(this).prop('value', 'Expand');
            } else if (action === 'Expand') {
                $('table tr').filter('.show-' + indexerId + '-' + showId).show();
                $(this).prop('value', 'Collapse');
            }
        } else {
            $.getJSON('manage/showSubtitleMissed', {
                indexer: indexerId, // eslint-disable-line camelcase
                showid: showId, // eslint-disable-line camelcase
                whichSubs: $('#selectSubLang').val()
            }, data => {
                $.each(data, (season, eps) => {
                    $.each(eps, (episode, data) => {
                        lastRow.after($.makeSubtitleRow(indexerId, showId, season, episode, data.name, data.subtitles, checked));
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
