$(function() {
    $('.title a').each(function() {
        var indexerName = $(this).parent().attr('data-indexer-name');
        var seriesId = $(this).parent().attr('data-series-id');
        $(this).qtip({
            content: {
                text: 'Loading...',
                ajax: {
                    url: 'home/sceneExceptions',
                    type: 'GET',
                    data: {
                        indexername: indexerName,
                        seriesid: seriesId
                    },
                    success: function(data) {
                        this.set('content.text', data);
                    }
                }
            },
            show: {
                solo: true
            },
            position: {
                my: 'bottom center',
                at: 'top center',
                adjust: {
                    y: 10,
                    x: 0
                }
            },
            style: {
                tip: {
                    corner: true,
                    method: 'polygon'
                },
                classes: 'qtip-rounded qtip-shadow ui-tooltip-sb'
            }
        });
    });
});
