// eslint-disable-line max-lines
// @TODO Move these into common.ini when possible,
//       currently we can't do that as browser.js and a few others need it before this is loaded
var topImageHtml = '<img src="images/top.gif" width="31" height="11" alt="Jump to top" />'; // eslint-disable-line no-unused-vars
var webRoot = $('base').attr('href');
var apiRoot = $('body').attr('api-root');
var apiKey = $('body').attr('api-key');

$.fn.extend({
    addRemoveWarningClass: function (_) {
        if (_) {
            return $(this).removeClass('warning');
        }
        return $(this).addClass('warning');
    }
});

var SICKRAGE = {
    common: {},
    config: {
        providers: function() {
            // @TODO This function need to be filled with ConfigProviders.js but can't be as we've got scope issues currently.
            console.log('This function need to be filled with ConfigProviders.js but can\'t be as we\'ve got scope issues currently.');
        }
    },
    home: {},
    manage: {},
    history: {},
    errorlogs: {},
    schedule: {},
    addShows: {}
};

var UTIL = {
    exec: function(controller, action) {
        var ns = SICKRAGE;
        action = (action === undefined) ? 'init' : action;

        if (controller !== '' && ns[controller] && typeof ns[controller][action] === 'function') {
            ns[controller][action]();
        }
    },
    init: function() {
        var body = document.body;
        var controller = body.getAttribute('data-controller');
        var action = body.getAttribute('data-action');

        UTIL.exec('common');
        UTIL.exec(controller);
        UTIL.exec(controller, action);
    }
};

$.ajaxSetup({
    beforeSend: function(xhr, options) {
        if (/^https?:\/\/|^\/\//i.test(options.url) === false) {
            options.url = webRoot + options.url;
        }
    }
});

$.ajax({
    url: apiRoot + 'info?api_key=' + apiKey,
    type: 'GET',
    dataType: 'json'
}).done(function(data) {
    if (data.status === 200) {
        SICKRAGE.info = data.data;
        SICKRAGE.info.themeSpinner = SICKRAGE.info.themeName === 'dark' ? '-dark' : '';
        SICKRAGE.info.loading = '<img src="images/loading16' + SICKRAGE.info.themeSpinner + '.gif" height="16" width="16" />';

        if (navigator.userAgent.indexOf('PhantomJS') === -1) {
            $(document).ready(UTIL.init);
        }
    }
});

function isMeta(pyVar, result) { // eslint-disable-line no-unused-vars
    var reg = new RegExp(result.length > 1 ? result.join('|') : result);
    if (pyVar.match('sickbeard')) {
        pyVar.split('.')[1].toLowerCase().replace(/(_\w)/g, function(m) {
            return m[1].toUpperCase();
        });
    }
    return (reg).test(SICKRAGE.info[pyVar]);
}
