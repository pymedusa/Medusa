PNotify.prototype.options.maxonscreen = 5;

$.fn.forcedSearches = [];

function enableLink(el) {
    el.on('click.disabled', false);
    el.prop('enableClick', '1');
    el.fadeTo('fast', 1);
}

function disableLink(el) {
    el.off('click.disabled');
    el.prop('enableClick', '0');
    el.fadeTo('fast', 0.5);
}

function updateImages(data) {
    $.each(data.episodes, (name, ep) => {
        // Get td element for current ep
        const loadingImage = 'loading16.gif';
        const queuedImage = 'queued.png';
        const searchImage = 'search16.png';
        let htmlContent = '';
        // Try to get the <a> Element
        const el = $('a[id=' + ep.show.indexer + 'x' + ep.show.series_id + 'x' + ep.episode.season + 'x' + ep.episode.episode + ']');
        const img = el.children('img[data-ep-search]');
        const parent = el.parent();
        if (el) {
            if (ep.search.status.toLowerCase() === 'searching') {
                // El=$('td#' + ep.season + 'x' + ep.episode + '.search img');
                img.prop('title', 'Searching');
                img.prop('alt', 'Searching');
                img.prop('src', 'images/' + loadingImage);
                disableLink(el);
                htmlContent = ep.search.status;
            } else if (ep.search.status.toLowerCase() === 'queued') {
                // El=$('td#' + ep.season + 'x' + ep.episode + '.search img');
                img.prop('title', 'Queued');
                img.prop('alt', 'queued');
                img.prop('src', 'images/' + queuedImage);
                disableLink(el);
                htmlContent = ep.search.status;
            } else if (ep.search.status.toLowerCase() === 'finished') {
                // El=$('td#' + ep.season + 'x' + ep.episode + '.search img');
                img.prop('title', 'Searching');
                img.prop('alt', 'searching');
                img.parent().prop('class', 'epRetry');
                img.prop('src', 'images/' + searchImage);
                enableLink(el);

                // Update Status and Quality
                let qualityPill = '';
                if (ep.episode.quality_style !== 'na') {
                    // @FIXME: (sharkykh) This is a hack to get the QualityPill's scoped style to work.
                    const qualityPillScopeId = window.Vue.options.components['quality-pill'].options._scopeId;
                    qualityPill = ' <span ' + qualityPillScopeId + ' class="quality ' + ep.episode.quality_style + '">' + ep.episode.quality_name + '</span>';
                }
                htmlContent = ep.episode.status + qualityPill;
                parent.closest('tr').prop('class', ep.episode.overview + ' season-' + ep.episode.season + ' seasonstyle');
            }
            // Update the status column if it exists
            parent.siblings('.col-status').html(htmlContent);
        }
        const elementCompleteEpisodes = $('a[id=forceUpdate-' + ep.show.indexer + 'x' + ep.show.series_id + 'x' + ep.episode.season + 'x' + ep.episode.episode + ']');
        const imageCompleteEpisodes = elementCompleteEpisodes.children('img');
        if (elementCompleteEpisodes) {
            if (ep.search.status.toLowerCase() === 'searching') {
                imageCompleteEpisodes.prop('title', 'Searching');
                imageCompleteEpisodes.prop('alt', 'Searching');
                imageCompleteEpisodes.prop('src', 'images/' + loadingImage);
                disableLink(elementCompleteEpisodes);
            } else if (ep.search.status.toLowerCase() === 'queued') {
                imageCompleteEpisodes.prop('title', 'Queued');
                imageCompleteEpisodes.prop('alt', 'queued');
                imageCompleteEpisodes.prop('src', 'images/' + queuedImage);
            } else if (ep.search.status.toLowerCase() === 'finished') {
                imageCompleteEpisodes.prop('title', 'Forced Search');
                imageCompleteEpisodes.prop('alt', '[search]');
                imageCompleteEpisodes.prop('src', 'images/' + searchImage);
                if (ep.episode.overview.toLowerCase() === 'snatched') {
                    elementCompleteEpisodes.closest('tr').remove();
                } else {
                    enableLink(elementCompleteEpisodes);
                }
            }
        }
    });
}

