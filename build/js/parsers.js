(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
// eslint-disable-line max-lines
// @TODO Move these into common.ini when possible,
//       currently we can't do that as browser.js and a few others need it before this is loaded
var topImageHtml = '<img src="images/top.gif" width="31" height="11" alt="Jump to top" />'; // eslint-disable-line no-unused-vars
var apiRoot = $('body').attr('api-root');
var apiKey = $('body').attr('api-key');

var MEDUSA = {
    common: {},
    config: {},
    home: {},
    manage: {},
    history: {},
    errorlogs: {},
    schedule: {},
    addShows: {}
};

var UTIL = {
    exec: function (controller, action) {
        var ns = MEDUSA;
        action = action === undefined ? 'init' : action;

        if (controller !== '' && ns[controller] && typeof ns[controller][action] === 'function') {
            ns[controller][action]();
        }
    },
    init: function () {
        if (typeof startVue === 'function') {
            // eslint-disable-line no-undef
            startVue(); // eslint-disable-line no-undef
        } else {
            $('[v-cloak]').removeAttr('v-cloak');
        }

        var body = document.body;
        $('[asset]').each(function () {
            let asset = $(this).attr('asset');
            let series = $(this).attr('series');
            let path = apiRoot + 'series/' + series + '/asset/' + asset + '?api_key=' + apiKey;
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
        var controller = body.getAttribute('data-controller');
        var action = body.getAttribute('data-action');

        UTIL.exec('common');
        UTIL.exec(controller);
        UTIL.exec(controller, action);
    }
};

$.extend({
    isMeta: function (pyVar, result) {
        // eslint-disable-line no-unused-vars
        var reg = new RegExp(result.length > 1 ? result.join('|') : result);

        if (typeof pyVar === 'object' && Object.keys(pyVar).length === 1) {
            return reg.test(MEDUSA.config[Object.keys(pyVar)[0]][pyVar[Object.keys(pyVar)[0]]]);
        }
        if (pyVar.match('medusa')) {
            pyVar.split('.')[1].toLowerCase().replace(/(_\w)/g, function (m) {
                return m[1].toUpperCase();
            });
        }
        return reg.test(MEDUSA.config[pyVar]);
    }
});

$.fn.extend({
    addRemoveWarningClass: function (_) {
        if (_) {
            return $(this).removeClass('warning');
        }
        return $(this).addClass('warning');
    }
});

var triggerConfigLoaded = function () {
    // Create the event.
    var event = new CustomEvent('build', { detail: 'medusa config loaded' });
    event.initEvent('build', true, true);
    // Trigger the event.
    document.dispatchEvent(event);
};

if (!document.location.pathname.endsWith('/login/')) {
    api.get('config/main').then(function (response) {
        log.setDefaultLevel('trace');
        $.extend(MEDUSA.config, response.data);
        MEDUSA.config.themeSpinner = MEDUSA.config.themeName === 'dark' ? '-dark' : '';
        MEDUSA.config.loading = '<img src="images/loading16' + MEDUSA.config.themeSpinner + '.gif" height="16" width="16" />';

        if (navigator.userAgent.indexOf('PhantomJS') === -1) {
            $(document).ready(UTIL.init);
        }
        triggerConfigLoaded();
    }).catch(function (err) {
        log.error(err);
        alert('Unable to connect to Medusa!'); // eslint-disable-line no-alert
    });
}

module.exports = MEDUSA;

},{}],2:[function(require,module,exports){
const MEDUSA = require('./core');
$.tablesorter.addParser({
    id: 'loadingNames',
    is: function () {
        return false;
    },
    format: function (s) {
        if (s.indexOf('Loading...') === 0) {
            return s.replace('Loading...', '000');
        }
        return MEDUSA.config.sortArticle ? s || '' : (s || '').replace(/^(The|A|An)\s/i, ''); // eslint-disable-line no-undef
    },
    type: 'text'
});
$.tablesorter.addParser({
    id: 'quality',
    is: function () {
        return false;
    },
    format: function (s) {
        var replacements = {
            custom: 11,
            bluray: 10, // Custom: Only bluray
            hd1080p: 9,
            '1080p': 8, // Custom: Only 1080p
            hdtv: 7, // Custom: 1080p and 720p (only HDTV)
            'web-dl': 6, // Custom: 1080p and 720p (only WEB-DL)
            hd720p: 5,
            '720p': 4, // Custom: Only 720p
            hd: 3,
            sd: 2,
            any: 1,
            best: 0
        };
        return replacements[s.toLowerCase()];
    },
    type: 'numeric'
});
$.tablesorter.addParser({
    id: 'realISODate',
    is: function () {
        return false;
    },
    format: function (s) {
        return new Date(s).getTime();
    },
    type: 'numeric'
});

$.tablesorter.addParser({
    id: 'cDate',
    is: function () {
        return false;
    },
    format: function (s) {
        return s;
    },
    type: 'numeric'
});
$.tablesorter.addParser({
    id: 'eps',
    is: function () {
        return false;
    },
    format: function (s) {
        var match = s.match(/^(.*)/);

        if (match === null || match[1] === '?') {
            return -10;
        }

        var nums = match[1].split(' / ');
        if (nums[0].indexOf('+') !== -1) {
            var numParts = nums[0].split('+');
            nums[0] = numParts[0];
        }

        nums[0] = parseInt(nums[0], 10);
        nums[1] = parseInt(nums[1], 10);

        if (nums[0] === 0) {
            return nums[1];
        }
        var finalNum = parseInt($('meta[data-var="max_download_count"]').data('content') * nums[0] / nums[1], 10);
        var pct = Math.round(nums[0] / nums[1] * 100) / 1000;
        if (finalNum > 0) {
            finalNum += nums[0];
        }

        return finalNum + pct;
    },
    type: 'numeric'
});

},{"./core":1}]},{},[2]);

//# sourceMappingURL=parsers.js.map
