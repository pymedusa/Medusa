MEDUSA.home.snatchSelection = function() {
    $(document.body).on('click', '.imdbPlot', event => {
        $(event.currentTarget).prev('span').toggle();
        if ($(event.currentTarget).html() === '..show less') {
            $(event.currentTarget).html('..show more');
        } else {
            $(event.currentTarget).html('..show less');
        }
        moveSummaryBackground();
    });

    // Adjust the summary background position and size on page load and resize
    function moveSummaryBackground() {
        const height = $('#summary').height() + 10;
        const top = $('#summary').offset().top + 5;
        $('#summaryBackground').height(height);
        $('#summaryBackground').offset({ top, left: 0 });
        $('#summaryBackground').show();
    }

    $(window).resize(() => {
        moveSummaryBackground();
    });

    const updateSpinner = function(message, showSpinner) {
        // Get spinner object as needed
        const spinner = $('#searchNotification');
        if (showSpinner) {
            message = '<img id="searchingAnim" src="images/loading32' + MEDUSA.config.themeSpinner + '.gif" height="16" width="16" />&nbsp;' + message;
        }
        $(spinner).empty().append(message);
    };

    // Check the previous status of the history table, for hidden or shown, through the data attribute
    // data-history-toggle-hidden
    function toggleHistoryTable() {  // eslint-disable-line no-unused-vars
        // Get previous state which was saved on the wrapper
        const showOrHide = $('#wrapper').attr('data-history-toggle');
        $('#historydata').collapse(showOrHide);
    }

    $.fn.loadContainer = function(path, loadingTxt, errorTxt, callback) {
        updateSpinner(loadingTxt);
        $('#manualSearchMeta').load(path + ' #manualSearchMeta meta');
        $(this).load(path + ' #manualSearchTbody tr', (response, status) => {
            if (status === 'error') {
                updateSpinner(errorTxt, false);
            }
            if (typeof callback !== 'undefined') {
                callback();
            }
        });
    };

    // Click event for the download button for snatching a result
    $(document.body).on('click', '.epManualSearch', event => {
        event.preventDefault();
        const link = event.currentTarget;
        $(link).children('img').prop('src', 'images/loading16.gif');
        $.getJSON(event.currentTarget.href, data => {
            if (data.result === 'success') {
                $(link).children('img').prop('src', 'images/save.png');
            } else {
                $(link).children('img').prop('src', 'images/no16.png');
            }
        });
    });

    $.fn.generateStars = function() {
        return this.each((index, element) => {
            $(element).html($('<span/>').width($(element).text() * 12));
        });
    };

    function initTableSorter(table) {
        // Nasty hack to re-initialize tablesorter after refresh
        $(table).tablesorter({
            widgets: ['saveSort', 'stickyHeaders', 'columnSelector', 'filter'],
            widgetOptions: {
                filter_columnFilters: true, // eslint-disable-line camelcase
                filter_hideFilters: true, // eslint-disable-line camelcase
                filter_saveFilters: true, // eslint-disable-line camelcase
                columnSelector_saveColumns: true, // eslint-disable-line camelcase
                columnSelector_layout: '<label><input type="checkbox">{name}</label>', // eslint-disable-line camelcase
                columnSelector_mediaquery: false, // eslint-disable-line camelcase
                columnSelector_cssChecked: 'checked' // eslint-disable-line camelcase
            },
            textExtraction: (function() {
                return {
                    // 2: Provider
                    2(node) {
                        return $(node).find('img').attr('title');
                    },
                    // 6: The size column needs an explicit field for the filtering on raw size.
                    6(node) {
                        return node.getAttribute('data-size');
                    },
                    // 9: Published date
                    9(node) {
                        return node.getAttribute('data-datetime');
                    },
                    // 10: Added date
                    10(node) {
                        return node.getAttribute('data-datetime');
                    }
                };
            })(),
            headers: {
                9: { sorter: 'realISODate' }, // Published
                10: { sorter: 'realISODate' }, // Added
                11: { sorter: false, parser: false } // Snatch link
            }
        });
    }

    $('.imdbstars').generateStars();

    function checkCacheUpdates(repeat) {
        const self = this;
        let pollInterval = 5000;
        repeat = repeat || true;

        const indexerName = $('meta[data-last-prov-updates]').attr('data-indexer-name');
        const seriesId = $('meta[data-last-prov-updates]').attr('data-series-id');
        const season = $('meta[data-last-prov-updates]').attr('data-season');
        const episode = $('meta[data-last-prov-updates]').attr('data-episode');
        const data = $('meta[data-last-prov-updates]').data('last-prov-updates');
        const manualSearchType = $('meta[data-last-prov-updates]').attr('data-manual-search-type');

        const checkParams = [indexerName, seriesId, season, episode].every(checkIsTrue => {
            return checkIsTrue;
        });

        if (!checkParams) {
            console.log(```Something went wrong in getthing the paramaters from dom. indexerName: ${indexerName}, 
                        seriesId: ${seriesId}, season: ${season}, episode: ${episode}```);
            return;
        }

        let urlParams = '?indexername=' + indexerName + '&seriesid=' + seriesId + '&season=' + season + '&episode=' + episode;

        if (manualSearchType === 'season') {
            urlParams += '&manual_search_type=' + manualSearchType;
        }

        if (!$.isNumeric(seriesId) || !$.isNumeric(season) || !$.isNumeric(episode)) {
            setTimeout(() => {
                checkCacheUpdates(true);
            }, 200);
        }

        self.refreshResults = function() {
            // @FIXME: In the current transition phase to Vue, we can't load pages in this way, so use reload instead.
            /*
            $('#manualSearchTbody').loadContainer(
                'home/snatchSelection' + urlParams,
                'Loading new search results...',
                'Time out, refresh page to try again',
                toggleHistoryTable // This is a callback function
            );
            */
            window.location.reload();
        };

        $.ajax({
            url: 'home/manualSearchCheckCache' + urlParams,
            type: 'GET',
            data,
            contentType: 'application/json',
            error() {
                // Repeat = false;
                console.log('Error occurred!!');
                $('.manualSearchButton').removeAttr('disabled');
            },
            complete() {
                if (repeat) {
                    setTimeout(checkCacheUpdates, pollInterval);
                }
            },
            timeout: 15000 // Timeout after 15s
        }).done(data => {
            // @TODO: Combine the lower if statements
            if (data === '') {
                updateSpinner('Search finished', false);
                $('.manualSearchButton').removeAttr('disabled');
                repeat = false;
            }

            if (data.result === 'refresh') {
                self.refreshResults();
                updateSpinner('Refreshed results...', true);
            }
            if (data.result === 'searching') {
                // Ep is searched, you will get a results any minute now
                pollInterval = 5000;
                $('.manualSearchButton').prop('disabled', true);
                updateSpinner('The episode is being searched, please wait......', true);
            }
            if (data.result === 'queued') {
                // Ep is queued, this might take some time to get results
                pollInterval = 7000;
                $('.manualSearchButton').prop('disabled', true);
                updateSpinner('The episode has been queued, because another search is taking place. please wait..', true);
            }
            if (data.result === 'finished') {
                // Ep search is finished
                updateSpinner('Search finished', false);
                $('.manualSearchButton').removeAttr('disabled');
                repeat = false;
                $('#srchresults').trigger('update', true);
                $('[datetime]').timeago();
            }
            if (data.result === 'error') {
                // Ep search is finished but with an error
                console.log('Probably tried to call manualSelectCheckCache, while page was being refreshed.');
                $('.manualSearchButton').removeAttr('disabled');
                repeat = true;
            }
        });
    }

    setTimeout(checkCacheUpdates, 2000);

    // Click event for the reload results and force search buttons
    $(document.body).on('click', '.manualSearchButton', event => {
        event.preventDefault();
        $('.manualSearchButton').prop('disabled', true);
        const indexerName = $('meta[data-last-prov-updates]').attr('data-indexer-name');
        const seriesId = $('meta[data-last-prov-updates]').attr('data-series-id');
        const season = $('meta[data-last-prov-updates]').attr('data-season');
        const episode = $('meta[data-last-prov-updates]').attr('data-episode');
        const manualSearchType = $('meta[data-last-prov-updates]').attr('data-manual-search-type');
        const forceSearch = $(event.currentTarget).attr('data-force-search');

        const checkParams = [indexerName, seriesId, season, episode].every(checkIsTrue => {
            return checkIsTrue;
        });

        if (!checkParams) {
            console.log(```Something went wrong in getthing the paramaters from dom. indexerName: ${indexerName},
                        seriesId: ${seriesId}, season: ${season}, episode: ${episode}```);
            return;
        }

        if ($.isNumeric(seriesId) && $.isNumeric(season) && $.isNumeric(episode)) {
            updateSpinner('Started a forced manual search...', true);
            $.getJSON('home/snatchSelection', {
                indexername: indexerName,
                seriesid: seriesId,
                season,
                episode,
                manual_search_type: manualSearchType, // eslint-disable-line camelcase
                perform_search: forceSearch // eslint-disable-line camelcase
            });
            // Force the search, but give the checkCacheUpdates the time to start up a search thread
            setTimeout(() => {
                checkCacheUpdates(true);
            }, 2000);
        }
    });

    // Moved and rewritten this from displayShow. This changes the button when clicked for collapsing/expanding the
    // "Show History" button to show or hide the snatch/download/failed history for a manual searched episode or pack.

    $('#popover').popover({
        placement: 'bottom',
        html: true, // Required if content has HTML
        content: '<div id="popover-target"></div>'
    }).on('shown.bs.popover', () => { // Bootstrap popover event triggered when the popover opens
        $.tablesorter.columnSelector.attachTo($('#srchresults'), '#popover-target');
    });

    $('#btnReset').click(() => {
        $('#showTable')
            .trigger('saveSortReset') // Clear saved sort
            .trigger('sortReset'); // Reset current table sort
        return false;
    });

    $(() => {
        initTableSorter('#srchresults');
        moveSummaryBackground();
        $('body').on('hide.bs.collapse', '.collapse.toggle', () => {
            $('#showhistory').text('Show History');
            $('#wrapper').prop('data-history-toggle', 'hide');
        });
        $('body').on('show.bs.collapse', '.collapse.toggle', () => {
            $('#showhistory').text('Hide History');
            $('#wrapper').prop('data-history-toggle', 'show');
        });
    });

    $(document.body).on('click', '.release-name-ellipses, .release-name-ellipses-toggled', event => {
        const target = $(event.currentTarget);

        if (target.hasClass('release-name-ellipses')) {
            target.switchClass('release-name-ellipses', 'release-name-ellipses-toggled', 100);
        } else {
            target.switchClass('release-name-ellipses-toggled', 'release-name-ellipses', 100);
        }
    });
};
