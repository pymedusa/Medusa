(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
const MEDUSA = require('../core');
MEDUSA.addShows.addExistingShow = function () {
    $('#tableDiv').on('click', '#checkAll', function () {
        var seasonCheck = this;
        $('.dirCheck').each(function () {
            this.checked = seasonCheck.checked;
        });
    });

    $('#submitShowDirs').on('click', function () {
        var dirArr = [];
        $('.dirCheck').each(function () {
            if (this.checked === true) {
                var originalIndexer = $(this).attr('data-indexer');
                var indexerId = '|' + $(this).attr('data-indexer-id');
                var showName = $(this).attr('data-show-name');
                var showDir = $(this).attr('data-show-dir');

                var indexer = $(this).closest('tr').find('select').val();
                if (originalIndexer !== indexer || originalIndexer === '0') {
                    indexerId = '';
                }
                dirArr.push(encodeURIComponent(indexer + '|' + showDir + indexerId + '|' + showName));
            }
        });

        if (dirArr.length === 0) {
            return false;
        }

        window.location.href = $('base').attr('href') + 'addShows/addExistingShows?promptForSettings=' + ($('#promptForSettings').prop('checked') ? 'on' : 'off') + '&shows_to_add=' + dirArr.join('&shows_to_add=');
    });

    function loadContent() {
        var url = '';
        $('.dir_check').each(function (i, w) {
            if ($(w).is(':checked')) {
                if (url.length !== 0) {
                    url += '&';
                }
                url += 'rootDir=' + encodeURIComponent($(w).attr('id'));
            }
        });

        $('#tableDiv').html('<img id="searchingAnim" src="images/loading32.gif" height="32" width="32" /> loading folders...');
        $.get('addShows/massAddTable/', url, function (data) {
            $('#tableDiv').html(data);
            $('#addRootDirTable').tablesorter({
                // sortList: [[1,0]],
                widgets: ['zebra'],
                headers: {
                    0: { sorter: false }
                }
            });
        });
    }

    var lastTxt = '';
    // @TODO this needs a real name, for now this fixes the issue of the page not loading at all,
    //       before I added this I couldn't get the directories to show in the table
    var a = function () {
        if (lastTxt === $('#rootDirText').val()) {
            return false;
        }
        lastTxt = $('#rootDirText').val();
        $('#rootDirStaticList').html('');
        $('#rootDirs option').each(function (i, w) {
            $('#rootDirStaticList').append('<li class="ui-state-default ui-corner-all"><input type="checkbox" class="cb dir_check" id="' + $(w).val() + '" checked=checked> <label for="' + $(w).val() + '"><b>' + $(w).val() + '</b></label></li>');
        });
        loadContent();
    };

    a();

    $('#rootDirText').on('change', a);

    $('#rootDirStaticList').on('click', '.dir_check', loadContent);

    $('#tableDiv').on('click', '.showManage', function (event) {
        event.preventDefault();
        $('#tabs').tabs('option', 'active', 0);
        $('html,body').animate({ scrollTop: 0 }, 1000);
    });
};

},{"../core":3}],2:[function(require,module,exports){
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

},{}],3:[function(require,module,exports){
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

},{"./api":2}]},{},[1]);

//# sourceMappingURL=add-existing-show.js.map
