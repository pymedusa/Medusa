MEDUSA.home.status = function() {
    if (MEDUSA.config.fanartBackground) {
        let asset = 'show/' + $('#showID').attr('value') + '?type=fanart';
        let path = apiRoot + 'asset/' + asset + '&api_key=' + apiKey;
        $.backstretch(path);
        $('.backstretch').css('top',backstretchOffset());
        $('.backstretch').css('opacity', MEDUSA.config.fanartBackgroundOpacity).fadeIn(500);
    }

    function backstretchOffset() {
        var offset = '50px';
        if ($(window).width() < 1281) {
            offset = '50px';
        }
        return offset;
    }

    $('#schedulerStatusTable').tablesorter({
        widgets: ['saveSort', 'zebra'],
        textExtraction: {
            5: function(node) {
                return $(node).data('seconds');
            },
            6: function(node) {
                return $(node).data('seconds');
            }
        },
        headers: {
            5: {
                sorter: 'digit'
            },
            6: {
                sorter: 'digit'
            }
        }
    });
    $('#queueStatusTable').tablesorter({
        widgets: ['saveSort', 'zebra'],
        sortList: [[3, 0], [4, 0], [2, 1]]
    });
};
