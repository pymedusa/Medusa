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
MEDUSA.manage.index = function () {
    $('.resetsorting').on('click', function () {
        $('table').trigger('filterReset');
    });

    $('#massUpdateTable:has(tbody tr)').tablesorter({
        sortList: [[1, 0]],
        textExtraction: {
            2: function (node) {
                return $(node).find('span').text().toLowerCase();
            }, // eslint-disable-line brace-style
            3: function (node) {
                return $(node).find('img').attr('alt');
            }, // eslint-disable-line brace-style
            4: function (node) {
                return $(node).find('img').attr('alt');
            }, // eslint-disable-line brace-style
            5: function (node) {
                return $(node).find('img').attr('alt');
            }, // eslint-disable-line brace-style
            6: function (node) {
                return $(node).find('img').attr('alt');
            }, // eslint-disable-line brace-style
            7: function (node) {
                return $(node).find('img').attr('alt');
            }, // eslint-disable-line brace-style
            8: function (node) {
                return $(node).find('img').attr('alt');
            }, // eslint-disable-line brace-style
            9: function (node) {
                return $(node).find('img').attr('alt');
            } // eslint-disable-line brace-style
        },
        widgets: ['zebra', 'filter', 'columnSelector'],
        headers: {
            0: { sorter: false, filter: false },
            1: { sorter: 'showNames' },
            2: { sorter: 'quality' },
            3: { sorter: 'sports' },
            4: { sorter: 'scene' },
            5: { sorter: 'anime' },
            6: { sorter: 'flatfold' },
            7: { sorter: 'paused' },
            8: { sorter: 'subtitle' },
            9: { sorter: 'default_ep_status' },
            10: { sorter: 'status' },
            11: { sorter: false },
            12: { sorter: false },
            13: { sorter: false },
            14: { sorter: false },
            15: { sorter: false },
            16: { sorter: false }
        },
        widgetOptions: {
            columnSelector_mediaquery: false // eslint-disable-line camelcase
        }
    });
    $('#popover').popover({
        placement: 'bottom',
        html: true, // required if content has HTML
        content: '<div id="popover-target"></div>'
    }).on('shown.bs.popover', function () {
        // bootstrap popover event triggered when the popover opens
        // call this function to copy the column selection code into the popover
        $.tablesorter.columnSelector.attachTo($('#massUpdateTable'), '#popover-target');
    });
};

},{"../core":2}]},{},[3]);

//# sourceMappingURL=index.js.map
