MEDUSA.history.index = function() {
    $('#historyTable:has(tbody tr)').tablesorter({
        widgets: ['saveSort', 'zebra', 'filter'],
        sortList: [[0, 1]],
        textExtraction: (function() {
            if ($.isMeta('HISTORY_LAYOUT', ['detailed'])) {
                return {
                    0: function(node) { return $(node).find('time').attr('datetime'); }, // eslint-disable-line brace-style
                    4: function(node) { return $(node).find('span').text().toLowerCase(); } // eslint-disable-line brace-style
                };
            }
            return {
                0: function(node) { return $(node).find('time').attr('datetime'); }, // eslint-disable-line brace-style
                1: function(node) { return $(node).find('span').text().toLowerCase(); }, // eslint-disable-line brace-style
                2: function(node) { return $(node).attr('provider') === null ? null : $(node).attr('provider').toLowerCase(); }, // eslint-disable-line brace-style
                5: function(node) { return $(node).attr('quality').toLowerCase(); } // eslint-disable-line brace-style
            };
        })(),
        headers: (function() {
            if ($.isMeta('HISTORY_LAYOUT', ['detailed'])) {
                return {
                    0: {sorter: 'realISODate'},
                    4: {sorter: 'quality'}
                };
            }
            return {
                0: {sorter: 'realISODate'},
                4: {sorter: 'title'},
                5: {sorter: 'quality'}
            };
        })()
    });

    $('#history_limit').on('change', function() {
        window.location.href = 'history/?limit=' + $(this).val();
    });
};
