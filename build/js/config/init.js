(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
const MEDUSA = require('../core');
MEDUSA.config.init = function () {
    $('#config-components').tabs();

    $('.viewIf').on('click', function () {
        if ($(this).prop('checked')) {
            $('.hide_if_' + $(this).attr('id')).css('display', 'none');
            $('.show_if_' + $(this).attr('id')).fadeIn('fast', 'linear');
        } else {
            $('.show_if_' + $(this).attr('id')).css('display', 'none');
            $('.hide_if_' + $(this).attr('id')).fadeIn('fast', 'linear');
        }
    });

    $('.datePresets').on('click', function () {
        var def = $('#date_presets').val();
        if ($(this).prop('checked') && def === '%x') {
            def = '%a, %b %d, %Y';
            $('#date_use_system_default').html('1');
        } else if (!$(this).prop('checked') && $('#date_use_system_default').html() === '1') {
            def = '%x';
        }

        $('#date_presets').prop('name', 'date_preset_old');
        $('#date_presets').prop('id', 'date_presets_old');

        $('#date_presets_na').prop('name', 'date_preset');
        $('#date_presets_na').prop('id', 'date_presets');

        $('#date_presets_old').prop('name', 'date_preset_na');
        $('#date_presets_old').prop('id', 'date_presets_na');

        if (def) {
            $('#date_presets').val(def);
        }
    });

    // bind 'myForm' and provide a simple callback function
    $('#configForm').ajaxForm({
        beforeSubmit: function () {
            $('.config_submitter .config_submitter_refresh').each(function () {
                $(this).prop('disabled', 'disabled');
                $(this).after('<span><img src="images/loading16' + MEDUSA.config.themeSpinner + '.gif"> Saving...</span>');
                $(this).hide();
            });
        },
        success: function () {
            setTimeout(function () {
                $('.config_submitter').each(function () {
                    $(this).removeAttr('disabled');
                    $(this).next().remove();
                    $(this).show();
                });
                $('.config_submitter_refresh').each(function () {
                    $(this).removeAttr('disabled');
                    $(this).next().remove();
                    $(this).show();
                    window.location.href = $('base').attr('href') + 'config/providers/';
                });
                $('#email_show').trigger('notify');
                $('#prowl_show').trigger('notify');
            }, 2000);
        }
    });

    $('#api_key').on('click', function () {
        $('#api_key').select();
    });

    $('#generate_new_apikey').on('click', function () {
        $.get('config/general/generate_api_key', function (data) {
            if (data.error !== undefined) {
                alert(data.error); // eslint-disable-line no-alert
                return;
            }
            $('#api_key').val(data);
        });
    });

    $('#branchCheckout').on('click', function () {
        var url = 'home/branchCheckout?branch=' + $('#branchVersion').val();
        $.getJSON('home/getDBcompare', function (data) {
            if (data.status === 'success') {
                if (data.message === 'equal') {
                    // Checkout Branch
                    window.location.href = $('base').attr('href') + url;
                }
                if (data.message === 'upgrade') {
                    if (confirm('Changing branch will upgrade your database.\nYou won\'t be able to downgrade afterward.\nDo you want to continue?')) {
                        // eslint-disable-line no-alert
                        // Checkout Branch
                        window.location.href = $('base').attr('href') + url;
                    }
                }
                if (data.message === 'downgrade') {
                    alert('Can\'t switch branch as this will result in a database downgrade.'); // eslint-disable-line no-alert
                }
            }
        });
    });

    $('#branchForceUpdate').on('click', function () {
        $('#branchForceUpdate').prop('disabled', true);
        $('#git_reset_branches').prop('disabled', true);
        $.getJSON('home/branchForceUpdate', function (data) {
            $('#git_reset_branches').empty();
            data.resetBranches.forEach(function (branch) {
                $('#git_reset_branches').append('<option value="' + branch + '" selected="selected" >' + branch + '</option>');
            });
            data.branches.forEach(function (branch) {
                $('#git_reset_branches').append('<option value="' + branch + '" >' + branch + '</option>');
            });
            $('#git_reset_branches').prop('disabled', false);
            $('#branchForceUpdate').prop('disabled', false);
        });
    });

    // GitHub Auth Types
    function setupGithubAuthTypes() {
        var selected = parseInt($('input[name="git_auth_type"]').filter(':checked').val(), 10);

        $('div[name="content_github_auth_type"]').each(function (index) {
            if (index === selected) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    }
    // GitHub Auth Types
    setupGithubAuthTypes();

    $('input[name="git_auth_type"]').on('click', function () {
        setupGithubAuthTypes();
    });

    $('#git_token').on('click', function () {
        $('#git_token').select();
    });

    $('#create_access_token').popover({
        placement: 'left',
        html: true, // required if content has HTML
        title: 'Github Token',
        content: '<p>Copy the generated token and paste it in the token input box.</p>' + '<p><a href="' + MEDUSA.config.anonRedirect + 'https://github.com/settings/tokens/new?description=Medusa&scopes=user,gist,public_repo" target="_blank">' + '<input class="btn" type="button" value="Continue to Github..."></a></p><br/>'
    });

    $('#manage_tokens').on('click', function () {
        window.open(MEDUSA.config.anonRedirect + 'https://github.com/settings/tokens', '_blank');
    });
};

},{"../core":2}],2:[function(require,module,exports){
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
    exec: function (controller, action) {
        var ns = MEDUSA;
        action = action === undefined ? 'init' : action;

        if (controller !== '' && ns[controller] && typeof ns[controller][action] === 'function') {
            ns[controller][action]();
        }
    },
    init: function () {
        if (typeof startVue === 'function') {
            // eslint-disable-line no-undef
            startVue(); // eslint-disable-line no-undef
        } else {
            $('[v-cloak]').removeAttr('v-cloak');
        }

        var body = document.body;
        $('[asset]').each(function () {
            let asset = $(this).attr('asset');
            let series = $(this).attr('series');
            let path = apiRoot + 'series/' + series + '/asset/' + asset + '?api_key=' + apiKey;
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
    isMeta: function (pyVar, result) {
        // eslint-disable-line no-unused-vars
        var reg = new RegExp(result.length > 1 ? result.join('|') : result);

        if (typeof pyVar === 'object' && Object.keys(pyVar).length === 1) {
            return reg.test(MEDUSA.config[Object.keys(pyVar)[0]][pyVar[Object.keys(pyVar)[0]]]);
        }
        if (pyVar.match('medusa')) {
            pyVar.split('.')[1].toLowerCase().replace(/(_\w)/g, function (m) {
                return m[1].toUpperCase();
            });
        }
        return reg.test(MEDUSA.config[pyVar]);
    }
});

$.fn.extend({
    addRemoveWarningClass: function (_) {
        if (_) {
            return $(this).removeClass('warning');
        }
        return $(this).addClass('warning');
    }
});

var triggerConfigLoaded = function () {
    // Create the event.
    var event = new CustomEvent('build', { detail: 'medusa config loaded' });
    event.initEvent('build', true, true);
    // Trigger the event.
    document.dispatchEvent(event);
};

if (!document.location.pathname.endsWith('/login/')) {
    api.get('config/main').then(function (response) {
        log.setDefaultLevel('trace');
        $.extend(MEDUSA.config, response.data);
        MEDUSA.config.themeSpinner = MEDUSA.config.themeName === 'dark' ? '-dark' : '';
        MEDUSA.config.loading = '<img src="images/loading16' + MEDUSA.config.themeSpinner + '.gif" height="16" width="16" />';

        if (navigator.userAgent.indexOf('PhantomJS') === -1) {
            $(document).ready(UTIL.init);
        }
        triggerConfigLoaded();
    }).catch(function (err) {
        log.error(err);
        alert('Unable to connect to Medusa!'); // eslint-disable-line no-alert
    });
}

module.exports = MEDUSA;

},{}]},{},[1]);

//# sourceMappingURL=init.js.map
