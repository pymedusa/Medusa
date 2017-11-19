
const MEDUSA = require('../core');
const api = require('../api');

MEDUSA.schedule.index = function() {
    if ($.isMeta({ layout: 'schedule' }, ['list'])) {
        const sortCodes = {
            date: 0,
            show: 2,
            network: 5
        };
        const sort = MEDUSA.config.comingEpsSort;
        const sortList = (sort in sortCodes) ? [[sortCodes[sort], 0]] : [[0, 0]];

        $('#showListTable:has(tbody tr)').tablesorter({
            widgets: ['stickyHeaders', 'filter', 'columnSelector', 'saveSort'],
            sortList,
            textExtraction: {
                0: node => $(node).find('time').attr('datetime'),
                1: node => $(node).find('time').attr('datetime'),
                7: node => $(node).find('span').text().toLowerCase(),
                8: node => $(node).find('a[data-indexer-name]').attr('data-indexer-name')
            },
            headers: {
                0: { sorter: 'realISODate' },
                1: { sorter: 'realISODate' },
                2: { sorter: 'loadingNames' },
                4: { sorter: 'loadingNames' },
                7: { sorter: 'quality' },
                8: { sorter: 'text' },
                9: { sorter: false }
            },
            widgetOptions: {
                filter_columnFilters: true, // eslint-disable-line camelcase
                filter_hideFilters: true, // eslint-disable-line camelcase
                filter_saveFilters: true, // eslint-disable-line camelcase
                columnSelector_mediaquery: false // eslint-disable-line camelcase
            }
        });

        $.ajaxEpSearch();
    }

    if ($.isMeta({ layout: 'schedule' }, ['banner', 'poster'])) {
        $.ajaxEpSearch({
            size: 16,
            loadingImage: 'loading16' + MEDUSA.config.themeSpinner + '.gif'
        });
        $('.ep_summary').hide();
        $('.ep_summaryTrigger').on('click', function() {
            $(this).next('.ep_summary').slideToggle('normal', function() {
                $(this).prev('.ep_summaryTrigger').prop('src', function(i, src) {
                    return $(this).next('.ep_summary').is(':visible') ? src.replace('plus', 'minus') : src.replace('minus', 'plus');
                });
            });
        });
    }

    $('#popover').popover({
        placement: 'bottom',
        html: true,
        content: '<div id="popover-target"></div>'
    }).on('shown.bs.popover', () => {
        // call this function to copy the column selection code into the popover
        window.$.tablesorter.columnSelector.attachTo($('#showListTable'), '#popover-target');
    });

    $('.show-option select[name="layout"]').on('change', function() {
        api.patch('config/main', {
            layout: {
                schedule: $(this).val()
            }
        }).then(response => {
            log.info(response);
            window.location.reload();
        }).catch(err => {
            log.info(err);
        });
    });
};
