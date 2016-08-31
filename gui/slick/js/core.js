// eslint-disable-line max-lines
// @TODO Move these into common.ini when possible,
//       currently we can't do that as browser.js and a few others need it before this is loaded
var topImageHtml = '<img src="images/top.gif" width="31" height="11" alt="Jump to top" />'; // eslint-disable-line no-unused-vars
var webRoot = $('base').attr('href');
var apiRoot = $('body').attr('api-root');
var apiKey = $('body').attr('api-key');

$.fn.extend({
    addRemoveWarningClass: function (_) {
        if (_) {
            return $(this).removeClass('warning');
        }
        return $(this).addClass('warning');
    }
});

var SICKRAGE = {
    common: {
        init: function() {
            $.confirm.options = {
                confirmButton: 'Yes',
                cancelButton: 'Cancel',
                dialogClass: 'modal-dialog',
                post: false,
                confirm: function(e) {
                    location.href = e.context.href;
                }
            };

            $('a.shutdown').confirm({
                title: 'Shutdown',
                text: 'Are you sure you want to shutdown Medusa?'
            });

            $('a.restart').confirm({
                title: 'Restart',
                text: 'Are you sure you want to restart Medusa?'
            });

            $('a.removeshow').confirm({
                title: 'Remove Show',
                text: 'Are you sure you want to remove <span class="footerhighlight">' + $('#showtitle').data('showname') + '</span> from the database?<br><br><input type="checkbox" id="deleteFiles"> <span class="red-text">Check to delete files as well. IRREVERSIBLE</span></input>',
                confirm: function(e) {
                    location.href = e.context.href + ($('#deleteFiles')[0].checked ? '&full=1' : '');
                }
            });

            $('a.clearhistory').confirm({
                title: 'Clear History',
                text: 'Are you sure you want to clear all download history?'
            });

            $('a.trimhistory').confirm({
                title: 'Trim History',
                text: 'Are you sure you want to trim all download history older than 30 days?'
            });

            $('a.submiterrors').confirm({
                title: 'Submit Errors',
                text: 'Are you sure you want to submit these errors ?<br><br><span class="red-text">Make sure Medusa is updated and trigger<br> this error with debug enabled before submitting</span>'
            });

            $('#config-components').tabs({
                activate: function (event, ui) {
                    var lastOpenedPanel = $(this).data('lastOpenedPanel');

                    if (!lastOpenedPanel) {
                        lastOpenedPanel = $(ui.oldPanel);
                    }

                    if (!$(this).data('topPositionTab')) {
                        $(this).data('topPositionTab', $(ui.newPanel).position().top);
                    }

                    // Dont use the builtin fx effects. This will fade in/out both tabs, we dont want that
                    // Fadein the new tab yourself
                    $(ui.newPanel).hide().fadeIn(0);

                    if (lastOpenedPanel) {
                        // 1. Show the previous opened tab by removing the jQuery UI class
                        // 2. Make the tab temporary position:absolute so the two tabs will overlap
                        // 3. Set topposition so they will overlap if you go from tab 1 to tab 0
                        // 4. Remove position:absolute after animation
                        lastOpenedPanel
                            .toggleClass('ui-tabs-hide')
                            .css('position', 'absolute')
                            .css('top', $(this).data('topPositionTab') + 'px')
                            .fadeOut(0, function () {
                                $(this).css('position', '');
                            });
                    }

                    // Saving the last tab has been opened
                    $(this).data('lastOpenedPanel', $(ui.newPanel));
                }
            });

            // @TODO Replace this with a real touchscreen check
            // hack alert: if we don't have a touchscreen, and we are already hovering the mouse, then click should link instead of toggle
            if ((navigator.maxTouchPoints || 0) < 2) {
                $('.dropdown-toggle').on('click', function() {
                    var $this = $(this);
                    if ($this.attr('aria-expanded') === 'true') {
                        window.location.href = $this.attr('href');
                    }
                });
            }

            if (SICKRAGE.info.fuzzyDating) {
                $.timeago.settings.allowFuture = true;
                $.timeago.settings.strings = {
                    prefixAgo: null,
                    prefixFromNow: 'In ',
                    suffixAgo: 'ago',
                    suffixFromNow: '',
                    seconds: 'less than a minute',
                    minute: 'about a minute',
                    minutes: '%d minutes',
                    hour: 'an hour',
                    hours: '%d hours',
                    day: 'a day',
                    days: '%d days',
                    month: 'a month',
                    months: '%d months',
                    year: 'a year',
                    years: '%d years',
                    wordSeparator: ' ',
                    numbers: []
                };
                $('[datetime]').timeago();
            }

            $(document.body).on('click', 'a[data-no-redirect]', function(e) {
                e.preventDefault();
                $.get($(this).attr('href'));
                return false;
            });

            $(document.body).on('click', '.bulkCheck', function() {
                var bulkCheck = this;
                var whichBulkCheck = $(bulkCheck).attr('id');

                $('.' + whichBulkCheck + ':visible').each(function() {
                    $(this).prop('checked', $(bulkCheck).prop('checked'));
                });
            });

            $('.enabler').each(function() {
                if (!$(this).prop('checked')) {
                    $('#content_' + $(this).attr('id')).hide();
                }
            });

            $('.enabler').on('click', function() {
                if ($(this).prop('checked')) {
                    $('#content_' + $(this).attr('id')).fadeIn('fast', 'linear');
                } else {
                    $('#content_' + $(this).attr('id')).fadeOut('fast', 'linear');
                }
            });
        }
    },
    config: {
        providers: function() {
            // @TODO This function need to be filled with ConfigProviders.js but can't be as we've got scope issues currently.
            console.log('This function need to be filled with ConfigProviders.js but can\'t be as we\'ve got scope issues currently.');
        }
    },
    home: {
        index: function() {
            // Resets the tables sorting, needed as we only use a single call for both tables in tablesorter
            $('.resetsorting').on('click', function() {
                $('table').trigger('filterReset');
            });

            // Handle filtering in the poster layout
            $('#filterShowName').on('input', _.debounce(function() {
                $('.show-grid').isotope({
                    filter: function () {
                        var name = $(this).attr('data-name').toLowerCase();
                        return name.indexOf($('#filterShowName').val().toLowerCase()) > -1;
                    }
                });
            }, 500));

            function resizePosters(newSize) {
                var fontSize;
                var logoWidth;
                var borderRadius;
                var borderWidth;
                if (newSize < 125) { // small
                    borderRadius = 3;
                    borderWidth = 4;
                } else if (newSize < 175) { // medium
                    fontSize = 9;
                    logoWidth = 40;
                    borderRadius = 4;
                    borderWidth = 5;
                } else { // large
                    fontSize = 11;
                    logoWidth = 50;
                    borderRadius = 6;
                    borderWidth = 6;
                }

                // If there's a poster popup, remove it before resizing
                $('#posterPopup').remove();

                if (fontSize === undefined) {
                    $('.show-details').hide();
                } else {
                    $('.show-details').show();
                    $('.show-dlstats, .show-quality').css('fontSize', fontSize);
                    $('.show-network-image').css('width', logoWidth);
                }

                $('.show-container').css({
                    width: newSize,
                    borderWidth: borderWidth,
                    borderRadius: borderRadius
                });
            }

            var posterSize;
            if (typeof (Storage) !== 'undefined') {
                posterSize = parseInt(localStorage.getItem('posterSize'), 10);
            }
            if (typeof (posterSize) !== 'number' || isNaN(posterSize)) {
                posterSize = 188;
            }
            resizePosters(posterSize);

            $('#posterSizeSlider').slider({
                min: 75,
                max: 250,
                value: posterSize,
                change: function (e, ui) {
                    if (typeof (Storage) !== 'undefined') {
                        localStorage.setItem('posterSize', ui.value);
                    }
                    resizePosters(ui.value);
                    $('.show-grid').isotope('layout');
                }
            });

            // This needs to be refined to work a little faster.
            $('.progressbar').each(function() {
                var percentage = $(this).data('progress-percentage');
                var classToAdd = percentage === 100 ? 100 : percentage > 80 ? 80 : percentage > 60 ? 60 : percentage > 40 ? 40 : 20; // eslint-disable-line no-nested-ternary
                $(this).progressbar({
                    value: percentage
                });
                if ($(this).data('progress-text')) {
                    $(this).append('<div class="progressbarText" title="' + $(this).data('progress-tip') + '">' + $(this).data('progress-text') + '</div>');
                }
                $(this).find('.ui-progressbar-value').addClass('progress-' + classToAdd);
            });

            $('img#network').on('error', function() {
                $(this).parent().text($(this).attr('alt'));
                $(this).remove();
            });

            $('#showListTableShows:has(tbody tr), #showListTableAnime:has(tbody tr)').tablesorter({
                sortList: [[7, 1], [2, 0]],
                textExtraction: {
                    0: function(node) { return $(node).find('time').attr('datetime'); }, // eslint-disable-line brace-style
                    1: function(node) { return $(node).find('time').attr('datetime'); }, // eslint-disable-line brace-style
                    3: function(node) { return $(node).find('span').prop('title').toLowerCase(); }, // eslint-disable-line brace-style
                    4: function(node) { return $(node).find('span').text().toLowerCase(); }, // eslint-disable-line brace-style
                    5: function(node) { return $(node).find('span:first').text(); }, // eslint-disable-line brace-style
                    6: function(node) { return $(node).data('show-size'); }, // eslint-disable-line brace-style
                    7: function(node) { return $(node).find('img').attr('alt'); } // eslint-disable-line brace-style
                },
                widgets: ['saveSort', 'zebra', 'stickyHeaders', 'filter', 'columnSelector'],
                headers: {
                    0: {sorter: 'realISODate'},
                    1: {sorter: 'realISODate'},
                    2: {sorter: 'loadingNames'},
                    4: {sorter: 'quality'},
                    5: {sorter: 'eps'},
                    6: {sorter: 'digit'},
                    7: {filter: 'parsed'}
                },
                widgetOptions: {
                    filter_columnFilters: true, // eslint-disable-line camelcase
                    filter_hideFilters: true, // eslint-disable-line camelcase
                    filter_saveFilters: true, // eslint-disable-line camelcase
                    filter_functions: { // eslint-disable-line camelcase
                        5: function(e, n, f) {
                            var test = false;
                            var pct = Math.floor((n % 1) * 1000);
                            if (f === '') {
                                test = true;
                            } else {
                                var result = f.match(/(<|<=|>=|>)\s+(\d+)/i);
                                if (result) {
                                    if (result[1] === '<') {
                                        if (pct < parseInt(result[2]), 10) {
                                            test = true;
                                        }
                                    } else if (result[1] === '<=') {
                                        if (pct <= parseInt(result[2]), 10) {
                                            test = true;
                                        }
                                    } else if (result[1] === '>=') {
                                        if (pct >= parseInt(result[2]), 10) {
                                            test = true;
                                        }
                                    } else if (result[1] === '>') {
                                        if (pct > parseInt(result[2]), 10) {
                                            test = true;
                                        }
                                    }
                                }

                                result = f.match(/(\d+)\s(-|to)\s+(\d+)/i);
                                if (result) {
                                    if ((result[2] === '-') || (result[2] === 'to')) {
                                        if ((pct >= parseInt(result[1], 10)) && (pct <= parseInt(result[3], 10))) {
                                            test = true;
                                        }
                                    }
                                }

                                result = f.match(/(=)?\s?(\d+)\s?(=)?/i);
                                if (result) {
                                    if ((result[1] === '=') || (result[3] === '=')) {
                                        if (parseInt(result[2], 10) === pct) {
                                            test = true;
                                        }
                                    }
                                }

                                if (!isNaN(parseFloat(f)) && isFinite(f)) {
                                    if (parseInt(f, 10) === pct) {
                                        test = true;
                                    }
                                }
                            }
                            return test;
                        }
                    },
                    'columnSelector_mediaquery': false
                },
                sortStable: true,
                sortAppend: [[2, 0]]
            });

            $('.show-grid').imagesLoaded(function () {
                $('.loading-spinner').hide();
                $('.show-grid').show().isotope({
                    itemSelector: '.show-container',
                    sortBy: SICKRAGE.info.posterSortby,
                    sortAscending: SICKRAGE.info.posterSortdir,
                    layoutMode: 'masonry',
                    masonry: {
                        isFitWidth: true
                    },
                    getSortData: {
                        name: function (itemElem) {
                            var name = $(itemElem).attr('data-name') || '';
                            return (SICKRAGE.info.sortArticle ? name : name.replace(/^((?:The|A|An)\s)/i, '')).toLowerCase();
                        },
                        network: '[data-network]',
                        date: function (itemElem) {
                            var date = $(itemElem).attr('data-date');
                            return date.length && parseInt(date, 10) || Number.POSITIVE_INFINITY;
                        },
                        progress: function (itemElem) {
                            var progress = $(itemElem).attr('data-progress');
                            return progress.length && parseInt(progress, 10) || Number.NEGATIVE_INFINITY;
                        }
                    }
                });

                // When posters are small enough to not display the .show-details
                // table, display a larger poster when hovering.
                var posterHoverTimer = null;
                $('.show-container').on('mouseenter', function () {
                    var poster = $(this);
                    if (poster.find('.show-details').css('display') !== 'none') {
                        return;
                    }
                    posterHoverTimer = setTimeout(function () {
                        posterHoverTimer = null;
                        $('#posterPopup').remove();
                        var popup = poster.clone().attr({
                            id: 'posterPopup'
                        });
                        var origLeft = poster.offset().left;
                        var origTop = poster.offset().top;
                        popup.css({
                            position: 'absolute',
                            margin: 0,
                            top: origTop,
                            left: origLeft
                        });
                        popup.find('.show-details').show();
                        popup.on('mouseleave', function () {
                            $(this).remove();
                        });
                        popup.zIndex(9999);
                        popup.appendTo('body');

                        var height = 438;
                        var width = 250;
                        var newTop = (origTop + (poster.height() / 2)) - (height / 2);
                        var newLeft = (origLeft + (poster.width() / 2)) - (width / 2);

                        // Make sure the popup isn't outside the viewport
                        var margin = 5;
                        var scrollTop = $(window).scrollTop();
                        var scrollLeft = $(window).scrollLeft();
                        var scrollBottom = scrollTop + $(window).innerHeight();
                        var scrollRight = scrollLeft + $(window).innerWidth();
                        if (newTop < scrollTop + margin) {
                            newTop = scrollTop + margin;
                        }
                        if (newLeft < scrollLeft + margin) {
                            newLeft = scrollLeft + margin;
                        }
                        if (newTop + height + margin > scrollBottom) {
                            newTop = scrollBottom - height - margin;
                        }
                        if (newLeft + width + margin > scrollRight) {
                            newLeft = scrollRight - width - margin;
                        }

                        popup.animate({
                            top: newTop,
                            left: newLeft,
                            width: 250,
                            height: 438
                        });
                    }, 300);
                }).on('mouseleave', function () {
                    if (posterHoverTimer !== null) {
                        clearTimeout(posterHoverTimer);
                    }
                });
            });

            $('#postersort').on('change', function() {
                $('.show-grid').isotope({sortBy: $(this).val()});
                $.get($(this).find('option[value=' + $(this).val() + ']').attr('data-sort'));
            });

            $('#postersortdirection').on('change', function() {
                $('.show-grid').isotope({sortAscending: ($(this).val() === 'true')});
                $.get($(this).find('option[value=' + $(this).val() + ']').attr('data-sort'));
            });

            $('#popover').popover({
                placement: 'bottom',
                html: true, // required if content has HTML
                content: '<div id="popover-target"></div>'
            }).on('shown.bs.popover', function () { // bootstrap popover event triggered when the popover opens
                // call this function to copy the column selection code into the popover
                $.tablesorter.columnSelector.attachTo($('#showListTableShows'), '#popover-target');
                if (SICKRAGE.info.animeSplitHome) {
                    $.tablesorter.columnSelector.attachTo($('#showListTableAnime'), '#popover-target');
                }
            });
        },
        displayShow: function() {
            if (SICKRAGE.info.fanartBackground) {
                $.backstretch('showPoster/?show=' + $('#showID').attr('value') + '&which=fanart');
                $('.backstretch').css('opacity', SICKRAGE.info.fanartBackgroundOpacity).fadeIn(500);
            }

            $.ajaxEpSearch({
                colorRow: true
            });

            $.ajaxEpSubtitlesSearch();

            $('#seasonJump').on('change', function() {
                var id = $('#seasonJump option:selected').val();
                if (id && id !== 'jump') {
                    var season = $('#seasonJump option:selected').data('season');
                    $('html,body').animate({scrollTop: $('[name ="' + id.substring(1) + '"]').offset().top - 50}, 'slow');
                    $('#collapseSeason-' + season).collapse('show');
                    location.hash = id;
                }
                $(this).val('jump');
            });

            $('#prevShow').on('click', function() {
                $('#pickShow option:selected').prev('option').prop('selected', true);
                $('#pickShow').change();
            });

            $('#nextShow').on('click', function() {
                $('#pickShow option:selected').next('option').prop('selected', true);
                $('#pickShow').change();
            });

            $('#changeStatus').on('click', function() {
                var epArr = [];

                $('.epCheck').each(function () {
                    if (this.checked === true) {
                        epArr.push($(this).attr('id'));
                    }
                });

                if (epArr.length === 0) {
                    return false;
                }

                window.location.href = 'home/setStatus?show=' + $('#showID').attr('value') + '&eps=' + epArr.join('|') + '&status=' + $('#statusSelect').val();
            });

            $('.seasonCheck').on('click', function() {
                var seasCheck = this;
                var seasNo = $(seasCheck).attr('id');

                $('#collapseSeason-' + seasNo).collapse('show');
                $('.epCheck:visible').each(function () {
                    var epParts = $(this).attr('id').split('x');
                    if (epParts[0] === seasNo) {
                        this.checked = seasCheck.checked;
                    }
                });
            });

            var lastCheck = null;
            $('.epCheck').on('click', function (event) {
                if (!lastCheck || !event.shiftKey) {
                    lastCheck = this;
                    return;
                }

                var check = this;
                var found = 0;

                $('.epCheck').each(function() {
                    if (found === 1) {
                        this.checked = lastCheck.checked;
                    }

                    if (found === 1) {
                        return false;
                    }

                    if (this === check || this === lastCheck) {
                        found++;
                    }
                });
            });

            // selects all visible episode checkboxes.
            $('.seriesCheck').on('click', function () {
                $('.epCheck:visible').each(function () {
                    this.checked = true;
                });
                $('.seasonCheck:visible').each(function () {
                    this.checked = true;
                });
            });

            // clears all visible episode checkboxes and the season selectors
            $('.clearAll').on('click', function () {
                $('.epCheck:visible').each(function () {
                    this.checked = false;
                });
                $('.seasonCheck:visible').each(function () {
                    this.checked = false;
                });
            });

            // handle the show selection dropbox
            $('#pickShow').on('change', function () {
                var val = $(this).val();
                if (val === 0) {
                    return;
                }
                window.location.href = 'home/displayShow?show=' + val;
            });

            // show/hide different types of rows when the checkboxes are changed
            $('#checkboxControls input').on('change', function () {
                var whichClass = $(this).attr('id');
                $(this).showHideRows(whichClass);
            });

            // initially show/hide all the rows according to the checkboxes
            $('#checkboxControls input').each(function() {
                var status = $(this).prop('checked');
                $('tr.' + $(this).attr('id')).each(function() {
                    if (status) {
                        $(this).show();
                    } else {
                        $(this).hide();
                    }
                });
            });

            $.fn.showHideRows = function(whichClass) {
                var status = $('#checkboxControls > input, #' + whichClass).prop('checked');
                $('tr.' + whichClass).each(function() {
                    if (status) {
                        $(this).show();
                    } else {
                        $(this).hide();
                    }
                });

                // hide season headers with no episodes under them
                $('tr.seasonheader').each(function () {
                    var numRows = 0;
                    var seasonNo = $(this).attr('id');
                    $('tr.' + seasonNo + ' :visible').each(function () {
                        numRows++;
                    });
                    if (numRows === 0) {
                        $(this).hide();
                        $('#' + seasonNo + '-cols').hide();
                    } else {
                        $(this).show();
                        $('#' + seasonNo + '-cols').show();
                    }
                });
            };

            function setEpisodeSceneNumbering(forSeason, forEpisode, sceneSeason, sceneEpisode) {
                var showId = $('#showID').val();
                var indexer = $('#indexer').val();

                if (sceneSeason === '') {
                    sceneSeason = null;
                }
                if (sceneEpisode === '') {
                    sceneEpisode = null;
                }

                $.getJSON('home/setSceneNumbering', {
                    show: showId,
                    indexer: indexer,
                    forSeason: forSeason,
                    forEpisode: forEpisode,
                    sceneSeason: sceneSeason,
                    sceneEpisode: sceneEpisode
                }, function(data) {
                    // Set the values we get back
                    if (data.sceneSeason === null || data.sceneEpisode === null) {
                        $('#sceneSeasonXEpisode_' + showId + '_' + forSeason + '_' + forEpisode).val('');
                    } else {
                        $('#sceneSeasonXEpisode_' + showId + '_' + forSeason + '_' + forEpisode).val(data.sceneSeason + 'x' + data.sceneEpisode);
                    }
                    if (!data.success) {
                        if (data.errorMessage) {
                            alert(data.errorMessage);
                        } else {
                            alert('Update failed.');
                        }
                    }
                });
            }

            function setAbsoluteSceneNumbering(forAbsolute, sceneAbsolute) {
                var showId = $('#showID').val();
                var indexer = $('#indexer').val();

                if (sceneAbsolute === '') {
                    sceneAbsolute = null;
                }

                $.getJSON('home/setSceneNumbering', {
                    show: showId,
                    indexer: indexer,
                    forAbsolute: forAbsolute,
                    sceneAbsolute: sceneAbsolute
                }, function(data) {
                    // Set the values we get back
                    if (data.sceneAbsolute === null) {
                        $('#sceneAbsolute_' + showId + '_' + forAbsolute).val('');
                    } else {
                        $('#sceneAbsolute_' + showId + '_' + forAbsolute).val(data.sceneAbsolute);
                    }

                    if (!data.success) {
                        if (data.errorMessage) {
                            alert(data.errorMessage);
                        } else {
                            alert('Update failed.');
                        }
                    }
                });
            }

            function setInputValidInvalid(valid, el) {
                if (valid) {
                    $(el).css({
                        'background-color': '#90EE90', // green
                        'color': '#FFF',
                        'font-weight': 'bold'
                    });
                    return true;
                }
                $(el).css({
                    'background-color': '#FF0000', // red
                    'color': '#FFF!important',
                    'font-weight': 'bold'
                });
                return false;
            }

            $('.sceneSeasonXEpisode').on('change', function() {
                // Strip non-numeric characters
                var value = $(this).val();
                $(this).val(value.replace(/[^0-9xX]*/g, ''));
                var forSeason = $(this).attr('data-for-season');
                var forEpisode = $(this).attr('data-for-episode');

                // If empty reset the field
                if (value === '') {
                    setEpisodeSceneNumbering(forSeason, forEpisode, null, null);
                    return;
                }

                var m = $(this).val().match(/^(\d+)x(\d+)$/i);
                var onlyEpisode = $(this).val().match(/^(\d+)$/i);
                var sceneSeason = null;
                var sceneEpisode = null;
                var isValid = false;
                if (m) {
                    sceneSeason = m[1];
                    sceneEpisode = m[2];
                    isValid = setInputValidInvalid(true, $(this));
                } else if (onlyEpisode) {
                    // For example when '5' is filled in instead of '1x5', asume it's the first season
                    sceneSeason = forSeason;
                    sceneEpisode = onlyEpisode[1];
                    isValid = setInputValidInvalid(true, $(this));
                } else {
                    isValid = setInputValidInvalid(false, $(this));
                }

                if (isValid) {
                    setEpisodeSceneNumbering(forSeason, forEpisode, sceneSeason, sceneEpisode);
                }
            });

            $('.sceneAbsolute').on('change', function() {
                // Strip non-numeric characters
                $(this).val($(this).val().replace(/[^0-9xX]*/g, ''));
                var forAbsolute = $(this).attr('data-for-absolute');

                var m = $(this).val().match(/^(\d{1,3})$/i);
                var sceneAbsolute = null;
                if (m) {
                    sceneAbsolute = m[1];
                }
                setAbsoluteSceneNumbering(forAbsolute, sceneAbsolute);
            });

            $('.addQTip').each(function () {
                $(this).css({'cursor': 'help', 'text-shadow': '0px 0px 0.5px #666'});
                $(this).qtip({
                    show: {solo: true},
                    position: {viewport: $(window), my: 'left center', adjust: {y: -10, x: 2}},
                    style: {tip: {corner: true, method: 'polygon'}, classes: 'qtip-rounded qtip-shadow ui-tooltip-sb'}
                });
            });

            $.fn.generateStars = function() {
                return this.each(function(i, e) {
                    $(e).html($('<span/>').width($(e).text() * 12));
                });
            };

            $('.imdbstars').generateStars();

            $('#showTable, #animeTable').tablesorter({
                widgets: ['saveSort', 'stickyHeaders', 'columnSelector'],
                widgetOptions: {
                    columnSelector_saveColumns: true, // eslint-disable-line camelcase
                    columnSelector_layout: '<br><label><input type="checkbox">{name}</label>', // eslint-disable-line camelcase
                    columnSelector_mediaquery: false, // eslint-disable-line camelcase
                    columnSelector_cssChecked: 'checked' // eslint-disable-line camelcase
                }
            });

            $('#popover').popover({
                placement: 'bottom',
                html: true, // required if content has HTML
                content: '<div id="popover-target"></div>'
            }).on('shown.bs.popover', function () { // bootstrap popover event triggered when the popover opens
                $.tablesorter.columnSelector.attachTo($('#showTable, #animeTable'), '#popover-target');
            });

            // Moved and rewritten this from displayShow. This changes the button when clicked for collapsing/expanding the
            // Season to Show Episodes or Hide Episodes.
            $(function() {
                $('.collapse.toggle').on('hide.bs.collapse', function () {
                    var reg = /collapseSeason-([0-9]+)/g;
                    var result = reg.exec(this.id);
                    $('#showseason-' + result[1]).text('Show Episodes');
                });
                $('.collapse.toggle').on('show.bs.collapse', function () {
                    var reg = /collapseSeason-([0-9]+)/g;
                    var result = reg.exec(this.id);
                    $('#showseason-' + result[1]).text('Hide Episodes');
                });
            });

            // Set the season exception based on using the get_xem_numbering_for_show() for animes if available in data.xemNumbering,
            // or else try to map using just the data.season_exceptions.
            function setSeasonSceneException(data) {
                $.each(data.seasonExceptions, function(season, nameExceptions) {
                    var foundInXem = false;
                    // Check if it is a season name exception, we don't handle the show name exceptions here
                    if (season >= 0) {
                        // Loop through the xem mapping, and check if there is a xem_season, that needs to show the season name exception
                        $.each(data.xemNumbering, function(indexerSeason, xemSeason) {
                            if (xemSeason === parseInt(season, 10)) {
                                foundInXem = true;
                                $('<img>', {
                                    id: 'xem-exception-season-' + xemSeason,
                                    alt: '[xem]',
                                    height: '16',
                                    width: '16',
                                    src: 'images/xem.png',
                                    title: nameExceptions.join(', ')
                                }).appendTo('[data-season=' + indexerSeason + ']');
                            }
                        });

                        // This is not a xem season exception, let's set the exceptions as a medusa exception
                        if (!foundInXem) {
                            $('<img>', {
                                id: 'xem-exception-season-' + season,
                                alt: '[medusa]',
                                height: '16',
                                width: '16',
                                src: 'images/ico/favicon-16.png',
                                title: nameExceptions.join(', ')
                            }).appendTo('[data-season=' + season + ']');
                        }
                    }
                });
            }

            // @TODO: OMG: This is just a basic json, in future it should be based on the CRUD route.
            // Get the season exceptions and the xem season mappings.
            $.getJSON('home/getSeasonSceneExceptions', {
                indexer: $('input#indexer').val(),
                indexer_id: $('input#showID').val() // eslint-disable-line camelcase
            }, function(data) {
                setSeasonSceneException(data);
            });
        },
        snatchSelection: function() {
            if (SICKRAGE.info.fanartBackground) {
                 $.backstretch('showPoster/?show=' + $('#showID').attr('value') + '&which=fanart');
                 $('.backstretch').css('opacity', SICKRAGE.info.fanartBackgroundOpacity).fadeIn(500);
            }
            var spinner = $('#searchNotification');
            var updateSpinner = function(spinner, message, showSpinner) {
                if (showSpinner) {
                    $(spinner).html('<img id="searchingAnim" src="images/loading32' + SICKRAGE.info.themeSpinner + '.gif" height="16" width="16" />&nbsp;' + message);
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
                $.getJSON(this.href, function (data) {
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
                    success: function (data) {
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
                    error: function () {
                        // repeat = false;
                        console.log('Error occurred!!');
                        $('.manualSearchButton').removeAttr('disabled');
                    },
                    complete: function () {
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
            }).on('shown.bs.popover', function () { // bootstrap popover event triggered when the popover opens
                $.tablesorter.columnSelector.attachTo($('#showTable'), '#popover-target');
            });

            $('#btnReset').click(function() {
                $('#showTable')
                .trigger('saveSortReset') // clear saved sort
                .trigger('sortReset');    // reset current table sort
                return false;
            });

            $(function() {
                $('body').on('hide.bs.collapse', '.collapse.toggle', function () {
                    $('#showhistory').text('Show History');
                    $('#wrapper').prop('data-history-toggle', 'hide');
                });
                $('body').on('show.bs.collapse', '.collapse.toggle', function () {
                    $('#showhistory').text('Hide History');
                    $('#wrapper').prop('data-history-toggle', 'show');
                });
            });
        },
        postProcess: function() {
            $('#episodeDir').fileBrowser({
                title: 'Select Unprocessed Episode Folder',
                key: 'postprocessPath'
            });
        },
        status: function() {
            $('#schedulerStatusTable').tablesorter({
                widgets: ['saveSort', 'zebra'],
                textExtraction: {
                    5: function(node) {
                        return $(node).data('seconds');
                    },
                    6: function(node) {
                        return $(node).data('seconds');
                    }
                },
                headers: {
                    5: {
                        sorter: 'digit'
                    },
                    6: {
                        sorter: 'digit'
                    }
                }
            });
            $('#queueStatusTable').tablesorter({
                widgets: ['saveSort', 'zebra'],
                sortList: [[3, 0], [4, 0], [2, 1]]
            });
        },
        restart: function() {
            var currentPid = $('.messages').attr('current-pid');
            var defaultPage = $('.messages').attr('default-page');
            var checkIsAlive = setInterval(function() {
                $.get('home/is_alive/', function(data) {
                    if (data.msg.toLowerCase() === 'nope') {
                        // if it's still initializing then just wait and try again
                        $('#restart_message').show();
                    } else if (currentPid === '' || data.msg === currentPid) {
                        $('#shut_down_loading').hide();
                        $('#shut_down_success').show();
                        currentPid = data.msg;
                    } else {
                        clearInterval(checkIsAlive);
                        $('#restart_loading').hide();
                        $('#restart_success').show();
                        $('#refresh_message').show();
                        setTimeout(function() {
                            window.location = defaultPage + '/';
                        }, 5000);
                    }
                }, 'jsonp');
            }, 100);
        },
        editShow: function() {
            if (SICKRAGE.info.fanartBackground) {
                $.backstretch('showPoster/?show=' + $('#show').attr('value') + '&which=fanart');
                $('.backstretch').css('opacity', SICKRAGE.info.fanartBackgroundOpacity).fadeIn(500);
            }
        }
    },
    manage: {
        init: function() {
            $.makeEpisodeRow = function(indexerId, season, episode, name, checked) {
                var row = '';
                row += ' <tr class="' + $('#row_class').val() + ' show-' + indexerId + '">';
                row += '  <td class="tableleft" align="center"><input type="checkbox" class="' + indexerId + '-epcheck" name="' + indexerId + '-' + season + 'x' + episode + '"' + (checked ? ' checked' : '') + '></td>';
                row += '  <td>' + season + 'x' + episode + '</td>';
                row += '  <td class="tableright" style="width: 100%">' + name + '</td>';
                row += ' </tr>';

                return row;
            };

            $.makeSubtitleRow = function(indexerId, season, episode, name, subtitles, checked) {
                var row = '';
                row += '<tr class="good show-' + indexerId + '">';
                row += '<td align="center"><input type="checkbox" class="' + indexerId + '-epcheck" name="' + indexerId + '-' + season + 'x' + episode + '"' + (checked ? ' checked' : '') + '></td>';
                row += '<td style="width: 2%;">' + season + 'x' + episode + '</td>';
                if (subtitles.length > 0) {
                    row += '<td style="width: 8%;">';
                    subtitles = subtitles.split(',');
                    for (var i in subtitles) {
                        if ({}.hasOwnProperty.call(subtitles, i)) {
                            row += '<img src="images/subtitles/flags/' + subtitles[i] + '.png" width="16" height="11" alt="' + subtitles[i] + '" />&nbsp;';
                        }
                    }
                    row += '</td>';
                } else {
                    row += '<td style="width: 8%;">None</td>';
                }
                row += '<td>' + name + '</td>';
                row += '</tr>';

                return row;
            };
        },
        index: function() {
            $('.resetsorting').on('click', function() {
                $('table').trigger('filterReset');
            });

            $('#massUpdateTable:has(tbody tr)').tablesorter({
                sortList: [[1, 0]],
                textExtraction: {
                    2: function(node) { return $(node).find('span').text().toLowerCase(); }, // eslint-disable-line brace-style
                    3: function(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
                    4: function(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
                    5: function(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
                    6: function(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
                    7: function(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
                    8: function(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
                    9: function(node) { return $(node).find('img').attr('alt'); } // eslint-disable-line brace-style
                },
                widgets: ['zebra', 'filter', 'columnSelector'],
                headers: {
                    0: {sorter: false, filter: false},
                    1: {sorter: 'showNames'},
                    2: {sorter: 'quality'},
                    3: {sorter: 'sports'},
                    4: {sorter: 'scene'},
                    5: {sorter: 'anime'},
                    6: {sorter: 'flatfold'},
                    7: {sorter: 'paused'},
                    8: {sorter: 'subtitle'},
                    9: {sorter: 'default_ep_status'},
                    10: {sorter: 'status'},
                    11: {sorter: false},
                    12: {sorter: false},
                    13: {sorter: false},
                    14: {sorter: false},
                    15: {sorter: false},
                    16: {sorter: false}
                },
                widgetOptions: {
                    columnSelector_mediaquery: false // eslint-disable-line camelcase
                }
            });
            $('#popover').popover({
                placement: 'bottom',
                html: true, // required if content has HTML
                content: '<div id="popover-target"></div>'
            }).on('shown.bs.popover', function () { // bootstrap popover event triggered when the popover opens
                // call this function to copy the column selection code into the popover
                $.tablesorter.columnSelector.attachTo($('#massUpdateTable'), '#popover-target');
            });
        },
        backlogOverview: function() {
            $('#pickShow').on('change', function() {
                var id = $(this).val();
                if (id) {
                    $('html,body').animate({scrollTop: $('#show-' + id).offset().top - 25}, 'slow');
                }
            });
        },
        failedDownloads: function() {
            $('#failedTable:has(tbody tr)').tablesorter({
                widgets: ['zebra'],
                sortList: [[0, 0]],
                headers: {3: {sorter: false}}
            });
            $('#limit').on('change', function() {
                window.location.href = 'manage/failedDownloads/?limit=' + $(this).val();
            });

            $('#submitMassRemove').on('click', function() {
                var removeArr = [];

                $('.removeCheck').each(function() {
                    if (this.checked === true) {
                        removeArr.push($(this).attr('id').split('-')[1]);
                    }
                });

                if (removeArr.length === 0) {
                    return false;
                }

                window.location.href = 'manage/failedDownloads?toRemove=' + removeArr.join('|');
            });

            if ($('.removeCheck').length) {
                $('.removeCheck').each(function(name) {
                    var lastCheck = null;
                    $(name).click(function(event) {
                        if (!lastCheck || !event.shiftKey) {
                            lastCheck = this;
                            return;
                        }

                        var check = this;
                        var found = 0;

                        $(name + ':visible').each(function() {
                            if (found === 1) {
                                this.checked = lastCheck.checked;
                            }
                            if (found === 2) {
                                return false;
                            }

                            if (this === check || this === lastCheck) {
                                found++;
                            }
                        });
                    });
                });
            }
        },
        massEdit: function() {
            $('#location').fileBrowser({title: 'Select Show Location'});
        },
        episodeStatuses: function() {
            $('.allCheck').on('click', function() {
                var indexerId = $(this).attr('id').split('-')[1];
                $('.' + indexerId + '-epcheck').prop('checked', $(this).prop('checked'));
            });

            $('.get_more_eps').on('click', function() {
                var curIndexerId = $(this).attr('id');
                var checked = $('#allCheck-' + curIndexerId).prop('checked');
                var lastRow = $('tr#' + curIndexerId);
                var clicked = $(this).attr('data-clicked');
                var action = $(this).attr('value');

                if (clicked) {
                    if (action.toLowerCase() === 'collapse') {
                        $('table tr').filter('.show-' + curIndexerId).hide();
                        $(this).prop('value', 'Expand');
                    } else if (action.toLowerCase() === 'expand') {
                        $('table tr').filter('.show-' + curIndexerId).show();
                        $(this).prop('value', 'Collapse');
                    }
                } else {
                    $.getJSON('manage/showEpisodeStatuses', {
                        indexer_id: curIndexerId, // eslint-disable-line camelcase
                        whichStatus: $('#oldStatus').val()
                    }, function (data) {
                        $.each(data, function(season, eps) {
                            $.each(eps, function(episode, name) {
                                lastRow.after($.makeEpisodeRow(curIndexerId, season, episode, name, checked));
                            });
                        });
                    });
                    $(this).prop('data-clicked', 1);
                    $(this).prop('value', 'Collapse');
                }
            });

            // selects all visible episode checkboxes.
            $('.selectAllShows').on('click', function() {
                $('.allCheck').each(function() {
                    this.checked = true;
                });
                $('input[class*="-epcheck"]').each(function() {
                    this.checked = true;
                });
            });

            // clears all visible episode checkboxes and the season selectors
            $('.unselectAllShows').on('click', function() {
                $('.allCheck').each(function() {
                    this.checked = false;
                });
                $('input[class*="-epcheck"]').each(function() {
                    this.checked = false;
                });
            });
        },
        subtitleMissed: function() {
            $('.allCheck').on('click', function() {
                var indexerId = $(this).attr('id').split('-')[1];
                $('.' + indexerId + '-epcheck').prop('checked', $(this).prop('checked'));
            });

            $('.get_more_eps').on('click', function() {
                var indexerId = $(this).attr('id');
                var checked = $('#allCheck-' + indexerId).prop('checked');
                var lastRow = $('tr#' + indexerId);
                var clicked = $(this).attr('data-clicked');
                var action = $(this).attr('value');

                if (clicked) {
                    if (action === 'Collapse') {
                        $('table tr').filter('.show-' + indexerId).hide();
                        $(this).prop('value', 'Expand');
                    } else if (action === 'Expand') {
                        $('table tr').filter('.show-' + indexerId).show();
                        $(this).prop('value', 'Collapse');
                    }
                } else {
                    $.getJSON('manage/showSubtitleMissed', {
                        indexer_id: indexerId, // eslint-disable-line camelcase
                        whichSubs: $('#selectSubLang').val()
                    }, function(data) {
                        $.each(data, function(season, eps) {
                            $.each(eps, function(episode, data) {
                                lastRow.after($.makeSubtitleRow(indexerId, season, episode, data.name, data.subtitles, checked));
                            });
                        });
                    });
                    $(this).prop('data-clicked', 1);
                    $(this).prop('value', 'Collapse');
                }
            });

            // selects all visible episode checkboxes.
            $('.selectAllShows').on('click', function() {
                $('.allCheck').each(function() {
                    this.checked = true;
                });
                $('input[class*="-epcheck"]').each(function() {
                    this.checked = true;
                });
            });

            // clears all visible episode checkboxes and the season selectors
            $('.unselectAllShows').on('click', function() {
                $('.allCheck').each(function() {
                    this.checked = false;
                });
                $('input[class*="-epcheck"]').each(function() {
                    this.checked = false;
                });
            });
        }
    },
    history: {
        index: function() {
            $('#historyTable:has(tbody tr)').tablesorter({
                widgets: ['zebra', 'filter'],
                sortList: [[0, 1]],
                textExtraction: (function() {
                    if (isMeta('HISTORY_LAYOUT', ['detailed'])) {
                        return {
                            0: function(node) { return $(node).find('time').attr('datetime'); }, // eslint-disable-line brace-style
                            4: function(node) { return $(node).find('span').text().toLowerCase(); } // eslint-disable-line brace-style
                        };
                    }
                    return {
                        0: function(node) { return $(node).find('time').attr('datetime'); }, // eslint-disable-line brace-style
                        1: function(node) { return $(node).find('span').text().toLowerCase(); }, // eslint-disable-line brace-style
                        2: function(node) { return $(node).attr('provider') == null ? null : $(node).attr('provider').toLowerCase(); }, // eslint-disable-line brace-style
                        5: function(node) { return $(node).attr('quality').toLowerCase(); } // eslint-disable-line brace-style
                    };
                }()),
                headers: (function() {
                    if (isMeta('HISTORY_LAYOUT', ['detailed'])) {
                        return {
                            0: {sorter: 'realISODate'},
                            4: {sorter: 'quality'}
                        };
                    }
                    return {
                        0: {sorter: 'realISODate'},
                        4: {sorter: false},
                        5: {sorter: 'quality'}
                    };
                }())
            });

            $('#history_limit').on('change', function() {
                window.location.href = 'history/?limit=' + $(this).val();
            });
        }
    },
    errorlogs: {
        viewlogs: function() {
            $('#min_level,#log_filter,#log_search,#log_period').on('keyup change', _.debounce(function() {
                $('#min_level').prop('disabled', true);
                $('#log_filter').prop('disabled', true);
                $('#log_period').prop('disabled', true);
                document.body.style.cursor = 'wait';
                var params = $.param({
                    min_level: $('select[name=min_level]').val(),
                    log_filter: $('select[name=log_filter]').val(),
                    log_period: $('select[name=log_period]').val(),
                    log_search: $('#log_search').val()
                });
                $.get('errorlogs/viewlog/?' + params, function(data) {
                    history.pushState('data', '', 'errorlogs/viewlog/?' + params);
                    $('pre').html($(data).find('pre').html());
                    $('#min_level').prop('disabled', false);
                    $('#log_filter').prop('disabled', false);
                    $('#log_period').prop('disabled', false);
                    document.body.style.cursor = 'default';
                });
            }, 500));
        }
    },
    schedule: {
        index: function() {
            if (isMeta('comingEpsLayout', ['list'])) {
                var sortCodes = {
                    date: 0,
                    show: 2,
                    network: 5
                };
                var sort = SICKRAGE.info.comingEpsSort;
                var sortList = (sort in sortCodes) ? [[sortCodes[sort], 0]] : [[0, 0]];

                $('#showListTable:has(tbody tr)').tablesorter({
                    widgets: ['stickyHeaders', 'filter', 'columnSelector', 'saveSort'],
                    sortList: sortList,
                    textExtraction: {
                        0: function(node) { return $(node).find('time').attr('datetime'); },
                        1: function(node) { return $(node).find('time').attr('datetime'); },
                        7: function(node) { return $(node).find('span').text().toLowerCase(); }
                    },
                    headers: {
                        0: {sorter: 'realISODate'},
                        1: {sorter: 'realISODate'},
                        2: {sorter: 'loadingNames'},
                        4: {sorter: 'loadingNames'},
                        7: {sorter: 'quality'},
                        8: {sorter: false},
                        9: {sorter: false}
                    },
                    widgetOptions: {
                        filter_columnFilters: true, // eslint-disable-line camelcase
                        filter_hideFilters: true, // eslint-disable-line camelcase
                        filter_saveFilters: true, // eslint-disable-line camelcase
                        columnSelector_mediaquery: false // eslint-disable-line camelcase
                    }
                });

                $.ajaxEpSearch();
            }

            if (isMeta('comingEpsLayout', ['banner', 'poster'])) {
                $.ajaxEpSearch({
                    size: 16,
                    loadingImage: 'loading16' + SICKRAGE.info.themeSpinner + '.gif'
                });
                $('.ep_summary').hide();
                $('.ep_summaryTrigger').on('click', function() {
                    $(this).next('.ep_summary').slideToggle('normal', function() {
                        $(this).prev('.ep_summaryTrigger').prop('src', function(i, src) {
                            return $(this).next('.ep_summary').is(':visible') ? src.replace('plus', 'minus') : src.replace('minus', 'plus');
                        });
                    });
                });
            }

            $('#popover').popover({
                placement: 'bottom',
                html: true, // required if content has HTML
                content: '<div id="popover-target"></div>'
            }).on('shown.bs.popover', function () { // bootstrap popover event triggered when the popover opens
                // call this function to copy the column selection code into the popover
                $.tablesorter.columnSelector.attachTo($('#showListTable'), '#popover-target');
            });
        }
    },
    config: {},
    addShows: {}
};

var UTIL = {
    exec: function(controller, action) {
        var ns = SICKRAGE;
        action = (action === undefined) ? 'init' : action;

        if (controller !== '' && ns[controller] && typeof ns[controller][action] === 'function') {
            ns[controller][action]();
        }
    },
    init: function() {
        var body = document.body;
        var controller = body.getAttribute('data-controller');
        var action = body.getAttribute('data-action');

        UTIL.exec('common');
        UTIL.exec(controller);
        UTIL.exec(controller, action);
    }
};

$.ajaxSetup({
    beforeSend: function(xhr, options) {
        if (/^https?:\/\/|^\/\//i.test(options.url) === false) {
            options.url = webRoot + options.url;
        }
    }
});

$.ajax({
    url: apiRoot + 'info?api_key=' + apiKey,
    type: 'GET',
    dataType: 'json'
}).done(function(data) {
    if (data.status === 200) {
        SICKRAGE.info = data.data;
        SICKRAGE.info.themeSpinner = SICKRAGE.info.themeName === 'dark' ? '-dark' : '';
        SICKRAGE.info.loading = '<img src="images/loading16' + SICKRAGE.info.themeSpinner + '.gif" height="16" width="16" />';

        if (navigator.userAgent.indexOf('PhantomJS') === -1) {
            $(document).ready(UTIL.init);
        }
    }
});

function isMeta(pyVar, result) {
    var reg = new RegExp(result.length > 1 ? result.join('|') : result);
    if (pyVar.match('sickbeard')) {
        pyVar.split('.')[1].toLowerCase().replace(/(_\w)/g, function(m) {
            return m[1].toUpperCase();
        });
    }
    return (reg).test(SICKRAGE.info[pyVar]);
}
