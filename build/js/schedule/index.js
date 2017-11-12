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
MEDUSA.schedule.index = function () {
    if ($.isMeta({ layout: 'schedule' }, ['list'])) {
        var sortCodes = {
            date: 0,
            show: 2,
            network: 5
        };
        var sort = MEDUSA.config.comingEpsSort;
        var sortList = sort in sortCodes ? [[sortCodes[sort], 0]] : [[0, 0]];

        $('#showListTable:has(tbody tr)').tablesorter({
            widgets: ['stickyHeaders', 'filter', 'columnSelector', 'saveSort'],
            sortList: sortList,
            textExtraction: {
                0: function (node) {
                    return $(node).find('time').attr('datetime');
                }, // eslint-disable-line brace-style
                1: function (node) {
                    return $(node).find('time').attr('datetime');
                }, // eslint-disable-line brace-style
                7: function (node) {
                    return $(node).find('span').text().toLowerCase();
                }, // eslint-disable-line brace-style
                8: function (node) {
                    return $(node).find('a[data-indexer-name]').attr('data-indexer-name');
                } // eslint-disable-line brace-style
            },
            headers: {
                0: { sorter: 'realISODate' },
                1: { sorter: 'realISODate' },
                2: { sorter: 'loadingNames' },
                4: { sorter: 'loadingNames' },
                7: { sorter: 'quality' },
                8: { sorter: 'text' },
                9: { sorter: false }
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

    if ($.isMeta({ layout: 'schedule' }, ['banner', 'poster'])) {
        $.ajaxEpSearch({
            size: 16,
            loadingImage: 'loading16' + MEDUSA.config.themeSpinner + '.gif'
        });
        $('.ep_summary').hide();
        $('.ep_summaryTrigger').on('click', function () {
            $(this).next('.ep_summary').slideToggle('normal', function () {
                $(this).prev('.ep_summaryTrigger').prop('src', function (i, src) {
                    return $(this).next('.ep_summary').is(':visible') ? src.replace('plus', 'minus') : src.replace('minus', 'plus');
                });
            });
        });
    }

    $('#popover').popover({
        placement: 'bottom',
        html: true, // required if content has HTML
        content: '<div id="popover-target"></div>'
    }).on('shown.bs.popover', function () {
        // bootstrap popover event triggered when the popover opens
        // call this function to copy the column selection code into the popover
        $.tablesorter.columnSelector.attachTo($('#showListTable'), '#popover-target');
    });

    $('.show-option select[name="layout"]').on('change', function () {
        api.patch('config/main', {
            layout: {
                schedule: $(this).val()
            }
        }).then(function (response) {
            log.info(response);
            window.location.reload();
        }).catch(function (err) {
            log.info(err);
        });
    });
};

},{"../core":2}]},{},[3]);

//# sourceMappingURL=index.js.map
