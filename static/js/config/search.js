MEDUSA.config.search = function() {
    $('#config-components').tabs();
    $('#nzb_dir').fileBrowser({title: 'Select .nzb black hole/watch location'});
    $('#torrent_dir').fileBrowser({title: 'Select .torrent black hole/watch location'});
    $('#torrent_path').fileBrowser({title: 'Select .torrent download location'});

    $.fn.nzbMethodHandler = function() {
        var selectedProvider = $('#nzb_method :selected').val();
        var blackholeSettings = '#blackhole_settings';
        var sabnzbdSettings = '#sabnzbd_settings';
        var testSABnzbd = '#testSABnzbd';
        var testSABnzbdResult = '#testSABnzbd_result';
        var testNZBget = '#testNZBget';
        var testNZBgetResult = '#testNZBgetResult';
        var nzbgetSettings = '#nzbget_settings';

        $('#nzb_method_icon').removeClass(function(index, css) {
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

    $.torrentMethodHandler = function() {
        $('#options_torrent_clients').hide();
        $('#options_torrent_blackhole').hide();

        var selectedProvider = $('#torrent_method :selected').val();
        var host = ' host:port';
        var username = ' username';
        var password = ' password';
        var client = '';
        var optionPanel = '#options_torrent_blackhole';
        var rpcurl = ' RPC URL';

        $('#torrent_method_icon').removeClass(function(index, css) {
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
            } else if (selectedProvider.toLowerCase() === 'transmission') {
                client = 'Transmission';
                $('#torrent_seed_time_label').text('Stop seeding when inactive for');
                $('#torrent_seed_time_option').show();
                $('#torrent_high_bandwidth_option').show();
                $('#torrent_label_option').hide();
                $('#torrent_label_anime_option').hide();
                $('#torrent_rpcurl_option').show();
                $('#host_desc_torrent').text('URL to your Transmission client (e.g. http://localhost:9091)');
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
            } else if (selectedProvider.toLowerCase() === 'deluged') {
                client = 'Deluge';
                $('#torrent_verify_cert_option').hide();
                $('#torrent_verify_deluge').hide();
                $('#torrent_verify_rtorrent').hide();
                $('#label_warning_deluge').show();
                $('#label_anime_warning_deluge').show();
                $('#torrent_username_option').show();
                $('#host_desc_torrent').text('IP or Hostname of your Deluge Daemon (e.g. scgi://localhost:58846)');
            } else if (selectedProvider.toLowerCase() === 'download_station') {
                client = 'Synology DS';
                $('#torrent_label_option').hide();
                $('#torrent_label_anime_option').hide();
                $('#torrent_paused_option').hide();
                $('#torrent_path_option').find('.fileBrowser').hide();
                $('#host_desc_torrent').text('URL to your Synology DS client (e.g. http://localhost:5000)');
                $('#path_synology').show();
            } else if (selectedProvider.toLowerCase() === 'rtorrent') {
                client = 'rTorrent';
                $('#torrent_paused_option').hide();
                $('#host_desc_torrent').text('URL to your rTorrent client (e.g. scgi://localhost:5000 <br> or https://localhost/rutorrent/plugins/httprpc/action.php)');
                $('#torrent_verify_cert_option').show();
                $('#torrent_verify_deluge').hide();
                $('#torrent_verify_rtorrent').show();
                $('#torrent_auth_type_option').show();
            } else if (selectedProvider.toLowerCase() === 'qbittorrent') {
                client = 'qbittorrent';
                $('#torrent_path_option').hide();
                $('#label_warning_qbittorrent').show();
                $('#label_anime_warning_qbittorrent').show();
                $('#host_desc_torrent').text('URL to your qbittorrent client (e.g. http://localhost:8080)');
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
            }
            $('#host_title').text(client + host);
            $('#username_title').text(client + username);
            $('#password_title').text(client + password);
            $('#torrent_client').text(client);
            $('#rpcurl_title').text(client + rpcurl);
            optionPanel = '#options_torrent_clients';
        }
        $(optionPanel).show();
    };

    $('#torrent_host').on('input', function() {
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

    $('#testSABnzbd').on('click', function() {
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
        }, function(data) {
            $('#testSABnzbd_result').html(data);
        });
    });

    $('#testNZBget').on('click', function() {
        var nzbget = {};
        $('#testNZBget_result').html(MEDUSA.config.loading);
        nzbget.host = $('#nzbget_host').val();
        nzbget.username = $('#nzbget_username').val();
        nzbget.password = $('#nzbget_password').val();
        nzbget.useHttps = $('#nzbget_use_https').val();

        $.get('home/testNZBget', {
            host: nzbget.host,
            username: nzbget.username,
            password: nzbget.password,
            use_https: nzbget.useHttps // eslint-disable-line camelcase
        }, function(data) {
            $('#testNZBget_result').html(data);
        });
    });

    $('#torrent_method').on('change', $.torrentMethodHandler);

    $.torrentMethodHandler();

    $('#test_torrent').on('click', function() {
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
        }, function(data) {
            $('#test_torrent_result').html(data);
        });
    });
};
