(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
const baseUrl = $('body').attr('api-root');
const idToken = $('body').attr('api-key');

const api = axios.create({
    baseURL: baseUrl,
    timeout: 10000,
    headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Api-Key': idToken
    }
});

module.exports = api;

},{}],2:[function(require,module,exports){
const MEDUSA = require('../core');
MEDUSA.config.search = function () {
    $('#config-components').tabs();
    $('#nzb_dir').fileBrowser({ title: 'Select .nzb black hole/watch location' });
    $('#torrent_dir').fileBrowser({ title: 'Select .torrent black hole/watch location' });
    $('#torrent_path').fileBrowser({ title: 'Select .torrent download location' });
    $('#torrent_seed_location').fileBrowser({ title: 'Select Post-Processed seeding torrents location' });

    $.fn.nzbMethodHandler = function () {
        var selectedProvider = $('#nzb_method :selected').val();
        var blackholeSettings = '#blackhole_settings';
        var sabnzbdSettings = '#sabnzbd_settings';
        var testSABnzbd = '#testSABnzbd';
        var testSABnzbdResult = '#testSABnzbd_result';
        var testNZBget = '#testNZBget';
        var testNZBgetResult = '#testNZBgetResult';
        var nzbgetSettings = '#nzbget_settings';

        $('#nzb_method_icon').removeClass(function (index, css) {
            return (css.match(/(^|\s)add-client-icon-\S+/g) || []).join(' ');
        });
        $('#nzb_method_icon').addClass('add-client-icon-' + selectedProvider.replace('_', '-'));

        $(blackholeSettings).hide();
        $(sabnzbdSettings).hide();
        $(testSABnzbd).hide();
        $(testSABnzbdResult).hide();
        $(nzbgetSettings).hide();
        $(testNZBget).hide();
        $(testNZBgetResult).hide();

        if (selectedProvider.toLowerCase() === 'blackhole') {
            $(blackholeSettings).show();
        } else if (selectedProvider.toLowerCase() === 'nzbget') {
            $(nzbgetSettings).show();
            $(testNZBget).show();
            $(testNZBgetResult).show();
        } else {
            $(sabnzbdSettings).show();
            $(testSABnzbd).show();
            $(testSABnzbdResult).show();
        }
    };

    $.torrentMethodHandler = function () {
        $('#options_torrent_clients').hide();
        $('#options_torrent_blackhole').hide();

        var selectedProvider = $('#torrent_method :selected').val();
        var host = ' host:port';
        var username = ' username';
        var password = ' password';
        var client = '';
        var optionPanel = '#options_torrent_blackhole';
        var rpcurl = ' RPC URL';

        $('#torrent_method_icon').removeClass(function (index, css) {
            return (css.match(/(^|\s)add-client-icon-\S+/g) || []).join(' ');
        });
        $('#torrent_method_icon').addClass('add-client-icon-' + selectedProvider.replace('_', '-'));

        if (selectedProvider.toLowerCase() !== 'blackhole') {
            $('#label_warning_deluge').hide();
            $('#label_anime_warning_deluge').hide();
            $('#host_desc_torrent').show();
            $('#torrent_verify_cert_option').hide();
            $('#torrent_verify_deluge').hide();
            $('#torrent_verify_rtorrent').hide();
            $('#torrent_auth_type_option').hide();
            $('#torrent_path_option').show();
            $('#torrent_path_option').find('.fileBrowser').show();
            $('#torrent_seed_location_option').hide();
            $('#torrent_seed_time_option').hide();
            $('#torrent_high_bandwidth_option').hide();
            $('#torrent_label_option').show();
            $('#torrent_label_anime_option').show();
            $('#path_synology').hide();
            $('#torrent_paused_option').show();
            $('#torrent_rpcurl_option').hide();

            if (selectedProvider.toLowerCase() === 'utorrent') {
                client = 'uTorrent';
                $('#torrent_path_option').hide();
                $('#torrent_seed_time_label').text('Minimum seeding time is');
                $('#torrent_seed_time_option').show();
                $('#host_desc_torrent').text('URL to your uTorrent client (e.g. http://localhost:8000)');
                $('#torrent_seed_location_option').hide();
            } else if (selectedProvider.toLowerCase() === 'transmission') {
                client = 'Transmission';
                $('#torrent_seed_time_label').text('Stop seeding when inactive for');
                $('#torrent_seed_time_option').show();
                $('#torrent_high_bandwidth_option').show();
                $('#torrent_label_option').hide();
                $('#torrent_label_anime_option').hide();
                $('#torrent_rpcurl_option').show();
                $('#host_desc_torrent').text('URL to your Transmission client (e.g. http://localhost:9091)');
                $('#torrent_seed_location_option').show();
            } else if (selectedProvider.toLowerCase() === 'deluge') {
                client = 'Deluge';
                $('#torrent_verify_cert_option').show();
                $('#torrent_verify_deluge').show();
                $('#torrent_verify_rtorrent').hide();
                $('#label_warning_deluge').show();
                $('#label_anime_warning_deluge').show();
                $('#torrent_username_option').hide();
                $('#torrent_username').prop('value', '');
                $('#host_desc_torrent').text('URL to your Deluge client (e.g. http://localhost:8112)');
                $('#torrent_seed_location_option').show();
            } else if (selectedProvider.toLowerCase() === 'deluged') {
                client = 'Deluge';
                $('#torrent_verify_cert_option').hide();
                $('#torrent_verify_deluge').hide();
                $('#torrent_verify_rtorrent').hide();
                $('#label_warning_deluge').show();
                $('#label_anime_warning_deluge').show();
                $('#torrent_username_option').show();
                $('#host_desc_torrent').text('IP or Hostname of your Deluge Daemon (e.g. scgi://localhost:58846)');
                $('#torrent_seed_location_option').show();
            } else if (selectedProvider.toLowerCase() === 'download_station') {
                client = 'Synology DS';
                $('#torrent_label_option').hide();
                $('#torrent_label_anime_option').hide();
                $('#torrent_paused_option').hide();
                $('#torrent_path_option').find('.fileBrowser').hide();
                $('#host_desc_torrent').text('URL to your Synology DS client (e.g. http://localhost:5000)');
                $('#path_synology').show();
                $('#torrent_seed_location_option').hide();
            } else if (selectedProvider.toLowerCase() === 'rtorrent') {
                client = 'rTorrent';
                $('#torrent_paused_option').hide();
                $('#host_desc_torrent').text('URL to your rTorrent client (e.g. scgi://localhost:5000 <br> or https://localhost/rutorrent/plugins/httprpc/action.php)');
                $('#torrent_verify_cert_option').show();
                $('#torrent_verify_deluge').hide();
                $('#torrent_verify_rtorrent').show();
                $('#torrent_auth_type_option').show();
                $('#torrent_seed_location_option').hide();
            } else if (selectedProvider.toLowerCase() === 'qbittorrent') {
                client = 'qbittorrent';
                $('#torrent_path_option').hide();
                $('#label_warning_qbittorrent').show();
                $('#label_anime_warning_qbittorrent').show();
                $('#host_desc_torrent').text('URL to your qbittorrent client (e.g. http://localhost:8080)');
                $('#torrent_seed_location_option').hide();
            } else if (selectedProvider.toLowerCase() === 'mlnet') {
                client = 'mlnet';
                $('#torrent_path_option').hide();
                $('#torrent_label_option').hide();
                $('#torrent_verify_cert_option').hide();
                $('#torrent_verify_deluge').hide();
                $('#torrent_verify_rtorrent').hide();
                $('#torrent_label_anime_option').hide();
                $('#torrent_paused_option').hide();
                $('#host_desc_torrent').text('URL to your MLDonkey (e.g. http://localhost:4080)');
                $('#torrent_seed_location_option').hide();
            }
            $('#host_title').text(client + host);
            $('#username_title').text(client + username);
            $('#password_title').text(client + password);
            $('#torrent_client, #torrent_client_seed_path').text(client);
            $('#rpcurl_title').text(client + rpcurl);
            optionPanel = '#options_torrent_clients';
        }
        $(optionPanel).show();
    };

    $('#torrent_host').on('input', function () {
        if ($('#torrent_method :selected').val().toLowerCase() === 'rtorrent') {
            var hostname = $('#torrent_host').val();
            var isMatch = hostname.substr(0, 7) === 'scgi://';

            if (isMatch) {
                $('#torrent_username_option').hide();
                $('#torrent_username').prop('value', '');
                $('#torrent_password_option').hide();
                $('#torrent_password').prop('value', '');
                $('#torrent_auth_type_option').hide();
                $('#torrent_auth_type option[value=none]').prop('selected', true);
            } else {
                $('#torrent_username_option').show();
                $('#torrent_password_option').show();
                $('#torrent_auth_type_option').show();
            }
        }
    });

    $('#nzb_method').on('change', $(this).nzbMethodHandler);

    $(this).nzbMethodHandler();

    $('#testSABnzbd').on('click', function () {
        var sab = {};
        $('#testSABnzbd_result').html(MEDUSA.config.loading);
        sab.host = $('#sab_host').val();
        sab.username = $('#sab_username').val();
        sab.password = $('#sab_password').val();
        sab.apiKey = $('#sab_apikey').val();

        $.get('home/testSABnzbd', {
            host: sab.host,
            username: sab.username,
            password: sab.password,
            apikey: sab.apiKey
        }, function (data) {
            $('#testSABnzbd_result').html(data);
        });
    });

    $('#testNZBget').on('click', function () {
        var nzbget = {};
        $('#testNZBget_result').html(MEDUSA.config.loading);
        nzbget.host = $('#nzbget_host').val();
        nzbget.username = $('#nzbget_username').val();
        nzbget.password = $('#nzbget_password').val();
        nzbget.useHttps = $('#nzbget_use_https').prop('checked');

        $.get('home/testNZBget', {
            host: nzbget.host,
            username: nzbget.username,
            password: nzbget.password,
            use_https: nzbget.useHttps // eslint-disable-line camelcase
        }, function (data) {
            $('#testNZBget_result').html(data);
        });
    });

    $('#torrent_method').on('change', $.torrentMethodHandler);

    $.torrentMethodHandler();

    $('#test_torrent').on('click', function () {
        var torrent = {};
        $('#test_torrent_result').html(MEDUSA.config.loading);
        torrent.method = $('#torrent_method :selected').val();
        torrent.host = $('#torrent_host').val();
        torrent.username = $('#torrent_username').val();
        torrent.password = $('#torrent_password').val();

        $.get('home/testTorrent', {
            torrent_method: torrent.method, // eslint-disable-line camelcase
            host: torrent.host,
            username: torrent.username,
            password: torrent.password
        }, function (data) {
            $('#test_torrent_result').html(data);
        });
    });
};

},{"../core":3}],3:[function(require,module,exports){
const api = require('./api');

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
        action = action === undefined ? 'init' : action;

        if (controller !== '' && ns[controller] && typeof ns[controller][action] === 'function') {
            ns[controller][action]();
        }
    },
    init() {
        if (typeof startVue === 'function') {
            // eslint-disable-line no-undef
            startVue(); // eslint-disable-line no-undef
        } else {
            $('[v-cloak]').removeAttr('v-cloak');
        }

        const body = document.body;
        $('[asset]').each(function () {
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
    isMeta(pyVar, result) {
        const reg = new RegExp(result.length > 1 ? result.join('|') : result);

        if (typeof pyVar === 'object' && Object.keys(pyVar).length === 1) {
            return reg.test(MEDUSA.config[Object.keys(pyVar)[0]][pyVar[Object.keys(pyVar)[0]]]);
        }
        if (pyVar.match('medusa')) {
            pyVar.split('.')[1].toLowerCase().replace(/(_\w)/g, m => m[1].toUpperCase());
        }
        return reg.test(MEDUSA.config[pyVar]);
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

const triggerConfigLoaded = function () {
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
        triggerConfigLoaded();
    }).catch(err => {
        log.error(err);
        alert('Unable to connect to Medusa!'); // eslint-disable-line no-alert
    });
}

module.exports = MEDUSA;

},{"./api":1}]},{},[2]);

//# sourceMappingURL=search.js.map
