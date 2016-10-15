MEDUSA.schedule.index = function() {
    if ($.isMeta('comingEpsLayout', ['list'])) {
        var sortCodes = {
            date: 0,
            show: 2,
            network: 5
        };
        var sort = MEDUSA.config.comingEpsSort;
        var sortList = (sort in sortCodes) ? [[sortCodes[sort], 0]] : [[0, 0]];

        $('#showListTable:has(tbody tr)').tablesorter({
            widgets: ['stickyHeaders', 'filter', 'columnSelector', 'saveSort'],
            sortList: sortList,
            textExtraction: {
                0: function(node) { return $(node).find('time').attr('datetime'); }, // eslint-disable-line brace-style
                1: function(node) { return $(node).find('time').attr('datetime'); }, // eslint-disable-line brace-style
                7: function(node) { return $(node).find('span').text().toLowerCase(); } // eslint-disable-line brace-style
            },
            headers: {
                0: {sorter: 'realISODate'},
                1: {sorter: 'realISODate'},
                2: {sorter: 'loadingNames'},
                4: {sorter: 'loadingNames'},
                7: {sorter: 'quality'},
                8: {sorter: false},
                9: {sorter: false}
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

    if ($.isMeta('comingEpsLayout', ['banner', 'poster'])) {
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
        html: true, // required if content has HTML
        content: '<div id="popover-target"></div>'
    }).on('shown.bs.popover', function() { // bootstrap popover event triggered when the popover opens
        // call this function to copy the column selection code into the popover
        $.tablesorter.columnSelector.attachTo($('#showListTable'), '#popover-target');
    });
};
