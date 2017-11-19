
const MEDUSA = require('../core');

MEDUSA.manage.subtitleMissedPP = function() {
    startAjaxEpisodeSubtitles(); // eslint-disable-line no-undef
    $.ajaxEpSubtitlesSearch();

    $('#releasesPP:has(tbody tr)').tablesorter({
        sortList: [[3, 1], [0, 0]],
        textExtraction: {
            0: node => $(node).find('a').text().toLowerCase(),
            1: node => $(node).text().toLowerCase(),
            2: node => $(node).find('span').text().toLowerCase(),
            3: node => $(node).find('span').attr('datetime')
        },
        widgets: ['saveSort', 'filter'],
        headers: {
            0: { sorter: 'show' },
            1: { sorter: 'episode' },
            2: { sorter: 'release' },
            3: { sorter: 'realISODate' },
            4: { sorter: false, filter: false }
        },
        widgetOptions: {
            filter_columnFilters: true, // eslint-disable-line camelcase
            filter_hideFilters: true, // eslint-disable-line camelcase
            filter_saveFilters: true, // eslint-disable-line camelcase
            columnSelector_mediaquery: false // eslint-disable-line camelcase
        }
    });
};
