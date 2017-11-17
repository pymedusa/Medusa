const Url = require('url');
const medusa = require('.');

const wsMessageUrl = 'ws/ui';
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

const displayPNotify = (type, title, message, id) => {
    new PNotify({ // eslint-disable-line no-new
        type,
        title,
        desktop: {
            tag: id
        },
        text: String(message).replace(/<br[\s/]*(?:\s[^>]*)?>/ig, '\n')
            .replace(/<[/]?b(?:\s[^>]*)?>/ig, '*')
            .replace(/<i(?:\s[^>]*)?>/ig, '[').replace(/<[/]i>/ig, ']')
            .replace(/<(?:[/]?ul|\/li)(?:\s[^>]*)?>/ig, '').replace(/<li(?:\s[^>]*)?>/ig, '\n* ')
    });
};

const wsCheckNotifications = async () => {
    await medusa.auth({ apiKey: $('body').attr('api-key') });
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = new Url($('base').attr('href'));
    url.protocol = protocol;
    url.pathname += wsMessageUrl;
    const ws = new WebSocket(url.href);
    ws.onmessage = evt => {
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
    };

    ws.onerror = () => {
        log.warn('Error connecting to websocket. Please check your network connection. ' +
            'If you are using a reverse proxy, please take a look at our wiki for config examples.');
        displayPNotify('notice', 'Error connecting to websocket.', 'Please check your network connection. ' +
            'If you are using a reverse proxy, please take a look at our wiki for config examples.');
    };
};

// Listen for the config loaded event.
window.addEventListener('build', e => {
    if (e.detail === 'medusa config loaded') {
        wsCheckNotifications();
        if (test) {
            displayPNotify('error', 'test', 'test<br><i class="test-class">hello <b>world</b></i><ul><li>item 1</li><li>item 2</li></ul>', 'notification-test');
        }
    }
}, false);
