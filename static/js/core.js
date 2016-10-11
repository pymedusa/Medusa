// eslint-disable-line max-lines
// @TODO Move these into common.ini when possible,
//       currently we can't do that as browser.js and a few others need it before this is loaded
var topImageHtml = '<img src="images/top.gif" width="31" height="11" alt="Jump to top" />'; // eslint-disable-line no-unused-vars
var webRoot = $('base').attr('href');
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
        var body = document.body;
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
        if (pyVar.match('medusa')) {
            pyVar.split('.')[1].toLowerCase().replace(/(_\w)/g, function(m) {
                return m[1].toUpperCase();
            });
        }
        return (reg).test(MEDUSA.info[pyVar]);
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
}).success(function(data) {
    MEDUSA.info = data;
    MEDUSA.info.themeSpinner = MEDUSA.info.themeName === 'dark' ? '-dark' : '';
    MEDUSA.info.loading = '<img src="images/loading16' + MEDUSA.info.themeSpinner + '.gif" height="16" width="16" />';
    if (typeof startVue === 'undefined') { // eslint-disable-line no-undef
        $('[v-cloak]').removeAttr('v-cloak');
    } else {
        startVue(); // eslint-disable-line no-undef
    }

    if (navigator.userAgent.indexOf('PhantomJS') === -1) {
        $(document).ready(UTIL.init);
    }
}).fail(function() {
    alert('Unable to connect to Medusa!'); // eslint-disable-line no-alert
});
