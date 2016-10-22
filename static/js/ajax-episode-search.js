var searchStatusUrl = 'home/getManualSearchStatus';
var failedDownload = false;
var qualityDownload = false;
var selectedEpisode = '';
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
    $.each(data.episodes, function(name, ep) {
        // Get td element for current ep
        var loadingImage = 'loading16.gif';
        var queuedImage = 'queued.png';
        var searchImage = 'search16.png';
        var htmlContent = '';
        // Try to get the <a> Element
        var el = $('a[id=' + ep.show + 'x' + ep.season + 'x' + ep.episode + ']');
        var img = el.children('img[data-ep-search]');
        var parent = el.parent();
        if (el) {
            var rSearchTerm = '';
            if (ep.searchstatus.toLowerCase() === 'searching') {
                // el=$('td#' + ep.season + 'x' + ep.episode + '.search img');
                img.prop('title', 'Searching');
                img.prop('alt', 'Searching');
                img.prop('src', 'images/' + loadingImage);
                disableLink(el);
                // Update Status and Quality
                rSearchTerm = /(\w+)\s\((.+?)\)/;
                htmlContent = ep.searchstatus;
            } else if (ep.searchstatus.toLowerCase() === 'queued') {
                // el=$('td#' + ep.season + 'x' + ep.episode + '.search img');
                img.prop('title', 'Queued');
                img.prop('alt', 'queued');
                img.prop('src', 'images/' + queuedImage);
                disableLink(el);
                htmlContent = ep.searchstatus;
            } else if (ep.searchstatus.toLowerCase() === 'finished') {
                // el=$('td#' + ep.season + 'x' + ep.episode + '.search img');
                img.prop('title', 'Searching');
                img.prop('alt', 'searching');
                img.parent().prop('class', 'epRetry');
                img.prop('src', 'images/' + searchImage);
                enableLink(el);

                // Update Status and Quality
                rSearchTerm = /(\w+)\s\((.+?)\)/;
                htmlContent = ep.status.replace(rSearchTerm, "$1" + ' <span class="quality ' + ep.quality + '">' + "$2" + '</span>'); // eslint-disable-line quotes, no-useless-concat
                parent.closest('tr').prop('class', ep.overview + ' season-' + ep.season + ' seasonstyle');
            }
            // update the status column if it exists
            parent.siblings('.col-status').html(htmlContent);
        }
        var elementCompleteEpisodes = $('a[id=forceUpdate-' + ep.show + 'x' + ep.season + 'x' + ep.episode + ']');
        var imageCompleteEpisodes = elementCompleteEpisodes.children('img');
        if (elementCompleteEpisodes) {
            if (ep.searchstatus.toLowerCase() === 'searching') {
                imageCompleteEpisodes.prop('title', 'Searching');
                imageCompleteEpisodes.prop('alt', 'Searching');
                imageCompleteEpisodes.prop('src', 'images/' + loadingImage);
                disableLink(elementCompleteEpisodes);
            } else if (ep.searchstatus.toLowerCase() === 'queued') {
                imageCompleteEpisodes.prop('title', 'Queued');
                imageCompleteEpisodes.prop('alt', 'queued');
                imageCompleteEpisodes.prop('src', 'images/' + queuedImage);
            } else if (ep.searchstatus.toLowerCase() === 'finished') {
                imageCompleteEpisodes.prop('title', 'Forced Search');
                imageCompleteEpisodes.prop('alt', '[search]');
                imageCompleteEpisodes.prop('src', 'images/' + searchImage);
                if (ep.overview.toLowerCase() === 'snatched') {
                    elementCompleteEpisodes.closest('tr').remove();
                } else {
                    enableLink(elementCompleteEpisodes);
                }
            }
        }
    });
}

