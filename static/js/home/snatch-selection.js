MEDUSA.home.snatchSelection = function() {
    $('.imdbPlot').on('click', function() {
        $(this).prev('span').toggle();
        if ($(this).html() === "..show less") {
            $(this).html("..show more");
        } else {
            $(this).html("..show less");
        }
        moveSummaryBackground();
    });

    // adjust the summary background position and size on page load and resize
    function moveSummaryBackground() {
        var height = $("#summary").height() + 10;
        var top = $("#summary").offset().top + 5;
        $("#summaryBackground").height(height);
        $("#summaryBackground").offset({ top: top, left: 0});
    }

    $(window).resize(function() {
        moveSummaryBackground();
    });

    var updateSpinner = function(message, showSpinner) {
        // get spinner object as needed
        var spinner = $('#searchNotification');
        if (showSpinner) {
            message = '<img id="searchingAnim" src="images/loading32' + MEDUSA.config.themeSpinner + '.gif" height="16" width="16" />&nbsp;' + message;
        }
        $(spinner).empty().append(message);
    };

    // Check the previous status of the history table, for hidden or shown, through the data attribute
    // data-history-toggle-hidden
    function toggleHistoryTable() {
        // Get previous state which was saved on the wrapper
        var showOrHide = $('#wrapper').attr('data-history-toggle');
        $('#historydata').collapse(showOrHide);
    }

    $.fn.loadContainer = function(path, loadingTxt, errorTxt, callback) {
        updateSpinner(loadingTxt);
        $(this).load(path + ' #container', function(response, status) {
            if (status === 'error') {
                updateSpinner(errorTxt, false);
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
            widgets: ['saveSort', 'stickyHeaders', 'columnSelector', 'filter'],
            widgetOptions: {
                filter_columnFilters: true, // eslint-disable-line camelcase
                filter_hideFilters: true, // eslint-disable-line camelcase
                filter_saveFilters: true, // eslint-disable-line camelcase
                columnSelector_saveColumns: true, // eslint-disable-line camelcase
                columnSelector_layout: '<label><input type="checkbox">{name}</label>', // eslint-disable-line camelcase
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

        var urlParams =  show + '&season=' + season + '&episode=' + episode;

        if (manualSearchType == 'season') {
            urlParams += '&manual_search_type=' + manualSearchType
        }

        if (!$.isNumeric(show) || !$.isNumeric(season) || !$.isNumeric(episode)) {
            setTimeout(function() {
                checkCacheUpdates(true);
            }, 200);
        }

        self.refreshResults = function() {
            $('#wrapper').loadContainer(
                    'home/snatchSelection?show=' + urlParams,
                    'Loading new search results...',
                    'Time out, refresh page to try again',
                    toggleHistoryTable // This is a callback function
            );
        };

        $.ajax({
            url: 'home/manualSearchCheckCache?show=' + urlParams,
            type: 'GET',
            data: data,
            contentType: 'application/json',
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
        }).done(function(data) {
            if (data.result === 'refresh') {
                self.refreshResults();
                updateSpinner('Refreshed results...', true);
                initTableSorter('#srchresults');
            }
            if (data.result === 'searching') {
                // ep is searched, you will get a results any minute now
                pollInterval = 5000;
                $('.manualSearchButton').prop('disabled', true);
                updateSpinner('The episode is being searched, please wait......', true);
                initTableSorter('#srchresults');
            }
            if (data.result === 'queued') {
                // ep is queued, this might take some time to get results
                pollInterval = 7000;
                $('.manualSearchButton').prop('disabled', true);
                updateSpinner('The episode has been queued, because another search is taking place. please wait..', true);
                initTableSorter('#srchresults');
            }
            if (data.result === 'finished') {
                // ep search is finished
                updateSpinner('Search finished', false);
                $('.manualSearchButton').removeAttr('disabled');
                repeat = false;
                initTableSorter('#srchresults');
                $('[datetime]').timeago();
            }
            if (data.result === 'error') {
                // ep search is finished but with an error
                console.log('Probably tried to call manualSelectCheckCache, while page was being refreshed.');
                $('.manualSearchButton').removeAttr('disabled');
                repeat = true;
                initTableSorter('#srchresults');
            }
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
            updateSpinner('Started a forced manual search...', true);
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
        $.tablesorter.columnSelector.attachTo($('#srchresults'), '#popover-target');
    });

    $('#btnReset').click(function() {
        $('#showTable')
        .trigger('saveSortReset') // clear saved sort
        .trigger('sortReset');    // reset current table sort
        return false;
    });

    $(function() {
        moveSummaryBackground();
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
