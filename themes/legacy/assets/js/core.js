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
    exec: function(controller, action) {
        var ns = MEDUSA;
        action = (action === undefined) ? 'init' : action;

        if (controller !== '' && ns[controller] && typeof ns[controller][action] === 'function') {
            ns[controller][action]();
        }
    },
    init: function() {
        if (typeof startVue === 'function') { // eslint-disable-line no-undef
            startVue(); // eslint-disable-line no-undef
        } else {
            $('[v-cloak]').removeAttr('v-cloak');
        }

        var body = document.body;
        $('[asset]').each(function() {
            var asset = $(this).attr('asset');
            var series = $(this).attr('series');
            var path = apiRoot + 'series/' + series + '/asset/' + asset + '?api_key=' + apiKey;
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
    isMeta: function(pyVar, result) { // eslint-disable-line no-unused-vars
        var reg = new RegExp(result.length > 1 ? result.join('|') : result);

        if (typeof (pyVar) === 'object' && Object.keys(pyVar).length === 1) {
            return (reg).test(MEDUSA.config[Object.keys(pyVar)[0]][pyVar[Object.keys(pyVar)[0]]]);
        }
        if (pyVar.match('medusa')) {
            pyVar.split('.')[1].toLowerCase().replace(/(_\w)/g, function(m) {
                return m[1].toUpperCase();
            });
        }
        return (reg).test(MEDUSA.config[pyVar]);
    }
});

$.fn.extend({
    addRemoveWarningClass: function(_) {
        if (_) {
            return $(this).removeClass('warning');
        }
        return $(this).addClass('warning');
    }
});

var triggerConfigLoaded = function() {
    // Create the event.
    var event = document.createEvent('CustomEvent');
    event.initCustomEvent('build', false, false, {
        detail: 'medusa config loaded'
    });

    // Trigger the event.
    document.dispatchEvent(event);
};

if (!document.location.pathname.endsWith('/login/')) {
    api.get('config/main').then(function(response) {
        log.setDefaultLevel('trace');
        $.extend(MEDUSA.config, response.data);
        MEDUSA.config.themeSpinner = MEDUSA.config.themeName === 'dark' ? '-dark' : '';
        MEDUSA.config.loading = '<img src="images/loading16' + MEDUSA.config.themeSpinner + '.gif" height="16" width="16" />';

        if (navigator.userAgent.indexOf('PhantomJS') === -1) {
            $(document).ready(UTIL.init);
        }

        MEDUSA.config.indexers.indexerIdToName = function(indexer) {
            if (!indexer) {
                return '';
            }
            return MEDUSA.config.indexers.config[parseInt(indexer, 10)];
        };

        MEDUSA.config.indexers.nameToIndexerId = function(name) {
            if (!name) {
                return '';
            }
            return Object.keys(MEDUSA.config.indexers.config).map(function(key) { // eslint-disable-line array-callback-return
                if (MEDUSA.config.indexers.config[key] === name) {
                    return key;
                }
            })[0];
        };

        triggerConfigLoaded();
    }).catch(function(err) {
        log.error(err);
        alert('Unable to connect to Medusa!'); // eslint-disable-line no-alert
    });
}

// Notifications
var WSMessageUrl = '/ui'; // eslint-disable-line xo/filename-case
var test = !1;
var iconUrl = 'images/ico/favicon-120.png';

PNotify.prototype.options.addclass = 'stack-bottomright';
PNotify.prototype.options.buttons.closer_hover = !1; // eslint-disable-line camelcase
PNotify.prototype.options.delay = 5000;
PNotify.prototype.options.desktop = { desktop: !0, icon: iconUrl };
PNotify.prototype.options.hide = !0;
PNotify.prototype.options.history = !1;
PNotify.prototype.options.shadow = !1;
PNotify.prototype.options.stack = { dir1: 'up', dir2: 'left', firstpos1: 25, firstpos2: 25 };
PNotify.prototype.options.styling = 'jqueryui';
PNotify.prototype.options.width = '340px';
PNotify.desktop.permission();

function displayPNotify(type, title, message, id) {
    new PNotify({ // eslint-disable-line no-new
        type: type,
        title: title,
        desktop: {
            tag: id
        },
        text: String(message).replace(/<br[\s/]*(?:\s[^>]*)?>/ig, '\n')
            .replace(/<[/]?b(?:\s[^>]*)?>/ig, '*')
            .replace(/<i(?:\s[^>]*)?>/ig, '[').replace(/<[/]i>/ig, ']')
            .replace(/<(?:[/]?ul|\/li)(?:\s[^>]*)?>/ig, '').replace(/<li(?:\s[^>]*)?>/ig, '\n* ')
    });
}

function wsCheckNotifications() {
    var proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    var webRoot = MEDUSA.config.webRoot || '';
    var ws = new WebSocket(proto + '//' + window.location.hostname + ':' + window.location.port + webRoot + '/ws' + WSMessageUrl);
    ws.onmessage = function(evt) {
        var msg;
        try {
            msg = JSON.parse(evt.data);
        } catch (e) { // eslint-disable-line unicorn/catch-error-name
            msg = evt.data;
        }

        // Add handling for different kinds of events. For ex: {"event": "notification", "data": {"title": ..}}
        if (msg.event === 'notification') {
            displayPNotify(msg.data.type, msg.data.title, msg.data.body, msg.data.hash);
        } else {
            displayPNotify('info', '', msg);
        }
    };

    ws.onerror = function() {
        log.warn('Error connecting to websocket. Please check your network connection. ' +
            'If you are using a reverse proxy, please take a look at our wiki for config examples.');
        displayPNotify('notice', 'Error connecting to websocket.', 'Please check your network connection. ' +
            'If you are using a reverse proxy, please take a look at our wiki for config examples.');
    };
    console.log('Notifications library loaded.');
}

// Run functions that depend on loading of the config.
// Listen for the config loaded event.
window.addEventListener('build', function(e) {
    if (e.detail === 'medusa config loaded') {
        /**
         * Search for anchors with the attribute indexer-to-name and translate the indexer id to a name using the helper
         * function MEDUSA.config.indexers.indexerIdToName().
         *
         * The anchor is rebuild using the indexer name.
         */
        $('[data-indexer-to-name]').each(function(index, target) {
            var indexerId = $(target).attr('data-indexer-to-name');
            var indexerName = MEDUSA.config.indexers.indexerIdToName(indexerId);

            var re = /indexer-to-name/gi;

            $.each(target.attributes, function(index, attr) {
                if (attr.name !== 'data-indexer-to-name' && target[attr.name]) {
                    target[attr.name] = target[attr.name].replace(re, indexerName);
                }
            });
        });

        wsCheckNotifications();
        if (test) {
            displayPNotify('error', 'test', 'test<br><i class="test-class">hello <b>world</b></i><ul><li>item 1</li><li>item 2</li></ul>', 'notification-test');
        }
    }
}, false);
