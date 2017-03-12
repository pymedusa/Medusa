MEDUSA.manage.index = function() {
    $('.resetsorting').on('click', function() {
        $('table').trigger('filterReset');
    });

    $('#massUpdateTable:has(tbody tr)').tablesorter({
        sortList: [[1, 0]],
        textExtraction: {
            2: function(node) { return $(node).find('span').text().toLowerCase(); }, // eslint-disable-line brace-style
            3: function(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
            4: function(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
            5: function(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
            6: function(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
            7: function(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
            8: function(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
            9: function(node) { return $(node).find('img').attr('alt'); } // eslint-disable-line brace-style
        },
        widgets: ['zebra', 'filter', 'columnSelector'],
        headers: {
            0: {sorter: false, filter: false},
            1: {sorter: 'showNames'},
            2: {sorter: 'quality'},
            3: {sorter: 'sports'},
            4: {sorter: 'scene'},
            5: {sorter: 'anime'},
            6: {sorter: 'flatfold'},
            7: {sorter: 'paused'},
            8: {sorter: 'subtitle'},
            9: {sorter: 'default_ep_status'},
            10: {sorter: 'status'},
            11: {sorter: false},
            12: {sorter: false},
            13: {sorter: false},
            14: {sorter: false},
            15: {sorter: false},
            16: {sorter: false}
        },
        widgetOptions: {
            columnSelector_mediaquery: false // eslint-disable-line camelcase
        }
    });
    $('#popover').popover({
        placement: 'bottom',
        html: true, // required if content has HTML
        content: '<div id="popover-target"></div>'
    }).on('shown.bs.popover', function() { // bootstrap popover event triggered when the popover opens
        // call this function to copy the column selection code into the popover
        $.tablesorter.columnSelector.attachTo($('#massUpdateTable'), '#popover-target');
    });
};
