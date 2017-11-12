(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
const searchStatusUrl = 'home/getManualSearchStatus';
let failedDownload = false;
let qualityDownload = false;
let selectedEpisode = '';
PNotify.prototype.options.maxonscreen = 5;

$.fn.forcedSearches = [];

const enableLink = el => {
    el.on('click.disabled', false);
    el.prop('enableClick', '1');
    el.fadeTo('fast', 1);
};

const disableLink = el => {
    el.off('click.disabled');
    el.prop('enableClick', '0');
    el.fadeTo('fast', 0.5);
};

const updateImages = data => {
    $.each(data.episodes, (name, ep) => {
        // Get td element for current ep
        const loadingImage = 'loading16.gif';
        const queuedImage = 'queued.png';
        const searchImage = 'search16.png';
        let htmlContent = '';
        // Try to get the <a> Element
        const el = $('a[id=' + ep.show + 'x' + ep.season + 'x' + ep.episode + ']');
        const img = el.children('img[data-ep-search]');
        const parent = el.parent();
        if (el) {
            let rSearchTerm = '';
            if (ep.searchstatus.toLowerCase() === 'searching') {
                //
                // el=$('td#' + ep.season + 'x' + ep.episode + '.search img');
                img.prop('title', 'Searching');
                img.prop('alt', 'Searching');
                img.prop('src', 'images/' + loadingImage);
                disableLink(el);
                htmlContent = ep.searchstatus;
            } else if (ep.searchstatus.toLowerCase() === 'queued') {
                //
                // el=$('td#' + ep.season + 'x' + ep.episode + '.search img');
                img.prop('title', 'Queued');
                img.prop('alt', 'queued');
                img.prop('src', 'images/' + queuedImage);
                disableLink(el);
                htmlContent = ep.searchstatus;
            } else if (ep.searchstatus.toLowerCase() === 'finished') {
                //
                // el=$('td#' + ep.season + 'x' + ep.episode + '.search img');
                img.prop('title', 'Searching');
                img.prop('alt', 'searching');
                img.parent().prop('class', 'epRetry');
                img.prop('src', 'images/' + searchImage);
                enableLink(el);

                // Update Status and Quality
                rSearchTerm = /(\w+(\s\((\bBest\b|\bProper\b)\))?)\s\((.+?)\)/;
                htmlContent = ep.status.replace(rSearchTerm, "$1" + ' <span class="quality ' + ep.quality + '">' + "$4" + '</span>'); // eslint-disable-line quotes, no-useless-concat
                parent.closest('tr').prop('class', ep.overview + ' season-' + ep.season + ' seasonstyle');
            }
            // Update the status column if it exists
            parent.siblings('.col-status').html(htmlContent);
        }
        const elementCompleteEpisodes = $('a[id=forceUpdate-' + ep.show + 'x' + ep.season + 'x' + ep.episode + ']');
        const imageCompleteEpisodes = elementCompleteEpisodes.children('img');
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
};

const checkManualSearches = () => {
    const showId = $('#series-id').val();
    const url = showId === undefined ? searchStatusUrl : searchStatusUrl + '?show=' + showId;
    let pollInterval = 5000;
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
        //
        // cleanupManualSearches(data);
    });
};

$(document).ready(() => checkManualSearches());

$.ajaxEpSearch = function (options) {
    options = $.extend({}, {
        size: 16,
        colorRow: false,
        loadingImage: 'loading16.gif',
        queuedImage: 'queued.png',
        noImage: 'no16.png',
        yesImage: 'yes16.png'
    }, options);

    $('.epRetry').on('click', function (event) {
        event.preventDefault();

        // Check if we have disabled the click
        if ($(this).prop('enableClick') === '0') {
            return false;
        }

        selectedEpisode = $(this);

        $('#forcedSearchModalFailed').modal('show');
    });

    const forcedSearch = () => {
        const parent = selectedEpisode.parent();
        let imageName;
        let imageResult;
        let htmlContent;

        // Create var for anchor
        const link = selectedEpisode;

        // Create var for img under anchor and set options for the loading gif
        const img = selectedEpisode.children('img');
        img.prop('title', 'loading');
        img.prop('alt', '');
        img.prop('src', 'images/' + options.loadingImage);

        let url = selectedEpisode.prop('href');

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
                // Applying the quality class
                const rSearchTerm = /(\w+)\s\((.+?)\)/;
                htmlContent = data.result.replace(rSearchTerm, '$1 <span class="quality ' + data.quality + '">$2</span>');
                // Update the status column if it exists
                parent.siblings('.col-status').html(htmlContent);
                // Only if the queuing was successful, disable the onClick event of the loading image
                disableLink(link);
            }

            // Put the corresponding image as the result of queuing of the manual search
            img.prop('title', imageResult);
            img.prop('alt', imageResult);
            img.prop('height', options.size);
            img.prop('src', 'images/' + imageName);
        });
        return false;
    };

    $('.epSearch').on('click', function (event) {
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

    $('.epManualSearch').on('click', function (event) {
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

    $('#forcedSearchModalFailed .btn').on('click', function () {
        failedDownload = $(this).text().toLowerCase() === 'yes';
        $('#forcedSearchModalQuality').modal('show');
    });

    $('#forcedSearchModalQuality .btn').on('click', function () {
        qualityDownload = $(this).text().toLowerCase() === 'yes';
        forcedSearch();
    });
};

},{}]},{},[1]);

//# sourceMappingURL=ajax-episode-search.js.map