function checkManualSearches() {
    var pollInterval = 5000;
    var showId = $('#showID').val();
    var url = showId === undefined ? searchStatusUrl : searchStatusUrl + '?show=' + showId;
    $.ajax({
        url: url,
        done: function(data) {
            if (data.episodes) {
                pollInterval = 5000;
            } else {
                pollInterval = 15000;
            }

            updateImages(data);
            // cleanupManualSearches(data);
        },
        error: function() {
            pollInterval = 30000;
        },
        type: 'GET',
        dataType: 'JSON',
        complete: function() {
            setTimeout(checkManualSearches, pollInterval);
        },
        timeout: 15000 // timeout every 15 secs
    });
}

$(document).ready(function() {
    checkManualSearches();
});

(function() {
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

            selectedEpisode = $(this);

            $('#forcedSearchModalFailed').modal('show');
        });

        function forcedSearch() {
            var imageName;
            var imageResult;
            var htmlContent;

            var parent = selectedEpisode.parent();

            // Create var for anchor
            var link = selectedEpisode;

            // Create var for img under anchor and set options for the loading gif
            var img = selectedEpisode.children('img');
            img.prop('title', 'loading');
            img.prop('alt', '');
            img.prop('src', '/images/' + options.loadingImage);

            var url = selectedEpisode.prop('href');

            if (!failedDownload) {
                url = url.replace('retryEpisode', 'searchEpisode');
            }

            // Only pass the down_cur_quality flag when retryEpisode() is called
            if (qualityDownload && url.indexOf('retryEpisode') >= 0) {
                url += '&down_cur_quality=1';
            }

            $.getJSON(url, function(data) {
                // if they failed then just put the red X
                if (data.result.toLowerCase() === 'failure') {
                    imageName = options.noImage;
                    imageResult = 'failed';
                } else {
                    // if the snatch was successful then apply the
                    // corresponding class and fill in the row appropriately
                    imageName = options.loadingImage;
                    imageResult = 'success';
                    // color the row
                    if (options.colorRow) {
                        parent.parent().removeClass('skipped wanted qual good unaired').addClass('snatched');
                    }
                    // applying the quality class
                    var rSearchTerm = /(\w+)\s\((.+?)\)/;
                    htmlContent = data.result.replace(rSearchTerm, '$1 <span class="quality ' + data.quality + '">$2</span>');
                    // update the status column if it exists
                    parent.siblings('.col-status').html(htmlContent);
                    // Only if the queuing was successful, disable the onClick event of the loading image
                    disableLink(link);
                }

                // put the corresponding image as the result of queuing of the manual search
                img.prop('title', imageResult);
                img.prop('alt', imageResult);
                img.prop('height', options.size);
                img.prop('src', 'images/' + imageName);
            });

            // don't follow the link
            return false;
        }

        $('.epSearch').on('click', function(event) {
            event.preventDefault();

            // Check if we have disabled the click
            if ($(this).prop('enableClick') === '0') {
                return false;
            }

            selectedEpisode = $(this);

            // @TODO: Replace this with an easier to read selector
            if ($(this).parent().parent().children('.col-status').children('.quality').length > 0) {
                $('#forcedSearchModalQuality').modal('show');
            } else {
                forcedSearch();
            }
        });

        $('.epManualSearch').on('click', function(event) {
            event.preventDefault();
            var performSearch = '0';
            var showAllResults = '0';

            // @TODO: Omg this disables all the manual snatch icons, when one is clicked
            if ($(this).hasClass('disabled')) {
                return false;
            }

            $('.epManualSearch').addClass('disabled');
            $('.epManualSearch').fadeTo(1, 0.1);

            var url = this.href + '&perform_search=' + performSearch + '&show_all_results=' + showAllResults;
            if (event.shiftKey || event.ctrlKey || event.which === 2) {
                window.open(url, '_blank');
            } else {
                window.location = url;
            }
        });

        $('#forcedSearchModalFailed .btn').on('click', function() {
            failedDownload = ($(this).text().toLowerCase() === 'yes');
            $('#forcedSearchModalQuality').modal('show');
        });

        $('#forcedSearchModalQuality .btn').on('click', function() {
            qualityDownload = ($(this).text().toLowerCase() === 'yes');
            forcedSearch();
        });
    };
})();
