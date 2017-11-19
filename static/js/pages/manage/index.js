const MEDUSA = require('../../core');

MEDUSA.manage.index = function() {
    $('.resetsorting').on('click', () => {
        $('table').trigger('filterReset');
    });

    $('#massUpdateTable:has(tbody tr)').tablesorter({
        sortList: [[1, 0]],
        textExtraction: {
            2: node => $(node).find('span').text().toLowerCase(),
            3: node => $(node).find('img').attr('alt'),
            4: node => $(node).find('img').attr('alt'),
            5: node => $(node).find('img').attr('alt'),
            6: node => $(node).find('img').attr('alt'),
            7: node => $(node).find('img').attr('alt'),
            8: node => $(node).find('img').attr('alt'),
            9: node => $(node).find('img').attr('alt')
        },
        widgets: ['zebra', 'filter', 'columnSelector'],
        headers: {
            0: { sorter: false, filter: false },
            1: { sorter: 'showNames' },
            2: { sorter: 'quality' },
            3: { sorter: 'sports' },
            4: { sorter: 'scene' },
            5: { sorter: 'anime' },
            6: { sorter: 'flatfold' },
            7: { sorter: 'paused' },
            8: { sorter: 'subtitle' },
            9: { sorter: 'default_ep_status' },
            10: { sorter: 'status' },
            11: { sorter: false },
            12: { sorter: false },
            13: { sorter: false },
            14: { sorter: false },
            15: { sorter: false },
            16: { sorter: false }
        },
        widgetOptions: {
            columnSelector_mediaquery: false // eslint-disable-line camelcase
        }
    });
    $('#popover').popover({
        placement: 'bottom',
        html: true,
        content: '<div id="popover-target"></div>'
    }).on('shown.bs.popover', () => {
        // Call this function to copy the column selection code into the popover
        window.$.tablesorter.columnSelector.attachTo($('#massUpdateTable'), '#popover-target');
    });
};
