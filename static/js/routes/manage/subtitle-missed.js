const subtitleMissed = () => {
    $('.allCheck').on('click', function() {
        const indexerId = $(this).attr('id').split('-')[1];
        $('.' + indexerId + '-epcheck').prop('checked', $(this).prop('checked'));
    });

    $('.get_more_eps').on('click', function() {
        const indexerId = $(this).attr('id');
        const checked = $('#allCheck-' + indexerId).prop('checked');
        const lastRow = $('tr#' + indexerId);
        const clicked = $(this).data('clicked');
        const action = $(this).attr('value');

        if (clicked) {
            if (action === 'Collapse') {
                $('table tr').filter('.show-' + indexerId).hide();
                $(this).prop('value', 'Expand');
            } else if (action === 'Expand') {
                $('table tr').filter('.show-' + indexerId).show();
                $(this).prop('value', 'Collapse');
            }
        } else {
            $.getJSON('manage/showSubtitleMissed', {
                indexer_id: indexerId, // eslint-disable-line camelcase
                whichSubs: $('#selectSubLang').val()
            }, data => {
                $.each(data, (season, eps) => {
                    $.each(eps, (episode, data) => {
                        lastRow.after($.makeSubtitleRow(indexerId, season, episode, data.name, data.subtitles, checked));
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

module.exports = subtitleMissed;
