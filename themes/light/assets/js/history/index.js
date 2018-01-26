MEDUSA.history.index = function() {
    $('#historyTable:has(tbody tr)').tablesorter({
        widgets: ['saveSort', 'zebra', 'filter'],
        sortList: [[0, 1]],
        textExtraction: (function() {
            if ($.isMeta({ layout: 'history' }, ['detailed'])) {
                return {
                    // 0: Time 1: Episode 2: Action 3: Provider 4: Quality
                    0(node) {
                        return $(node).find('time').attr('datetime');
                    },
                    1(node) {
                        return $(node).find('a').text();
                    }
                };
            }
            return {
                // 0: Time 1: Episode 2: Snatched 3: Downloaded 4: Quality
                0(node) {
                    return $(node).find('time').attr('datetime');
                },
                1(node) {
                    return $(node).find('a').text();
                }, // Episode
                2(node) {
                    return $(node).find('img').attr('title') === undefined ? '' : $(node).find('img').attr('title');
                },
                3(node) {
                    return $(node).find('img').attr('title') === undefined ? '' : $(node).find('img').attr('title');
                }
            };
        })(),
        headers: (function() {
            if ($.isMeta({ layout: 'history' }, ['detailed'])) {
                return {
                    0: { sorter: 'realISODate' }
                };
            }
            return {
                0: { sorter: 'realISODate' },
                2: { sorter: 'text' }
            };
        })()
    });

    $('#history_limit').on('change', function() {
        window.location.href = $('base').attr('href') + 'history/?limit=' + $(this).val();
    });

    $('.show-option select[name="layout"]').on('change', function() {
        api.patch('config/main', {
            layout: {
                history: $(this).val()
            }
        }).then(response => {
            log.info(response);
            window.location.reload();
        }).catch(err => {
            log.info(err);
        });
    });
};
