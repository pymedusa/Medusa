<%inherit file="/layouts/main.mako"/>
<%!
    import re
    from medusa import app
    from medusa.common import SKIPPED, WANTED, UNAIRED, ARCHIVED, IGNORED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, FAILED
    from medusa.common import Quality, qualityPresets, statusStrings, qualityPresetStrings, cpu_presets, MULTI_EP_STRINGS
    from medusa.indexers.indexer_api import indexerApi
    from medusa.indexers.utils import get_trakt_indexer
%>
<%block name="scripts">
<script>
window.app = {};
window.app = new Vue({
    store,
    el: '#vue-wrap',
    metaInfo: {
        title: 'Config - Notifications'
    },
    data() {
        return {
            header: 'Notifications'
        };
    },
    mounted() {
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
    }
});
</script>
</%block>
<%block name="content">
<h1 class="header">{{header}}</h1>
<div id="config">
    <div id="config-content">
        <form id="configForm" action="config/notifications/saveNotifications" method="post">
            <div id="config-components">
                <ul>
                    <li><app-link href="#home-theater-nas">Home Theater / NAS</app-link></li>
                    <li><app-link href="#devices">Devices</app-link></li>
                    <li><app-link href="#social">Social</app-link></li>
                </ul>
                <div id="home-theater-nas">
                    
                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <span class="icon-notifiers-kodi" title="KODI"></span>
                            <h3><app-link href="http://kodi.tv">KODI</app-link></h3>
                            <p>A free and open source cross-platform media center and home entertainment system software with a 10-foot user interface designed for the living-room TV.</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for KODI -->

                                <config-checkbox :checked="config.kodi.enabled" label="Enable" id="use_kodi" :explaination="['Send KODI commands?']" @change="save()"  @update="config.kodi.enabled = $event"></config-checkbox>

                                <div v-show="config.kodi.enabled" id="content-use-kodi"> <!-- show based on config.kodi.enabled -->

                                    <config-checkbox :checked="config.kodi.alwaysOn" label="Always on" id="kodi_always_on" :explaination="['log errors when unreachable?']" @change="save()"  @update="config.kodi.alwaysOn = $event"></config-checkbox>
                                    
                                    <div class="form-group">
                                        <div class="row">
                                            <label for="kodi_notify_onsnatch" class="col-sm-2 control-label">
                                                <span>Notify on snatch</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <toggle-button :width="45" :height="22" id="kodi_notify_onsnatch" name="kodi_notify_onsnatch" v-model="config.kodi.notify.snatch" sync></toggle-button>
                                                <p>send a notification when a download starts?</p>
                                            </div>
                                        </div>
                                    </div>

                                    <div class="form-group">
                                            <div class="row">
                                                <label for="kodi_notify_ondownload" class="col-sm-2 control-label">
                                                    <span>Notify on download</span>
                                                </label>
                                                <div class="col-sm-10 content">
                                                    <toggle-button :width="45" :height="22" id="kodi_notify_ondownload" name="kodi_notify_ondownload" v-model="config.kodi.notify.download" sync></toggle-button>
                                                    <p>send a notification when a download finishes?</p>
                                                </div>
                                            </div>
                                        </div>
                                        
                                    <div class="form-group">
                                            <div class="row">
                                                <label for="kodi_notify_onsubtitledownload" class="col-sm-2 control-label">
                                                    <span>Notify on subtitle download</span>
                                                </label>
                                                <div class="col-sm-10 content">
                                                    <toggle-button :width="45" :height="22" id="kodi_notify_onsubtitledownload" name="kodi_notify_onsubtitledownload" v-model="config.kodi.notify.subtitleDownload" sync></toggle-button>
                                                    <p>send a notification when subtitles are downloaded?</p>
                                                </div>
                                            </div>
                                        </div>

                                    <div class="form-group">
                                            <div class="row">
                                                <label for="kodi_update_library" class="col-sm-2 control-label">
                                                    <span>Update library</span>
                                                </label>
                                                <div class="col-sm-10 content">
                                                    <toggle-button :width="45" :height="22" id="kodi_update_library" name="kodi_update_library" v-model="config.kodi.notify.library" sync></toggle-button>
                                                    <p>update KODI library when a download finishes?</p>
                                                </div>
                                            </div>
                                        </div>

                                    <div class="form-group">
                                            <div class="row">
                                                <label for="kodi_update_full" class="col-sm-2 control-label">
                                                    <span>Full library update</span>
                                                </label>
                                                <div class="col-sm-10 content">
                                                    <toggle-button :width="45" :height="22" id="kodi_update_full" name="kodi_update_full" v-model="config.kodi.update.full" sync></toggle-button>
                                                    <p>perform a full library update if update per-show fails?</p>
                                                </div>
                                            </div>
                                        </div>

                                    <div class="form-group">
                                        <div class="row">
                                            <label for="kodi_clean_library" class="col-sm-2 control-label">
                                                <span>Clean library</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <toggle-button :width="45" :height="22" id="kodi_clean_library" name="kodi_clean_library" v-model="config.kodi.cleanLibrary" sync></toggle-button>
                                                <p>clean KODI library when replaces a already downloaded episode?</p>
                                            </div>
                                        </div>
                                    </div>

                                    <div class="form-group">
                                        <div class="row">
                                            <label for="kodi_update_onlyfirst" class="col-sm-2 control-label">
                                                <span>Only update first host</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <toggle-button :width="45" :height="22" id="kodi_update_onlyfirst" name="kodi_update_onlyfirst" v-model="config.kodi.update.onlyFirst" sync></toggle-button>
                                                <p>only send library updates/clean to the first active host?</p>
                                            </div>
                                        </div>
                                    </div>

                                    <div class="form-group">
                                        <div class="row">
                                            <label for="kodi_host" class="col-sm-2 control-label">
                                                <span>KODI IP:Port</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <!-- @TODO: replace with a select-list component, when the KODI_HOSTS is patchable through apiv2 -->
                                                <input type="text" name="kodi_host" id="kodi_host" value="${','.join(app.KODI_HOST)}" class="form-control input-sm max-input450"/>
                                                <p>host running KODI (eg. 192.168.1.100:8080)</p>
                                                <p>(multiple host strings must be separated by commas)</p>
                                            </div>
                                        </div>
                                    </div>

                                    <div class="form-group">
                                        <div class="row">
                                            <label for="kodi_username" class="col-sm-2 control-label">
                                                <span>Username</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <input type="text" name="kodi_username" id="kodi_username" value="${app.KODI_USERNAME}" class="form-control input-sm max-input350" autocomplete="no" />
                                                <p>username for your KODI server (blank for none)</p>
                                            </div>
                                        </div>
                                    </div>

                                    <div class="form-group">
                                        <div class="row">
                                            <label for="kodi_password" class="col-sm-2 control-label">
                                                <span>Password</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                    <input type="password" name="kodi_password" id="kodi_password" value="${app.KODI_PASSWORD}" class="form-control input-sm max-input350" autocomplete="no"/>
                                                <p>password for your KODI server (blank for none)</p>
                                            </div>
                                        </div>
                                    </div>

                                    <div class="testNotification" id="testKODI-result">Click below to test.</div>
                                    <input  class="btn-medusa" type="button" value="Test KODI" id="testKODI" />
                                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes" />
                            
                                </div>

                            </fieldset>    
                        </div>

                    </div>

                    <div class="row component-group">
                        <div class="component-group-desc col-xs-12 col-md-2">
                            <span class="icon-notifiers-plex" title="Plex Media Server"></span>
                            <h3><app-link href="https://plex.tv">Plex Media Server</app-link></h3>
                            <p>Experience your media on a visually stunning, easy to use interface on your Mac connected to your TV. Your media library has never looked this good!</p>
                            <p class="plexinfo hide">For sending notifications to Plex Home Theater (PHT) clients, use the KODI notifier with port <b>3005</b>.</p>
                        </div>
                        <div class="col-xs-12 col-md-10">
                            <fieldset class="component-group-list">
                                <!-- All form components here for plex media server -->
                                <div class="form-group">
                                    <div class="row">
                                        <label for="use_plex_server" class="col-sm-2 control-label">
                                            <span>Password</span>
                                        </label>
                                        <div class="col-sm-10 content">
                                            <toggle-button :width="45" :height="22" id="use_kodi" name="use_kodi" v-model="config.plex.server.enabled" sync></toggle-button>
                                            <p>Send Plex Media Server library updates?</p>
                                        </div>
                                    </div>
                                </div>

                                <div v-show="config.plex.server.enabled" id="content-use-kodi"> <!-- show based on config.plex.server.enabled -->
                                    <div class="form-group">
                                        <div class="row">
                                            <label for="plex_server_token" class="col-sm-2 control-label">
                                                <span>Plex Media Server Auth Token</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                    <input type="text" name="plex_server_token" id="plex_server_token" value="${app.PLEX_SERVER_TOKEN}" class="form-control input-sm input250"/>
                                                <p>Auth Token used by plex</p>
                                                <p><span>See: <app-link href="https://support.plex.tv/hc/en-us/articles/204059436-Finding-your-account-token-X-Plex-Token" class="wiki"><strong>Finding your account token</strong></app-link></span></p>
                                            </div>
                                        </div>
                                    </div>

                                    <div class="form-group">
                                        <div class="row">
                                            <label for="plex_server_username" class="col-sm-2 control-label">
                                                <span>Username</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <input type="text" name="plex_server_username" id="plex_server_username" value="${app.PLEX_SERVER_USERNAME}" class="form-control input-sm max-input250" autocomplete="no"/>
                                                <p>blank = no authentication</p>
                                            </div>
                                        </div>
                                    </div>

                                    <div class="form-group">
                                        <div class="row">
                                            <label for="plex_server_password" class="col-sm-2 control-label">
                                                <span>Password</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                    <input type="password" name="plex_server_password" id="plex_server_password" value="${'*' * len(app.PLEX_SERVER_PASSWORD)}" class="form-control input-sm input250" autocomplete="no"/>
                                                <p>blank = no authentication</p>
                                            </div>
                                        </div>
                                    </div>

                                    <div class="form-group">
                                        <div class="row">
                                            <label for="plex_update_library" class="col-sm-2 control-label">
                                                <span>Update Library</span>
                                            </label>
                                            <div class="col-sm-10 content">
                                                <toggle-button :width="45" :height="22" id="plex_update_library" name="plex_update_library" v-model="config.kodi.enabled" sync></toggle-button>
                                                <p>update Plex Media Server library when a download finishes</p>
                                            </div>
                                        </div>
                                    </div>
                                
                                </div>
                            
                            
                            </fieldset>
                        </div>
                    </div>    

                        
                            <div id="content_use_plex_server">
                                
                                <div class="component-group" style="padding: 0; min-height: 130px;">

                                    
                                </div>
                                <div class="component-group" style="padding: 0; min-height: 50px;">
                                    <div class="field-pair">
                                        <label for="plex_update_library">
                                            <span class="component-title">Update Library</span>
                                            <span class="component-desc">
                                                <input type="checkbox" class="enabler" name="plex_update_library" id="plex_update_library" ${'checked="checked"' if app.PLEX_UPDATE_LIBRARY else ''}/>
                                                <p>update Plex Media Server library when a download finishes</p>
                                            </span>
                                        </label>
                                    </div>
                                    <div id="content_plex_update_library">
                                        <div class="field-pair">
                                            <label for="plex_server_host">
                                                <span class="component-title">Plex Media Server IP:Port</span>
                                                <span class="component-desc">
                                                    <input type="text" name="plex_server_host" id="plex_server_host" value="${re.sub(r'\b,\b', ', ', ','.join(app.PLEX_SERVER_HOST))}" class="form-control input-sm input350"/>
                                                    <div class="clear-left">
                                                        <p>one or more hosts running Plex Media Server<br>(eg. 192.168.1.1:32400, 192.168.1.2:32400)</p>
                                                    </div>
                                                </span>
                                            </label>
                                        </div>
                                        <div class="field-pair">
                                            <label for="plex_server_https">
                                                <span class="component-title">HTTPS</span>
                                                <span class="component-desc">
                                                    <input type="checkbox" name="plex_server_https" id="plex_server_https" ${'checked="checked"' if app.PLEX_SERVER_HTTPS else ''}/>
                                                    <p>use https for plex media server requests?</p>
                                                </span>
                                            </label>
                                        </div>
                                        <div class="field-pair">
                                            <div class="testNotification" id="testPMS-result">Click below to test Plex Media Server(s)</div>
                                            <input class="btn-medusa" type="button" value="Test Plex Media Server" id="testPMS" />
                                            <input type="submit" class="config_submitter btn-medusa" value="Save Changes" />
                                            <div class="clear-left">&nbsp;</div>
                                        </div>
                                    </div>
                                </div>
                            </div><!-- /content_use_plex_server -->
                        </fieldset>
                    </div><!-- /plex media server component-group -->
                    <div class="component-group-desc-legacy">
                        <span class="icon-notifiers-plexth" title="Plex Home Theater"></span>
                        <h3><app-link href="https://plex.tv">Plex Home Theater</app-link></h3>
                    </div>
                    <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="use_plex_client">
                                    <span class="component-title">Enable</span>
                                    <span class="component-desc">
                                        <input type="checkbox" class="enabler" name="use_plex_client" id="use_plex_client" :checked="config.plex.client.enabled"/>
                                        <p>Send Plex Home Theater notifications?</p>
                                    </span>
                                </label>
                            </div>
                            <div id="content_use_plex_client">
                                <div class="field-pair">
                                    <label for="plex_notify_onsnatch">
                                        <span class="component-title">Notify on snatch</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="plex_notify_onsnatch" id="plex_notify_onsnatch" ${'checked="checked"' if app.PLEX_NOTIFY_ONSNATCH else ''}/>
                                            <p>send a notification when a download starts?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="plex_notify_ondownload">
                                        <span class="component-title">Notify on download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="plex_notify_ondownload" id="plex_notify_ondownload" ${'checked="checked"' if app.PLEX_NOTIFY_ONDOWNLOAD else ''}/>
                                            <p>send a notification when a download finishes?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="plex_notify_onsubtitledownload">
                                        <span class="component-title">Notify on subtitle download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="plex_notify_onsubtitledownload" id="plex_notify_onsubtitledownload" ${'checked="checked"' if app.PLEX_NOTIFY_ONSUBTITLEDOWNLOAD else ''}/>
                                            <p>send a notification when subtitles are downloaded?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="plex_client_host">
                                        <span class="component-title">Plex Home Theater IP:Port</span>
                                        <span class="component-desc">
                                            <input type="text" name="plex_client_host" id="plex_client_host" value="${','.join(app.PLEX_CLIENT_HOST)}" class="form-control input-sm input350"/>
                                            <div class="clear-left">
                                                <p>one or more hosts running Plex Home Theater<br>(eg. 192.168.1.100:3000, 192.168.1.101:3000)</p>
                                            </div>
                                        </span>
                                    </label>
                                </div>
                                <div class="component-group" style="padding: 0; min-height: 130px;">
                                    <div class="field-pair">
                                        <label for="plex_server_username">
                                            <span class="component-title">Username</span>
                                            <span class="component-desc">
                                                <input type="text" name="plex_client_username" id="plex_client_username" value="${app.PLEX_CLIENT_USERNAME}" class="form-control input-sm input250"
                                                       autocomplete="no" />
                                                <p>blank = no authentication</p>
                                            </span>
                                        </label>
                                    </div>
                                    <div class="field-pair">
                                        <label for="plex_client_password">
                                            <span class="component-title">Password</span>
                                            <span class="component-desc">
                                                <input type="password" name="plex_client_password" id="plex_client_password" value="${'*' * len(app.PLEX_CLIENT_PASSWORD)}" class="form-control input-sm input250" autocomplete="no"/>
                                                <p>blank = no authentication</p>
                                            </span>
                                        </label>
                                    </div>
                                </div>
                                <div class="field-pair">
                                    <div class="testNotification" id="testPHT-result">Click below to test Plex Home Theater(s)</div>
                                    <input class="btn-medusa" type="button" value="Test Plex Home Theater" id="testPHT" />
                                    <input type="submit" class="config_submitter btn-medusa" value="Save Changes" />
                                    <div class=clear-left><p>Note: some Plex Home Theaters <b class="boldest">do not</b> support notifications e.g. Plexapp for Samsung TVs</p></div>
                                </div>
                            </div><!-- /content_use_plex_client -->
                        </fieldset>
                    </div><!-- /Plex Home Theater component-group -->
                    <div class="component-group-desc-legacy">
                        <span class="icon-notifiers-emby" title="Emby"></span>
                        <h3><app-link href="http://emby.media">Emby</app-link></h3>
                        <p>A home media server built using other popular open source technologies.</p>
                    </div>
                    <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="use_emby">
                                    <span class="component-title">Enable</span>
                                    <span class="component-desc">
                                        <input type="checkbox" class="enabler" name="use_emby" id="use_emby" :checked="config.emby.enabled"/>
                                        <p>Send update commands to Emby?<p>
                                    </span>
                                </label>
                            </div>
                            <div id="content_use_emby">
                                <div class="field-pair">
                                    <label for="emby_host">
                                        <span class="component-title">Emby IP:Port</span>
                                        <input type="text" name="emby_host" id="emby_host" value="${app.EMBY_HOST}" class="form-control input-sm input250"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">host running Emby (eg. 192.168.1.100:8096)</span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="emby_apikey">
                                        <span class="component-title">Emby API Key</span>
                                        <input type="text" name="emby_apikey" id="emby_apikey" value="${app.EMBY_APIKEY}" class="form-control input-sm input250"/>
                                    </label>
                                </div>
                                <div class="testNotification" id="testEMBY-result">Click below to test.</div>
                                <input class="btn-medusa" type="button" value="Test Emby" id="testEMBY" />
                                <input type="submit" class="config_submitter btn-medusa" value="Save Changes" />
                            </div><!-- /content_use_emby //-->
                        </fieldset>
                    </div><!-- /emby component-group //-->
                    <div class="component-group-desc-legacy">
                        <span class="icon-notifiers-nmj" title="Networked Media Jukebox"></span>
                        <h3><app-link href="http://www.popcornhour.com/">NMJ</app-link></h3>
                        <p>The Networked Media Jukebox, or NMJ, is the official media jukebox interface made available for the Popcorn Hour 200-series.</p>
                    </div>
                    <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="use_nmj">
                                    <span class="component-title">Enable</span>
                                    <span class="component-desc">
                                        <input type="checkbox" class="enabler" name="use_nmj" id="use_nmj" ${'checked="checked"' if app.USE_NMJ else ''}/>
                                        <p>Send update commands to NMJ?</p>
                                    </span>
                                </label>
                            </div>
                            <div id="content_use_nmj">
                                <div class="field-pair">
                                    <label for="nmj_host">
                                        <span class="component-title">Popcorn IP address</span>
                                        <input type="text" name="nmj_host" id="nmj_host" value="${app.NMJ_HOST}" class="form-control input-sm input250"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">IP address of Popcorn 200-series (eg. 192.168.1.100)</span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">Get settings</span>
                                        <input class="btn-medusa btn-inline" type="button" value="Get Settings" id="settingsNMJ" />
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">the Popcorn Hour device must be powered on and NMJ running.</span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="nmj_database">
                                        <span class="component-title">NMJ database</span>
                                        <input type="text" name="nmj_database" id="nmj_database" value="${app.NMJ_DATABASE}" class="form-control input-sm input250" ${'' if app.NMJ_DATABASE else ' readonly="readonly"'}  />
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">automatically filled via the 'Get Settings' button.</span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="nmj_mount">
                                        <span class="component-title">NMJ mount url</span>
                                        <input type="text" name="nmj_mount" id="nmj_mount" value="${app.NMJ_MOUNT}" class="form-control input-sm input250" ${'' if app.NMJ_MOUNT else ' readonly="readonly"'}  />
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">automatically filled via the 'Get Settings' button.</span>
                                    </label>
                                </div>
                                <div class="testNotification" id="testNMJ-result">Click below to test.</div>
                                <input class="btn-medusa" type="button" value="Test NMJ" id="testNMJ" />
                                <input type="submit" class="config_submitter btn-medusa" value="Save Changes" />
                            </div><!-- /content_use_nmj //-->
                        </fieldset>
                    </div><!-- /nmj component-group //-->
                    <div class="component-group-desc-legacy">
                        <span class="icon-notifiers-nmj" title="Networked Media Jukebox v2"></span>
                        <h3><app-link href="http://www.popcornhour.com/">NMJv2</app-link></h3>
                        <p>The Networked Media Jukebox, or NMJv2, is the official media jukebox interface made available for the Popcorn Hour 300 & 400-series.</p>
                    </div>
                    <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="use_nmjv2">
                                    <span class="component-title">Enable</span>
                                    <span class="component-desc">
                                        <input type="checkbox" class="enabler" name="use_nmjv2" id="use_nmjv2" ${'checked="checked"' if app.USE_NMJv2 else ''}/>
                                        <p>Send update commands to NMJv2?</p>
                                    </span>
                                </label>
                            </div>
                            <div id="content_use_nmjv2">
                                <div class="field-pair">
                                    <label for="nmjv2_host">
                                        <span class="component-title">Popcorn IP address</span>
                                        <input type="text" name="nmjv2_host" id="nmjv2_host" value="${app.NMJv2_HOST}" class="form-control input-sm input250"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">IP address of Popcorn 300/400-series (eg. 192.168.1.100)</span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <span class="component-title">Database location</span>
                                    <span class="component-desc">
                                        <label for="NMJV2_DBLOC_A" class="space-right">
                                            <input type="radio" NAME="nmjv2_dbloc" VALUE="local" id="NMJV2_DBLOC_A" ${'checked="checked"' if app.NMJv2_DBLOC == 'local' else ''}/>PCH Local Media
                                        </label>
                                        <label for="NMJV2_DBLOC_B">
                                            <input type="radio" NAME="nmjv2_dbloc" VALUE="network" id="NMJV2_DBLOC_B" ${'checked="checked"' if app.NMJv2_DBLOC == 'network' else ''}/>PCH Network Media
                                        </label>
                                    </span>
                                </div>
                                <div class="field-pair">
                                    <label for="NMJv2db_instance">
                                        <span class="component-title">Database instance</span>
                                        <span class="component-desc">
                                        <select id="NMJv2db_instance" class="form-control input-sm">
                                            <option value="0">#1 </option>
                                            <option value="1">#2 </option>
                                            <option value="2">#3 </option>
                                            <option value="3">#4 </option>
                                            <option value="4">#5 </option>
                                            <option value="5">#6 </option>
                                            <option value="6">#7 </option>
                                        </select>
                                        </span>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">adjust this value if the wrong database is selected.</span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="settingsNMJv2">
                                        <span class="component-title">Find database</span>
                                        <input type="button" class="btn-medusa btn-inline" value="Find Database" id="settingsNMJv2" />
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">the Popcorn Hour device must be powered on.</span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="nmjv2_database">
                                        <span class="component-title">NMJv2 database</span>
                                        <input type="text" name="nmjv2_database" id="nmjv2_database" value="${app.NMJv2_DATABASE}" class="form-control input-sm input250" ${'' if app.NMJv2_DATABASE else ' readonly="readonly"'}  />
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">automatically filled via the 'Find Database' buttons.</span>
                                    </label>
                                </div>
                            <div class="testNotification" id="testNMJv2-result">Click below to test.</div>
                            <input class="btn-medusa" type="button" value="Test NMJv2" id="testNMJv2" />
                            <input type="submit" class="config_submitter btn-medusa" value="Save Changes" />
                            </div><!-- /content_use_nmjv2 //-->
                        </fieldset>
                    </div><!-- /nmjv2 component-group //-->
                        <div class="component-group-desc-legacy">
                            <span class="icon-notifiers-syno1" title="Synology"></span>
                            <h3><app-link href="http://synology.com/">Synology</app-link></h3>
                            <p>The Synology DiskStation NAS.</p>
                            <p>Synology Indexer is the daemon running on the Synology NAS to build its media database.</p>
                        </div>
                    <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="use_synoindex">
                                    <span class="component-title">Enable</span>
                                    <span class="component-desc">
                                        <input type="checkbox" class="enabler" name="use_synoindex" id="use_synoindex" ${'checked="checked"' if app.USE_SYNOINDEX else ''}/>
                                        <p>Send Synology notifications?</p>
                                    </span>
                                </label>
                                <label>
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc"><b>Note:</b> requires Medusa to be running on your Synology NAS.</span>
                                </label>
                            </div>
                            <div id="content_use_synoindex">
                                <input type="submit" class="config_submitter btn-medusa" value="Save Changes" />
                            </div><!-- /content_use_synoindex //-->
                        </fieldset>
                    </div><!-- /synoindex component-group //-->
                        <div class="component-group-desc-legacy">
                            <span class="icon-notifiers-syno2" title="Synology Indexer"></span>
                            <h3><app-link href="http://synology.com/">Synology Notifier</app-link></h3>
                            <p>Synology Notifier is the notification system of Synology DSM</p>
                        </div>
                    <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="use_synologynotifier">
                                    <span class="component-title">Enable</span>
                                    <span class="component-desc">
                                        <input type="checkbox" class="enabler" name="use_synologynotifier" id="use_synologynotifier" ${'checked="checked"' if app.USE_SYNOLOGYNOTIFIER else ''}/>
                                        <p>Send notifications to the Synology Notifier?</p>
                                    </span>
                                </label>
                                <label>
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc"><b>Note:</b> requires Medusa to be running on your Synology DSM.</span>
                                </label>
                               </div>
                            <div id="content_use_synologynotifier">
                                <div class="field-pair">
                                    <label for="synologynotifier_notify_onsnatch">
                                        <span class="component-title">Notify on snatch</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="synologynotifier_notify_onsnatch" id="synologynotifier_notify_onsnatch" ${'checked="checked"' if app.SYNOLOGYNOTIFIER_NOTIFY_ONSNATCH else ''}/>
                                            <p>send a notification when a download starts?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="synologynotifier_notify_ondownload">
                                        <span class="component-title">Notify on download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="synologynotifier_notify_ondownload" id="synologynotifier_notify_ondownload" ${'checked="checked"' if app.SYNOLOGYNOTIFIER_NOTIFY_ONDOWNLOAD else ''}/>
                                            <p>send a notification when a download finishes?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="synologynotifier_notify_onsubtitledownload">
                                        <span class="component-title">Notify on subtitle download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="synologynotifier_notify_onsubtitledownload" id="synologynotifier_notify_onsubtitledownload" ${'checked="checked"' if app.SYNOLOGYNOTIFIER_NOTIFY_ONSUBTITLEDOWNLOAD else ''}/>
                                            <p>send a notification when subtitles are downloaded?</p>
                                        </span>
                                    </label>
                                </div>
                                <input type="submit" class="config_submitter btn-medusa" value="Save Changes" />
                               </div>
                        </fieldset>
                    </div><!-- /synology notifier component-group //-->
                        <div class="component-group-desc-legacy">
                            <span class="icon-notifiers-pytivo" title="pyTivo"></span>
                            <h3><app-link href="http://pytivo.sourceforge.net/wiki/index.php/PyTivo">pyTivo</app-link></h3>
                            <p>pyTivo is both an HMO and GoBack server. This notifier will load the completed downloads to your Tivo.</p>
                        </div>
                    <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="use_pytivo">
                                    <span class="component-title">Enable</span>
                                    <span class="component-desc">
                                        <input type="checkbox" class="enabler" name="use_pytivo" id="use_pytivo" ${'checked="checked"' if app.USE_PYTIVO else ''}/>
                                        <p>Send notifications to pyTivo?</p>
                                    </span>
                                </label>
                                <label>
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc"><b>Note:</b> requires the downloaded files to be accessible by pyTivo.</span>
                                </label>
                            </div>
                            <div id="content_use_pytivo">
                                <div class="field-pair">
                                    <label for="pytivo_host">
                                        <span class="component-title">pyTivo IP:Port</span>
                                        <input type="text" name="pytivo_host" id="pytivo_host" value="${app.PYTIVO_HOST}" class="form-control input-sm input250"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">host running pyTivo (eg. 192.168.1.1:9032)</span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="pytivo_share_name">
                                        <span class="component-title">pyTivo share name</span>
                                        <input type="text" name="pytivo_share_name" id="pytivo_share_name" value="${app.PYTIVO_SHARE_NAME}" class="form-control input-sm input250"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">value used in pyTivo Web Configuration to name the share.</span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="pytivo_tivo_name">
                                        <span class="component-title">Tivo name</span>
                                        <input type="text" name="pytivo_tivo_name" id="pytivo_tivo_name" value="${app.PYTIVO_TIVO_NAME}" class="form-control input-sm input250"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">(Messages &amp; Settings > Account &amp; System Information > System Information > DVR name)</span>
                                    </label>
                                </div>
                                <input type="submit" class="config_submitter btn-medusa" value="Save Changes" />
                            </div><!-- /content_use_pytivo //-->
                        </fieldset>
                    </div><!-- /component-group //-->
                </div><!-- #home-theater-nas //-->
                <div id="devices">
                    <div class="component-group-desc-legacy">
                        <span class="icon-notifiers-growl" title="Growl"></span>
                        <h3><app-link href="http://growl.info/">Growl</app-link></h3>
                        <p>A cross-platform unobtrusive global notification system.</p>
                    </div>
                    <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="use_growl">
                                    <span class="component-title">Enable</span>
                                    <span class="component-desc">
                                        <input type="checkbox" class="enabler" name="use_growl" id="use_growl" ${'checked="checked"' if app.USE_GROWL else ''}/>
                                        <p>Send Growl notifications?</p>
                                    </span>
                                </label>
                            </div>
                            <div id="content_use_growl">
                                <div class="field-pair">
                                    <label for="growl_notify_onsnatch">
                                        <span class="component-title">Notify on snatch</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="growl_notify_onsnatch" id="growl_notify_onsnatch" ${'checked="checked"' if app.GROWL_NOTIFY_ONSNATCH else ''}/>
                                            <p>send a notification when a download starts?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="growl_notify_ondownload">
                                        <span class="component-title">Notify on download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="growl_notify_ondownload" id="growl_notify_ondownload" ${'checked="checked"' if app.GROWL_NOTIFY_ONDOWNLOAD else ''}/>
                                            <p>send a notification when a download finishes?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="growl_notify_onsubtitledownload">
                                        <span class="component-title">Notify on subtitle download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="growl_notify_onsubtitledownload" id="growl_notify_onsubtitledownload" ${'checked="checked"' if app.GROWL_NOTIFY_ONSUBTITLEDOWNLOAD else ''}/>
                                            <p>send a notification when subtitles are downloaded?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="growl_host">
                                        <span class="component-title">Growl IP:Port</span>
                                        <input type="text" name="growl_host" id="growl_host" value="${app.GROWL_HOST}" class="form-control input-sm input250"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">host running Growl (eg. 192.168.1.100:23053)</span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="growl_password">
                                        <span class="component-title">Password</span>
                                        <input type="password" name="growl_password" id="growl_password" value="${app.GROWL_PASSWORD}" class="form-control input-sm input250" autocomplete="no"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">may leave blank if Medusa is on the same host.</span>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">otherwise Growl <b>requires</b> a password to be used.</span>
                                    </label>
                                </div>
                                <div class="testNotification" id="testGrowl-result">Click below to register and test Growl, this is required for Growl notifications to work.</div>
                                <input  class="btn-medusa" type="button" value="Register Growl" id="testGrowl" />
                                <input type="submit" class="config_submitter btn-medusa" value="Save Changes" />
                            </div><!-- /content_use_growl //-->
                        </fieldset>
                    </div><!-- /growl component-group //-->
                        <div class="component-group-desc-legacy">
                            <span class="icon-notifiers-prowl" title="Prowl"></span>
                            <h3><app-link href="http://www.prowlapp.com/">Prowl</app-link></h3>
                            <p>A Growl client for iOS.</p>
                        </div>
                    <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="use_prowl">
                                    <span class="component-title">Enable</span>
                                    <span class="component-desc">
                                        <input type="checkbox" class="enabler" name="use_prowl" id="use_prowl" ${'checked="checked"' if app.USE_PROWL else ''}/>
                                        <p>Send Prowl notifications?</p>
                                    </span>
                                </label>
                            </div>
                            <div id="content_use_prowl">
                                <div class="field-pair">
                                    <label for="prowl_notify_onsnatch">
                                        <span class="component-title">Notify on snatch</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="prowl_notify_onsnatch" id="prowl_notify_onsnatch" ${'checked="checked"' if app.PROWL_NOTIFY_ONSNATCH else ''}/>
                                            <p>send a notification when a download starts?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="prowl_notify_ondownload">
                                        <span class="component-title">Notify on download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="prowl_notify_ondownload" id="prowl_notify_ondownload" ${'checked="checked"' if app.PROWL_NOTIFY_ONDOWNLOAD else ''}/>
                                            <p>send a notification when a download finishes?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="prowl_notify_onsubtitledownload">
                                        <span class="component-title">Notify on subtitle download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="prowl_notify_onsubtitledownload" id="prowl_notify_onsubtitledownload" ${'checked="checked"' if app.PROWL_NOTIFY_ONSUBTITLEDOWNLOAD else ''}/>
                                            <p>send a notification when subtitles are downloaded?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                     <label for="prowl_message_title">
                                         <span class="component-title">Prowl Message Title:</span>
                                         <input type="text" name="prowl_message_title" id="prowl_message_title" value="${app.PROWL_MESSAGE_TITLE}" class="form-control input-sm input250"/>
                                     </label>
                                </div>
                                <div class="field-pair">
                                    <label for="prowl_api">
                                        <span class="component-title">Global Prowl API key(s):</span>
                                        <input type="text" name="prowl_api" id="prowl_api" value="${','.join(app.PROWL_API)}" class="form-control input-sm input250"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">Prowl API(s) listed here, separated by commas if applicable, will<br> receive notifications for <b>all</b> shows.
                                                                     Your Prowl API key is available at:
                                                                     <app-link href="https://www.prowlapp.com/api_settings.php">
                                                                     https://www.prowlapp.com/api_settings.php</app-link><br>
                                                                     (This field may be blank except when testing.)</span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="prowl_show">
                                        <span class="component-title">Show notification list</span>
                                        <select name="prowl_show" id="prowl_show" class="form-control input-sm">
                                            <option value="-1">-- Select a Show --</option>
                                        </select>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <input type="text" name="prowl_show_list" id="prowl_show_list" class="form-control input-sm input350"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">Configure per-show notifications here by entering Prowl API key(s), separated by commas,
                                                                     after selecting a show in the drop-down box.   Be sure to activate the 'Save for this show'
                                                                     button below after each entry.</span>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <input id="prowl_show_save" class="btn-medusa" type="button" value="Save for this show" />
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="prowl_priority">
                                        <span class="component-title">Prowl priority:</span>
                                        <select id="prowl_priority" name="prowl_priority" class="form-control input-sm">
                                            <option value="-2" ${'selected="selected"' if app.PROWL_PRIORITY == '-2' else ''}>Very Low</option>
                                            <option value="-1" ${'selected="selected"' if app.PROWL_PRIORITY == '-1' else ''}>Moderate</option>
                                            <option value="0" ${'selected="selected"' if app.PROWL_PRIORITY == '0' else ''}>Normal</option>
                                            <option value="1" ${'selected="selected"' if app.PROWL_PRIORITY == '1' else ''}>High</option>
                                            <option value="2" ${'selected="selected"' if app.PROWL_PRIORITY == '2' else ''}>Emergency</option>
                                        </select>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">priority of Prowl messages from Medusa.</span>
                                    </label>
                                </div>
                                <div class="testNotification" id="testProwl-result">Click below to test.</div>
                                <input  class="btn-medusa" type="button" value="Test Prowl" id="testProwl" />
                                <input type="submit" class="config_submitter btn-medusa" value="Save Changes" />
                            </div><!-- /content_use_prowl //-->
                        </fieldset>
                    </div><!-- /prowl component-group //-->
                        <div class="component-group-desc-legacy">
                            <span class="icon-notifiers-libnotify" title="Libnotify"></span>
                            <h3><app-link href="http://library.gnome.org/devel/libnotify/">Libnotify</app-link></h3>
                            <p>The standard desktop notification API for Linux/*nix systems.  This notifier will only function if the pynotify module is installed (Ubuntu/Debian package <app-link href="apt:python-notify">python-notify</app-link>).</p>
                        </div>
                    <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="use_libnotify">
                                    <span class="component-title">Enable</span>
                                    <span class="component-desc">
                                        <input type="checkbox" class="enabler" name="use_libnotify" id="use_libnotify" ${'checked="checked"' if app.USE_LIBNOTIFY else ''}/>
                                        <p>Send Libnotify notifications?</p>
                                    </span>
                                </label>
                            </div>
                            <div id="content_use_libnotify">
                                <div class="field-pair">
                                    <label for="libnotify_notify_onsnatch">
                                        <span class="component-title">Notify on snatch</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="libnotify_notify_onsnatch" id="libnotify_notify_onsnatch" ${'checked="checked"' if app.LIBNOTIFY_NOTIFY_ONSNATCH else ''}/>
                                            <p>send a notification when a download starts?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="libnotify_notify_ondownload">
                                        <span class="component-title">Notify on download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="libnotify_notify_ondownload" id="libnotify_notify_ondownload" ${'checked="checked"' if app.LIBNOTIFY_NOTIFY_ONDOWNLOAD else ''}/>
                                            <p>send a notification when a download finishes?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="libnotify_notify_onsubtitledownload">
                                        <span class="component-title">Notify on subtitle download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="libnotify_notify_onsubtitledownload" id="libnotify_notify_onsubtitledownload" ${'checked="checked"' if app.LIBNOTIFY_NOTIFY_ONSUBTITLEDOWNLOAD else ''}/>
                                            <p>send a notification when subtitles are downloaded?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="testNotification" id="testLibnotify-result">Click below to test.</div>
                                <input  class="btn-medusa" type="button" value="Test Libnotify" id="testLibnotify" />
                                <input type="submit" class="config_submitter btn-medusa" value="Save Changes" />
                            </div><!-- /content_use_libnotify //-->
                        </fieldset>
                    </div><!-- /libnotify component-group //-->
                        <div class="component-group-desc-legacy">
                            <span class="icon-notifiers-pushover" title="Pushover"></span>
                            <h3><app-link href="https://pushover.net/">Pushover</app-link></h3>
                            <p>Pushover makes it easy to send real-time notifications to your Android and iOS devices.</p>
                        </div>
                    <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="use_pushover">
                                    <span class="component-title">Enable</span>
                                    <span class="component-desc">
                                        <input type="checkbox" class="enabler" name="use_pushover" id="use_pushover" ${'checked="checked"' if app.USE_PUSHOVER else ''}/>
                                        <p>Send Pushover notifications?</p>
                                    </span>
                                </label>
                            </div>
                            <div id="content_use_pushover">
                                <div class="field-pair">
                                    <label for="pushover_notify_onsnatch">
                                        <span class="component-title">Notify on snatch</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="pushover_notify_onsnatch" id="pushover_notify_onsnatch" ${'checked="checked"' if app.PUSHOVER_NOTIFY_ONSNATCH else ''}/>
                                            <p>send a notification when a download starts?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="pushover_notify_ondownload">
                                        <span class="component-title">Notify on download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="pushover_notify_ondownload" id="pushover_notify_ondownload" ${'checked="checked"' if app.PUSHOVER_NOTIFY_ONDOWNLOAD else ''}/>
                                            <p>send a notification when a download finishes?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="pushover_notify_onsubtitledownload">
                                        <span class="component-title">Notify on subtitle download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="pushover_notify_onsubtitledownload" id="pushover_notify_onsubtitledownload" ${'checked="checked"' if app.PUSHOVER_NOTIFY_ONSUBTITLEDOWNLOAD else ''}/>
                                            <p>send a notification when subtitles are downloaded?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="pushover_userkey">
                                        <span class="component-title">Pushover key</span>
                                        <input type="text" name="pushover_userkey" id="pushover_userkey" value="${app.PUSHOVER_USERKEY}" class="form-control input-sm input250"
                                               autocomplete="no" />
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">user key of your Pushover account</span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="pushover_apikey">
                                        <span class="component-title">Pushover API key</span>
                                        <input type="text" name="pushover_apikey" id="pushover_apikey" value="${app.PUSHOVER_APIKEY}" class="form-control input-sm input250"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc"><app-link href="https://pushover.net/apps/build/"><b>Click here</b></app-link> to create a Pushover API key</span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="pushover_device">
                                        <span class="component-title">Pushover devices</span>
                                        <input type="text" name="pushover_device" id="pushover_device" value="${','.join(app.PUSHOVER_DEVICE)}" class="form-control input-sm input250"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">comma separated list of pushover devices you want to send notifications to</span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="pushover_sound">
                                        <span class="component-title">Pushover notification sound</span>
                                        <select id="pushover_sound" name="pushover_sound" class="form-control input-sm">
                                            <option value="pushover" ${'selected="selected"' if app.PUSHOVER_SOUND == 'pushover' else ''}>Pushover</option>
                                            <option value="bike" ${'selected="selected"' if app.PUSHOVER_SOUND == 'bike' else ''}>Bike</option>
                                            <option value="bugle" ${'selected="selected"' if app.PUSHOVER_SOUND == 'bugle' else ''}>Bugle</option>
                                            <option value="cashregister" ${'selected="selected"' if app.PUSHOVER_SOUND == 'cashregister' else ''}>Cash Register</option>
                                            <option value="classical" ${'selected="selected"' if app.PUSHOVER_SOUND == 'classical' else ''}>Classical</option>
                                            <option value="cosmic" ${'selected="selected"' if app.PUSHOVER_SOUND == 'cosmic' else ''}>Cosmic</option>
                                            <option value="falling" ${'selected="selected"' if app.PUSHOVER_SOUND == 'falling' else ''}>Falling</option>
                                            <option value="gamelan" ${'selected="selected"' if app.PUSHOVER_SOUND == 'gamelan' else ''}>Gamelan</option>
                                            <option value="incoming" ${'selected="selected"' if app.PUSHOVER_SOUND == 'incoming' else ''}> Incoming</option>
                                            <option value="intermission" ${'selected="selected"' if app.PUSHOVER_SOUND == 'intermission' else ''}>Intermission</option>
                                            <option value="magic" ${'selected="selected"' if app.PUSHOVER_SOUND == 'magic' else ''}>Magic</option>
                                            <option value="mechanical" ${'selected="selected"' if app.PUSHOVER_SOUND == 'mechanical' else ''}>Mechanical</option>
                                            <option value="pianobar" ${'selected="selected"' if app.PUSHOVER_SOUND == 'pianobar' else ''}>Piano Bar</option>
                                            <option value="siren" ${'selected="selected"' if app.PUSHOVER_SOUND == 'siren' else ''}>Siren</option>
                                            <option value="spacealarm" ${'selected="selected"' if app.PUSHOVER_SOUND == 'spacealarm' else ''}>Space Alarm</option>
                                            <option value="tugboat" ${'selected="selected"' if app.PUSHOVER_SOUND == 'tugboat' else ''}>Tug Boat</option>
                                            <option value="alien" ${'selected="selected"' if app.PUSHOVER_SOUND == 'alien' else ''}>Alien Alarm (long)</option>
                                            <option value="climb" ${'selected="selected"' if app.PUSHOVER_SOUND == 'climb' else ''}>Climb (long)</option>
                                            <option value="persistent" ${'selected="selected"' if app.PUSHOVER_SOUND == 'persistent' else ''}>Persistent (long)</option>
                                            <option value="echo" ${'selected="selected"' if app.PUSHOVER_SOUND == 'echo' else ''}>Pushover Echo (long)</option>
                                            <option value="updown" ${'selected="selected"' if app.PUSHOVER_SOUND == 'updown' else ''}>Up Down (long)</option>
                                            <option value="none" ${'selected="selected"' if app.PUSHOVER_SOUND == 'none' else ''}>None (silent)</option>
                                            <option value="default" ${'selected="selected"' if app.PUSHOVER_SOUND == 'default' else ''}>Device specific</option>
                                        </select>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">Choose notification sound to use</span>
                                    </label>
                                </div>
                                <div class="testNotification" id="testPushover-result">Click below to test.</div>
                                <input  class="btn-medusa" type="button" value="Test Pushover" id="testPushover" />
                                <input type="submit" class="config_submitter btn-medusa" value="Save Changes" />
                            </div><!-- /content_use_pushover //-->
                        </fieldset>
                    </div><!-- /pushover component-group //-->
                        <div class="component-group-desc-legacy">
                            <span class="icon-notifiers-boxcar2" title="Boxcar 2"></span>
                            <h3><app-link href="https://new.boxcar.io/">Boxcar 2</app-link></h3>
                            <p>Read your messages where and when you want them!</p>
                        </div>
                    <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="use_boxcar2">
                                    <span class="component-title">Enable</span>
                                    <span class="component-desc">
                                        <input type="checkbox" class="enabler" name="use_boxcar2" id="use_boxcar2" ${'checked="checked"' if app.USE_BOXCAR2 else ''}/>
                                        <p>Send Boxcar notifications?</p>
                                    </span>
                                </label>
                            </div>
                            <div id="content_use_boxcar2">
                                <div class="field-pair">
                                    <label for="boxcar2_notify_onsnatch">
                                        <span class="component-title">Notify on snatch</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="boxcar2_notify_onsnatch" id="boxcar2_notify_onsnatch" ${'checked="checked"' if app.BOXCAR2_NOTIFY_ONSNATCH else ''}/>
                                            <p>send a notification when a download starts?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="boxcar2_notify_ondownload">
                                        <span class="component-title">Notify on download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="boxcar2_notify_ondownload" id="boxcar2_notify_ondownload" ${'checked="checked"' if app.BOXCAR2_NOTIFY_ONDOWNLOAD else ''}/>
                                            <p>send a notification when a download finishes?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="boxcar2_notify_onsubtitledownload">
                                        <span class="component-title">Notify on subtitle download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="boxcar2_notify_onsubtitledownload" id="boxcar2_notify_onsubtitledownload" ${'checked="checked"' if app.BOXCAR2_NOTIFY_ONSUBTITLEDOWNLOAD else ''}/>
                                            <p>send a notification when subtitles are downloaded?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="boxcar2_accesstoken">
                                        <span class="component-title">Boxcar2 access token</span>
                                        <input type="text" name="boxcar2_accesstoken" id="boxcar2_accesstoken" value="${app.BOXCAR2_ACCESSTOKEN}" class="form-control input-sm input250"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">access token for your Boxcar account.</span>
                                    </label>
                                </div>
                                <div class="testNotification" id="testBoxcar2-result">Click below to test.</div>
                                <input  class="btn-medusa" type="button" value="Test Boxcar" id="testBoxcar2" />
                                <input type="submit" class="config_submitter btn-medusa" value="Save Changes" />
                            </div><!-- /content_use_boxcar2 //-->
                        </fieldset>
                    </div><!-- /boxcar2 component-group //-->
                        <div class="component-group-desc-legacy">
                            <span class="icon-notifiers-pushalot" title="Pushalot"></span>
                            <h3><app-link href="https://pushalot.com">Pushalot</app-link></h3>
                            <p>Pushalot is a platform for receiving custom push notifications to connected devices running Windows Phone or Windows 8.</p>
                        </div>
                    <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="use_pushalot">
                                    <span class="component-title">Enable</span>
                                    <span class="component-desc">
                                        <input type="checkbox" class="enabler" name="use_pushalot" id="use_pushalot" ${'checked="checked"' if app.USE_PUSHALOT else ''}/>
                                        <p>Send Pushalot notifications ?
                                    </span>
                                </label>
                            </div>
                            <div id="content_use_pushalot">
                                <div class="field-pair">
                                    <label for="pushalot_notify_onsnatch">
                                        <span class="component-title">Notify on snatch</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="pushalot_notify_onsnatch" id="pushalot_notify_onsnatch" ${'checked="checked"' if app.PUSHALOT_NOTIFY_ONSNATCH else ''}/>
                                            <p>send a notification when a download starts?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="pushalot_notify_ondownload">
                                        <span class="component-title">Notify on download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="pushalot_notify_ondownload" id="pushalot_notify_ondownload" ${'checked="checked"' if app.PUSHALOT_NOTIFY_ONDOWNLOAD else ''}/>
                                            <p>send a notification when a download finishes?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="pushalot_notify_onsubtitledownload">
                                        <span class="component-title">Notify on subtitle download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="pushalot_notify_onsubtitledownload" id="pushalot_notify_onsubtitledownload" ${'checked="checked"' if app.PUSHALOT_NOTIFY_ONSUBTITLEDOWNLOAD else ''}/>
                                            <p>send a notification when subtitles are downloaded?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="pushalot_authorizationtoken">
                                        <span class="component-title">Pushalot authorization token</span>
                                        <input type="text" name="pushalot_authorizationtoken" id="pushalot_authorizationtoken" value="${app.PUSHALOT_AUTHORIZATIONTOKEN}" class="form-control input-sm input350"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">authorization token of your Pushalot account.</span>
                                    </label>
                                </div>
                                <div class="testNotification" id="testPushalot-result">Click below to test.</div>
                                <input type="button" class="btn-medusa" value="Test Pushalot" id="testPushalot" />
                                <input type="submit" class="btn-medusa config_submitter" value="Save Changes" />
                            </div><!-- /content_use_pushalot //-->
                        </fieldset>
                    </div><!-- /pushalot component-group //-->
                        <div class="component-group-desc-legacy">
                            <span class="icon-notifiers-pushbullet" title="Pushbullet"></span>
                            <h3><app-link href="https://www.pushbullet.com">Pushbullet</app-link></h3>
                            <p>Pushbullet is a platform for receiving custom push notifications to connected devices running Android and desktop Chrome browsers.</p>
                        </div>
                    <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="use_pushbullet">
                                    <span class="component-title">Enable</span>
                                    <span class="component-desc">
                                        <input type="checkbox" class="enabler" name="use_pushbullet" id="use_pushbullet" ${'checked="checked"' if app.USE_PUSHBULLET else ''}/>
                                        <p>Send Pushbullet notifications?</p>
                                    </span>
                                </label>
                            </div>
                            <div id="content_use_pushbullet">
                                <div class="field-pair">
                                    <label for="pushbullet_notify_onsnatch">
                                        <span class="component-title">Notify on snatch</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="pushbullet_notify_onsnatch" id="pushbullet_notify_onsnatch" ${'checked="checked"' if app.PUSHBULLET_NOTIFY_ONSNATCH else ''}/>
                                            <p>send a notification when a download starts?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="pushbullet_notify_ondownload">
                                        <span class="component-title">Notify on download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="pushbullet_notify_ondownload" id="pushbullet_notify_ondownload" ${'checked="checked"' if app.PUSHBULLET_NOTIFY_ONDOWNLOAD else ''}/>
                                            <p>send a notification when a download finishes?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="pushbullet_notify_onsubtitledownload">
                                        <span class="component-title">Notify on subtitle download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="pushbullet_notify_onsubtitledownload" id="pushbullet_notify_onsubtitledownload" ${'checked="checked"' if app.PUSHBULLET_NOTIFY_ONSUBTITLEDOWNLOAD else ''}/>
                                            <p>send a notification when subtitles are downloaded?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="pushbullet_api">
                                        <span class="component-title">Pushbullet API key</span>
                                        <input type="text" name="pushbullet_api" id="pushbullet_api" value="${app.PUSHBULLET_API}" class="form-control input-sm input350"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">API key of your Pushbullet account</span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="pushbullet_device_list">
                                        <span class="component-title">Pushbullet devices</span>
                                        <select name="pushbullet_device_list" id="pushbullet_device_list" class="form-control input-sm"></select>
                                        <input type="hidden" id="pushbullet_device" value="${app.PUSHBULLET_DEVICE}">
                                        <input type="button" class="btn-medusa btn-inline" value="Update device list" id="getPushbulletDevices" />
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">select device you wish to push to.</span>
                                    </label>
                                </div>
                                <div class="testNotification" id="testPushbullet-result">Click below to test.</div>
                                <input type="button" class="btn-medusa" value="Test Pushbullet" id="testPushbullet" />
                                <input type="submit" class="btn-medusa config_submitter" value="Save Changes" />
                            </div><!-- /content_use_pushbullet //-->
                        </fieldset>
                    </div><!-- /pushbullet component-group //-->
                        <div class="component-group-desc-legacy">
                            <span class="icon-notifiers-freemobile" title="Free Mobile"></span>
                            <h3><app-link href="http://mobile.free.fr/">Free Mobile</app-link></h3>
                            <p>Free Mobile is a famous French cellular network provider.<br> It provides to their customer a free SMS API.</p>
                        </div>
                    <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="use_freemobile">
                                    <span class="component-title">Enable</span>
                                    <span class="component-desc">
                                        <input type="checkbox" class="enabler" name="use_freemobile" id="use_freemobile" ${'checked="checked"' if app.USE_FREEMOBILE else ''}/>
                                        <p>Send SMS notifications?</p>
                                    </span>
                                </label>
                            </div>
                            <div id="content_use_freemobile">
                                <div class="field-pair">
                                    <label for="freemobile_notify_onsnatch">
                                        <span class="component-title">Notify on snatch</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="freemobile_notify_onsnatch" id="freemobile_notify_onsnatch" ${'checked="checked"' if app.FREEMOBILE_NOTIFY_ONSNATCH else ''}/>
                                            <p>send a SMS when a download starts?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="freemobile_notify_ondownload">
                                        <span class="component-title">Notify on download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="freemobile_notify_ondownload" id="freemobile_notify_ondownload" ${'checked="checked"' if app.FREEMOBILE_NOTIFY_ONDOWNLOAD else ''}/>
                                            <p>send a SMS when a download finishes?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="freemobile_notify_onsubtitledownload">
                                        <span class="component-title">Notify on subtitle download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="freemobile_notify_onsubtitledownload" id="freemobile_notify_onsubtitledownload" ${'checked="checked"' if app.FREEMOBILE_NOTIFY_ONSUBTITLEDOWNLOAD else ''}/>
                                            <p>send a SMS when subtitles are downloaded?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="freemobile_id">
                                        <span class="component-title">Free Mobile customer ID</span>
                                        <input type="text" name="freemobile_id" id="freemobile_id" value="${app.FREEMOBILE_ID}" class="form-control input-sm input250"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">It's your Free Mobile customer ID (8 digits)</span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="freemobile_password">
                                        <span class="component-title">Free Mobile API Key</span>
                                        <input type="text" name="freemobile_apikey" id="freemobile_apikey" value="${app.FREEMOBILE_APIKEY}" class="form-control input-sm input250"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">Find your API Key in your customer portal.</span>
                                    </label>
                                </div>
                                <div class="testNotification" id="testFreeMobile-result">Click below to test your settings.</div>
                                <input  class="btn-medusa" type="button" value="Test SMS" id="testFreeMobile" />
                                <input type="submit" class="config_submitter btn-medusa" value="Save Changes" />
                            </div><!-- /content_use_freemobile //-->
                        </fieldset>
                    </div><!-- /freemobile component-group //-->

                    <div class="component-group-desc-legacy">
                        <span class="icon-notifiers-telegram" title="Telegram"></span>
                        <h3><app-link href="https://telegram.org/">Telegram</app-link></h3>
                        <p>Telegram is a cloud-based instant messaging service.</p>
                    </div>
                    <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="use_telegram">
                                    <span class="component-title">Enable</span>
                                    <span class="component-desc">
                                        <input type="checkbox" class="enabler" name="use_telegram" id="use_telegram" ${'checked="checked"' if app.USE_TELEGRAM else ''}/>
                                        <p>Send Telegram notifications?</p>
                                    </span>
                                </label>
                            </div>
                            <div id="content_use_telegram">
                                <div class="field-pair">
                                    <label for="telegram_notify_onsnatch">
                                        <span class="component-title">Notify on snatch</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="telegram_notify_onsnatch" id="telegram_notify_onsnatch" ${'checked="checked"' if app.TELEGRAM_NOTIFY_ONSNATCH else ''}/>
                                            <p>Send a message when a download starts?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="telegram_notify_ondownload">
                                        <span class="component-title">Notify on download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="telegram_notify_ondownload" id="telegram_notify_ondownload" ${'checked="checked"' if app.TELEGRAM_NOTIFY_ONDOWNLOAD else ''}/>
                                            <p>Send a message when a download finishes?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="telegram_notify_onsubtitledownload">
                                        <span class="component-title">Notify on subtitle download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="telegram_notify_onsubtitledownload" id="telegram_notify_onsubtitledownload" ${'checked="checked"' if app.TELEGRAM_NOTIFY_ONSUBTITLEDOWNLOAD else ''}/>
                                            <p>Send a message when subtitles are downloaded?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="telegram_id">
                                        <span class="component-title">User/group ID</span>
                                        <input type="text" name="telegram_id" id="telegram_id" value="${app.TELEGRAM_ID}" class="form-control input-sm input250"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">Contact @myidbot on Telegram to get an ID</span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="telegram_password">
                                        <span class="component-title">Bot API token</span>
                                        <input type="text" name="telegram_apikey" id="telegram_apikey" value="${app.TELEGRAM_APIKEY}" class="form-control input-sm input250"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">Contact @BotFather on Telegram to set up one</span>
                                    </label>
                                </div>
                                <div class="testNotification" id="testTelegram-result">Click below to test your settings.</div>
                                <input  class="btn-medusa" type="button" value="Test Telegram" id="testTelegram" />
                                <input type="submit" class="config_submitter btn-medusa" value="Save Changes" />
                            </div><!-- /content_use_telegram //-->
                        </fieldset>
                    </div><!-- /telegram component-group //-->
                </div><!-- #devices //-->
                <div id="social">
                    <div class="component-group-desc-legacy">
                        <span class="icon-notifiers-twitter" title="Twitter"></span>
                        <h3><app-link href="https://www.twitter.com">Twitter</app-link></h3>
                        <p>A social networking and microblogging service, enabling its users to send and read other users' messages called tweets.</p>
                    </div>
                    <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="use_twitter">
                                    <span class="component-title">Enable</span>
                                    <span class="component-desc">
                                        <input type="checkbox" class="enabler" name="use_twitter" id="use_twitter" ${'checked="checked"' if app.USE_TWITTER else ''}/>
                                        <p>Should Medusa post tweets on Twitter?</p>
                                    </span>
                                </label>
                                <label>
                                    <span class="component-title">&nbsp;</span>
                                    <span class="component-desc"><b>Note:</b> you may want to use a secondary account.</span>
                                </label>
                            </div>
                            <div id="content_use_twitter">
                                <div class="field-pair">
                                    <label for="twitter_notify_onsnatch">
                                        <span class="component-title">Notify on snatch</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="twitter_notify_onsnatch" id="twitter_notify_onsnatch" ${'checked="checked"' if app.TWITTER_NOTIFY_ONSNATCH else ''}/>
                                            <p>send a notification when a download starts?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="twitter_notify_ondownload">
                                        <span class="component-title">Notify on download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="twitter_notify_ondownload" id="twitter_notify_ondownload" ${'checked="checked"' if app.TWITTER_NOTIFY_ONDOWNLOAD else ''}/>
                                            <p>send a notification when a download finishes?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="twitter_notify_onsubtitledownload">
                                        <span class="component-title">Notify on subtitle download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="twitter_notify_onsubtitledownload" id="twitter_notify_onsubtitledownload" ${'checked="checked"' if app.TWITTER_NOTIFY_ONSUBTITLEDOWNLOAD else ''}/>
                                            <p>send a notification when subtitles are downloaded?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="twitter_usedm">
                                        <span class="component-title">Send direct message</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="twitter_usedm" id="twitter_usedm" ${'checked="checked"' if app.TWITTER_USEDM else ''}/>
                                            <p>send a notification via Direct Message, not via status update</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="twitter_dmto">
                                        <span class="component-title">Send DM to</span>
                                        <input type="text" name="twitter_dmto" id="twitter_dmto" value="${app.TWITTER_DMTO}" class="form-control input-sm input250"/>
                                    </label>
                                    <p>
                                        <span class="component-desc">Twitter account to send Direct Messages to (must follow you)</span>
                                    </p>
                                </div>
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">Step One</span>
                                    </label>
                                    <label>
                                        <span style="font-size: 11px;">Click the "Request Authorization" button.<br> This will open a new page containing an auth key.<br> <b>Note:</b> if nothing happens check your popup blocker.<br></span>
                                        <input class="btn-medusa" type="button" value="Request Authorization" id="twitterStep1" />
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">Step Two</span>
                                    </label>
                                    <label>
                                        <span style="font-size: 11px;">Enter the key Twitter gave you below, and click "Verify Key".<br><br></span>
                                        <input type="text" id="twitter_key" value="" class="form-control input-sm input350"/>
                                        <input class="btn-medusa btn-inline" type="button" value="Verify Key" id="twitterStep2" />
                                    </label>
                                </div>
                                <!--
                                <div class="field-pair">
                                    <label>
                                        <span class="component-title">Step Three</span>
                                    </label>
                                </div>
                                //-->
                                <div class="testNotification" id="testTwitter-result">Click below to test.</div>
                                <input  class="btn-medusa" type="button" value="Test Twitter" id="testTwitter" />
                                <input type="submit" class="config_submitter btn-medusa" value="Save Changes" />
                            </div><!-- /content_use_twitter //-->
                        </fieldset>
                    </div><!-- twitter .component-group //-->
                        <div class="component-group-desc-legacy">
                            <span class="icon-notifiers-trakt" title="Trakt"></span>
                            <h3><app-link href="https://trakt.tv/">Trakt</app-link></h3>
                            <p>trakt helps keep a record of what TV shows and movies you are watching. Based on your favorites, trakt recommends additional shows and movies you'll enjoy!</p>
                        </div><!-- .component-group-desc-legacy //-->
                    <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="use_trakt">
                                    <span class="component-title">Enable</span>
                                    <span class="component-desc">
                                        <input type="checkbox" class="enabler" name="use_trakt" id="use_trakt" ${'checked="checked"' if app.USE_TRAKT else ''}/>
                                        <p>Send Trakt.tv notifications?</p>
                                    </span>
                                </label>
                            </div><!-- .field-pair //-->
                            <div id="content_use_trakt">
                                <div class="field-pair">
                                    <label for="trakt_username">
                                        <span class="component-title">Username</span>
                                        <input type="text" name="trakt_username" id="trakt_username" value="${app.TRAKT_USERNAME}" class="form-control input-sm input250"
                                               autocomplete="no" />
                                    </label>
                                    <p>
                                        <span class="component-desc">username of your Trakt account.</span>
                                    </p>
                                </div>
                                <input type="hidden" id="trakt_pin_url" value="${app.TRAKT_PIN_URL}">
                                <div class="field-pair">
                                    <label for="trakt_pin">
                                        <span class="component-title">Trakt PIN</span>
                                        <input type="text" name="trakt_pin" id="trakt_pin" value="" class="form-control input-sm input250" ${'disabled' if app.TRAKT_ACCESS_TOKEN else ''} />
                                        <input type="button" class="btn-medusa" value="Get ${'New' if app.TRAKT_ACCESS_TOKEN else ''} Trakt PIN" id="TraktGetPin" />
                                        <input type="button" class="btn-medusa hide" value="Authorize Medusa" id="authTrakt" />
                                    </label>
                                    <p>
                                        <span class="component-desc">PIN code to authorize Medusa to access Trakt on your behalf.</span>
                                    </p>
                                </div>
                                <div class="field-pair">
                                    <label for="trakt_timeout">
                                        <span class="component-title">API Timeout</span>
                                        <input type="number" min="10" step="1" name="trakt_timeout" id="trakt_timeout" value="${app.TRAKT_TIMEOUT}" class="form-control input-sm input75"/>
                                    </label>
                                    <p>
                                        <span class="component-desc">
                                            Seconds to wait for Trakt API to respond. (Use 0 to wait forever)
                                        </span>
                                    </p>
                                </div>
                                <div class="field-pair">
                                    <label for="trakt_default_indexer">
                                        <span class="component-title">Default indexer</span>
                                        <span class="component-desc">
                                            <select id="trakt_default_indexer" name="trakt_default_indexer" class="form-control input-sm">
                                                <% indexers = indexerApi().indexers %>
                                                % for indexer in indexers:
                                                    <%
                                                        if not get_trakt_indexer(indexer):
                                                            continue
                                                    %>
                                                <option value="${indexer}" ${'selected="selected"' if app.TRAKT_DEFAULT_INDEXER == indexer else ''}>${indexers[indexer]}</option>
                                                % endfor
                                            </select>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="trakt_sync">
                                        <span class="component-title">Sync libraries</span>
                                        <span class="component-desc">
                                            <input type="checkbox" class="enabler" name="trakt_sync" id="trakt_sync" ${'checked="checked"' if app.TRAKT_SYNC else ''}/>
                                            <p>Sync your Medusa show library with your Trakt collection.</p>
                                            <p><b>Note:</b> Don't enable this setting if you use the Trakt addon for Kodi or any other script that syncs your library.</p>
                                            <p>Kodi detects that the episode was deleted and removes from collection which causes Medusa to re-add it. This causes a loop between Medusa and Kodi adding and deleting the episode.</p>
                                        </span>
                                    </label>
                                </div>
                                <div id="content_trakt_sync">
                                    <div class="field-pair">
                                        <label for="trakt_sync_remove">
                                            <span class="component-title">Remove Episodes From Collection</span>
                                            <span class="component-desc">
                                                <input type="checkbox" name="trakt_sync_remove" id="trakt_sync_remove" ${'checked="checked"' if app.TRAKT_SYNC_REMOVE else ''}/>
                                                <p>Remove an Episode from your Trakt Collection if it is not in your Medusa Library.</p>
                                                <p><b>Note:</b> Don't enable this setting if you use the Trakt addon for Kodi or any other script that syncs your library.</p>
                                            </span>
                                        </label>
                                     </div>
                                </div>
                                <div class="field-pair">
                                    <label for="trakt_sync_watchlist">
                                        <span class="component-title">Sync watchlist</span>
                                        <span class="component-desc">
                                            <input type="checkbox" class="enabler" name="trakt_sync_watchlist" id="trakt_sync_watchlist" ${'checked="checked"' if app.TRAKT_SYNC_WATCHLIST else ''}/>
                                            <p>Sync your Medusa library with your Trakt Watchlist (either Show and Episode).</p>
                                            <p>Episode will be added on watch list when wanted or snatched and will be removed when downloaded </p>
                                            <p><b>Note:</b> By design, Trakt automatically removes episodes and/or shows from watchlist as soon you have watched them.</p>
                                        </span>
                                    </label>
                                </div>
                                <div id="content_trakt_sync_watchlist">
                                    <div class="field-pair">
                                        <label for="trakt_method_add">
                                            <span class="component-title">Watchlist add method</span>
                                               <select id="trakt_method_add" name="trakt_method_add" class="form-control input-sm">
                                                <option value="0" ${'selected="selected"' if app.TRAKT_METHOD_ADD == 0 else ''}>Skip All</option>
                                                <option value="1" ${'selected="selected"' if app.TRAKT_METHOD_ADD == 1 else ''}>Download Pilot Only</option>
                                                <option value="2" ${'selected="selected"' if app.TRAKT_METHOD_ADD == 2 else ''}>Get whole show</option>
                                            </select>
                                        </label>
                                        <label>
                                            <span class="component-title">&nbsp;</span>
                                            <span class="component-desc">method in which to download episodes for new shows.</span>
                                        </label>
                                    </div>
                                    <div class="field-pair">
                                        <label for="trakt_remove_watchlist">
                                            <span class="component-title">Remove episode</span>
                                            <span class="component-desc">
                                                <input type="checkbox" name="trakt_remove_watchlist" id="trakt_remove_watchlist" ${'checked="checked"' if app.TRAKT_REMOVE_WATCHLIST else ''}/>
                                                <p>remove an episode from your watchlist after it is downloaded.</p>
                                            </span>
                                        </label>
                                    </div>
                                    <div class="field-pair">
                                        <label for="trakt_remove_serieslist">
                                            <span class="component-title">Remove series</span>
                                            <span class="component-desc">
                                                <input type="checkbox" name="trakt_remove_serieslist" id="trakt_remove_serieslist" ${'checked="checked"' if app.TRAKT_REMOVE_SERIESLIST else ''}/>
                                                <p>remove the whole series from your watchlist after any download.</p>
                                            </span>
                                        </label>
                                    </div>
                                    <div class="field-pair">
                                        <label for="trakt_remove_show_from_application">
                                            <span class="component-title">Remove watched show:</span>
                                            <span class="component-desc">
                                                <input type="checkbox" name="trakt_remove_show_from_application" id="trakt_remove_show_from_application" ${'checked="checked"' if app.TRAKT_REMOVE_SHOW_FROM_APPLICATION else ''}/>
                                                <p>remove the show from Medusa if it's ended and completely watched</p>
                                            </span>
                                        </label>
                                    </div>
                                    <div class="field-pair">
                                        <label for="trakt_start_paused">
                                            <span class="component-title">Start paused</span>
                                            <span class="component-desc">
                                                <input type="checkbox" name="trakt_start_paused" id="trakt_start_paused" ${'checked="checked"' if app.TRAKT_START_PAUSED else ''}/>
                                                <p>shows grabbed from your trakt watchlist start paused.</p>
                                            </span>
                                        </label>
                                    </div>
                                </div>
                                <div class="field-pair">
                                    <label for="trakt_blacklist_name">
                                        <span class="component-title">Trakt blackList name</span>
                                        <input type="text" name="trakt_blacklist_name" id="trakt_blacklist_name" value="${app.TRAKT_BLACKLIST_NAME}" class="form-control input-sm input150"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">Name(slug) of List on Trakt for blacklisting show on 'Add Trending Show' & 'Add Recommended Shows' pages</span>
                                    </label>
                                </div>
                                <div class="testNotification" id="testTrakt-result">Click below to test.</div>
                                <input type="button" class="btn-medusa" value="Test Trakt" id="testTrakt" />
                                <input type="button" class="btn-medusa" value="Force Sync" id="forceSync" />
                                <input type="submit" class="btn-medusa config_submitter" value="Save Changes" />
                            </div><!-- #content_use_trakt //-->
                        </fieldset><!-- .component-group-desc-legacy //-->
                    </div><!-- trakt .component-group //-->

                    <div class="component-group-desc-legacy">
                        <span class="icon-notifiers-email" title="Email"></span>
                        <h3><app-link href="https://en.wikipedia.org/wiki/Comparison_of_webmail_providers">Email</app-link></h3>
                        <p>Allows configuration of email notifications on a per show basis.</p>
                    </div><!-- .component-group-desc-legacy //-->
                    <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="use_email">
                                    <span class="component-title">Enable</span>
                                    <span class="component-desc">
                                        <input type="checkbox" class="enabler" name="use_email" id="use_email" ${'checked="checked"' if app.USE_EMAIL else ''}/>
                                        <p>Send email notifications?</p>
                                    </span>
                                </label>
                            </div><!-- .field-pair //-->
                            <div id="content_use_email">
                                <div class="field-pair">
                                    <label for="email_notify_onsnatch">
                                        <span class="component-title">Notify on snatch</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="email_notify_onsnatch" id="email_notify_onsnatch" ${'checked="checked"' if app.EMAIL_NOTIFY_ONSNATCH else ''}/>
                                            <p>send a notification when a download starts?</p>
                                        </span>
                                    </label>
                                </div><!-- .field-pair //-->
                                <div class="field-pair">
                                    <label for="email_notify_ondownload">
                                        <span class="component-title">Notify on download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="email_notify_ondownload" id="email_notify_ondownload" ${'checked="checked"' if app.EMAIL_NOTIFY_ONDOWNLOAD else ''}/>
                                            <p>send a notification when a download finishes?</p>
                                        </span>
                                    </label>
                                </div><!-- .field-pair //-->
                                <div class="field-pair">
                                    <label for="email_notify_onsubtitledownload">
                                        <span class="component-title">Notify on subtitle download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="email_notify_onsubtitledownload" id="email_notify_onsubtitledownload" ${'checked="checked"' if app.EMAIL_NOTIFY_ONSUBTITLEDOWNLOAD else ''}/>
                                            <p>send a notification when subtitles are downloaded?</p>
                                        </span>
                                    </label>
                                </div><!-- .field-pair //-->
                                <div class="field-pair">
                                    <label for="email_host">
                                        <span class="component-title">SMTP host</span>
                                        <input type="text" name="email_host" id="email_host" value="${app.EMAIL_HOST}" class="form-control input-sm input250"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">hostname of your SMTP email server.</span>
                                    </label>
                                </div><!-- .field-pair //-->
                                <div class="field-pair">
                                    <label for="email_port">
                                        <span class="component-title">SMTP port</span>
                                        <input type="number" min="1" step="1" name="email_port" id="email_port" value="${app.EMAIL_PORT}" class="form-control input-sm input75"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">port number used to connect to your SMTP host.</span>
                                    </label>
                                </div><!-- .field-pair //-->
                                <div class="field-pair">
                                    <label for="email_from">
                                        <span class="component-title">SMTP from</span>
                                        <input type="text" name="email_from" id="email_from" value="${app.EMAIL_FROM}" class="form-control input-sm input250"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">sender email address, some hosts require a real address.</span>
                                    </label>
                                </div><!-- .field-pair //-->
                                <div class="field-pair">
                                    <label for="email_tls">
                                        <span class="component-title">Use TLS</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="email_tls" id="email_tls" ${'checked="checked"' if app.EMAIL_TLS else ''}/>
                                            <p>check to use TLS encryption.</p>
                                        </span>
                                    </label>
                                </div><!-- .field-pair //-->
                                <div class="field-pair">
                                    <label for="email_user">
                                        <span class="component-title">SMTP user</span>
                                        <input type="text" name="email_user" id="email_user" value="${app.EMAIL_USER}" class="form-control input-sm input250"
                                               autocomplete="no" />
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">(optional) your SMTP server username.</span>
                                    </label>
                                </div><!-- .field-pair //-->
                                <div class="field-pair">
                                    <label for="email_password">
                                        <span class="component-title">SMTP password</span>
                                        <input type="password" name="email_password" id="email_password" value="${app.EMAIL_PASSWORD}" class="form-control input-sm input250" autocomplete="no"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">(optional) your SMTP server password.</span>
                                    </label>
                                </div><!-- .field-pair //-->
                                <div class="field-pair">
                                    <label for="email_list">
                                        <span class="component-title">Global email list</span>
                                        <input type="text" name="email_list" id="email_list" value="${','.join(app.EMAIL_LIST)}" class="form-control input-sm input350"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">
                                            Email addresses listed here, separated by commas if applicable, will<br>
                                            receive notifications for <b>all</b> shows.<br>
                                            (This field may be blank except when testing.)
                                        </span>
                                    </label>
                                </div><!-- .field-pair //-->
                                <div class="field-pair">
                                    <label for="email_subject">
                                        <span class="component-title">Email Subject</span>
                                        <input type="text" name="email_subject" id="email_subject" value="${app.EMAIL_SUBJECT}" class="form-control input-sm input350"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">
                                            Use a custom subject for some privacy protection?<br>
                                            (Leave blank for the default Medusa subject)
                                        </span>
                                    </label>
                                </div><!-- .field-pair //-->
                                <div class="field-pair">
                                    <label for="email_show">
                                        <span class="component-title">Show notification list</span>
                                        <select name="email_show" id="email_show" class="form-control input-sm">
                                            <option value="-1">-- Select a Show --</option>
                                        </select>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <input type="text" name="email_show_list" id="email_show_list" class="form-control input-sm input350"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">
                                            Configure per-show notifications here by entering email address(es), separated by commas,
                                            after selecting a show in the drop-down box.   Be sure to activate the 'Save for this show'
                                            button below after each entry.
                                        </span>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <input id="email_show_save" class="btn-medusa" type="button" value="Save for this show" />
                                    </label>
                                </div><!-- .field-pair //-->
                                <div class="testNotification" id="testEmail-result">
                                    Click below to test.
                                </div><!-- #testEmail-result //-->
                                <input class="btn-medusa" type="button" value="Test Email" id="testEmail" />
                                <input class="btn-medusa" type="submit" class="config_submitter" value="Save Changes" />
                            </div><!-- #content_use_email //-->
                        </fieldset><!-- .component-group-list //-->
                    </div><!-- email .component-group //-->


                    <div class="component-group-desc-legacy">
                        <span class="icon-notifiers-slack" title="Slack"></span>
                        <h3><app-link href="https://slack.com">Slack</app-link></h3>
                        <p>Slack is a messaging app for teams.</p>
                    </div>
                    <div class="component-group">
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <label for="use_slack">
                                    <span class="component-title">Enable</span>
                                    <span class="component-desc">
                                        <input type="checkbox" class="enabler" name="use_slack" id="use_slack" ${'checked="checked"' if app.USE_SLACK else ''}/>
                                        <p>Send Slack notifications?</p>
                                    </span>
                                </label>
                            </div>
                            <div id="content_use_slack">
                                <div class="field-pair">
                                    <label for="slack_notify_onsnatch">
                                        <span class="component-title">Notify on snatch</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="slack_notify_onsnatch" id="slack_notify_onsnatch" ${'checked="checked"' if app.SLACK_NOTIFY_SNATCH else ''}/>
                                            <p>Send a message when a download starts?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="slack_notify_ondownload">
                                        <span class="component-title">Notify on download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="slack_notify_ondownload" id="slack_notify_ondownload" ${'checked="checked"' if app.SLACK_NOTIFY_DOWNLOAD else ''}/>
                                            <p>Send a message when a download finishes?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="slack_notify_onsubtitledownload">
                                        <span class="component-title">Notify on subtitle download</span>
                                        <span class="component-desc">
                                            <input type="checkbox" name="slack_notify_onsubtitledownload" id="slack_notify_onsubtitledownload" ${'checked="checked"' if app.SLACK_NOTIFY_SUBTITLEDOWNLOAD else ''}/>
                                            <p>Send a message when subtitles are downloaded?</p>
                                        </span>
                                    </label>
                                </div>
                                <div class="field-pair">
                                    <label for="slack_webhook">
                                        <span class="component-title">Slack Incoming Webhook</span>
                                        <input type="text" name="slack_webhook" id="slack_webhook" value="${app.SLACK_WEBHOOK}" class="form-control input-sm input250"/>
                                    </label>
                                    <label>
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">Create an incoming webhook, to communicate with your slack channel.
                                        <app-link href="https://my.slack.com/services/new/incoming-webhook">https://my.slack.com/services/new/incoming-webhook/</app-link></span>
                                    </label>
                                </div>
                                <div class="testNotification" id="testSlack-result">Click below to test your settings.</div>
                                <input  class="btn-medusa" type="button" value="Test Slack" id="testSlack" />
                                <input type="submit" class="config_submitter btn-medusa" value="Save Changes" />
                            </div><!-- /content_use_slack //-->
                        </fieldset>
                    </div><!-- /slack component-group //-->

                </div><!-- #social //-->
                <br><input type="submit" class="config_submitter btn-medusa" value="Save Changes" /><br>
            </div><!-- #config-components //-->
        </form><!-- #configForm //-->
    </div><!-- #config-content //-->
</div><!-- #config //-->
<div class="clearfix"></div>
</%block>