function checkManualSearches() {
    let pollInterval = 5000;
    const searchStatusUrl = 'home/getManualSearchStatus';

    // Try to get a indexer name and series id. If we can't get any, we request the manual search status for all shows.
    const indexerName = $('#indexer-name').val();
    const seriesId = $('#series-id').val();

    const url = seriesId === undefined ? searchStatusUrl : searchStatusUrl + '?indexername=' + indexerName + '&seriesid=' + seriesId;
    $.ajax({
        url,
        error() {
            pollInterval = 30000;
        },
        type: 'GET',
        dataType: 'JSON',
        complete() {
            setTimeout(checkManualSearches, pollInterval);
        },
        timeout: 15000 // Timeout every 15 secs
    }).done(data => {
        if (data.episodes) {
            pollInterval = 5000;
        } else {
            pollInterval = 15000;
        }
        updateImages(data);
        // CleanupManualSearches(data);
    });
}

$(document).ready(() => {
    checkManualSearches();
});

$.ajaxEpSearch = function(options) {
    options = $.extend({}, {
        size: 16,
        colorRow: false,
        loadingImage: 'loading16.gif',
        queuedImage: 'queued.png',
        noImage: 'no16.png',
        yesImage: 'yes16.png'
    }, options);

    $('.epRetry').on('click', function(event) {
        event.preventDefault();

        // Check if we have disabled the click
        if ($(this).prop('enableClick') === '0') {
            return false;
        }

        $.selectedEpisode = $(this);

        $('#forcedSearchModalFailed').modal('show');
    });

    function forcedSearch() {
        let imageName;
        let imageResult;
        const failedDownload = false;
        const qualityDownload = false;

        const parent = $.selectedEpisode.parent();

        // Create var for anchor
        const link = $.selectedEpisode;

        // Create var for img under anchor and set options for the loading gif
        const img = $.selectedEpisode.children('img');
        img.prop('title', 'loading');
        img.prop('alt', '');
        img.prop('src', 'images/' + options.loadingImage);

        let url = $.selectedEpisode.prop('href');

        if (!failedDownload) {
            url = url.replace('retryEpisode', 'searchEpisode');
        }

        // Only pass the down_cur_quality flag when retryEpisode() is called
        if (qualityDownload && url.indexOf('retryEpisode') >= 0) {
            url += '&down_cur_quality=1';
        }

        // @TODO: Move to the API
        $.getJSON(url, data => {
            // If they failed then just put the red X
            if (data.result.toLowerCase() === 'failure') {
                imageName = options.noImage;
                imageResult = 'failed';
            } else {
                // If the snatch was successful then apply the
                // corresponding class and fill in the row appropriately
                imageName = options.loadingImage;
                imageResult = 'success';
                // Color the row
                if (options.colorRow) {
                    parent.parent().removeClass('skipped wanted qual good unaired').addClass('snatched');
                }
                // Only if the queuing was successful, disable the onClick event of the loading image
                disableLink(link);
            }

            // Put the corresponding image as the result of queuing of the manual search
            img.prop('title', imageResult);
            img.prop('alt', imageResult);
            img.prop('height', options.size);
            img.prop('src', 'images/' + imageName);
        });

        // Don't follow the link
        return false;
    }

    $('.epSearch').on('click', function(event) {
        event.preventDefault();

        // Check if we have disabled the click
        if ($(this).prop('enableClick') === '0') {
            return false;
        }

        $.selectedEpisode = $(this);

        // @TODO: Replace this with an easier to read selector
        if ($(this).parent().parent().children('.col-status').children('.quality').length > 0) {
            $('#forcedSearchModalQuality').modal('show');
        } else {
            forcedSearch();
        }
    });

    $('.epManualSearch').on('click', function(event) {
        event.preventDefault();

        // @TODO: Omg this disables all the manual snatch icons, when one is clicked
        if ($(this).hasClass('disabled')) {
            return false;
        }

        $('.epManualSearch').addClass('disabled');
        $('.epManualSearch').fadeTo(1, 0.1);

        const url = this.href;
        if (event.shiftKey || event.ctrlKey || event.which === 2) {
            window.open(url, '_blank');
        } else {
            window.location = url;
        }
    });
};
