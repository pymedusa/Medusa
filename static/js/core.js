var topImageHtml = '<img src="images/top.gif" width="31" height="11" alt="Jump to top" />';
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
        if (typeof startVue === 'function') {
            startVue();
        } else {
            $('[v-cloak]').removeAttr('v-cloak');
        }

        var body = document.body;
        var controller = body.getAttribute('data-controller');
        var action = body.getAttribute('data-action');

        UTIL.exec('common');
        UTIL.exec(controller);
        UTIL.exec(controller, action);
    }
};

// @TODO: Remove this whole crap!
$.extend({
    isMeta: function(pyVar, result) {
        var reg = new RegExp(result.length > 1 ? result.join('|') : result);
        if (pyVar.match('medusa')) {
            pyVar.split('.')[1].toLowerCase().replace(/(_\w)/g, function(m) {
                return m[1].toUpperCase();
            });
        }
        return (reg).test(MEDUSA.config[pyVar]);
    }
});

// Toggles a warning class
$.fn.extend({
    addRemoveWarningClass: function(_) {
        if (_) {
            return $(this).removeClass('warning');
        }
        return $(this).addClass('warning');
    }
});

if (!document.location.pathname.endsWith('/login/')) {
    api.get('config').then(function(response) {
        log.setDefaultLevel('trace');
        $.extend(MEDUSA.config, response.data);
        MEDUSA.config.themeSpinner = MEDUSA.config.themeName === 'dark' ? '-dark' : '';
        MEDUSA.config.loading = '<img src="images/loading16' + MEDUSA.config.themeSpinner + '.gif" height="16" width="16" />';

        $('[asset]').each(function(){
            let asset = $(this).attr('asset');
            let path = apiRoot + 'asset/' + asset + '&api_key=' + apiKey;
            if (this.tagName.toLowerCase() === 'img') {
                $(this).attr('src', path);
            }
            if (this.tagName.toLowerCase() === 'a') {
                $(this).attr('href', path);
            }
        });

        if (navigator.userAgent.indexOf('PhantomJS') === -1) {
            $(document).ready(UTIL.init);
        }
    }).catch(function (error) {
        alert('Unable to connect to Medusa!'); // eslint-disable-line no-alert
    });
}
