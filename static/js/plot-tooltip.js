$(function() {
    $('.plotInfo').each(function() {
        var match = $(this).attr('id').match(/^plot_info_([\da-z]+)_(\d+)_(\d+)$/);
        // http://localhost:8081/api/v2/series/tvdb83462/episode/s01e01/description?api_key=xxx
        $(this).qtip({
            content: {
                text: function(event, qt) {
                    api.get('series/' + match[1] + '/episode/s' + match[2] + 'e' + match[3] + '/description').then(function(response) {
                        // Set the tooltip content upon successful retrieval
                        qt.set('content.text', response.data);
                    }, function(xhr) {
                        // Upon failure... set the tooltip content to the status and error value
                        qt.set('content.text', 'Error while loading plot: ' + xhr.status + ': ' + xhr.statusText);
                    });
                    return 'Loading...';
                }
            },
            show: {
                solo: true
            },
            position: {
                my: 'left center',
                adjust: {
                    y: -10,
                    x: 2
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
