$(() => {
    $('.title a').each(function() {
        const indexerName = $(this).parent().attr('data-indexer-name');
        const showId = $(this).parent().attr('data-show-id');
        $(this).qtip({
            content: {
                text: 'Loading...',
                ajax: {
                    url: 'home/sceneExceptions',
                    type: 'GET',
                    data: {
                        indexername: indexerName,
                        showid: showId
                    },
                    success(data) {
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
