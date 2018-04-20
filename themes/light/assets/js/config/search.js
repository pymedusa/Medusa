MEDUSA.config.search = function() {
    $('#config-components').tabs();
    $('#nzb_dir').fileBrowser({ title: 'Select .nzb black hole/watch location' });
    $('#torrent_dir').fileBrowser({ title: 'Select .torrent black hole/watch location' });
    $('#torrent_path').fileBrowser({ title: 'Select .torrent download location' });
    $('#torrent_seed_location').fileBrowser({ title: 'Select Post-Processed seeding torrents location' });

    $.fn.nzbMethodHandler = function() {
        const selectedProvider = $('#nzb_method :selected').val();
        const blackholeSettings = '#blackhole_settings';
        const sabnzbdSettings = '#sabnzbd_settings';
        const testSABnzbd = '#testSABnzbd';
        const testSABnzbdResult = '#testSABnzbd_result';
        const testNZBget = '#testNZBget';
        const testNZBgetResult = '#testNZBgetResult';
        const nzbgetSettings = '#nzbget_settings';

        $('#nzb_method_icon').removeClass((index, css) => {
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

        const selectedProvider = $('#torrent_method :selected').val();
        const host = ' host:port';
        const username = ' username';
        const password = ' password';
        let client = '';
        let optionPanel = '#options_torrent_blackhole';
        const rpcurl = ' RPC URL';

        $('#torrent_method_icon').removeClass((index, css) => {
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
                $('#label_warning_utorrent').show();
                $('#label_anime_warning_utorrent').show();
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

    $('#torrent_host').on('input', () => {
        if ($('#torrent_method :selected').val().toLowerCase() === 'rtorrent') {
            const hostname = $('#torrent_host').val();
            const isMatch = hostname.substr(0, 7) === 'scgi://';

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

    $('#testSABnzbd').on('click', () => {
        const sab = {};
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
        }, data => {
            $('#testSABnzbd_result').html(data);
        });
    });

    $('#testNZBget').on('click', () => {
        const nzbget = {};
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
        }, data => {
            $('#testNZBget_result').html(data);
        });
    });

    $('#torrent_method').on('change', $.torrentMethodHandler);

    $.torrentMethodHandler();

    $('#test_torrent').on('click', () => {
        const torrent = {};
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
        }, data => {
            $('#test_torrent_result').html(data);
        });
    });
};
