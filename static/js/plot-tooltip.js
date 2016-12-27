$(function() {
    $('.plotInfo').each(function() {
        var match = $(this).attr('id').match(/^plot_info_([\da-z]+)_(\d+)_(\d+)$/);
        // http://localhost:8081/api/v2/show/tvdb83462/s01e01/description?api_key=xxx
        $(this).qtip({
            content: {
                text: function(event, qt) {
                    api.get('show/' + match[1] + '/s' + match[2] + 'e' + match[3] + '/description').then(function(response) {
                        // Set the tooltip content upon successful retrieval
                        qt.set('content.text', response.data);
                    }, function(xhr, status, error) {
                        // Upon failure... set the tooltip content to the status and error value
                        qt.set('content.text', status + ': ' + error);
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
