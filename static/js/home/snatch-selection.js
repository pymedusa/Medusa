MEDUSA.home.snatchSelection = function() {
    if (MEDUSA.config.fanartBackground) {
        $.backstretch('showPoster/?show=' + $('#showID').attr('value') + '&which=fanart');
        $('.backstretch').css('opacity', MEDUSA.config.fanartBackgroundOpacity).fadeIn(500);
    }
    var spinner = $('#searchNotification');
    var updateSpinner = function(spinner, message, showSpinner) {
        if (showSpinner) {
            $(spinner).html('<img id="searchingAnim" src="images/loading32' + MEDUSA.config.themeSpinner + '.gif" height="16" width="16" />&nbsp;' + message);
        } else {
            $(spinner).empty().html(message);
        }
    };

    // Check the previous status of the history table, for hidden or shown, through the data attribute
    // data-history-toggle-hidden
    function toggleHistoryTable() {
        // Get previous state which was saved on the wrapper
        var showOrHide = $('#wrapper').attr('data-history-toggle');
        $('#historydata').collapse(showOrHide);
    }

    $.fn.loadContainer = function(path, loadingTxt, errorTxt, callback) {
        updateSpinner(spinner, loadingTxt);
        $(this).load(path + ' #container', function(response, status) {
            if (status === 'error') {
                updateSpinner(spinner, errorTxt, false);
            }
            if (typeof callback !== 'undefined') {
                callback();
            }
        });
    };

    // Click event for the download button for snatching a result
    $('body').on('click', '.epManualSearch', function(event) {
        event.preventDefault();
        var link = this;
        $(link).children('img').prop('src', 'images/loading16.gif');
        $.getJSON(this.href, function(data) {
            if (data.result === 'success') {
                $(link).children('img').prop('src', 'images/save.png');
            } else {
                $(link).children('img').prop('src', 'images/no16.png');
            }
        });
    });

    $.fn.generateStars = function() {
        return this.each(function(i, e) {
            $(e).html($('<span/>').width($(e).text() * 12));
        });
    };

    function initTableSorter(table) {
        // Nasty hack to re-initialize tablesorter after refresh
        $(table).tablesorter({
            widthFixed: true,
            widgets: ['saveSort', 'stickyHeaders', 'columnSelector', 'filter'],
            widgetOptions: {
                filter_columnFilters: true, // eslint-disable-line camelcase
                filter_hideFilters: true, // eslint-disable-line camelcase
                filter_saveFilters: true, // eslint-disable-line camelcase
                columnSelector_saveColumns: true, // eslint-disable-line camelcase
                columnSelector_layout: '<br><label><input type="checkbox">{name}</label>', // eslint-disable-line camelcase
                columnSelector_mediaquery: false, // eslint-disable-line camelcase
                columnSelector_cssChecked: 'checked' // eslint-disable-line camelcase
            }
        });
    }

    $('.imdbstars').generateStars();

    function checkCacheUpdates(repeat) {
        var self = this;
        var pollInterval = 5000;
        repeat = repeat || true;

        var show = $('meta[data-last-prov-updates]').attr('data-show');
        var season = $('meta[data-last-prov-updates]').attr('data-season');
        var episode = $('meta[data-last-prov-updates]').attr('data-episode');
        var data = $('meta[data-last-prov-updates]').data('last-prov-updates');
        var manualSearchType = $('meta[data-last-prov-updates]').attr('data-manual-search-type');

        if (!$.isNumeric(show) || !$.isNumeric(season) || !$.isNumeric(episode)) {
            setTimeout(function() {
                checkCacheUpdates(true);
            }, 200);
        }

        self.refreshResults = function() {
            $('#wrapper').loadContainer(
                    'home/snatchSelection?show=' + show + '&season=' + season + '&episode=' + episode + '&manual_search_type=' + manualSearchType + '&perform_search=0',
                    'Loading new search results...',
                    'Time out, refresh page to try again',
                    toggleHistoryTable // This is a callback function
            );
        };

        $.ajax({
            url: 'home/manualSearchCheckCache?show=' + show + '&season=' + season + '&episode=' + episode + '&manual_search_type=' + manualSearchType,
            type: 'GET',
            data: data,
            contentType: 'application/json',
            success: function(data) {
                if (data.result === 'refresh') {
                    self.refreshResults();
                    updateSpinner(spinner, 'Refreshed results...', true);
                    initTableSorter('#showTable');
                }
                if (data.result === 'searching') {
                    // ep is searched, you will get a results any minute now
                    pollInterval = 5000;
                    $('.manualSearchButton').prop('disabled', true);
                    updateSpinner(spinner, 'The episode is being searched, please wait......', true);
                    initTableSorter('#showTable');
                }
                if (data.result === 'queued') {
                    // ep is queued, this might take some time to get results
                    pollInterval = 7000;
                    $('.manualSearchButton').prop('disabled', true);
                    updateSpinner(spinner, 'The episode has been queued, because another search is taking place. please wait..', true);
                    initTableSorter('#showTable');
                }
                if (data.result === 'finished') {
                    // ep search is finished
                    updateSpinner(spinner, 'Search finished', false);
                    $('.manualSearchButton').removeAttr('disabled');
                    repeat = false;
                    initTableSorter('#showTable');
                }
                if (data.result === 'error') {
                    // ep search is finished
                    console.log('Probably tried to call manualSelectCheckCache, while page was being refreshed.');
                    $('.manualSearchButton').removeAttr('disabled');
                    repeat = true;
                    initTableSorter('#showTable');
                }
            },
            error: function() {
                // repeat = false;
                console.log('Error occurred!!');
                $('.manualSearchButton').removeAttr('disabled');
            },
            complete: function() {
                if (repeat) {
                    setTimeout(checkCacheUpdates, pollInterval);
                }
            },
            timeout: 15000 // timeout after 15s
        });
    }

    setTimeout(checkCacheUpdates, 2000);

    // Click event for the reload results and force search buttons
    $('body').on('click', '.manualSearchButton', function(event) {
        event.preventDefault();
        $('.manualSearchButton').prop('disabled', true);
        var show = $('meta[data-last-prov-updates]').attr('data-show');
        var season = $('meta[data-last-prov-updates]').attr('data-season');
        var episode = $('meta[data-last-prov-updates]').attr('data-episode');
        var manualSearchType = $('meta[data-last-prov-updates]').attr('data-manual-search-type');
        var forceSearch = $(this).attr('data-force-search');

        if ($.isNumeric(show) && $.isNumeric(season) && $.isNumeric(episode)) {
            updateSpinner(spinner, 'Started a forced manual search...', true);
            $.getJSON('home/snatchSelection', {
                show: show,
                season: season,
                episode: episode,
                manual_search_type: manualSearchType, // eslint-disable-line camelcase
                perform_search: forceSearch // eslint-disable-line camelcase
            });
            // Force the search, but give the checkCacheUpdates the time to start up a search thread
            setTimeout(function() {
                checkCacheUpdates(true);
            }, 2000);
        }
    });

    // Moved and rewritten this from displayShow. This changes the button when clicked for collapsing/expanding the
    // "Show History" button to show or hide the snatch/download/failed history for a manual searched episode or pack.
    initTableSorter('#showTable');

    $('#popover').popover({
        placement: 'bottom',
        html: true, // required if content has HTML
        content: '<div id="popover-target"></div>'
    }).on('shown.bs.popover', function() { // bootstrap popover event triggered when the popover opens
        $.tablesorter.columnSelector.attachTo($('#showTable'), '#popover-target');
    });

    $('#btnReset').click(function() {
        $('#showTable')
        .trigger('saveSortReset') // clear saved sort
        .trigger('sortReset');    // reset current table sort
        return false;
    });

    $(function() {
        $('body').on('hide.bs.collapse', '.collapse.toggle', function() {
            $('#showhistory').text('Show History');
            $('#wrapper').prop('data-history-toggle', 'hide');
        });
        $('body').on('show.bs.collapse', '.collapse.toggle', function() {
            $('#showhistory').text('Hide History');
            $('#wrapper').prop('data-history-toggle', 'show');
        });
    });
};
