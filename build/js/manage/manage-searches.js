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
const MEDUSA = require('../core');
MEDUSA.manage.manageSearches = function () {
    /**
     * Get total number current scene exceptions per source. Will request medusa, xem and anidb name exceptions.
     * @param exceptions - A list of exception types with their last_updates.
     */
    var updateExceptionTable = function (exceptions) {
        var status = $('#sceneExceptionStatus');

        var medusaException = exceptions.data.filter(function (obj) {
            return obj.id === 'local';
        });
        var cusExceptionDate = new Date(medusaException[0].lastRefresh * 1000).toLocaleDateString();

        var xemException = exceptions.data.filter(function (obj) {
            return obj.id === 'xem';
        });
        var xemExceptionDate = new Date(xemException[0].lastRefresh * 1000).toLocaleDateString();

        var anidbException = exceptions.data.filter(function (obj) {
            return obj.id === 'anidb';
        });
        var anidbExceptionDate = new Date(anidbException[0].lastRefresh * 1000).toLocaleDateString();

        var table = $('<ul class="simpleList"></ul>').append('<li>' + '<a href="' + MEDUSA.config.anonRedirect + 'https://github.com/pymedusa/Medusa/wiki/Scene-exceptions-and-numbering">' + 'Last updated medusa\'s exceptions</a> ' + cusExceptionDate).append('<li>' + '<a href="' + MEDUSA.config.anonRedirect + 'http://thexem.de">' + 'Last updated xem exceptions</a> ' + xemExceptionDate).append('<li>Last updated anidb exceptions ' + anidbExceptionDate);

        status.append(table);
        $('.forceSceneExceptionRefresh').removeClass('disabled');
    };

    /**
     * Update an element with a spinner gif and a descriptive message.
     * @param spinnerContainer - An element we can use to add the spinner and message to.
     * @param message - A string with the message to display behind the spinner.
     * @param showSpinner - A boolean to show or not show the spinner (gif).
     */
    var updateSpinner = function (spinnerContainer, message, showSpinner) {
        if (showSpinner) {
            message = '<img id="searchingAnim" src="images/loading32' + MEDUSA.config.themeSpinner + '.gif" height="16" width="16" />&nbsp;' + message;
        }
        $(spinnerContainer).empty().append(message);
    };

    /**
     * Trigger the force refresh of all the exception types.
     */
    $('.forceSceneExceptionRefresh').on('click', function () {
        var status = $('#sceneExceptionStatus');
        // Start a spinner.
        updateSpinner(status, 'Retrieving scene exceptions...', true);

        api.post('alias-source/all/operation', { type: 'REFRESH' }, {
            timeout: 60000
        }).then(function (response) {
            status[0].innerHTML = '';
            status.append($('<span></span>').text(response.data.result));

            api.get('alias-source').then(function (response) {
                updateExceptionTable(response);
                $('.forceSceneExceptionRefresh').addClass('disabled');
            }).catch(function (err) {
                log.error('Trying to get scene exceptions failed with error: ' + err);
                updateSpinner(status, 'Trying to get scene exceptions failed with error: ' + err, false);
            });
            updateSpinner(status, 'Finished updating scene exceptions.', false);
        }).catch(function (err) {
            log.error('Trying to update scene exceptions failed with error: ' + err);
            updateSpinner(status, 'Trying to update scene exceptions failed with error: ' + err, false);
        });
    });

    // Initially load the exception types last updates on page load.
    api.get('alias-source').then(function (response) {
        updateExceptionTable(response);
    }).catch(function (err) {
        log.error('Trying to get scene exceptions failed with error: ' + err);
    });
};

},{"../core":1}]},{},[2]);

//# sourceMappingURL=manage-searches.js.map
