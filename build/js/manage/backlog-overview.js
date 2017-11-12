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

MEDUSA.manage.backlogOverview = function () {
    const updateForcedSearch = data => {
        $.each(data.episodes, (name, ep) => {
            const el = $('a[id=' + ep.show + 'x' + ep.season + 'x' + ep.episode + ']');
            const img = el.children('img[data-ep-search]');
            const episodeStatus = ep.status.toLowerCase();
            const episodeSearchStatus = ep.searchstatus.toLowerCase();
            if (el) {
                if (episodeSearchStatus === 'searching' || episodeSearchStatus === 'queued') {
                    //
                    // el=$('td#' + ep.season + 'x' + ep.episode + '.search img');
                    img.prop('src', 'images/loading16.gif');
                } else if (episodeSearchStatus === 'finished') {
                    //
                    // el=$('td#' + ep.season + 'x' + ep.episode + '.search img');
                    if (episodeStatus.indexOf('snatched') >= 0) {
                        img.prop('src', 'images/yes16.png');
                        setTimeout(() => {
                            img.parent().parent().parent().remove();
                        }, 3000);
                    } else {
                        img.prop('src', 'images/search16.png');
                    }
                }
            }
        });
    };

    const checkForcedSearch = () => {
        let pollInterval = 5000;
        const searchStatusUrl = 'home/getManualSearchStatus';
        const showId = $('#series-id').val();
        const url = showId === undefined ? searchStatusUrl : searchStatusUrl + '?show=' + showId;
        $.ajax({
            url,
            error: () => {
                pollInterval = 30000;
            },
            type: 'GET',
            dataType: 'JSON',
            complete: () => {
                setTimeout(checkForcedSearch, pollInterval);
            },
            timeout: 15000 // Timeout every 15 secs
        }).done(data => {
            if (data.episodes) {
                pollInterval = 5000;
            } else {
                pollInterval = 15000;
            }
            updateForcedSearch(data);
        });
    };

    checkForcedSearch();

    $('#pickShow').on('change', function () {
        const id = $(this).val();
        if (id) {
            $('html,body').animate({ scrollTop: $('#show-' + id).offset().top - 25 }, 'slow');
        }
    });

    $('#backlog_period').on('change', function () {
        api.patch('config/main', {
            backlogOverview: {
                period: $(this).val()
            }
        }).then(response => {
            log.info(response);
            window.location.reload();
        }).catch(err => {
            log.error(err);
        });
    });

    $('#backlog_status').on('change', function () {
        api.patch('config/main', {
            backlogOverview: {
                status: $(this).val()
            }
        }).then(response => {
            log.info(response);
            window.location.reload();
        }).catch(err => {
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
        const url = $(this).prop('href');
        const img = $(this).children('img[data-ep-archive]');
        img.prop('title', 'Archiving');
        img.prop('alt', 'Archiving');
        img.prop('src', 'images/loading16.gif');

        $.getJSON(url, data => {
            // If they failed then just put the red X
            if (data.result.toLowerCase() === 'success') {
                img.prop('src', 'images/yes16.png');
                setTimeout(() => {
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
        const img = $(this).children('img[data-ep-search]');
        img.prop('title', 'Searching');
        img.prop('alt', 'Searching');
        img.prop('src', 'images/loading16.gif');
        const url = $(this).prop('href');
        $.getJSON(url, data => {
            // If they failed then just put the red X
            if (data.result.toLowerCase() === 'failed') {
                img.prop('src', 'images/no16.png');
            }
            return false;
        });
    });
};

},{"../core":2}]},{},[3]);

//# sourceMappingURL=backlog-overview.js.map
