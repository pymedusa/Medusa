var WSMessageUrl = '/ui'; // eslint-disable-line xo/filename-case
var test = !1;

var iconUrl = 'images/ico/favicon-120.png';

PNotify.prototype.options.addclass = 'stack-bottomright';
PNotify.prototype.options.buttons.closer_hover = !1; // eslint-disable-line camelcase
PNotify.prototype.options.delay = 5000;
PNotify.prototype.options.desktop = {desktop: !0, icon: iconUrl};
PNotify.prototype.options.hide = !0;
PNotify.prototype.options.history = !1;
PNotify.prototype.options.shadow = !1;
PNotify.prototype.options.stack = {dir1: 'up', dir2: 'left', firstpos1: 25, firstpos2: 25};
PNotify.prototype.options.styling = 'jqueryui';
PNotify.prototype.options.width = '340px';
PNotify.desktop.permission();

function displayPNotify(type, title, message) {
    new PNotify({ // eslint-disable-line no-new
        type: type,
        title: title,
        text: String(message).replace(/<br[\s/]*(?:\s[^>]*)?>/ig, '\n')
            .replace(/<[/]?b(?:\s[^>]*)?>/ig, '*')
            .replace(/<i(?:\s[^>]*)?>/ig, '[').replace(/<[/]i>/ig, ']')
            .replace(/<(?:[/]?ul|\/li)(?:\s[^>]*)?>/ig, '').replace(/<li(?:\s[^>]*)?>/ig, '\n* ')
    });
}

function wsCheckNotifications() {
    var proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    var ws = new WebSocket(proto + '//' + window.location.hostname + ':' + window.location.port + '/ws' + WSMessageUrl);
    ws.onmessage = function(evt) {
        var msg;
        try {
            msg = JSON.parse(evt.data);
        } catch (e) { // eslint-disable-line unicorn/catch-error-name
            msg = evt.data;
        }

        // Add handling for different kinds of events. For ex: {"event": "notification", "data": {"title": ..}}
        if (msg.event === 'notification') {
            displayPNotify(msg.data.type, msg.data.title, msg.data.body);
        } else {
            displayPNotify('info', '', msg);
        }
    };

    ws.onerror = function(evt) {
        console.log('Error connecting to websocket. Please check your network connecton: ' + evt);
        displayPNotify('notice', 'Error connecting to websocket.', 'Please check your network connection. ' +
            'If you are using a reverse proxy, please take a look at our wiki for config examples.');
    };
}

$(document).ready(function() {
    wsCheckNotifications();
    if (test) {
        displayPNotify('error', 'test', 'test<br><i class="test-class">hello <b>world</b></i><ul><li>item 1</li><li>item 2</li></ul>');
    }
});
