$(document).ready(() => {
    $('.plotInfo').each((index, element) => {
        const match = $(element).attr('id').match(/^plot_info_([\da-z]+)_(\d+)_(\d+)$/);
        // http://localhost:8081/api/v2/series/tvdb83462/episode/s01e01/description?api_key=xxx
        $(element).qtip({
            content: {
                text(event, qt) {
                    api.get('series/' + match[1] + '/episode/s' + match[2] + 'e' + match[3] + '/description').then(response => {
                        // Set the tooltip content upon successful retrieval
                        qt.set('content.text', response.data);
                    }, xhr => {
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
