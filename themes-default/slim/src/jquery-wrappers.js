const isDevelopment = process.env.NODE_ENV === 'development';
import padStart from 'lodash/padstart';

export {
    addQTip,
    attachImdbTooltip,
    isDevelopment,
    updateSearchIcons
};

/**
 * Attach a jquery qtip to elements with the .imdbstars class.
 */
const attachImdbTooltip = () => {
    $('.imdbstars').qtip({
        content: {
            text() {
                // Retrieve content from custom attribute of the $('.selector') elements.
                return $(this).attr('qtip-content');
            }
        },
        show: {
            solo: true
        },
        position: {
            my: 'right center',
            at: 'center left',
            adjust: {
                y: 0,
                x: -6
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
};

/** 
 * Attach a default qtip to elements with the addQTip class.
 */
const addQTip = () => {
    $('.addQTip').each(function() {
        $(this).css({
            'cursor': 'help', // eslint-disable-line quote-props
            'text-shadow': '0px 0px 0.5px #666'
        });
    
        const my = $(this).data('qtip-my') || 'left center';
        const at = $(this).data('qtip-at') || 'middle right';
    
        $(this).qtip({
            show: {
                solo: true
            },
            position: {
                my,
                at
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
}

/**
 * Start checking for running searches.
 * @param {String} showSlug - Show slug
 * @param {Object} vm - vue instance
 */
const updateSearchIcons = (showSlug, vm) => {
    if ($.fn.updateSearchIconsStarted || !showSlug) {
        return;
    }

    $.fn.updateSearchIconsStarted = true;
    $.fn.forcedSearches = [];

    const enableLink = el => {
        el.disabled = false;
    };

    const disableLink = el => {
        el.disabled = true;
    };

    const updateImages = results => {
        $.each(results, (index, ep) => {
            // Get td element for current ep
            const loadingImage = 'loading16.gif';
            const queuedImage = 'queued.png';
            const searchImage = 'search16.png';

            if (`${ep.indexer_name}${ep.series_id}` !== vm.show.id.slug) {
                return true;
            }

            // Try to get the <a> Element
            const img = vm.$refs[`search-s${padStart(ep.season, 2, '0')}e${padStart(ep.episode, 2, '0')}`];
            if (img) {
                if (ep.searchstatus.toLowerCase() === 'searching') {
                    // El=$('td#' + ep.season + 'x' + ep.episode + '.search img');
                    img.title = 'Searching';
                    img.alt = 'Searching';
                    img.src = 'images/' + loadingImage;
                    disableLink(img);
                } else if (ep.searchstatus.toLowerCase() === 'queued') {
                    // El=$('td#' + ep.season + 'x' + ep.episode + '.search img');
                    img.title = 'Queued';
                    img.alt = 'queued';
                    img.src = 'images/' + queuedImage;
                    disableLink(img);
                } else if (ep.searchstatus.toLowerCase() === 'finished') {
                    // El=$('td#' + ep.season + 'x' + ep.episode + '.search img');
                    img.title = 'Searching';
                    img.alt = 'searching';
                    img.src = 'images/' + searchImage;
                    enableLink(img);
                }
            }

            // // This is used by the schedule page partials. Leaving this here for now. Should work if the updateSearchIcons function
            // // is added to the mount method of the scheduled page.
            // const elementCompleteEpisodes = $('a[id=forceUpdate-' + ep.indexer_id + 'x' + ep.series_id + 'x' + ep.season + 'x' + ep.episode + ']');
            // const imageCompleteEpisodes = elementCompleteEpisodes.children('img');
            // if (elementCompleteEpisodes) {
            //     if (ep.searchstatus.toLowerCase() === 'searching') {
            //         imageCompleteEpisodes.prop('title', 'Searching');
            //         imageCompleteEpisodes.prop('alt', 'Searching');
            //         imageCompleteEpisodes.prop('src', 'images/' + loadingImage);
            //         disableLink(elementCompleteEpisodes);
            //     } else if (ep.searchstatus.toLowerCase() === 'queued') {
            //         imageCompleteEpisodes.prop('title', 'Queued');
            //         imageCompleteEpisodes.prop('alt', 'queued');
            //         imageCompleteEpisodes.prop('src', 'images/' + queuedImage);
            //     } else if (ep.searchstatus.toLowerCase() === 'finished') {
            //         imageCompleteEpisodes.prop('title', 'Forced Search');
            //         imageCompleteEpisodes.prop('alt', '[search]');
            //         imageCompleteEpisodes.prop('src', 'images/' + searchImage);
            //         if (ep.overview.toLowerCase() === 'snatched') {
            //             elementCompleteEpisodes.closest('tr').remove();
            //         } else {
            //             enableLink(elementCompleteEpisodes);
            //         }
            //     }
            // }
        });
    };

    /**
     * Check the search queues / history for current or past searches and update the icons.
     */
    const checkManualSearches = () => {
        let pollInterval = 5000;

        api.get(`search/${showSlug}`)
            .then(response => {
                if (response.data.results && response.data.results.length) {
                    pollInterval = 5000;
                } else {
                    pollInterval = 15000;
                }
                updateImages(response.data.results);
            }).catch(error => {
                console.error(String(error));
                pollInterval = 30000;
            }).finally(() => {
                setTimeout(checkManualSearches, pollInterval);
            })

        // Try to get a indexer name and series id. If we can't get any, we request the manual search status for all shows.
        // const indexerName = $('#indexer-name').val();
        // const seriesId = $('#series-id').val();

        // const url = seriesId === undefined ? searchStatusUrl : searchStatusUrl + '?indexername=' + indexerName + '&seriesid=' + seriesId;
        // $.ajax({
        //     url,
        //     error() {
                
        //     },
        //     type: 'GET',
        //     dataType: 'JSON',
        //     complete() {
        //         setTimeout(checkManualSearches, pollInterval);
        //     },
        //     timeout: 15000 // Timeout every 15 secs
        // }).done(data => {
            
        // });
    }

    checkManualSearches();
}