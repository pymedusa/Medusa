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
    history: {
        index: function() {
            $('#historyTable:has(tbody tr)').tablesorter({
                widgets: ['zebra', 'filter'],
                sortList: [[0, 1]],
                textExtraction: (function() {
                    if (isMeta('HISTORY_LAYOUT', ['detailed'])) {
                        return {
                            0: function(node) { return $(node).find('time').attr('datetime'); }, // eslint-disable-line brace-style
                            4: function(node) { return $(node).find('span').text().toLowerCase(); } // eslint-disable-line brace-style
                        };
                    }
                    return {
                        0: function(node) { return $(node).find('time').attr('datetime'); }, // eslint-disable-line brace-style
                        1: function(node) { return $(node).find('span').text().toLowerCase(); }, // eslint-disable-line brace-style
                        2: function(node) { return $(node).attr('provider') == null ? null : $(node).attr('provider').toLowerCase(); }, // eslint-disable-line brace-style
                        5: function(node) { return $(node).attr('quality').toLowerCase(); } // eslint-disable-line brace-style
                    };
                }()),
                headers: (function() {
                    if (isMeta('HISTORY_LAYOUT', ['detailed'])) {
                        return {
                            0: {sorter: 'realISODate'},
                            4: {sorter: 'quality'}
                        };
                    }
                    return {
                        0: {sorter: 'realISODate'},
                        4: {sorter: false},
                        5: {sorter: 'quality'}
                    };
                }())
            });

            $('#history_limit').on('change', function() {
                window.location.href = 'history/?limit=' + $(this).val();
            });
        }
    },
    errorlogs: {
        viewlogs: function() {
            $('#min_level,#log_filter,#log_search,#log_period').on('keyup change', _.debounce(function() {
                $('#min_level').prop('disabled', true);
                $('#log_filter').prop('disabled', true);
                $('#log_period').prop('disabled', true);
                document.body.style.cursor = 'wait';
                var params = $.param({
                    min_level: $('select[name=min_level]').val(),
                    log_filter: $('select[name=log_filter]').val(),
                    log_period: $('select[name=log_period]').val(),
                    log_search: $('#log_search').val()
                });
                $.get('errorlogs/viewlog/?' + params, function(data) {
                    history.pushState('data', '', 'errorlogs/viewlog/?' + params);
                    $('pre').html($(data).find('pre').html());
                    $('#min_level').prop('disabled', false);
                    $('#log_filter').prop('disabled', false);
                    $('#log_period').prop('disabled', false);
                    document.body.style.cursor = 'default';
                });
            }, 500));
        }
    },
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

function isMeta(pyVar, result) {
    var reg = new RegExp(result.length > 1 ? result.join('|') : result);
    if (pyVar.match('sickbeard')) {
        pyVar.split('.')[1].toLowerCase().replace(/(_\w)/g, function(m) {
            return m[1].toUpperCase();
        });
    }
    return (reg).test(SICKRAGE.info[pyVar]);
}
