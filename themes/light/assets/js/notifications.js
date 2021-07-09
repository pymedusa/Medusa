const iconUrl = 'images/ico/favicon-120.png';

PNotify.prototype.options.addclass = 'stack-bottomright';
PNotify.prototype.options.buttons.closer_hover = false; // eslint-disable-line camelcase
PNotify.prototype.options.delay = 5000;
PNotify.prototype.options.desktop = { desktop: !0, icon: iconUrl };
PNotify.prototype.options.hide = true;
PNotify.prototype.options.history = false;
PNotify.prototype.options.shadow = false;
PNotify.prototype.options.stack = { dir1: 'up', dir2: 'left', firstpos1: 25, firstpos2: 25 };
PNotify.prototype.options.styling = 'jqueryui';
PNotify.prototype.options.width = '340px';
PNotify.desktop.permission();

window.displayNotification = (type, title, message, id) => {
    new PNotify({ // eslint-disable-line no-new
        type,
        title,
        desktop: {
            tag: id
        },
        text: String(message).replace(/<br[\s/]*(?:\s[^>]*)?>/gi, '\n')
            .replace(/<\/?b(?:\s[^>]*)?>/gi, '*')
            .replace(/<i(?:\s[^>]*)?>/gi, '[').replace(/<\/i>/gi, ']')
            .replace(/<(?:\/?ul|\/li)(?:\s[^>]*)?>/gi, '').replace(/<li(?:\s[^>]*)?>/gi, '\n* ')
    });
};
