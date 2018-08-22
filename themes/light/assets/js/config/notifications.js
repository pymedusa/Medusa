MEDUSA.config.notifications = function() { // eslint-disable-line max-lines
    // @TODO: Remove this
    $.fn.extend({
        addRemoveWarningClass(_) {
            if (_) {
                return $(this).removeClass('warning');
            }
            return $(this).addClass('warning');
        }
    });

    $('#testGrowl').on('click', function() {
        const growl = {};
        growl.host = $.trim($('#growl_host').val());
        growl.password = $.trim($('#growl_password').val());
        if (!growl.host) {
            $('#testGrowl-result').html('Please fill out the necessary fields above.');
            $('#growl_host').addClass('warning');
            return;
        }
        $('#growl_host').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testGrowl-result').html(MEDUSA.config.loading);
        $.get('home/testGrowl', {
            host: growl.host,
            password: growl.password
        }).done(data => {
            $('#testGrowl-result').html(data);
            $('#testGrowl').prop('disabled', false);
        });
    });

    $('#testProwl').on('click', function() {
        const prowl = {};
        prowl.api = $.trim($('#prowl_api').val());
        prowl.priority = $('#prowl_priority').val();
        if (!prowl.api) {
            $('#testProwl-result').html('Please fill out the necessary fields above.');
            $('#prowl_api').addClass('warning');
            return;
        }
        $('#prowl_api').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testProwl-result').html(MEDUSA.config.loading);
        $.get('home/testProwl', {
            prowl_api: prowl.api, // eslint-disable-line camelcase
            prowl_priority: prowl.priority // eslint-disable-line camelcase
        }).done(data => {
            $('#testProwl-result').html(data);
            $('#testProwl').prop('disabled', false);
        });
    });

    $('#testKODI').on('click', function() {
        const kodi = {};
        kodi.host = $.trim($('#kodi_host').val());
        kodi.username = $.trim($('#kodi_username').val());
        kodi.password = $.trim($('#kodi_password').val());
        if (!kodi.host) {
            $('#testKODI-result').html('Please fill out the necessary fields above.');
            $('#kodi_host').addClass('warning');
            return;
        }
        $('#kodi_host').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testKODI-result').html(MEDUSA.config.loading);
        $.get('home/testKODI', {
            host: kodi.host,
            username: kodi.username,
            password: kodi.password
        }).done(data => {
            $('#testKODI-result').html(data);
            $('#testKODI').prop('disabled', false);
        });
    });

    $('#testPHT').on('click', function() {
        const plex = {};
        plex.client = {};
        plex.client.host = $.trim($('#plex_client_host').val());
        plex.client.username = $.trim($('#plex_client_username').val());
        plex.client.password = $.trim($('#plex_client_password').val());
        if (!plex.client.host) {
            $('#testPHT-result').html('Please fill out the necessary fields above.');
            $('#plex_client_host').addClass('warning');
            return;
        }
        $('#plex_client_host').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testPHT-result').html(MEDUSA.config.loading);
        $.get('home/testPHT', {
            host: plex.client.host,
            username: plex.client.username,
            password: plex.client.password
        }).done(data => {
            $('#testPHT-result').html(data);
            $('#testPHT').prop('disabled', false);
        });
    });

    $('#testPMS').on('click', function() {
        const plex = {};
        plex.server = {};
        plex.server.host = $.trim($('#plex_server_host').val());
        plex.server.username = $.trim($('#plex_server_username').val());
        plex.server.password = $.trim($('#plex_server_password').val());
        plex.server.token = $.trim($('#plex_server_token').val());
        if (!plex.server.host) {
            $('#testPMS-result').html('Please fill out the necessary fields above.');
            $('#plex_server_host').addClass('warning');
            return;
        }
        $('#plex_server_host').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testPMS-result').html(MEDUSA.config.loading);
        $.get('home/testPMS', {
            host: plex.server.host,
            username: plex.server.username,
            password: plex.server.password,
            plex_server_token: plex.server.token // eslint-disable-line camelcase
        }).done(data => {
            $('#testPMS-result').html(data);
            $('#testPMS').prop('disabled', false);
        });
    });

    $('#testEMBY').on('click', function() {
        const emby = {};
        emby.host = $('#emby_host').val();
        emby.apikey = $('#emby_apikey').val();
        if (!emby.host || !emby.apikey) {
            $('#testEMBY-result').html('Please fill out the necessary fields above.');
            $('#emby_host').addRemoveWarningClass(emby.host);
            $('#emby_apikey').addRemoveWarningClass(emby.apikey);
            return;
        }
        $('#emby_host,#emby_apikey').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testEMBY-result').html(MEDUSA.config.loading);
        $.get('home/testEMBY', {
            host: emby.host,
            emby_apikey: emby.apikey // eslint-disable-line camelcase
        }).done(data => {
            $('#testEMBY-result').html(data);
            $('#testEMBY').prop('disabled', false);
        });
    });

    $('#testBoxcar2').on('click', function() {
        const boxcar2 = {};
        boxcar2.accesstoken = $.trim($('#boxcar2_accesstoken').val());
        if (!boxcar2.accesstoken) {
            $('#testBoxcar2-result').html('Please fill out the necessary fields above.');
            $('#boxcar2_accesstoken').addClass('warning');
            return;
        }
        $('#boxcar2_accesstoken').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testBoxcar2-result').html(MEDUSA.config.loading);
        $.get('home/testBoxcar2', {
            accesstoken: boxcar2.accesstoken
        }).done(data => {
            $('#testBoxcar2-result').html(data);
            $('#testBoxcar2').prop('disabled', false);
        });
    });

    $('#testPushover').on('click', function() {
        const pushover = {};
        pushover.userkey = $('#pushover_userkey').val();
        pushover.apikey = $('#pushover_apikey').val();
        if (!pushover.userkey || !pushover.apikey) {
            $('#testPushover-result').html('Please fill out the necessary fields above.');
            $('#pushover_userkey').addRemoveWarningClass(pushover.userkey);
            $('#pushover_apikey').addRemoveWarningClass(pushover.apikey);
            return;
        }
        $('#pushover_userkey,#pushover_apikey').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testPushover-result').html(MEDUSA.config.loading);
        $.get('home/testPushover', {
            userKey: pushover.userkey,
            apiKey: pushover.apikey
        }).done(data => {
            $('#testPushover-result').html(data);
            $('#testPushover').prop('disabled', false);
        });
    });

    $('#testLibnotify').on('click', () => {
        $('#testLibnotify-result').html(MEDUSA.config.loading);
        $.get('home/testLibnotify', data => {
            $('#testLibnotify-result').html(data);
        });
    });

    $('#twitterStep1').on('click', () => {
        $('#testTwitter-result').html(MEDUSA.config.loading);
        $.get('home/twitterStep1', data => {
            window.open(data);
        }).done(() => {
            $('#testTwitter-result').html('<b>Step1:</b> Confirm Authorization');
        });
    });

    $('#twitterStep2').on('click', () => {
        const twitter = {};
        twitter.key = $.trim($('#twitter_key').val());
        $('#twitter_key').addRemoveWarningClass(twitter.key);
        if (twitter.key) {
            $('#testTwitter-result').html(MEDUSA.config.loading);
            $.get('home/twitterStep2', {
                key: twitter.key
            }, data => {
                $('#testTwitter-result').html(data);
            });
        }
        $('#testTwitter-result').html('Please fill out the necessary fields above.');
    });

    $('#testTwitter').on('click', () => {
        $.get('home/testTwitter', data => {
            $('#testTwitter-result').html(data);
        });
    });

    $('#settingsNMJ').on('click', () => {
        const nmj = {};
        if ($('#nmj_host').val()) {
            $('#testNMJ-result').html(MEDUSA.config.loading);
            nmj.host = $('#nmj_host').val();

            $.get('home/settingsNMJ', {
                host: nmj.host
            }, data => {
                if (data === null) {
                    $('#nmj_database').removeAttr('readonly');
                    $('#nmj_mount').removeAttr('readonly');
                }
                const JSONData = $.parseJSON(data);
                $('#testNMJ-result').html(JSONData.message);
                $('#nmj_database').val(JSONData.database);
                $('#nmj_mount').val(JSONData.mount);

                if (JSONData.database) {
                    $('#nmj_database').prop('readonly', true);
                } else {
                    $('#nmj_database').removeAttr('readonly');
                }
                if (JSONData.mount) {
                    $('#nmj_mount').prop('readonly', true);
                } else {
                    $('#nmj_mount').removeAttr('readonly');
                }
            });
        }
        alert('Please fill in the Popcorn IP address'); // eslint-disable-line no-alert
        $('#nmj_host').focus();
    });

    $('#testNMJ').on('click', function() {
        const nmj = {};
        nmj.host = $.trim($('#nmj_host').val());
        nmj.database = $('#nmj_database').val();
        nmj.mount = $('#nmj_mount').val();
        if (nmj.host) {
            $('#nmj_host').removeClass('warning');
            $(this).prop('disabled', true);
            $('#testNMJ-result').html(MEDUSA.config.loading);
            $.get('home/testNMJ', {
                host: nmj.host,
                database: nmj.database,
                mount: nmj.mount
            }).done(data => {
                $('#testNMJ-result').html(data);
                $('#testNMJ').prop('disabled', false);
            });
        }
        $('#testNMJ-result').html('Please fill out the necessary fields above.');
        $('#nmj_host').addClass('warning');
    });

    $('#settingsNMJv2').on('click', () => {
        const nmjv2 = {};
        if ($('#nmjv2_host').val()) {
            $('#testNMJv2-result').html(MEDUSA.config.loading);
            nmjv2.host = $('#nmjv2_host').val();
            nmjv2.dbloc = '';
            const radios = document.getElementsByName('nmjv2_dbloc');
            for (let i = 0, len = radios.length; i < len; i++) {
                if (radios[i].checked) {
                    nmjv2.dbloc = radios[i].value;
                    break;
                }
            }

            nmjv2.dbinstance = $('#NMJv2db_instance').val();
            $.get('home/settingsNMJv2', {
                host: nmjv2.host,
                dbloc: nmjv2.dbloc,
                instance: nmjv2.dbinstance
            }, data => {
                if (data === null) {
                    $('#nmjv2_database').removeAttr('readonly');
                }
                const JSONData = $.parseJSON(data);
                $('#testNMJv2-result').html(JSONData.message);
                $('#nmjv2_database').val(JSONData.database);

                if (JSONData.database) {
                    $('#nmjv2_database').prop('readonly', true);
                } else {
                    $('#nmjv2_database').removeAttr('readonly');
                }
            });
        }
        alert('Please fill in the Popcorn IP address'); // eslint-disable-line no-alert
        $('#nmjv2_host').focus();
    });

    $('#testNMJv2').on('click', function() {
        const nmjv2 = {};
        nmjv2.host = $.trim($('#nmjv2_host').val());
        if (nmjv2.host) {
            $('#nmjv2_host').removeClass('warning');
            $(this).prop('disabled', true);
            $('#testNMJv2-result').html(MEDUSA.config.loading);
            $.get('home/testNMJv2', {
                host: nmjv2.host
            }).done(data => {
                $('#testNMJv2-result').html(data);
                $('#testNMJv2').prop('disabled', false);
            });
        }
        $('#testNMJv2-result').html('Please fill out the necessary fields above.');
        $('#nmjv2_host').addClass('warning');
    });

    $('#testFreeMobile').on('click', function() {
        const freemobile = {};
        freemobile.id = $.trim($('#freemobile_id').val());
        freemobile.apikey = $.trim($('#freemobile_apikey').val());
        if (!freemobile.id || !freemobile.apikey) {
            $('#testFreeMobile-result').html('Please fill out the necessary fields above.');
            if (freemobile.id) {
                $('#freemobile_id').removeClass('warning');
            } else {
                $('#freemobile_id').addClass('warning');
            }
            if (freemobile.apikey) {
                $('#freemobile_apikey').removeClass('warning');
            } else {
                $('#freemobile_apikey').addClass('warning');
            }
            return;
        }
        $('#freemobile_id,#freemobile_apikey').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testFreeMobile-result').html(MEDUSA.config.loading);
        $.get('home/testFreeMobile', {
            freemobile_id: freemobile.id, // eslint-disable-line camelcase
            freemobile_apikey: freemobile.apikey // eslint-disable-line camelcase
        }).done(data => {
            $('#testFreeMobile-result').html(data);
            $('#testFreeMobile').prop('disabled', false);
        });
    });

    $('#testTelegram').on('click', function() {
        const telegram = {};
        telegram.id = $.trim($('#telegram_id').val());
        telegram.apikey = $.trim($('#telegram_apikey').val());
        if (!telegram.id || !telegram.apikey) {
            $('#testTelegram-result').html('Please fill out the necessary fields above.');
            $('#telegram_id').addRemoveWarningClass(telegram.id);
            $('#telegram_apikey').addRemoveWarningClass(telegram.apikey);
            return;
        }
        $('#telegram_id,#telegram_apikey').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testTelegram-result').html(MEDUSA.config.loading);
        $.get('home/testTelegram', {
            telegram_id: telegram.id, // eslint-disable-line camelcase
            telegram_apikey: telegram.apikey // eslint-disable-line camelcase
        }).done(data => {
            $('#testTelegram-result').html(data);
            $('#testTelegram').prop('disabled', false);
        });
    });

    $('#testSlack').on('click', function() {
        const slack = {};
        slack.webhook = $.trim($('#slack_webhook').val());

        if (!slack.webhook) {
            $('#testSlack-result').html('Please fill out the necessary fields above.');
            $('#slack_webhook').addRemoveWarningClass(slack.webhook);
            return;
        }
        $('#slack_webhook').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testSlack-result').html(MEDUSA.config.loading);
        $.get('home/testslack', {
            slack_webhook: slack.webhook // eslint-disable-line camelcase
        }).done(data => {
            $('#testSlack-result').html(data);
            $('#testSlack').prop('disabled', false);
        });
    });

    $('#TraktGetPin').on('click', () => {
        window.open($('#trakt_pin_url').val(), 'popUp', 'toolbar=no, scrollbars=no, resizable=no, top=200, left=200, width=650, height=550');
        $('#trakt_pin').prop('disabled', false);
    });

    $('#trakt_pin').on('keyup change', () => {
        if ($('#trakt_pin').val().length === 0) {
            $('#TraktGetPin').removeClass('hide');
            $('#authTrakt').addClass('hide');
        } else {
            $('#TraktGetPin').addClass('hide');
            $('#authTrakt').removeClass('hide');
        }
    });

    $('#authTrakt').on('click', () => {
        const trakt = {};
        trakt.pin = $('#trakt_pin').val();
        if (trakt.pin.length !== 0) {
            $.get('home/getTraktToken', {
                trakt_pin: trakt.pin // eslint-disable-line camelcase
            }).done(data => {
                $('#testTrakt-result').html(data);
                $('#authTrakt').addClass('hide');
                $('#trakt_pin').prop('disabled', true);
                $('#trakt_pin').val('');
                $('#TraktGetPin').removeClass('hide');
            });
        }
    });

    $('#testTrakt').on('click', function() {
        const trakt = {};
        trakt.username = $.trim($('#trakt_username').val());
        trakt.trendingBlacklist = $.trim($('#trakt_blacklist_name').val());
        if (!trakt.username) {
            $('#testTrakt-result').html('Please fill out the necessary fields above.');
            $('#trakt_username').addRemoveWarningClass(trakt.username);
            return;
        }

        if (/\s/g.test(trakt.trendingBlacklist)) {
            $('#testTrakt-result').html('Check blacklist name; the value needs to be a trakt slug');
            $('#trakt_blacklist_name').addClass('warning');
            return;
        }
        $('#trakt_username').removeClass('warning');
        $('#trakt_blacklist_name').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testTrakt-result').html(MEDUSA.config.loading);
        $.get('home/testTrakt', {
            username: trakt.username,
            blacklist_name: trakt.trendingBlacklist // eslint-disable-line camelcase
        }).done(data => {
            $('#testTrakt-result').html(data);
            $('#testTrakt').prop('disabled', false);
        });
    });

    $('#forceSync').on('click', () => {
        $('#testTrakt-result').html(MEDUSA.config.loading);
        $.getJSON('home/forceTraktSync', data => {
            $('#testTrakt-result').html(data.result);
        });
    });

    $('#testEmail').on('click', () => {
        let to = '';
        const status = $('#testEmail-result');
        status.html(MEDUSA.config.loading);
        let host = $('#email_host').val();
        host = host.length > 0 ? host : null;
        let port = $('#email_port').val();
        port = port.length > 0 ? port : null;
        const tls = $('#email_tls').attr('checked') === undefined ? 0 : 1;
        let from = $('#email_from').val();
        from = from.length > 0 ? from : 'root@localhost';
        const user = $('#email_user').val().trim();
        const pwd = $('#email_password').val();
        let err = '';
        if (host === null) {
            err += '<li style="color: red;">You must specify an SMTP hostname!</li>';
        }
        if (port === null) {
            err += '<li style="color: red;">You must specify an SMTP port!</li>';
        } else if (port.match(/^\d+$/) === null || parseInt(port, 10) > 65535) {
            err += '<li style="color: red;">SMTP port must be between 0 and 65535!</li>';
        }
        if (err.length > 0) {
            err = '<ol>' + err + '</ol>';
            status.html(err);
        } else {
            to = prompt('Enter an email address to send the test to:', null); // eslint-disable-line no-alert
            if (to === null || to.length === 0 || to.match(/.*@.*/) === null) {
                status.html('<p style="color: red;">You must provide a recipient email address!</p>');
            } else {
                $.get('home/testEmail', {
                    host,
                    port,
                    smtp_from: from, // eslint-disable-line camelcase
                    use_tls: tls, // eslint-disable-line camelcase
                    user,
                    pwd,
                    to
                }, msg => {
                    $('#testEmail-result').html(msg);
                });
            }
        }
    });

    $('#testPushalot').on('click', function() {
        const pushalot = {};
        pushalot.authToken = $.trim($('#pushalot_authorizationtoken').val());
        if (!pushalot.authToken) {
            $('#testPushalot-result').html('Please fill out the necessary fields above.');
            $('#pushalot_authorizationtoken').addClass('warning');
            return;
        }
        $('#pushalot_authorizationtoken').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testPushalot-result').html(MEDUSA.config.loading);
        $.get('home/testPushalot', {
            authorizationToken: pushalot.authToken
        }).done(data => {
            $('#testPushalot-result').html(data);
            $('#testPushalot').prop('disabled', false);
        });
    });

    $('#testPushbullet').on('click', function() {
        const pushbullet = {};
        pushbullet.api = $.trim($('#pushbullet_api').val());
        if (!pushbullet.api) {
            $('#testPushbullet-result').html('Please fill out the necessary fields above.');
            $('#pushbullet_api').addClass('warning');
            return;
        }
        $('#pushbullet_api').removeClass('warning');
        $(this).prop('disabled', true);
        $('#testPushbullet-result').html(MEDUSA.config.loading);
        $.get('home/testPushbullet', {
            api: pushbullet.api
        }).done(data => {
            $('#testPushbullet-result').html(data);
            $('#testPushbullet').prop('disabled', false);
        });
    });

    function getPushbulletDevices(msg) {
        const pushbullet = {};
        pushbullet.api = $('#pushbullet_api').val();

        if (msg) {
            $('#testPushbullet-result').html(MEDUSA.config.loading);
        }

        if (!pushbullet.api) {
            $('#testPushbullet-result').html('You didn\'t supply a Pushbullet api key');
            $('#pushbullet_api').focus();
            return false;
        }

        $.get('home/getPushbulletDevices', {
            api: pushbullet.api
        }, data => {
            pushbullet.devices = $.parseJSON(data).devices;
            pushbullet.currentDevice = $('#pushbullet_device').val();
            $('#pushbullet_device_list').html('');
            for (let i = 0, len = pushbullet.devices.length; i < len; i++) {
                if (pushbullet.devices[i].active === true) {
                    if (pushbullet.currentDevice === pushbullet.devices[i].iden) {
                        $('#pushbullet_device_list').append('<option value="' + pushbullet.devices[i].iden + '" selected>' + pushbullet.devices[i].nickname + '</option>');
                    } else {
                        $('#pushbullet_device_list').append('<option value="' + pushbullet.devices[i].iden + '">' + pushbullet.devices[i].nickname + '</option>');
                    }
                }
            }
            $('#pushbullet_device_list').prepend('<option value="" ' + (pushbullet.currentDevice === '' ? 'selected' : '') + '>All devices</option>');
            if (msg) {
                $('#testPushbullet-result').html(msg);
            }
        });

        $('#pushbullet_device_list').on('change', () => {
            $('#pushbullet_device').val($('#pushbullet_device_list').val());
            $('#testPushbullet-result').html('Don\'t forget to save your new pushbullet settings.');
        });
    }

    $('#getPushbulletDevices').on('click', () => {
        getPushbulletDevices('Device list updated. Please choose a device to push to.');
    });

    // We have to call this function on dom ready to create the devices select
    getPushbulletDevices();

    $('#email_show').on('change', () => {
        const key = parseInt($('#email_show').val(), 10);
        $.getJSON('home/loadShowNotifyLists', notifyData => {
            if (notifyData._size > 0) {
                $('#email_show_list').val(key >= 0 ? notifyData[key.toString()].list : '');
            }
        });
    });
    $('#prowl_show').on('change', () => {
        const key = parseInt($('#prowl_show').val(), 10);
        $.getJSON('home/loadShowNotifyLists', notifyData => {
            if (notifyData._size > 0) {
                $('#prowl_show_list').val(key >= 0 ? notifyData[key.toString()].prowl_notify_list : '');
            }
        });
    });

    function loadShowNotifyLists() {
        $.getJSON('home/loadShowNotifyLists', list => {
            let html;
            let s;
            if (list._size === 0) {
                return;
            }

            // Convert the 'list' object to a js array of objects so that we can sort it
            const _list = [];
            for (s in list) {
                if (s.charAt(0) !== '_') {
                    _list.push(list[s]);
                }
            }
            const sortedList = _list.sort((a, b) => {
                if (a.name < b.name) {
                    return -1;
                }
                if (a.name > b.name) {
                    return 1;
                }
                return 0;
            });
            html = '<option value="-1">-- Select --</option>';
            for (s in sortedList) {
                if (sortedList[s].id && sortedList[s].name) {
                    html += '<option value="' + sortedList[s].id + '">' + $('<div/>').text(sortedList[s].name).html() + '</option>';
                }
            }
            $('#email_show').html(html);
            $('#email_show_list').val('');

            $('#prowl_show').html(html);
            $('#prowl_show_list').val('');
        });
    }
    // Load the per show notify lists everytime this page is loaded
    loadShowNotifyLists();

    // Update the internal data struct anytime settings are saved to the server
    $('#email_show').on('notify', loadShowNotifyLists);
    $('#prowl_show').on('notify', loadShowNotifyLists);

    $('#email_show_save').on('click', () => {
        $.post('home/saveShowNotifyList', {
            show: $('#email_show').val(),
            emails: $('#email_show_list').val()
        }, loadShowNotifyLists);
    });
    $('#prowl_show_save').on('click', () => {
        $.post('home/saveShowNotifyList', {
            show: $('#prowl_show').val(),
            prowlAPIs: $('#prowl_show_list').val()
        }, () => {
            // Reload the per show notify lists to reflect changes
            loadShowNotifyLists();
        });
    });

    // Show instructions for plex when enabled
    $('#use_plex_server').on('click', function() {
        if ($(this).is(':checked')) {
            $('.plexinfo').removeClass('hide');
        } else {
            $('.plexinfo').addClass('hide');
        }
    });
};
