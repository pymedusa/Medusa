MEDUSA.history.index = function() {
    $('#historyTable:has(tbody tr)').tablesorter({
        widgets: ['saveSort', 'zebra', 'filter'],
        sortList: [[0, 1]],
        textExtraction: (function() {
            if ($.isMeta('historyLayout', ['detailed'])) {
                return {
                    // 0: Time 1: Episode 2: Action 3: Provider 4: Quality
                    0: function(node) { return $(node).find('time').attr('datetime'); }, // Time
                    1: function(node) { return $(node).find('a').text(); } // Episode
                };
            }
            return {
                // 0: Time 1: Episode 2: Snatched 3: Downloaded 4: Quality
                0: function(node) { return $(node).find('time').attr('datetime'); }, // Time
                1: function(node) { return $(node).find('a').text(); }, // Episode
                2: function(node) { return $(node).find('img').attr('title') === undefined ? '' : $(node).find('img').attr('title'); }, // Snatched
                3: function(node) { return $(node).find('img').attr('title') === undefined ? '' : $(node).find('img').attr('title'); } // Downloaded
            };
        })(),
        headers: (function() {
            if ($.isMeta('historyLayout', ['detailed'])) {
                return {
                    0: {sorter: 'realISODate'}
                };
            }
            return {
                0: {sorter: 'realISODate'},
                2: {sorter: 'text'}
            };
        })()
    });

    $('#history_limit').on('change', function() {
        window.location.href = $('base').attr('href') + 'history/?limit=' + $(this).val();
    });
};
