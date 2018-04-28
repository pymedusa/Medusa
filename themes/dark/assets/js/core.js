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
        action = (action === undefined) ? 'init' : action;

        if (controller !== '' && ns[controller] && typeof ns[controller][action] === 'function') {
            ns[controller][action]();
        }
    },
    init() {
        if (typeof startVue === 'function') { // eslint-disable-line no-undef
            startVue(); // eslint-disable-line no-undef
        } else {
            $('[v-cloak]').removeAttr('v-cloak');
        }

        const body = document.body;
        $('[asset]').each(function() {
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
    isMeta(pyVar, result) { // eslint-disable-line no-unused-vars
        const reg = new RegExp(result.length > 1 ? result.join('|') : result);

        if (typeof (pyVar) === 'object' && Object.keys(pyVar).length === 1) {
            return (reg).test(MEDUSA.config[Object.keys(pyVar)[0]][pyVar[Object.keys(pyVar)[0]]]);
        }
        if (pyVar.match('medusa')) {
            pyVar.split('.')[1].toLowerCase().replace(/(_\w)/g, m => {
                return m[1].toUpperCase();
            });
        }
        return (reg).test(MEDUSA.config[pyVar]);
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

const triggerConfigLoaded = function() {
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

        MEDUSA.config.indexers.indexerIdToName = indexerId => {
            if (!indexerId) {
                return '';
            }
            return Object.keys(MEDUSA.config.indexers.config.indexers).filter(indexer => { // eslint-disable-line array-callback-return
                if (MEDUSA.config.indexers.config.indexers[indexer].id === parseInt(indexerId, 10)) {
                    return MEDUSA.config.indexers.config.indexers[indexer].name;
                }
            })[0];
        };

        MEDUSA.config.indexers.nameToIndexerId = name => {
            if (!name) {
                return '';
            }
            return MEDUSA.config.indexers.config.indexers[name];
        };

        triggerConfigLoaded();
    }).catch(err => {
        log.error(err);
        alert('Unable to connect to Medusa!'); // eslint-disable-line no-alert
    });
}

// Notifications
const WSMessageUrl = '/ui'; // eslint-disable-line xo/filename-case
const test = !1;
const iconUrl = 'images/ico/favicon-120.png';

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
        type,
        title,
        desktop: {
            tag: id
        },
        text: String(message).replace(/<br[\s/]*(?:\s[^>]*)?>/ig, '\n') // eslint-disable-line unicorn/no-unsafe-regex
            .replace(/<[/]?b(?:\s[^>]*)?>/ig, '*') // eslint-disable-line unicorn/no-unsafe-regex
            .replace(/<i(?:\s[^>]*)?>/ig, '[').replace(/<[/]i>/ig, ']') // eslint-disable-line unicorn/no-unsafe-regex
            .replace(/<(?:[/]?ul|\/li)(?:\s[^>]*)?>/ig, '').replace(/<li(?:\s[^>]*)?>/ig, '\n* ') // eslint-disable-line unicorn/no-unsafe-regex
    });
}

function wsCheckNotifications() {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const webRoot = MEDUSA.config.webRoot || '';
    const ws = new WebSocket(proto + '//' + window.location.hostname + ':' + window.location.port + webRoot + '/ws' + WSMessageUrl);
    ws.addEventListener('message', evt => {
        let msg;
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
    });

    ws.addEventListener('error', () => {
        log.warn('Error connecting to websocket. Please check your network connection. ' +
            'If you are using a reverse proxy, please take a look at our wiki for config examples.');
        displayPNotify('notice', 'Error connecting to websocket.', 'Please check your network connection. ' +
            'If you are using a reverse proxy, please take a look at our wiki for config examples.');
    });
    console.log('Notifications library loaded.');
}

// Run functions that depend on loading of the config.
// Listen for the config loaded event.
window.addEventListener('build', e => {
    if (e.detail === 'medusa config loaded') {
        wsCheckNotifications();
        if (test) {
            displayPNotify('error', 'test', 'test<br><i class="test-class">hello <b>world</b></i><ul><li>item 1</li><li>item 2</li></ul>', 'notification-test');
        }
    }
}, false);
