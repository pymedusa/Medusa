(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
const baseUrl = $('body').attr('api-root');
const idToken = $('body').attr('api-key');

const api = axios.create({
    baseURL: baseUrl,
    timeout: 10000,
    headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Api-Key': idToken
    }
});

module.exports = api;

},{}],2:[function(require,module,exports){
const api = require('./api');

// eslint-disable-line max-lines
// @TODO Move these into common.ini when possible,
//       currently we can't do that as browser.js and a few others need it before this is loaded
const topImageHtml = '<img src="images/top.gif" width="31" height="11" alt="Jump to top" />'; // eslint-disable-line no-unused-vars
const apiRoot = $('body').attr('api-root');
const apiKey = $('body').attr('api-key');

const MEDUSA = {
    common: {},
    config: {},
    home: {},
    manage: {},
    history: {},
    errorlogs: {},
    schedule: {},
    addShows: {}
};

const UTIL = {
    exec(controller, action) {
        const ns = MEDUSA;
        action = action === undefined ? 'init' : action;

        if (controller !== '' && ns[controller] && typeof ns[controller][action] === 'function') {
            ns[controller][action]();
        }
    },
    init() {
        if (typeof startVue === 'function') {
            // eslint-disable-line no-undef
            startVue(); // eslint-disable-line no-undef
        } else {
            $('[v-cloak]').removeAttr('v-cloak');
        }

        const body = document.body;
        $('[asset]').each(function () {
            const asset = $(this).attr('asset');
            const series = $(this).attr('series');
            const path = apiRoot + 'series/' + series + '/asset/' + asset + '?api_key=' + apiKey;
            if (this.tagName.toLowerCase() === 'img') {
                if ($(this).attr('lazy') === 'on') {
                    $(this).attr('data-original', path);
                } else {
                    $(this).attr('src', path);
                }
            }
            if (this.tagName.toLowerCase() === 'a') {
                $(this).attr('href', path);
            }
        });
        const controller = body.getAttribute('data-controller');
        const action = body.getAttribute('data-action');

        UTIL.exec('common');
        UTIL.exec(controller);
        UTIL.exec(controller, action);
    }
};

$.extend({
    isMeta(pyVar, result) {
        const reg = new RegExp(result.length > 1 ? result.join('|') : result);

        if (typeof pyVar === 'object' && Object.keys(pyVar).length === 1) {
            return reg.test(MEDUSA.config[Object.keys(pyVar)[0]][pyVar[Object.keys(pyVar)[0]]]);
        }
        if (pyVar.match('medusa')) {
            pyVar.split('.')[1].toLowerCase().replace(/(_\w)/g, m => m[1].toUpperCase());
        }
        return reg.test(MEDUSA.config[pyVar]);
    }
});

$.fn.extend({
    addRemoveWarningClass(_) {
        if (_) {
            return $(this).removeClass('warning');
        }
        return $(this).addClass('warning');
    }
});

const triggerConfigLoaded = function () {
    // Create the event.
    const event = new CustomEvent('build', { detail: 'medusa config loaded' });
    event.initEvent('build', true, true);
    // Trigger the event.
    document.dispatchEvent(event);
};

if (!document.location.pathname.endsWith('/login/')) {
    api.get('config/main').then(response => {
        log.setDefaultLevel('trace');
        $.extend(MEDUSA.config, response.data);
        MEDUSA.config.themeSpinner = MEDUSA.config.themeName === 'dark' ? '-dark' : '';
        MEDUSA.config.loading = '<img src="images/loading16' + MEDUSA.config.themeSpinner + '.gif" height="16" width="16" />';

        if (navigator.userAgent.indexOf('PhantomJS') === -1) {
            $(document).ready(UTIL.init);
        }
        triggerConfigLoaded();
    }).catch(err => {
        log.error(err);
        alert('Unable to connect to Medusa!'); // eslint-disable-line no-alert
    });
}

module.exports = MEDUSA;

},{"./api":1}],3:[function(require,module,exports){
const MEDUSA = require('../core');

MEDUSA.home.snatchSelection = function () {
    // Adjust the summary background position and size on page load and resize
    const moveSummaryBackground = () => {
        const height = $('#summary').height() + 10;
        const top = $('#summary').offset().top + 5;
        $('#summaryBackground').height(height);
        $('#summaryBackground').offset({ top, left: 0 });
        $('#summaryBackground').show();
    };

    $('.imdbPlot').on('click', function () {
        $(this).prev('span').toggle();
        if ($(this).html() === '..show less') {
            $(this).html('..show more');
        } else {
            $(this).html('..show less');
        }
        moveSummaryBackground();
    });

    $(window).on('resize', () => {
        moveSummaryBackground();
    });

    const updateSpinner = (message, showSpinner) => {
        // Get spinner object as needed
        const spinner = $('#searchNotification');
        if (showSpinner) {
            message = '<img id="searchingAnim" src="images/loading32' + MEDUSA.config.themeSpinner + '.gif" height="16" width="16" />&nbsp;' + message;
        }
        $(spinner).empty().append(message);
    };

    // Check the previous status of the history table, for hidden or shown, through the data attribute
    // data-history-toggle-hidden
    const toggleHistoryTable = () => {
        // Get previous state which was saved on the wrapper
        const showOrHide = $('#wrapper').attr('data-history-toggle');
        $('#historydata').collapse(showOrHide);
    };

    $.fn.loadContainer = function (path, loadingTxt, errorTxt, callback) {
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
    $('body').on('click', '.epManualSearch', function (event) {
        event.preventDefault();
        const link = this;
        $(link).children('img').prop('src', 'images/loading16.gif');
        $.getJSON(this.href, data => {
            if (data.result === 'success') {
                $(link).children('img').prop('src', 'images/save.png');
            } else {
                $(link).children('img').prop('src', 'images/no16.png');
            }
        });
    });

    $.fn.generateStars = function () {
        return this.each((i, e) => {
            $(e).html($('<span/>').width($(e).text() * 12));
        });
    };

    const initTableSorter = table => {
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
            textExtraction: (() => {
                return {
                    // 6: The size column needs an explicit field for the filtering on raw size.
                    6(node) {
                        return node.getAttribute('data-size');
                    }
                };
            })()
        });
    };

    $('.imdbstars').generateStars();

    const checkCacheUpdates = function (repeat = true) {
        const self = this;
        const show = $('meta[data-last-prov-updates]').attr('data-show');
        const season = $('meta[data-last-prov-updates]').attr('data-season');
        const episode = $('meta[data-last-prov-updates]').attr('data-episode');
        const data = $('meta[data-last-prov-updates]').data('last-prov-updates');
        const manualSearchType = $('meta[data-last-prov-updates]').attr('data-manual-search-type');
        let pollInterval = 5000;

        let urlParams = show + '&season=' + season + '&episode=' + episode;

        if (manualSearchType === 'season') {
            urlParams += '&manual_search_type=' + manualSearchType;
        }

        if (!$.isNumeric(show) || !$.isNumeric(season) || !$.isNumeric(episode)) {
            setTimeout(() => {
                checkCacheUpdates(true);
            }, 200);
        }

        self.refreshResults = function () {
            $('#manualSearchTbody').loadContainer('home/snatchSelection?show=' + urlParams, 'Loading new search results...', 'Time out, refresh page to try again', toggleHistoryTable // This is a callback function
            );
        };

        $.ajax({
            url: 'home/manualSearchCheckCache?show=' + urlParams,
            type: 'GET',
            data,
            contentType: 'application/json',
            error() {
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
    };

    setTimeout(checkCacheUpdates, 2000);

    // Click event for the reload results and force search buttons
    $('body').on('click', '.manualSearchButton', function (event) {
        event.preventDefault();
        $('.manualSearchButton').prop('disabled', true);
        const show = $('meta[data-last-prov-updates]').attr('data-show');
        const season = $('meta[data-last-prov-updates]').attr('data-season');
        const episode = $('meta[data-last-prov-updates]').attr('data-episode');
        const manualSearchType = $('meta[data-last-prov-updates]').attr('data-manual-search-type');
        const forceSearch = $(this).attr('data-force-search');

        if ($.isNumeric(show) && $.isNumeric(season) && $.isNumeric(episode)) {
            updateSpinner('Started a forced manual search...', true);
            $.getJSON('home/snatchSelection', {
                show,
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
        html: true,
        content: '<div id="popover-target"></div>'
    }).on('shown.bs.popover', () => {
        $.tablesorter.columnSelector.attachTo($('#srchresults'), '#popover-target');
    });

    $('#btnReset').on('click', () => {
        $('#showTable').trigger('saveSortReset') // Clear saved sort
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

    $(document).on('click', '.release-name-ellipses, .release-name-ellipses-toggled', el => {
        const target = $(el.currentTarget);

        if (target.hasClass('release-name-ellipses')) {
            target.switchClass('release-name-ellipses', 'release-name-ellipses-toggled', 100);
        } else {
            target.switchClass('release-name-ellipses-toggled', 'release-name-ellipses', 100);
        }
    });
};

},{"../core":2}]},{},[3]);

//# sourceMappingURL=snatch-selection.js.map
