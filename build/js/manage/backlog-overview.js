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
MEDUSA.manage.backlogOverview = function () {
    checkForcedSearch();

    function checkForcedSearch() {
        var pollInterval = 5000;
        var searchStatusUrl = 'home/getManualSearchStatus';
        var showId = $('#series-id').val();
        var url = showId === undefined ? searchStatusUrl : searchStatusUrl + '?show=' + showId;
        $.ajax({
            url: url,
            error: function () {
                pollInterval = 30000;
            },
            type: 'GET',
            dataType: 'JSON',
            complete: function () {
                setTimeout(checkForcedSearch, pollInterval);
            },
            timeout: 15000 // timeout every 15 secs
        }).done(function (data) {
            if (data.episodes) {
                pollInterval = 5000;
            } else {
                pollInterval = 15000;
            }
            updateForcedSearch(data);
        });
    }

    function updateForcedSearch(data) {
        $.each(data.episodes, function (name, ep) {
            var el = $('a[id=' + ep.show + 'x' + ep.season + 'x' + ep.episode + ']');
            var img = el.children('img[data-ep-search]');
            var episodeStatus = ep.status.toLowerCase();
            var episodeSearchStatus = ep.searchstatus.toLowerCase();
            if (el) {
                if (episodeSearchStatus === 'searching' || episodeSearchStatus === 'queued') {
                    // el=$('td#' + ep.season + 'x' + ep.episode + '.search img');
                    img.prop('src', 'images/loading16.gif');
                } else if (episodeSearchStatus === 'finished') {
                    // el=$('td#' + ep.season + 'x' + ep.episode + '.search img');
                    if (episodeStatus.indexOf('snatched') >= 0) {
                        img.prop('src', 'images/yes16.png');
                        setTimeout(function () {
                            img.parent().parent().parent().remove();
                        }, 3000);
                    } else {
                        img.prop('src', 'images/search16.png');
                    }
                }
            }
        });
    }

    $('#pickShow').on('change', function () {
        var id = $(this).val();
        if (id) {
            $('html,body').animate({ scrollTop: $('#show-' + id).offset().top - 25 }, 'slow');
        }
    });

    $('#backlog_period').on('change', function () {
        api.patch('config/main', {
            backlogOverview: {
                period: $(this).val()
            }
        }).then(function (response) {
            log.info(response);
            window.location.reload();
        }).catch(function (err) {
            log.error(err);
        });
    });

    $('#backlog_status').on('change', function () {
        api.patch('config/main', {
            backlogOverview: {
                status: $(this).val()
            }
        }).then(function (response) {
            log.info(response);
            window.location.reload();
        }).catch(function (err) {
            log.error(err);
        });
    });

    $('.forceBacklog').on('click', function () {
        $.get($(this).attr('href'));
        $(this).text('Searching...');
        return false;
    });

    $('.epArchive').on('click', function (event) {
        event.preventDefault();
        var img = $(this).children('img[data-ep-archive]');
        img.prop('title', 'Archiving');
        img.prop('alt', 'Archiving');
        img.prop('src', 'images/loading16.gif');
        var url = $(this).prop('href');
        $.getJSON(url, function (data) {
            // if they failed then just put the red X
            if (data.result.toLowerCase() === 'success') {
                img.prop('src', 'images/yes16.png');
                setTimeout(function () {
                    img.parent().parent().parent().remove();
                }, 3000);
            } else {
                img.prop('src', 'images/no16.png');
            }
            return false;
        });
    });

    $('.epSearch').on('click', function (event) {
        event.preventDefault();
        var img = $(this).children('img[data-ep-search]');
        img.prop('title', 'Searching');
        img.prop('alt', 'Searching');
        img.prop('src', 'images/loading16.gif');
        var url = $(this).prop('href');
        $.getJSON(url, function (data) {
            // if they failed then just put the red X
            if (data.result.toLowerCase() === 'failed') {
                img.prop('src', 'images/no16.png');
            }
            return false;
        });
    });
};

},{"../core":1}]},{},[2]);

//# sourceMappingURL=backlog-overview.js.map
