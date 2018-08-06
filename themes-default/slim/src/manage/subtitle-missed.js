import $ from 'jquery';

export default () => {
    $('.allCheck').on('click', event => {
        const element = event.currentTarget;
        const seriesId = $(element).attr('data-indexer-id') + '-' + $(element).attr('data-series-id');
        $('.' + seriesId + '-epcheck').prop('checked', $(element).prop('checked'));
    });

    $('.get_more_eps').on('click', event => {
        const element = event.currentTarget;
        const indexerId = $(element).attr('data-indexer-id');
        const seriesId = $(element).attr('data-series-id');
        const checked = $('#allCheck-' + indexerId + '-' + seriesId).prop('checked');
        const lastRow = $('tr#' + indexerId + '-' + seriesId);
        const clicked = $(element).data('clicked');
        const action = $(element).attr('value');

        if (clicked) {
            if (action === 'Collapse') {
                $('table tr').filter('.show-' + indexerId + '-' + seriesId).hide();
                $(element).prop('value', 'Expand');
            } else if (action === 'Expand') {
                $('table tr').filter('.show-' + indexerId + '-' + seriesId).show();
                $(element).prop('value', 'Collapse');
            }
        } else {
            $.getJSON('manage/showSubtitleMissed', {
                indexer: indexerId,
                seriesid: seriesId,
                whichSubs: $('#selectSubLang').val()
            }, data => {
                $.each(data, (season, eps) => {
                    $.each(eps, (episode, data) => {
                        lastRow.after($.makeSubtitleRow(indexerId, seriesId, season, episode, data.name, data.subtitles, checked));
                    });
                });
            });
            $(element).data('clicked', 1);
            $(element).prop('value', 'Collapse');
        }
    });

    // Selects all visible episode checkboxes.
    $('.selectAllShows').on('click', () => {
        $('.allCheck').each((index, element) => {
            element.checked = true;
        });
        $('input[class*="-epcheck"]').each((index, element) => {
            element.checked = true;
        });
    });

    // Clears all visible episode checkboxes and the season selectors
    $('.unselectAllShows').on('click', () => {
        $('.allCheck').each((index, element) => {
            element.checked = false;
        });
        $('input[class*="-epcheck"]').each((index, element) => {
            element.checked = false;
        });
    });
};
