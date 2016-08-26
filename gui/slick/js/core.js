// eslint-disable-line max-lines
// @TODO Move these into common.ini when possible,
//       currently we can't do that as browser.js and a few others need it before this is loaded
var themeSpinner;
var anonRedirect;
var loading;
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
    common: {
        init: function() {
            $.confirm.options = {
                confirmButton: 'Yes',
                cancelButton: 'Cancel',
                dialogClass: 'modal-dialog',
                post: false,
                confirm: function(e) {
                    location.href = e.context.href;
                }
            };

            $('a.shutdown').confirm({
                title: 'Shutdown',
                text: 'Are you sure you want to shutdown Medusa?'
            });

            $('a.restart').confirm({
                title: 'Restart',
                text: 'Are you sure you want to restart Medusa?'
            });

            $('a.removeshow').confirm({
                title: 'Remove Show',
                text: 'Are you sure you want to remove <span class="footerhighlight">' + $('#showtitle').data('showname') + '</span> from the database?<br><br><input type="checkbox" id="deleteFiles"> <span class="red-text">Check to delete files as well. IRREVERSIBLE</span></input>',
                confirm: function(e) {
                    location.href = e.context.href + ($('#deleteFiles')[0].checked ? '&full=1' : '');
                }
            });

            $('a.clearhistory').confirm({
                title: 'Clear History',
                text: 'Are you sure you want to clear all download history?'
            });

            $('a.trimhistory').confirm({
                title: 'Trim History',
                text: 'Are you sure you want to trim all download history older than 30 days?'
            });

            $('a.submiterrors').confirm({
                title: 'Submit Errors',
                text: 'Are you sure you want to submit these errors ?<br><br><span class="red-text">Make sure Medusa is updated and trigger<br> this error with debug enabled before submitting</span>'
            });

            $('#config-components').tabs({
                activate: function (event, ui) {
                    var lastOpenedPanel = $(this).data('lastOpenedPanel');

                    if (!lastOpenedPanel) {
                        lastOpenedPanel = $(ui.oldPanel);
                    }

                    if (!$(this).data('topPositionTab')) {
                        $(this).data('topPositionTab', $(ui.newPanel).position().top);
                    }

                    // Dont use the builtin fx effects. This will fade in/out both tabs, we dont want that
                    // Fadein the new tab yourself
                    $(ui.newPanel).hide().fadeIn(0);

                    if (lastOpenedPanel) {
                        // 1. Show the previous opened tab by removing the jQuery UI class
                        // 2. Make the tab temporary position:absolute so the two tabs will overlap
                        // 3. Set topposition so they will overlap if you go from tab 1 to tab 0
                        // 4. Remove position:absolute after animation
                        lastOpenedPanel
                            .toggleClass('ui-tabs-hide')
                            .css('position', 'absolute')
                            .css('top', $(this).data('topPositionTab') + 'px')
                            .fadeOut(0, function () {
                                $(this).css('position', '');
                            });
                    }

                    // Saving the last tab has been opened
                    $(this).data('lastOpenedPanel', $(ui.newPanel));
                }
            });

            // @TODO Replace this with a real touchscreen check
            // hack alert: if we don't have a touchscreen, and we are already hovering the mouse, then click should link instead of toggle
            if ((navigator.maxTouchPoints || 0) < 2) {
                $('.dropdown-toggle').on('click', function() {
                    var $this = $(this);
                    if ($this.attr('aria-expanded') === 'true') {
                        window.location.href = $this.attr('href');
                    }
                });
            }

            if (SICKRAGE.info.fuzzyDating) {
                $.timeago.settings.allowFuture = true;
                $.timeago.settings.strings = {
                    prefixAgo: null,
                    prefixFromNow: 'In ',
                    suffixAgo: 'ago',
                    suffixFromNow: '',
                    seconds: 'less than a minute',
                    minute: 'about a minute',
                    minutes: '%d minutes',
                    hour: 'an hour',
                    hours: '%d hours',
                    day: 'a day',
                    days: '%d days',
                    month: 'a month',
                    months: '%d months',
                    year: 'a year',
                    years: '%d years',
                    wordSeparator: ' ',
                    numbers: []
                };
                $('[datetime]').timeago();
            }

            $(document.body).on('click', 'a[data-no-redirect]', function(e) {
                e.preventDefault();
                $.get($(this).attr('href'));
                return false;
            });

            $(document.body).on('click', '.bulkCheck', function() {
                var bulkCheck = this;
                var whichBulkCheck = $(bulkCheck).attr('id');

                $('.' + whichBulkCheck + ':visible').each(function() {
                    $(this).prop('checked', $(bulkCheck).prop('checked'));
                });
            });

            $('.enabler').each(function() {
                if (!$(this).prop('checked')) {
                    $('#content_' + $(this).attr('id')).hide();
                }
            });

            $('.enabler').on('click', function() {
                if ($(this).prop('checked')) {
                    $('#content_' + $(this).attr('id')).fadeIn('fast', 'linear');
                } else {
                    $('#content_' + $(this).attr('id')).fadeOut('fast', 'linear');
                }
            });
        }
    },
    config: {
        init: function() {
            $('#config-components').tabs();

            $('.viewIf').on('click', function() {
                if ($(this).prop('checked')) {
                    $('.hide_if_' + $(this).attr('id')).css('display', 'none');
                    $('.show_if_' + $(this).attr('id')).fadeIn('fast', 'linear');
                } else {
                    $('.show_if_' + $(this).attr('id')).css('display', 'none');
                    $('.hide_if_' + $(this).attr('id')).fadeIn('fast', 'linear');
                }
            });

            $('.datePresets').on('click', function() {
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
                beforeSubmit: function() {
                    $('.config_submitter .config_submitter_refresh').each(function() {
                        $(this).prop('disabled', 'disabled');
                        $(this).after('<span><img src="images/loading16' + themeSpinner + '.gif"> Saving...</span>');
                        $(this).hide();
                    });
                },
                success: function() {
                    setTimeout(function() {
                        $('.config_submitter').each(function() {
                            $(this).removeAttr('disabled');
                            $(this).next().remove();
                            $(this).show();
                        });
                        $('.config_submitter_refresh').each(function() {
                            $(this).removeAttr('disabled');
                            $(this).next().remove();
                            $(this).show();
                            window.location.href = 'config/providers/';
                        });
                        $('#email_show').trigger('notify');
                        $('#prowl_show').trigger('notify');
                    }, 2000);
                }
            });

            $('#api_key').on('click', function() {
                $('#api_key').select();
            });

            $('#generate_new_apikey').on('click', function() {
                $.get('config/general/generateApiKey', function(data) {
                    if (data.error !== undefined) {
                        alert(data.error);
                        return;
                    }
                    $('#api_key').val(data);
                });
            });

            $('#branchCheckout').on('click', function() {
                var url = 'home/branchCheckout?branch=' + $('#branchVersion').val();
                $.getJSON('home/getDBcompare', function(data) {
                    if (data.status === 'success') {
                        if (data.message === 'equal') {
                            // Checkout Branch
                            window.location.href = url;
                        }
                        if (data.message === 'upgrade') {
                            if (confirm('Changing branch will upgrade your database.\nYou won\'t be able to downgrade afterward.\nDo you want to continue?')) {
                                // Checkout Branch
                                window.location.href = url;
                            }
                        }
                        if (data.message === 'downgrade') {
                            alert('Can\'t switch branch as this will result in a database downgrade.');
                        }
                    }
                });
            });

            $('#branchForceUpdate').on('click', function() {
                $('#branchForceUpdate').prop('disabled', true);
                $('#git_reset_branches').prop('disabled', true);
                $.getJSON('home/branchForceUpdate', function(data) {
                    $('#git_reset_branches').empty();
                    data.resetBranches.forEach(function(branch) {
                        $('#git_reset_branches').append('<option value="' + branch + '" selected="selected" >' + branch + '</option>');
                    });
                    data.branches.forEach(function(branch) {
                        $('#git_reset_branches').append('<option value="' + branch + '" >' + branch + '</option>');
                    });
                    $('#git_reset_branches').prop('disabled', false);
                    $('#branchForceUpdate').prop('disabled', false);
                });
            });
        },
        index: function() {
            if ($('input[name=\'proxy_setting\']').val().length === 0) {
                $('input[id=\'proxy_indexers\']').prop('checked', false);
                $('label[for=\'proxy_indexers\']').hide();
            }

            $('input[name=\'proxy_setting\']').on('input', function() {
                if ($(this).val().length === 0) {
                    $('input[id=\'proxy_indexers\']').prop('checked', false);
                    $('label[for=\'proxy_indexers\']').hide();
                } else {
                    $('label[for=\'proxy_indexers\']').show();
                }
            });

            $('#log_dir').fileBrowser({title: 'Select log file folder location'});
        },
        backupRestore: function() {
            $('#Backup').on('click', function() {
                $('#Backup').prop('disabled', true);
                $('#Backup-result').html(loading);
                var backupDir = $('#backupDir').val();
                $.get('config/backuprestore/backup', {
                    backupDir: backupDir
                }).done(function (data) {
                    $('#Backup-result').html(data);
                    $('#Backup').prop('disabled', false);
                });
            });
            $('#Restore').on('click', function() {
                $('#Restore').prop('disabled', true);
                $('#Restore-result').html(loading);
                var backupFile = $('#backupFile').val();
                $.get('config/backuprestore/restore', {
                    backupFile: backupFile
                }).done(function (data) {
                    $('#Restore-result').html(data);
                    $('#Restore').prop('disabled', false);
                });
            });

            $('#backupDir').fileBrowser({
                title: 'Select backup folder to save to',
                key: 'backupPath'
            });
            $('#backupFile').fileBrowser({
                title: 'Select backup files to restore',
                key: 'backupFile',
                includeFiles: 1
            });
            $('#config-components').tabs();
        },
        notifications: function() {
            $('#testGrowl').on('click', function () {
                var growl = {};
                growl.host = $.trim($('#growl_host').val());
                growl.password = $.trim($('#growl_password').val());
                if (!growl.host) {
                    $('#testGrowl-result').html('Please fill out the necessary fields above.');
                    $('#growl_host').addClass('warning');
                    return;
                }
                $('#growl_host').removeClass('warning');
                $(this).prop('disabled', true);
                $('#testGrowl-result').html(loading);
                $.get('home/testGrowl', {
                    host: growl.host,
                    password: growl.password
                }).done(function (data) {
                    $('#testGrowl-result').html(data);
                    $('#testGrowl').prop('disabled', false);
                });
            });

            $('#testProwl').on('click', function () {
                var prowl = {};
                prowl.api = $.trim($('#prowl_api').val());
                prowl.priority = $('#prowl_priority').val();
                if (!prowl.api) {
                    $('#testProwl-result').html('Please fill out the necessary fields above.');
                    $('#prowl_api').addClass('warning');
                    return;
                }
                $('#prowl_api').removeClass('warning');
                $(this).prop('disabled', true);
                $('#testProwl-result').html(loading);
                $.get('home/testProwl', {
                    prowl_api: prowl.api, // eslint-disable-line camelcase
                    prowl_priority: prowl.priority // eslint-disable-line camelcase
                }).done(function (data) {
                    $('#testProwl-result').html(data);
                    $('#testProwl').prop('disabled', false);
                });
            });

            $('#testKODI').on('click', function () {
                var kodi = {};
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
                $('#testKODI-result').html(loading);
                $.get('home/testKODI', {
                    host: kodi.host,
                    username: kodi.username,
                    password: kodi.password
                }).done(function (data) {
                    $('#testKODI-result').html(data);
                    $('#testKODI').prop('disabled', false);
                });
            });

            $('#testPHT').on('click', function () {
                var plex = {};
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
                $('#testPHT-result').html(loading);
                $.get('home/testPHT', {
                    host: plex.client.host,
                    username: plex.client.username,
                    password: plex.client.password
                }).done(function (data) {
                    $('#testPHT-result').html(data);
                    $('#testPHT').prop('disabled', false);
                });
            });

            $('#testPMS').on('click', function () {
                var plex = {};
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
                $('#testPMS-result').html(loading);
                $.get('home/testPMS', {
                    host: plex.server.host,
                    username: plex.server.username,
                    password: plex.server.password,
                    plex_server_token: plex.server.token // eslint-disable-line camelcase
                }).done(function (data) {
                    $('#testPMS-result').html(data);
                    $('#testPMS').prop('disabled', false);
                });
            });

            $('#testEMBY').on('click', function () {
                var emby = {};
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
                $('#testEMBY-result').html(loading);
                $.get('home/testEMBY', {
                    host: emby.host,
                    emby_apikey: emby.apikey // eslint-disable-line camelcase
                }).done(function (data) {
                    $('#testEMBY-result').html(data);
                    $('#testEMBY').prop('disabled', false);
                });
            });

            $('#testBoxcar2').on('click', function () {
                var boxcar2 = {};
                boxcar2.accesstoken = $.trim($('#boxcar2_accesstoken').val());
                if (!boxcar2.accesstoken) {
                    $('#testBoxcar2-result').html('Please fill out the necessary fields above.');
                    $('#boxcar2_accesstoken').addClass('warning');
                    return;
                }
                $('#boxcar2_accesstoken').removeClass('warning');
                $(this).prop('disabled', true);
                $('#testBoxcar2-result').html(loading);
                $.get('home/testBoxcar2', {
                    accesstoken: boxcar2.accesstoken
                }).done(function (data) {
                    $('#testBoxcar2-result').html(data);
                    $('#testBoxcar2').prop('disabled', false);
                });
            });

            $('#testPushover').on('click', function () {
                var pushover = {};
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
                $('#testPushover-result').html(loading);
                $.get('home/testPushover', {
                    userKey: pushover.userkey,
                    apiKey: pushover.apikey
                }).done(function (data) {
                    $('#testPushover-result').html(data);
                    $('#testPushover').prop('disabled', false);
                });
            });

            $('#testLibnotify').on('click', function() {
                $('#testLibnotify-result').html(loading);
                $.get('home/testLibnotify', function (data) {
                    $('#testLibnotify-result').html(data);
                });
            });

            $('#twitterStep1').on('click', function() {
                $('#testTwitter-result').html(loading);
                $.get('home/twitterStep1', function (data) {
                    window.open(data);
                }).done(function() {
                    $('#testTwitter-result').html('<b>Step1:</b> Confirm Authorization');
                });
            });

            $('#twitterStep2').on('click', function () {
                var twitter = {};
                twitter.key = $.trim($('#twitter_key').val());
                $('#twitter_key').addRemoveWarningClass(twitter.key);
                if (twitter.key) {
                    $('#testTwitter-result').html(loading);
                    $.get('home/twitterStep2', {
                        key: twitter.key
                    }, function(data) {
                        $('#testTwitter-result').html(data);
                    });
                }
                $('#testTwitter-result').html('Please fill out the necessary fields above.');
            });

            $('#testTwitter').on('click', function() {
                $.get('home/testTwitter', function(data) {
                    $('#testTwitter-result').html(data);
                });
            });

            $('#settingsNMJ').on('click', function() {
                var nmj = {};
                if ($('#nmj_host').val()) {
                    $('#testNMJ-result').html(loading);
                    nmj.host = $('#nmj_host').val();

                    $.get('home/settingsNMJ', {
                        host: nmj.host
                    }, function (data) {
                        if (data === null) {
                            $('#nmj_database').removeAttr('readonly');
                            $('#nmj_mount').removeAttr('readonly');
                        }
                        var JSONData = $.parseJSON(data);
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
                alert('Please fill in the Popcorn IP address');
                $('#nmj_host').focus();
            });

            $('#testNMJ').on('click', function () {
                var nmj = {};
                nmj.host = $.trim($('#nmj_host').val());
                nmj.database = $('#nmj_database').val();
                nmj.mount = $('#nmj_mount').val();
                if (nmj.host) {
                    $('#nmj_host').removeClass('warning');
                    $(this).prop('disabled', true);
                    $('#testNMJ-result').html(loading);
                    $.get('home/testNMJ', {
                        host: nmj.host,
                        database: nmj.database,
                        mount: nmj.mount
                    }).done(function (data) {
                        $('#testNMJ-result').html(data);
                        $('#testNMJ').prop('disabled', false);
                    });
                }
                $('#testNMJ-result').html('Please fill out the necessary fields above.');
                $('#nmj_host').addClass('warning');
            });

            $('#settingsNMJv2').on('click', function() {
                var nmjv2 = {};
                if ($('#nmjv2_host').val()) {
                    $('#testNMJv2-result').html(loading);
                    nmjv2.host = $('#nmjv2_host').val();
                    nmjv2.dbloc = '';
                    var radios = document.getElementsByName('nmjv2_dbloc');
                    for (var i = 0, len = radios.length; i < len; i++) {
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
                    }, function (data) {
                        if (data === null) {
                            $('#nmjv2_database').removeAttr('readonly');
                        }
                        var JSONData = $.parseJSON(data);
                        $('#testNMJv2-result').html(JSONData.message);
                        $('#nmjv2_database').val(JSONData.database);

                        if (JSONData.database) {
                            $('#nmjv2_database').prop('readonly', true);
                        } else {
                            $('#nmjv2_database').removeAttr('readonly');
                        }
                    });
                }
                alert('Please fill in the Popcorn IP address');
                $('#nmjv2_host').focus();
            });

            $('#testNMJv2').on('click', function () {
                var nmjv2 = {};
                nmjv2.host = $.trim($('#nmjv2_host').val());
                if (nmjv2.host) {
                    $('#nmjv2_host').removeClass('warning');
                    $(this).prop('disabled', true);
                    $('#testNMJv2-result').html(loading);
                    $.get('home/testNMJv2', {
                        host: nmjv2.host
                    }).done(function (data) {
                        $('#testNMJv2-result').html(data);
                        $('#testNMJv2').prop('disabled', false);
                    });
                }
                $('#testNMJv2-result').html('Please fill out the necessary fields above.');
                $('#nmjv2_host').addClass('warning');
            });

            $('#testFreeMobile').on('click', function () {
                var freemobile = {};
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
                $('#testFreeMobile-result').html(loading);
                $.get('home/testFreeMobile', {
                    freemobile_id: freemobile.id, // eslint-disable-line camelcase
                    freemobile_apikey: freemobile.apikey // eslint-disable-line camelcase
                }).done(function (data) {
                    $('#testFreeMobile-result').html(data);
                    $('#testFreeMobile').prop('disabled', false);
                });
            });

            $('#testTelegram').on('click', function () {
                var telegram = {};
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
                $('#testTelegram-result').html(loading);
                $.get('home/testTelegram', {
                    telegram_id: telegram.id, // eslint-disable-line camelcase
                    telegram_apikey: telegram.apikey // eslint-disable-line camelcase
                }).done(function (data) {
                    $('#testTelegram-result').html(data);
                    $('#testTelegram').prop('disabled', false);
                });
            });

            $('#TraktGetPin').on('click', function () {
                window.open($('#trakt_pin_url').val(), 'popUp', 'toolbar=no, scrollbars=no, resizable=no, top=200, left=200, width=650, height=550');
                $('#trakt_pin').removeClass('hide');
            });

            $('#trakt_pin').on('keyup change', function() {
                if ($('#trakt_pin').val().length !== 0) {
                    $('#TraktGetPin').addClass('hide');
                    $('#authTrakt').removeClass('hide');
                } else {
                    $('#TraktGetPin').removeClass('hide');
                    $('#authTrakt').addClass('hide');
                }
            });

            $('#authTrakt').on('click', function() {
                var trakt = {};
                trakt.pin = $('#trakt_pin').val();
                if (trakt.pin.length !== 0) {
                    $.get('home/getTraktToken', {
                        trakt_pin: trakt.pin // eslint-disable-line camelcase
                    }).done(function (data) {
                        $('#testTrakt-result').html(data);
                        $('#authTrakt').addClass('hide');
                        $('#trakt_pin').addClass('hide');
                        $('#TraktGetPin').addClass('hide');
                    });
                }
            });

            $('#testTrakt').on('click', function () {
                var trakt = {};
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
                $('#testTrakt-result').html(loading);
                $.get('home/testTrakt', {
                    username: trakt.username,
                    blacklist_name: trakt.trendingBlacklist // eslint-disable-line camelcase
                }).done(function (data) {
                    $('#testTrakt-result').html(data);
                    $('#testTrakt').prop('disabled', false);
                });
            });

            $('#forceSync').on('click', function () {
                $('#testTrakt-result').html(loading);
                $.getJSON('home/forceTraktSync', function(data) {
                    $('#testTrakt-result').html(data.result);
                });
            });

            $('#testEmail').on('click', function () {
                var status;
                var host;
                var port;
                var tls;
                var from;
                var user;
                var pwd;
                var err;
                var to;
                status = $('#testEmail-result');
                status.html(loading);
                host = $('#email_host').val();
                host = host.length > 0 ? host : null;
                port = $('#email_port').val();
                port = port.length > 0 ? port : null;
                tls = $('#email_tls').attr('checked') === undefined ? 0 : 1;
                from = $('#email_from').val();
                from = from.length > 0 ? from : 'root@localhost';
                user = $('#email_user').val().trim();
                pwd = $('#email_password').val();
                err = '';
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
                    to = prompt('Enter an email address to send the test to:', null);
                    if (to === null || to.length === 0 || to.match(/.*@.*/) === null) {
                        status.html('<p style="color: red;">You must provide a recipient email address!</p>');
                    } else {
                        $.get('home/testEmail', {
                            host: host,
                            port: port,
                            smtp_from: from, // eslint-disable-line camelcase
                            use_tls: tls, // eslint-disable-line camelcase
                            user: user,
                            pwd: pwd,
                            to: to
                        }, function (msg) {
                            $('#testEmail-result').html(msg);
                        });
                    }
                }
            });

            $('#testNMA').on('click', function () {
                var nma = {};
                nma.api = $.trim($('#nma_api').val());
                nma.priority = $('#nma_priority').val();
                if (!nma.api) {
                    $('#testNMA-result').html('Please fill out the necessary fields above.');
                    $('#nma_api').addClass('warning');
                    return;
                }
                $('#nma_api').removeClass('warning');
                $(this).prop('disabled', true);
                $('#testNMA-result').html(loading);
                $.get('home/testNMA', {
                    nma_api: nma.api, // eslint-disable-line camelcase
                    nma_priority: nma.priority // eslint-disable-line camelcase
                }).done(function (data) {
                    $('#testNMA-result').html(data);
                    $('#testNMA').prop('disabled', false);
                });
            });

            $('#testPushalot').on('click', function () {
                var pushalot = {};
                pushalot.authToken = $.trim($('#pushalot_authorizationtoken').val());
                if (!pushalot.authToken) {
                    $('#testPushalot-result').html('Please fill out the necessary fields above.');
                    $('#pushalot_authorizationtoken').addClass('warning');
                    return;
                }
                $('#pushalot_authorizationtoken').removeClass('warning');
                $(this).prop('disabled', true);
                $('#testPushalot-result').html(loading);
                $.get('home/testPushalot', {
                    authorizationToken: pushalot.authToken
                }).done(function (data) {
                    $('#testPushalot-result').html(data);
                    $('#testPushalot').prop('disabled', false);
                });
            });

            $('#testPushbullet').on('click', function () {
                var pushbullet = {};
                pushbullet.api = $.trim($('#pushbullet_api').val());
                if (!pushbullet.api) {
                    $('#testPushbullet-result').html('Please fill out the necessary fields above.');
                    $('#pushbullet_api').addClass('warning');
                    return;
                }
                $('#pushbullet_api').removeClass('warning');
                $(this).prop('disabled', true);
                $('#testPushbullet-result').html(loading);
                $.get('home/testPushbullet', {
                    api: pushbullet.api
                }).done(function (data) {
                    $('#testPushbullet-result').html(data);
                    $('#testPushbullet').prop('disabled', false);
                });
            });

            function getPushbulletDevices(msg) {
                var pushbullet = {};
                pushbullet.api = $('#pushbullet_api').val();

                if (msg) {
                    $('#testPushbullet-result').html(loading);
                }

                if (!pushbullet.api) {
                    $('#testPushbullet-result').html('You didn\'t supply a Pushbullet api key');
                    $('#pushbullet_api').focus();
                    return false;
                }

                $.get('home/getPushbulletDevices', {
                    api: pushbullet.api
                }, function (data) {
                    pushbullet.devices = $.parseJSON(data).devices;
                    pushbullet.currentDevice = $('#pushbullet_device').val();
                    $('#pushbullet_device_list').html('');
                    for (var i = 0, len = pushbullet.devices.length; i < len; i++) {
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

                $('#pushbullet_device_list').on('change', function() {
                    $('#pushbullet_device').val($('#pushbullet_device_list').val());
                    $('#testPushbullet-result').html('Don\'t forget to save your new pushbullet settings.');
                });
            }

            $('#getPushbulletDevices').on('click', function() {
                getPushbulletDevices('Device list updated. Please choose a device to push to.');
            });

            // we have to call this function on dom ready to create the devices select
            getPushbulletDevices();

            $('#email_show').on('change', function() {
                var key = parseInt($('#email_show').val(), 10);
                $.getJSON('home/loadShowNotifyLists', function(notifyData) {
                    if (notifyData._size > 0) {
                        $('#email_show_list').val(key >= 0 ? notifyData[key.toString()].list : '');
                    }
                });
            });
            $('#prowl_show').on('change', function() {
                var key = parseInt($('#prowl_show').val(), 10);
                $.getJSON('home/loadShowNotifyLists', function(notifyData) {
                    if (notifyData._size > 0) {
                        $('#prowl_show_list').val(key >= 0 ? notifyData[key.toString()].prowl_notify_list : '');
                    }
                });
            });

            function loadShowNotifyLists() {
                $.getJSON('home/loadShowNotifyLists', function(list) {
                    var html;
                    var s;
                    if (list._size === 0) {
                        return;
                    }

                    // Convert the 'list' object to a js array of objects so that we can sort it
                    var _list = [];
                    for (s in list) {
                        if (s.charAt(0) !== '_') {
                            _list.push(list[s]);
                        }
                    }
                    var sortedList = _list.sort(function(a, b) {
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

            $('#email_show_save').on('click', function() {
                $.post('home/saveShowNotifyList', {
                    show: $('#email_show').val(),
                    emails: $('#email_show_list').val()
                }, loadShowNotifyLists);
            });
            $('#prowl_show_save').on('click', function() {
                $.post('home/saveShowNotifyList', {
                    show: $('#prowl_show').val(),
                    prowlAPIs: $('#prowl_show_list').val()
                }, function() {
                    // Reload the per show notify lists to reflect changes
                    loadShowNotifyLists();
                });
            });

            // show instructions for plex when enabled
            $('#use_plex_server').on('click', function() {
                if ($(this).is(':checked')) {
                    $('.plexinfo').removeClass('hide');
                } else {
                    $('.plexinfo').addClass('hide');
                }
            });
        },
        postProcessing: function() {
            $('#config-components').tabs();
            $('#tv_download_dir').fileBrowser({
                title: 'Select TV Download Directory'
            });

            // http://stackoverflow.com/questions/2219924/idiomatic-jquery-delayed-event-only-after-a-short-pause-in-typing-e-g-timew
            var typewatch = (function () {
                var timer = 0;
                return function (callback, ms) {
                    clearTimeout(timer);
                    timer = setTimeout(callback, ms);
                };
            })();

            function isRarSupported() {
                $.get('config/postProcessing/isRarSupported', function (data) {
                    if (data !== 'supported') {
                        $('#unpack').qtip('option', {
                            'content.text': 'Unrar Executable not found.',
                            'style.classes': 'qtip-rounded qtip-shadow qtip-red'
                        });
                        $('#unpack').qtip('toggle', true);
                        $('#unpack').css('background-color', '#FFFFDD');
                    }
                });
            }

            function fillExamples() {
                var example = {};

                example.pattern = $('#naming_pattern').val();
                example.multi = $('#naming_multi_ep :selected').val();
                example.animeType = $('input[name="naming_anime"]:checked').val();

                $.get('config/postProcessing/testNaming', {
                    pattern: example.pattern,
                    anime_type: 3 // eslint-disable-line camelcase
                }, function (data) {
                    if (data) {
                        $('#naming_example').text(data + '.ext');
                        $('#naming_example_div').show();
                    } else {
                        $('#naming_example_div').hide();
                    }
                });

                $.get('config/postProcessing/testNaming', {
                    pattern: example.pattern,
                    multi: example.multi,
                    anime_type: 3 // eslint-disable-line camelcase
                }, function (data) {
                    if (data) {
                        $('#naming_example_multi').text(data + '.ext');
                        $('#naming_example_multi_div').show();
                    } else {
                        $('#naming_example_multi_div').hide();
                    }
                });

                $.get('config/postProcessing/isNamingValid', {
                    pattern: example.pattern,
                    multi: example.multi,
                    anime_type: example.animeType // eslint-disable-line camelcase
                }, function (data) {
                    if (data === 'invalid') {
                        $('#naming_pattern').qtip('option', {
                            'content.text': 'This pattern is invalid.',
                            'style.classes': 'qtip-rounded qtip-shadow qtip-red'
                        });
                        $('#naming_pattern').qtip('toggle', true);
                        $('#naming_pattern').css('background-color', '#FFDDDD');
                    } else if (data === 'seasonfolders') {
                        $('#naming_pattern').qtip('option', {
                            'content.text': 'This pattern would be invalid without the folders, using it will force "Flatten" off for all shows.',
                            'style.classes': 'qtip-rounded qtip-shadow qtip-red'
                        });
                        $('#naming_pattern').qtip('toggle', true);
                        $('#naming_pattern').css('background-color', '#FFFFDD');
                    } else {
                        $('#naming_pattern').qtip('option', {
                            'content.text': 'This pattern is valid.',
                            'style.classes': 'qtip-rounded qtip-shadow qtip-green'
                        });
                        $('#naming_pattern').qtip('toggle', false);
                        $('#naming_pattern').css('background-color', '#FFFFFF');
                    }
                });
            }

            function fillAbdExamples() {
                var pattern = $('#naming_abd_pattern').val();

                $.get('config/postProcessing/testNaming', {
                    pattern: pattern,
                    abd: 'True'
                }, function (data) {
                    if (data) {
                        $('#naming_abd_example').text(data + '.ext');
                        $('#naming_abd_example_div').show();
                    } else {
                        $('#naming_abd_example_div').hide();
                    }
                });

                $.get('config/postProcessing/isNamingValid', {
                    pattern: pattern,
                    abd: 'True'
                }, function (data) {
                    if (data === 'invalid') {
                        $('#naming_abd_pattern').qtip('option', {
                            'content.text': 'This pattern is invalid.',
                            'style.classes': 'qtip-rounded qtip-shadow qtip-red'
                        });
                        $('#naming_abd_pattern').qtip('toggle', true);
                        $('#naming_abd_pattern').css('background-color', '#FFDDDD');
                    } else if (data === 'seasonfolders') {
                        $('#naming_abd_pattern').qtip('option', {
                            'content.text': 'This pattern would be invalid without the folders, using it will force "Flatten" off for all shows.',
                            'style.classes': 'qtip-rounded qtip-shadow qtip-red'
                        });
                        $('#naming_abd_pattern').qtip('toggle', true);
                        $('#naming_abd_pattern').css('background-color', '#FFFFDD');
                    } else {
                        $('#naming_abd_pattern').qtip('option', {
                            'content.text': 'This pattern is valid.',
                            'style.classes': 'qtip-rounded qtip-shadow qtip-green'
                        });
                        $('#naming_abd_pattern').qtip('toggle', false);
                        $('#naming_abd_pattern').css('background-color', '#FFFFFF');
                    }
                });
            }

            function fillSportsExamples() {
                var pattern = $('#naming_sports_pattern').val();

                $.get('config/postProcessing/testNaming', {
                    pattern: pattern,
                    sports: 'True' // @TODO does this actually need to be a string or can it be a boolean?
                }, function (data) {
                    if (data) {
                        $('#naming_sports_example').text(data + '.ext');
                        $('#naming_sports_example_div').show();
                    } else {
                        $('#naming_sports_example_div').hide();
                    }
                });

                $.get('config/postProcessing/isNamingValid', {
                    pattern: pattern,
                    sports: 'True' // @TODO does this actually need to be a string or can it be a boolean?
                }, function (data) {
                    if (data === 'invalid') {
                        $('#naming_sports_pattern').qtip('option', {
                            'content.text': 'This pattern is invalid.',
                            'style.classes': 'qtip-rounded qtip-shadow qtip-red'
                        });
                        $('#naming_sports_pattern').qtip('toggle', true);
                        $('#naming_sports_pattern').css('background-color', '#FFDDDD');
                    } else if (data === 'seasonfolders') {
                        $('#naming_sports_pattern').qtip('option', {
                            'content.text': 'This pattern would be invalid without the folders, using it will force "Flatten" off for all shows.',
                            'style.classes': 'qtip-rounded qtip-shadow qtip-red'
                        });
                        $('#naming_sports_pattern').qtip('toggle', true);
                        $('#naming_sports_pattern').css('background-color', '#FFFFDD');
                    } else {
                        $('#naming_sports_pattern').qtip('option', {
                            'content.text': 'This pattern is valid.',
                            'style.classes': 'qtip-rounded qtip-shadow qtip-green'
                        });
                        $('#naming_sports_pattern').qtip('toggle', false);
                        $('#naming_sports_pattern').css('background-color', '#FFFFFF');
                    }
                });
            }

            function fillAnimeExamples() {
                var example = {};
                example.pattern = $('#naming_anime_pattern').val();
                example.multi = $('#naming_anime_multi_ep :selected').val();
                example.animeType = $('input[name="naming_anime"]:checked').val();

                $.get('config/postProcessing/testNaming', {
                    pattern: example.pattern,
                    anime_type: example.animeType // eslint-disable-line camelcase
                }, function (data) {
                    if (data) {
                        $('#naming_example_anime').text(data + '.ext');
                        $('#naming_example_anime_div').show();
                    } else {
                        $('#naming_example_anime_div').hide();
                    }
                });

                $.get('config/postProcessing/testNaming', {
                    pattern: example.pattern,
                    multi: example.multi,
                    anime_type: example.animeType // eslint-disable-line camelcase
                }, function (data) {
                    if (data) {
                        $('#naming_example_multi_anime').text(data + '.ext');
                        $('#naming_example_multi_anime_div').show();
                    } else {
                        $('#naming_example_multi_anime_div').hide();
                    }
                });

                $.get('config/postProcessing/isNamingValid', {
                    pattern: example.pattern,
                    multi: example.multi,
                    anime_type: example.animeType // eslint-disable-line camelcase
                }, function (data) {
                    if (data === 'invalid') {
                        $('#naming_pattern').qtip('option', {
                            'content.text': 'This pattern is invalid.',
                            'style.classes': 'qtip-rounded qtip-shadow qtip-red'
                        });
                        $('#naming_pattern').qtip('toggle', true);
                        $('#naming_pattern').css('background-color', '#FFDDDD');
                    } else if (data === 'seasonfolders') {
                        $('#naming_pattern').qtip('option', {
                            'content.text': 'This pattern would be invalid without the folders, using it will force "Flatten" off for all shows.',
                            'style.classes': 'qtip-rounded qtip-shadow qtip-red'
                        });
                        $('#naming_pattern').qtip('toggle', true);
                        $('#naming_pattern').css('background-color', '#FFFFDD');
                    } else {
                        $('#naming_pattern').qtip('option', {
                            'content.text': 'This pattern is valid.',
                            'style.classes': 'qtip-rounded qtip-shadow qtip-green'
                        });
                        $('#naming_pattern').qtip('toggle', false);
                        $('#naming_pattern').css('background-color', '#FFFFFF');
                    }
                });
            }

            // @TODO all of these setup funcitons should be able to be rolled into a generic function

            function setupNaming() {
                // if it is a custom selection then show the text box
                if ($('#name_presets :selected').val().toLowerCase() === 'custom...') {
                    $('#naming_custom').show();
                } else {
                    $('#naming_custom').hide();
                    $('#naming_pattern').val($('#name_presets :selected').attr('id'));
                }
                fillExamples();
            }

            function setupAbdNaming() {
                // if it is a custom selection then show the text box
                if ($('#name_abd_presets :selected').val().toLowerCase() === 'custom...') {
                    $('#naming_abd_custom').show();
                } else {
                    $('#naming_abd_custom').hide();
                    $('#naming_abd_pattern').val($('#name_abd_presets :selected').attr('id'));
                }
                fillAbdExamples();
            }

            function setupSportsNaming() {
                // if it is a custom selection then show the text box
                if ($('#name_sports_presets :selected').val().toLowerCase() === 'custom...') {
                    $('#naming_sports_custom').show();
                } else {
                    $('#naming_sports_custom').hide();
                    $('#naming_sports_pattern').val($('#name_sports_presets :selected').attr('id'));
                }
                fillSportsExamples();
            }

            function setupAnimeNaming() {
                // if it is a custom selection then show the text box
                if ($('#name_anime_presets :selected').val().toLowerCase() === 'custom...') {
                    $('#naming_anime_custom').show();
                } else {
                    $('#naming_anime_custom').hide();
                    $('#naming_anime_pattern').val($('#name_anime_presets :selected').attr('id'));
                }
                fillAnimeExamples();
            }

            $('#unpack').on('change', function() {
                if (this.checked) {
                    isRarSupported();
                } else {
                    $('#unpack').qtip('toggle', false);
                }
            });

            // @TODO all of these on change funcitons should be able to be rolled into a generic jQuery function or maybe we could
            //       move all of the setup functions into these handlers?

            $('#name_presets').on('change', function() {
                setupNaming();
            });

            $('#name_abd_presets').on('change', function() {
                setupAbdNaming();
            });

            $('#naming_custom_abd').on('change', function() {
                setupAbdNaming();
            });

            $('#name_sports_presets').on('change', function() {
                setupSportsNaming();
            });

            $('#naming_custom_sports').on('change', function() {
                setupSportsNaming();
            });

            $('#name_anime_presets').on('change', function() {
                setupAnimeNaming();
            });

            $('#naming_custom_anime').on('change', function() {
                setupAnimeNaming();
            });

            $('input[name="naming_anime"]').on('click', function() {
                setupAnimeNaming();
            });

            // @TODO We might be able to change these from typewatch to _ debounce like we've done on the log page
            //       The main reason for doing this would be to use only open source stuff that's still being maintained

            $('#naming_multi_ep').on('change', fillExamples);
            $('#naming_pattern').on('focusout', fillExamples);
            $('#naming_pattern').on('keyup', function() {
                typewatch(function () {
                    fillExamples();
                }, 500);
            });

            $('#naming_anime_multi_ep').on('change', fillAnimeExamples);
            $('#naming_anime_pattern').on('focusout', fillAnimeExamples);
            $('#naming_anime_pattern').on('keyup', function() {
                typewatch(function () {
                    fillAnimeExamples();
                }, 500);
            });

            $('#naming_abd_pattern').on('focusout', fillExamples);
            $('#naming_abd_pattern').on('keyup', function() {
                typewatch(function () {
                    fillAbdExamples();
                }, 500);
            });

            $('#naming_sports_pattern').on('focusout', fillExamples);
            $('#naming_sports_pattern').on('keyup', function() {
                typewatch(function () {
                    fillSportsExamples();
                }, 500);
            });

            $('#naming_anime_pattern').on('focusout', fillExamples);
            $('#naming_anime_pattern').on('keyup', function() {
                typewatch(function () {
                    fillAnimeExamples();
                }, 500);
            });

            $('#show_naming_key').on('click', function() {
                $('#naming_key').toggle();
            });
            $('#show_naming_abd_key').on('click', function() {
                $('#naming_abd_key').toggle();
            });
            $('#show_naming_sports_key').on('click', function() {
                $('#naming_sports_key').toggle();
            });
            $('#show_naming_anime_key').on('click', function() {
                $('#naming_anime_key').toggle();
            });
            $('#do_custom').on('click', function() {
                $('#naming_pattern').val($('#name_presets :selected').attr('id'));
                $('#naming_custom').show();
                $('#naming_pattern').focus();
            });

            // @TODO We should see if these can be added with the on click or if we need to even call them on load
            setupNaming();
            setupAbdNaming();
            setupSportsNaming();
            setupAnimeNaming();

            // -- start of metadata options div toggle code --
            $('#metadataType').on('change keyup', function () {
                $(this).showHideMetadata();
            });

            $.fn.showHideMetadata = function () {
                $('.metadataDiv').each(function () {
                    var targetName = $(this).attr('id');
                    var selectedTarget = $('#metadataType :selected').val();

                    if (selectedTarget === targetName) {
                        $(this).show();
                    } else {
                        $(this).hide();
                    }
                });
            };
            // initialize to show the div
            $(this).showHideMetadata();
            // -- end of metadata options div toggle code --

            $('.metadata_checkbox').on('click', function() {
                $(this).refreshMetadataConfig(false);
            });

            $.fn.refreshMetadataConfig = function (first) {
                var curMost = 0;
                var curMostProvider = '';

                $('.metadataDiv').each(function() {
                    var generatorName = $(this).attr('id');

                    var configArray = [];
                    var showMetadata = $('#' + generatorName + '_show_metadata').prop('checked');
                    var episodeMetadata = $('#' + generatorName + '_episode_metadata').prop('checked');
                    var fanart = $('#' + generatorName + '_fanart').prop('checked');
                    var poster = $('#' + generatorName + '_poster').prop('checked');
                    var banner = $('#' + generatorName + '_banner').prop('checked');
                    var episodeThumbnails = $('#' + generatorName + '_episode_thumbnails').prop('checked');
                    var seasonPosters = $('#' + generatorName + '_season_posters').prop('checked');
                    var seasonBanners = $('#' + generatorName + '_season_banners').prop('checked');
                    var seasonAllPoster = $('#' + generatorName + '_season_all_poster').prop('checked');
                    var seasonAllBanner = $('#' + generatorName + '_season_all_banner').prop('checked');

                    configArray.push(showMetadata ? '1' : '0');
                    configArray.push(episodeMetadata ? '1' : '0');
                    configArray.push(fanart ? '1' : '0');
                    configArray.push(poster ? '1' : '0');
                    configArray.push(banner ? '1' : '0');
                    configArray.push(episodeThumbnails ? '1' : '0');
                    configArray.push(seasonPosters ? '1' : '0');
                    configArray.push(seasonBanners ? '1' : '0');
                    configArray.push(seasonAllPoster ? '1' : '0');
                    configArray.push(seasonAllBanner ? '1' : '0');

                    var curNumber = 0;
                    for (var i = 0, len = configArray.length; i < len; i++) {
                        curNumber += parseInt(configArray[i], 10);
                    }
                    if (curNumber > curMost) {
                        curMost = curNumber;
                        curMostProvider = generatorName;
                    }

                    $('#' + generatorName + '_eg_show_metadata').prop('class', showMetadata ? 'enabled' : 'disabled');
                    $('#' + generatorName + '_eg_episode_metadata').prop('class', episodeMetadata ? 'enabled' : 'disabled');
                    $('#' + generatorName + '_eg_fanart').prop('class', fanart ? 'enabled' : 'disabled');
                    $('#' + generatorName + '_eg_poster').prop('class', poster ? 'enabled' : 'disabled');
                    $('#' + generatorName + '_eg_banner').prop('class', banner ? 'enabled' : 'disabled');
                    $('#' + generatorName + '_eg_episode_thumbnails').prop('class', episodeThumbnails ? 'enabled' : 'disabled');
                    $('#' + generatorName + '_eg_season_posters').prop('class', seasonPosters ? 'enabled' : 'disabled');
                    $('#' + generatorName + '_eg_season_banners').prop('class', seasonBanners ? 'enabled' : 'disabled');
                    $('#' + generatorName + '_eg_season_all_poster').prop('class', seasonAllPoster ? 'enabled' : 'disabled');
                    $('#' + generatorName + '_eg_season_all_banner').prop('class', seasonAllBanner ? 'enabled' : 'disabled');
                    $('#' + generatorName + '_data').val(configArray.join('|'));
                });

                if (curMostProvider !== '' && first) {
                    $('#metadataType option[value=' + curMostProvider + ']').prop('selected', true);
                    $(this).showHideMetadata();
                }
            };

            $(this).refreshMetadataConfig(true);
            $('img[title]').qtip({
                position: {
                    viewport: $(window),
                    at: 'bottom center',
                    my: 'top right'
                },
                style: {
                    tip: {
                        corner: true,
                        method: 'polygon'
                    },
                    classes: 'qtip-shadow qtip-dark'
                }
            });
            $('i[title]').qtip({
                position: {
                    viewport: $(window),
                    at: 'top center',
                    my: 'bottom center'
                },
                style: {
                    tip: {
                        corner: true,
                        method: 'polygon'
                    },
                    classes: 'qtip-rounded qtip-shadow ui-tooltip-sb'
                }
            });
            $('.custom-pattern,#unpack').qtip({
                content: 'validating...',
                show: {
                    event: false,
                    ready: false
                },
                hide: false,
                position: {
                    viewport: $(window),
                    at: 'center left',
                    my: 'center right'
                },
                style: {
                    tip: {
                        corner: true,
                        method: 'polygon'
                    },
                    classes: 'qtip-rounded qtip-shadow qtip-red'
                }
            });
        },
        search: function() {
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

                if (selectedProvider.toLowerCase() === 'blackhole') {
                    $(blackholeSettings).show();
                } else if (selectedProvider.toLowerCase() === 'nzbget') {
                    $(nzbgetSettings).show();
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
                $('#testSABnzbd_result').html(loading);
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

            $('#torrent_method').on('change', $.torrentMethodHandler);

            $.torrentMethodHandler();

            $('#test_torrent').on('click', function() {
                var torrent = {};
                $('#test_torrent_result').html(loading);
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
        },
        subtitles: function() {
            $.fn.showHideServices = function() {
                $('.serviceDiv').each(function() {
                    var serviceName = $(this).attr('id');
                    var selectedService = $('#editAService :selected').val();

                    if (selectedService + 'Div' === serviceName) {
                        $(this).show();
                    } else {
                        $(this).hide();
                    }
                });
            };

            $.fn.addService = function(id, name, url, key, isDefault, showService) {
                if (url.match('/$') === null) {
                    url += '/';
                }

                if ($('#service_order_list > #'+id).length === 0 && showService !== false) {
                    var toAdd = '<li class="ui-state-default" id="' + id + '"> <input type="checkbox" id="enable_' + id + '" class="service_enabler" CHECKED> <a href="' + anonRedirect + url + '" class="imgLink" target="_new"><img src="images/services/newznab.gif" alt="' + name + '" width="16" height="16"></a> ' + name + '</li>';

                    $('#service_order_list').append(toAdd);
                    $('#service_order_list').sortable('refresh');
                }
            };

            $.fn.deleteService = function(id) {
                $('#service_order_list > #' + id).remove();
            };

            $.refreshServiceList = function() {
                var idArr = $('#service_order_list').sortable('toArray');
                var finalArr = [];
                $.each(idArr, function(key, val) {
                    var checked = $('#enable_' + val).is(':checked') ? '1' : '0';
                    finalArr.push(val + ':' + checked);
                });
                $('#service_order').val(finalArr.join(' '));
            };

            $('#editAService').on('change', function() {
                $.showHideServices();
            });

            $('.service_enabler').on('click', function() {
                $.refreshServiceList();
            });

            // initialization stuff
            $(this).showHideServices();

            $('#service_order_list').sortable({
                placeholder: 'ui-state-highlight',
                update: function() {
                    $.refreshServiceList();
                },
                create: function() {
                    $.refreshServiceList();
                }
            });

            $('#service_order_list').disableSelection();
        },
        providers: function() {
            // @TODO This function need to be filled with ConfigProviders.js but can't be as we've got scope issues currently.
            console.log('This function need to be filled with ConfigProviders.js but can\'t be as we\'ve got scope issues currently.');
        }
    },
    home: {
        init: function() {

        },
        index: function() {
            // Resets the tables sorting, needed as we only use a single call for both tables in tablesorter
            $('.resetsorting').on('click', function() {
                $('table').trigger('filterReset');
            });

            // Handle filtering in the poster layout
            $('#filterShowName').on('input', _.debounce(function() {
                $('.show-grid').isotope({
                    filter: function () {
                        var name = $(this).attr('data-name').toLowerCase();
                        return name.indexOf($('#filterShowName').val().toLowerCase()) > -1;
                    }
                });
            }, 500));

            function resizePosters(newSize) {
                var fontSize;
                var logoWidth;
                var borderRadius;
                var borderWidth;
                if (newSize < 125) { // small
                    borderRadius = 3;
                    borderWidth = 4;
                } else if (newSize < 175) { // medium
                    fontSize = 9;
                    logoWidth = 40;
                    borderRadius = 4;
                    borderWidth = 5;
                } else { // large
                    fontSize = 11;
                    logoWidth = 50;
                    borderRadius = 6;
                    borderWidth = 6;
                }

                // If there's a poster popup, remove it before resizing
                $('#posterPopup').remove();

                if (fontSize === undefined) {
                    $('.show-details').hide();
                } else {
                    $('.show-details').show();
                    $('.show-dlstats, .show-quality').css('fontSize', fontSize);
                    $('.show-network-image').css('width', logoWidth);
                }

                $('.show-container').css({
                    width: newSize,
                    borderWidth: borderWidth,
                    borderRadius: borderRadius
                });
            }

            var posterSize;
            if (typeof (Storage) !== 'undefined') {
                posterSize = parseInt(localStorage.getItem('posterSize'), 10);
            }
            if (typeof (posterSize) !== 'number' || isNaN(posterSize)) {
                posterSize = 188;
            }
            resizePosters(posterSize);

            $('#posterSizeSlider').slider({
                min: 75,
                max: 250,
                value: posterSize,
                change: function (e, ui) {
                    if (typeof (Storage) !== 'undefined') {
                        localStorage.setItem('posterSize', ui.value);
                    }
                    resizePosters(ui.value);
                    $('.show-grid').isotope('layout');
                }
            });

            // This needs to be refined to work a little faster.
            $('.progressbar').each(function() {
                var percentage = $(this).data('progress-percentage');
                var classToAdd = percentage === 100 ? 100 : percentage > 80 ? 80 : percentage > 60 ? 60 : percentage > 40 ? 40 : 20; // eslint-disable-line no-nested-ternary
                $(this).progressbar({
                    value: percentage
                });
                if ($(this).data('progress-text')) {
                    $(this).append('<div class="progressbarText" title="' + $(this).data('progress-tip') + '">' + $(this).data('progress-text') + '</div>');
                }
                $(this).find('.ui-progressbar-value').addClass('progress-' + classToAdd);
            });

            $('img#network').on('error', function() {
                $(this).parent().text($(this).attr('alt'));
                $(this).remove();
            });

            $('#showListTableShows:has(tbody tr), #showListTableAnime:has(tbody tr)').tablesorter({
                sortList: [[7, 1], [2, 0]],
                textExtraction: {
                    0: function(node) { return $(node).find('time').attr('datetime'); }, // eslint-disable-line brace-style
                    1: function(node) { return $(node).find('time').attr('datetime'); }, // eslint-disable-line brace-style
                    3: function(node) { return $(node).find('span').prop('title').toLowerCase(); }, // eslint-disable-line brace-style
                    4: function(node) { return $(node).find('span').text().toLowerCase(); }, // eslint-disable-line brace-style
                    5: function(node) { return $(node).find('span:first').text(); }, // eslint-disable-line brace-style
                    6: function(node) { return $(node).data('show-size'); }, // eslint-disable-line brace-style
                    7: function(node) { return $(node).find('img').attr('alt'); } // eslint-disable-line brace-style
                },
                widgets: ['saveSort', 'zebra', 'stickyHeaders', 'filter', 'columnSelector'],
                headers: {
                    0: {sorter: 'realISODate'},
                    1: {sorter: 'realISODate'},
                    2: {sorter: 'loadingNames'},
                    4: {sorter: 'quality'},
                    5: {sorter: 'eps'},
                    6: {sorter: 'digit'},
                    7: {filter: 'parsed'}
                },
                widgetOptions: {
                    filter_columnFilters: true, // eslint-disable-line camelcase
                    filter_hideFilters: true, // eslint-disable-line camelcase
                    filter_saveFilters: true, // eslint-disable-line camelcase
                    filter_functions: { // eslint-disable-line camelcase
                        5: function(e, n, f) {
                            var test = false;
                            var pct = Math.floor((n % 1) * 1000);
                            if (f === '') {
                                test = true;
                            } else {
                                var result = f.match(/(<|<=|>=|>)\s+(\d+)/i);
                                if (result) {
                                    if (result[1] === '<') {
                                        if (pct < parseInt(result[2]), 10) {
                                            test = true;
                                        }
                                    } else if (result[1] === '<=') {
                                        if (pct <= parseInt(result[2]), 10) {
                                            test = true;
                                        }
                                    } else if (result[1] === '>=') {
                                        if (pct >= parseInt(result[2]), 10) {
                                            test = true;
                                        }
                                    } else if (result[1] === '>') {
                                        if (pct > parseInt(result[2]), 10) {
                                            test = true;
                                        }
                                    }
                                }

                                result = f.match(/(\d+)\s(-|to)\s+(\d+)/i);
                                if (result) {
                                    if ((result[2] === '-') || (result[2] === 'to')) {
                                        if ((pct >= parseInt(result[1], 10)) && (pct <= parseInt(result[3], 10))) {
                                            test = true;
                                        }
                                    }
                                }

                                result = f.match(/(=)?\s?(\d+)\s?(=)?/i);
                                if (result) {
                                    if ((result[1] === '=') || (result[3] === '=')) {
                                        if (parseInt(result[2], 10) === pct) {
                                            test = true;
                                        }
                                    }
                                }

                                if (!isNaN(parseFloat(f)) && isFinite(f)) {
                                    if (parseInt(f, 10) === pct) {
                                        test = true;
                                    }
                                }
                            }
                            return test;
                        }
                    },
                    'columnSelector_mediaquery': false
                },
                sortStable: true,
                sortAppend: [[2, 0]]
            });

            $('.show-grid').imagesLoaded(function () {
                $('.loading-spinner').hide();
                $('.show-grid').show().isotope({
                    itemSelector: '.show-container',
                    sortBy: SICKRAGE.info.posterSortby,
                    sortAscending: SICKRAGE.info.posterSortdir,
                    layoutMode: 'masonry',
                    masonry: {
                        isFitWidth: true
                    },
                    getSortData: {
                        name: function (itemElem) {
                            var name = $(itemElem).attr('data-name') || '';
                            return (SICKRAGE.info.sortArticle ? name : name.replace(/^((?:The|A|An)\s)/i, '')).toLowerCase();
                        },
                        network: '[data-network]',
                        date: function (itemElem) {
                            var date = $(itemElem).attr('data-date');
                            return date.length && parseInt(date, 10) || Number.POSITIVE_INFINITY;
                        },
                        progress: function (itemElem) {
                            var progress = $(itemElem).attr('data-progress');
                            return progress.length && parseInt(progress, 10) || Number.NEGATIVE_INFINITY;
                        }
                    }
                });

                // When posters are small enough to not display the .show-details
                // table, display a larger poster when hovering.
                var posterHoverTimer = null;
                $('.show-container').on('mouseenter', function () {
                    var poster = $(this);
                    if (poster.find('.show-details').css('display') !== 'none') {
                        return;
                    }
                    posterHoverTimer = setTimeout(function () {
                        posterHoverTimer = null;
                        $('#posterPopup').remove();
                        var popup = poster.clone().attr({
                            id: 'posterPopup'
                        });
                        var origLeft = poster.offset().left;
                        var origTop = poster.offset().top;
                        popup.css({
                            position: 'absolute',
                            margin: 0,
                            top: origTop,
                            left: origLeft
                        });
                        popup.find('.show-details').show();
                        popup.on('mouseleave', function () {
                            $(this).remove();
                        });
                        popup.zIndex(9999);
                        popup.appendTo('body');

                        var height = 438;
                        var width = 250;
                        var newTop = (origTop + (poster.height() / 2)) - (height / 2);
                        var newLeft = (origLeft + (poster.width() / 2)) - (width / 2);

                        // Make sure the popup isn't outside the viewport
                        var margin = 5;
                        var scrollTop = $(window).scrollTop();
                        var scrollLeft = $(window).scrollLeft();
                        var scrollBottom = scrollTop + $(window).innerHeight();
                        var scrollRight = scrollLeft + $(window).innerWidth();
                        if (newTop < scrollTop + margin) {
                            newTop = scrollTop + margin;
                        }
                        if (newLeft < scrollLeft + margin) {
                            newLeft = scrollLeft + margin;
                        }
                        if (newTop + height + margin > scrollBottom) {
                            newTop = scrollBottom - height - margin;
                        }
                        if (newLeft + width + margin > scrollRight) {
                            newLeft = scrollRight - width - margin;
                        }

                        popup.animate({
                            top: newTop,
                            left: newLeft,
                            width: 250,
                            height: 438
                        });
                    }, 300);
                }).on('mouseleave', function () {
                    if (posterHoverTimer !== null) {
                        clearTimeout(posterHoverTimer);
                    }
                });
            });

            $('#postersort').on('change', function() {
                $('.show-grid').isotope({sortBy: $(this).val()});
                $.get($(this).find('option[value=' + $(this).val() + ']').attr('data-sort'));
            });

            $('#postersortdirection').on('change', function() {
                $('.show-grid').isotope({sortAscending: ($(this).val() === 'true')});
                $.get($(this).find('option[value=' + $(this).val() + ']').attr('data-sort'));
            });

            $('#popover').popover({
                placement: 'bottom',
                html: true, // required if content has HTML
                content: '<div id="popover-target"></div>'
            }).on('shown.bs.popover', function () { // bootstrap popover event triggered when the popover opens
                // call this function to copy the column selection code into the popover
                $.tablesorter.columnSelector.attachTo($('#showListTableShows'), '#popover-target');
                if (SICKRAGE.info.animeSplitHome) {
                    $.tablesorter.columnSelector.attachTo($('#showListTableAnime'), '#popover-target');
                }
            });
        },
        displayShow: function() {
            if (SICKRAGE.info.fanartBackground) {
                $.backstretch('showPoster/?show=' + $('#showID').attr('value') + '&which=fanart');
                $('.backstretch').css('opacity', SICKRAGE.info.fanartBackgroundOpacity).fadeIn(500);
            }

            $.ajaxEpSearch({
                colorRow: true
            });

            $.ajaxEpSubtitlesSearch();

            $('#seasonJump').on('change', function() {
                var id = $('#seasonJump option:selected').val();
                if (id && id !== 'jump') {
                    var season = $('#seasonJump option:selected').data('season');
                    $('html,body').animate({scrollTop: $('[name ="' + id.substring(1) + '"]').offset().top - 50}, 'slow');
                    $('#collapseSeason-' + season).collapse('show');
                    location.hash = id;
                }
                $(this).val('jump');
            });

            $('#prevShow').on('click', function() {
                $('#pickShow option:selected').prev('option').prop('selected', true);
                $('#pickShow').change();
            });

            $('#nextShow').on('click', function() {
                $('#pickShow option:selected').next('option').prop('selected', true);
                $('#pickShow').change();
            });

            $('#changeStatus').on('click', function() {
                var epArr = [];

                $('.epCheck').each(function () {
                    if (this.checked === true) {
                        epArr.push($(this).attr('id'));
                    }
                });

                if (epArr.length === 0) {
                    return false;
                }

                window.location.href = 'home/setStatus?show=' + $('#showID').attr('value') + '&eps=' + epArr.join('|') + '&status=' + $('#statusSelect').val();
            });

            $('.seasonCheck').on('click', function() {
                var seasCheck = this;
                var seasNo = $(seasCheck).attr('id');

                $('#collapseSeason-' + seasNo).collapse('show');
                $('.epCheck:visible').each(function () {
                    var epParts = $(this).attr('id').split('x');
                    if (epParts[0] === seasNo) {
                        this.checked = seasCheck.checked;
                    }
                });
            });

            var lastCheck = null;
            $('.epCheck').on('click', function (event) {
                if (!lastCheck || !event.shiftKey) {
                    lastCheck = this;
                    return;
                }

                var check = this;
                var found = 0;

                $('.epCheck').each(function() {
                    if (found === 1) {
                        this.checked = lastCheck.checked;
                    }

                    if (found === 1) {
                        return false;
                    }

                    if (this === check || this === lastCheck) {
                        found++;
                    }
                });
            });

            // selects all visible episode checkboxes.
            $('.seriesCheck').on('click', function () {
                $('.epCheck:visible').each(function () {
                    this.checked = true;
                });
                $('.seasonCheck:visible').each(function () {
                    this.checked = true;
                });
            });

            // clears all visible episode checkboxes and the season selectors
            $('.clearAll').on('click', function () {
                $('.epCheck:visible').each(function () {
                    this.checked = false;
                });
                $('.seasonCheck:visible').each(function () {
                    this.checked = false;
                });
            });

            // handle the show selection dropbox
            $('#pickShow').on('change', function () {
                var val = $(this).val();
                if (val === 0) {
                    return;
                }
                window.location.href = 'home/displayShow?show=' + val;
            });

            // show/hide different types of rows when the checkboxes are changed
            $('#checkboxControls input').on('change', function () {
                var whichClass = $(this).attr('id');
                $(this).showHideRows(whichClass);
            });

            // initially show/hide all the rows according to the checkboxes
            $('#checkboxControls input').each(function() {
                var status = $(this).prop('checked');
                $('tr.' + $(this).attr('id')).each(function() {
                    if (status) {
                        $(this).show();
                    } else {
                        $(this).hide();
                    }
                });
            });

            $.fn.showHideRows = function(whichClass) {
                var status = $('#checkboxControls > input, #' + whichClass).prop('checked');
                $('tr.' + whichClass).each(function() {
                    if (status) {
                        $(this).show();
                    } else {
                        $(this).hide();
                    }
                });

                // hide season headers with no episodes under them
                $('tr.seasonheader').each(function () {
                    var numRows = 0;
                    var seasonNo = $(this).attr('id');
                    $('tr.' + seasonNo + ' :visible').each(function () {
                        numRows++;
                    });
                    if (numRows === 0) {
                        $(this).hide();
                        $('#' + seasonNo + '-cols').hide();
                    } else {
                        $(this).show();
                        $('#' + seasonNo + '-cols').show();
                    }
                });
            };

            function setEpisodeSceneNumbering(forSeason, forEpisode, sceneSeason, sceneEpisode) {
                var showId = $('#showID').val();
                var indexer = $('#indexer').val();

                if (sceneSeason === '') {
                    sceneSeason = null;
                }
                if (sceneEpisode === '') {
                    sceneEpisode = null;
                }

                $.getJSON('home/setSceneNumbering', {
                    show: showId,
                    indexer: indexer,
                    forSeason: forSeason,
                    forEpisode: forEpisode,
                    sceneSeason: sceneSeason,
                    sceneEpisode: sceneEpisode
                }, function(data) {
                    // Set the values we get back
                    if (data.sceneSeason === null || data.sceneEpisode === null) {
                        $('#sceneSeasonXEpisode_' + showId + '_' + forSeason + '_' + forEpisode).val('');
                    } else {
                        $('#sceneSeasonXEpisode_' + showId + '_' + forSeason + '_' + forEpisode).val(data.sceneSeason + 'x' + data.sceneEpisode);
                    }
                    if (!data.success) {
                        if (data.errorMessage) {
                            alert(data.errorMessage);
                        } else {
                            alert('Update failed.');
                        }
                    }
                });
            }

            function setAbsoluteSceneNumbering(forAbsolute, sceneAbsolute) {
                var showId = $('#showID').val();
                var indexer = $('#indexer').val();

                if (sceneAbsolute === '') {
                    sceneAbsolute = null;
                }

                $.getJSON('home/setSceneNumbering', {
                    show: showId,
                    indexer: indexer,
                    forAbsolute: forAbsolute,
                    sceneAbsolute: sceneAbsolute
                }, function(data) {
                    // Set the values we get back
                    if (data.sceneAbsolute === null) {
                        $('#sceneAbsolute_' + showId + '_' + forAbsolute).val('');
                    } else {
                        $('#sceneAbsolute_' + showId + '_' + forAbsolute).val(data.sceneAbsolute);
                    }

                    if (!data.success) {
                        if (data.errorMessage) {
                            alert(data.errorMessage);
                        } else {
                            alert('Update failed.');
                        }
                    }
                });
            }

            function setInputValidInvalid(valid, el) {
                if (valid) {
                    $(el).css({
                        'background-color': '#90EE90', // green
                        'color': '#FFF',
                        'font-weight': 'bold'
                    });
                    return true;
                }
                $(el).css({
                    'background-color': '#FF0000', // red
                    'color': '#FFF!important',
                    'font-weight': 'bold'
                });
                return false;
            }

            $('.sceneSeasonXEpisode').on('change', function() {
                // Strip non-numeric characters
                var value = $(this).val();
                $(this).val(value.replace(/[^0-9xX]*/g, ''));
                var forSeason = $(this).attr('data-for-season');
                var forEpisode = $(this).attr('data-for-episode');

                // If empty reset the field
                if (value === '') {
                    setEpisodeSceneNumbering(forSeason, forEpisode, null, null);
                    return;
                }

                var m = $(this).val().match(/^(\d+)x(\d+)$/i);
                var onlyEpisode = $(this).val().match(/^(\d+)$/i);
                var sceneSeason = null;
                var sceneEpisode = null;
                var isValid = false;
                if (m) {
                    sceneSeason = m[1];
                    sceneEpisode = m[2];
                    isValid = setInputValidInvalid(true, $(this));
                } else if (onlyEpisode) {
                    // For example when '5' is filled in instead of '1x5', asume it's the first season
                    sceneSeason = forSeason;
                    sceneEpisode = onlyEpisode[1];
                    isValid = setInputValidInvalid(true, $(this));
                } else {
                    isValid = setInputValidInvalid(false, $(this));
                }

                if (isValid) {
                    setEpisodeSceneNumbering(forSeason, forEpisode, sceneSeason, sceneEpisode);
                }
            });

            $('.sceneAbsolute').on('change', function() {
                // Strip non-numeric characters
                $(this).val($(this).val().replace(/[^0-9xX]*/g, ''));
                var forAbsolute = $(this).attr('data-for-absolute');

                var m = $(this).val().match(/^(\d{1,3})$/i);
                var sceneAbsolute = null;
                if (m) {
                    sceneAbsolute = m[1];
                }
                setAbsoluteSceneNumbering(forAbsolute, sceneAbsolute);
            });

            $('.addQTip').each(function () {
                $(this).css({'cursor': 'help', 'text-shadow': '0px 0px 0.5px #666'});
                $(this).qtip({
                    show: {solo: true},
                    position: {viewport: $(window), my: 'left center', adjust: {y: -10, x: 2}},
                    style: {tip: {corner: true, method: 'polygon'}, classes: 'qtip-rounded qtip-shadow ui-tooltip-sb'}
                });
            });

            $.fn.generateStars = function() {
                return this.each(function(i, e) {
                    $(e).html($('<span/>').width($(e).text() * 12));
                });
            };

            $('.imdbstars').generateStars();

            $('#showTable, #animeTable').tablesorter({
                widgets: ['saveSort', 'stickyHeaders', 'columnSelector'],
                widgetOptions: {
                    columnSelector_saveColumns: true, // eslint-disable-line camelcase
                    columnSelector_layout: '<br><label><input type="checkbox">{name}</label>', // eslint-disable-line camelcase
                    columnSelector_mediaquery: false, // eslint-disable-line camelcase
                    columnSelector_cssChecked: 'checked' // eslint-disable-line camelcase
                }
            });

            $('#popover').popover({
                placement: 'bottom',
                html: true, // required if content has HTML
                content: '<div id="popover-target"></div>'
            }).on('shown.bs.popover', function () { // bootstrap popover event triggered when the popover opens
                $.tablesorter.columnSelector.attachTo($('#showTable, #animeTable'), '#popover-target');
            });

            // Moved and rewritten this from displayShow. This changes the button when clicked for collapsing/expanding the
            // Season to Show Episodes or Hide Episodes.
            $(function() {
                $('.collapse.toggle').on('hide.bs.collapse', function () {
                    var reg = /collapseSeason-([0-9]+)/g;
                    var result = reg.exec(this.id);
                    $('#showseason-' + result[1]).text('Show Episodes');
                });
                $('.collapse.toggle').on('show.bs.collapse', function () {
                    var reg = /collapseSeason-([0-9]+)/g;
                    var result = reg.exec(this.id);
                    $('#showseason-' + result[1]).text('Hide Episodes');
                });
            });

            // Set the season exception based on using the get_xem_numbering_for_show() for animes if available in data.xemNumbering,
            // or else try to map using just the data.season_exceptions.
            function setSeasonSceneException(data) {
                $.each(data.seasonExceptions, function(season, nameExceptions) {
                    var foundInXem = false;
                    // Check if it is a season name exception, we don't handle the show name exceptions here
                    if (season >= 0) {
                        // Loop through the xem mapping, and check if there is a xem_season, that needs to show the season name exception
                        $.each(data.xemNumbering, function(indexerSeason, xemSeason) {
                            if (xemSeason === parseInt(season, 10)) {
                                foundInXem = true;
                                $('<img>', {
                                    id: 'xem-exception-season-' + xemSeason,
                                    alt: '[xem]',
                                    height: '16',
                                    width: '16',
                                    src: 'images/xem.png',
                                    title: nameExceptions.join(', ')
                                }).appendTo('[data-season=' + indexerSeason + ']');
                            }
                        });

                        // This is not a xem season exception, let's set the exceptions as a medusa exception
                        if (!foundInXem) {
                            $('<img>', {
                                id: 'xem-exception-season-' + season,
                                alt: '[medusa]',
                                height: '16',
                                width: '16',
                                src: 'images/ico/favicon-16.png',
                                title: nameExceptions.join(', ')
                            }).appendTo('[data-season=' + season + ']');
                        }
                    }
                });
            }

            // @TODO: OMG: This is just a basic json, in future it should be based on the CRUD route.
            // Get the season exceptions and the xem season mappings.
            $.getJSON('home/getSeasonSceneExceptions', {
                indexer: $('input#indexer').val(),
                indexer_id: $('input#showID').val() // eslint-disable-line camelcase
            }, function(data) {
                setSeasonSceneException(data);
            });
        },
        snatchSelection: function() {
            if (SICKRAGE.info.fanartBackground) {
                 $.backstretch('showPoster/?show=' + $('#showID').attr('value') + '&which=fanart');
                 $('.backstretch').css('opacity', SICKRAGE.info.fanartBackgroundOpacity).fadeIn(500);
            }
            var spinner = $('#searchNotification');
            var updateSpinner = function(spinner, message, showSpinner) {
                if (showSpinner) {
                    $(spinner).html('<img id="searchingAnim" src="images/loading32' + themeSpinner + '.gif" height="16" width="16" />&nbsp;' + message);
                } else {
                    $(spinner).empty().html(message);
                }
            };

            // Check the previous status of the history table, for hidden or shown, through the data attribute
            // data-history-toggle-hidden
            function toggleHistoryTable() {
                // Get previous state which was saved on the wrapper
                var showOrHide = $('#wrapper').attr('data-history-toggle');
                $('#historydata').collapse(showOrHide);
            }

            $.fn.loadContainer = function(path, loadingTxt, errorTxt, callback) {
                updateSpinner(spinner, loadingTxt);
                $(this).load(path + ' #container', function(response, status) {
                    if (status === 'error') {
                        updateSpinner(spinner, errorTxt, false);
                    }
                    if (typeof callback !== 'undefined') {
                        callback();
                    }
                });
            };

            // Click event for the download button for snatching a result
            $('body').on('click', '.epManualSearch', function(event) {
                event.preventDefault();
                var link = this;
                $(link).children('img').prop('src', 'images/loading16.gif');
                $.getJSON(this.href, function (data) {
                    if (data.result === 'success') {
                        $(link).children('img').prop('src', 'images/save.png');
                    } else {
                        $(link).children('img').prop('src', 'images/no16.png');
                    }
                });
            });

            $.fn.generateStars = function() {
                return this.each(function(i, e) {
                    $(e).html($('<span/>').width($(e).text() * 12));
                });
            };

            function initTableSorter(table) {
                // Nasty hack to re-initialize tablesorter after refresh
                $(table).tablesorter({
                    widthFixed: true,
                    widgets: ['saveSort', 'stickyHeaders', 'columnSelector', 'filter'],
                    widgetOptions: {
                        filter_columnFilters: true, // eslint-disable-line camelcase
                        filter_hideFilters: true, // eslint-disable-line camelcase
                        filter_saveFilters: true, // eslint-disable-line camelcase
                        columnSelector_saveColumns: true, // eslint-disable-line camelcase
                        columnSelector_layout: '<br><label><input type="checkbox">{name}</label>', // eslint-disable-line camelcase
                        columnSelector_mediaquery: false, // eslint-disable-line camelcase
                        columnSelector_cssChecked: 'checked' // eslint-disable-line camelcase
                    }
                });
            }

            $('.imdbstars').generateStars();

            function checkCacheUpdates(repeat) {
                var self = this;
                var pollInterval = 5000;
                repeat = repeat || true;

                var show = $('meta[data-last-prov-updates]').attr('data-show');
                var season = $('meta[data-last-prov-updates]').attr('data-season');
                var episode = $('meta[data-last-prov-updates]').attr('data-episode');
                var data = $('meta[data-last-prov-updates]').data('last-prov-updates');
                var manualSearchType = $('meta[data-last-prov-updates]').attr('data-manual-search-type');

                if (!$.isNumeric(show) || !$.isNumeric(season) || !$.isNumeric(episode)) {
                    setTimeout(function() {
                        checkCacheUpdates(true);
                    }, 200);
                }

                self.refreshResults = function() {
                    $('#wrapper').loadContainer(
                            'home/snatchSelection?show=' + show + '&season=' + season + '&episode=' + episode + '&manual_search_type=' + manualSearchType + '&perform_search=0',
                            'Loading new search results...',
                            'Time out, refresh page to try again',
                            toggleHistoryTable // This is a callback function
                    );
                };

                $.ajax({
                    url: 'home/manualSearchCheckCache?show=' + show + '&season=' + season + '&episode=' + episode + '&manual_search_type=' + manualSearchType,
                    type: 'GET',
                    data: data,
                    contentType: 'application/json',
                    success: function (data) {
                        if (data.result === 'refresh') {
                            self.refreshResults();
                            updateSpinner(spinner, 'Refreshed results...', true);
                            initTableSorter('#showTable');
                        }
                        if (data.result === 'searching') {
                            // ep is searched, you will get a results any minute now
                            pollInterval = 5000;
                            $('.manualSearchButton').prop('disabled', true);
                            updateSpinner(spinner, 'The episode is being searched, please wait......', true);
                            initTableSorter('#showTable');
                        }
                        if (data.result === 'queued') {
                            // ep is queued, this might take some time to get results
                            pollInterval = 7000;
                            $('.manualSearchButton').prop('disabled', true);
                            updateSpinner(spinner, 'The episode has been queued, because another search is taking place. please wait..', true);
                            initTableSorter('#showTable');
                        }
                        if (data.result === 'finished') {
                            // ep search is finished
                            updateSpinner(spinner, 'Search finished', false);
                            $('.manualSearchButton').removeAttr('disabled');
                            repeat = false;
                            initTableSorter('#showTable');
                        }
                        if (data.result === 'error') {
                            // ep search is finished
                            console.log('Probably tried to call manualSelectCheckCache, while page was being refreshed.');
                            $('.manualSearchButton').removeAttr('disabled');
                            repeat = true;
                            initTableSorter('#showTable');
                        }
                    },
                    error: function () {
                        // repeat = false;
                        console.log('Error occurred!!');
                        $('.manualSearchButton').removeAttr('disabled');
                    },
                    complete: function () {
                        if (repeat) {
                            setTimeout(checkCacheUpdates, pollInterval);
                        }
                    },
                    timeout: 15000 // timeout after 15s
                });
            }

            setTimeout(checkCacheUpdates, 2000);

            // Click event for the reload results and force search buttons
            $('body').on('click', '.manualSearchButton', function(event) {
                event.preventDefault();
                $('.manualSearchButton').prop('disabled', true);
                var show = $('meta[data-last-prov-updates]').attr('data-show');
                var season = $('meta[data-last-prov-updates]').attr('data-season');
                var episode = $('meta[data-last-prov-updates]').attr('data-episode');
                var manualSearchType = $('meta[data-last-prov-updates]').attr('data-manual-search-type');
                var forceSearch = $(this).attr('data-force-search');

                if ($.isNumeric(show) && $.isNumeric(season) && $.isNumeric(episode)) {
                    updateSpinner(spinner, 'Started a forced manual search...', true);
                    $.getJSON('home/snatchSelection', {
                        show: show,
                        season: season,
                        episode: episode,
                        manual_search_type: manualSearchType, // eslint-disable-line camelcase
                        perform_search: forceSearch // eslint-disable-line camelcase
                    });
                    // Force the search, but give the checkCacheUpdates the time to start up a search thread
                    setTimeout(function() {
                        checkCacheUpdates(true);
                    }, 2000);
                }
            });

            // Moved and rewritten this from displayShow. This changes the button when clicked for collapsing/expanding the
            // "Show History" button to show or hide the snatch/download/failed history for a manual searched episode or pack.
            initTableSorter('#showTable');

            $('#popover').popover({
                placement: 'bottom',
                html: true, // required if content has HTML
                content: '<div id="popover-target"></div>'
            }).on('shown.bs.popover', function () { // bootstrap popover event triggered when the popover opens
                $.tablesorter.columnSelector.attachTo($('#showTable'), '#popover-target');
            });

            $('#btnReset').click(function() {
                $('#showTable')
                .trigger('saveSortReset') // clear saved sort
                .trigger('sortReset');    // reset current table sort
                return false;
            });

            $(function() {
                $('body').on('hide.bs.collapse', '.collapse.toggle', function () {
                    $('#showhistory').text('Show History');
                    $('#wrapper').prop('data-history-toggle', 'hide');
                });
                $('body').on('show.bs.collapse', '.collapse.toggle', function () {
                    $('#showhistory').text('Hide History');
                    $('#wrapper').prop('data-history-toggle', 'show');
                });
            });
        },
        postProcess: function() {
            $('#episodeDir').fileBrowser({
                title: 'Select Unprocessed Episode Folder',
                key: 'postprocessPath'
            });
        },
        status: function() {
            $('#schedulerStatusTable').tablesorter({
                widgets: ['saveSort', 'zebra'],
                textExtraction: {
                    5: function(node) {
                        return $(node).data('seconds');
                    },
                    6: function(node) {
                        return $(node).data('seconds');
                    }
                },
                headers: {
                    5: {
                        sorter: 'digit'
                    },
                    6: {
                        sorter: 'digit'
                    }
                }
            });
            $('#queueStatusTable').tablesorter({
                widgets: ['saveSort', 'zebra'],
                sortList: [[3, 0], [4, 0], [2, 1]]
            });
        },
        restart: function() {
            var currentPid = $('.messages').attr('current-pid');
            var defaultPage = $('.messages').attr('default-page');
            var checkIsAlive = setInterval(function() {
                $.get('home/is_alive/', function(data) {
                    if (data.msg.toLowerCase() === 'nope') {
                        // if it's still initializing then just wait and try again
                        $('#restart_message').show();
                    } else if (currentPid === '' || data.msg === currentPid) {
                        $('#shut_down_loading').hide();
                        $('#shut_down_success').show();
                        currentPid = data.msg;
                    } else {
                        clearInterval(checkIsAlive);
                        $('#restart_loading').hide();
                        $('#restart_success').show();
                        $('#refresh_message').show();
                        setTimeout(function() {
                            window.location = defaultPage + '/';
                        }, 5000);
                    }
                }, 'jsonp');
            }, 100);
        },
        editShow: function() {
            if (SICKRAGE.info.fanartBackground) {
                $.backstretch('showPoster/?show=' + $('#show').attr('value') + '&which=fanart');
                $('.backstretch').css('opacity', SICKRAGE.info.fanartBackgroundOpacity).fadeIn(500);
            }
        }
    },
    manage: {
        init: function() {
            $.makeEpisodeRow = function(indexerId, season, episode, name, checked) {
                var row = '';
                row += ' <tr class="' + $('#row_class').val() + ' show-' + indexerId + '">';
                row += '  <td class="tableleft" align="center"><input type="checkbox" class="' + indexerId + '-epcheck" name="' + indexerId + '-' + season + 'x' + episode + '"' + (checked ? ' checked' : '') + '></td>';
                row += '  <td>' + season + 'x' + episode + '</td>';
                row += '  <td class="tableright" style="width: 100%">' + name + '</td>';
                row += ' </tr>';

                return row;
            };

            $.makeSubtitleRow = function(indexerId, season, episode, name, subtitles, checked) {
                var row = '';
                row += '<tr class="good show-' + indexerId + '">';
                row += '<td align="center"><input type="checkbox" class="' + indexerId + '-epcheck" name="' + indexerId + '-' + season + 'x' + episode + '"' + (checked ? ' checked' : '') + '></td>';
                row += '<td style="width: 2%;">' + season + 'x' + episode + '</td>';
                if (subtitles.length > 0) {
                    row += '<td style="width: 8%;">';
                    subtitles = subtitles.split(',');
                    for (var i in subtitles) {
                        if ({}.hasOwnProperty.call(subtitles, i)) {
                            row += '<img src="images/subtitles/flags/' + subtitles[i] + '.png" width="16" height="11" alt="' + subtitles[i] + '" />&nbsp;';
                        }
                    }
                    row += '</td>';
                } else {
                    row += '<td style="width: 8%;">None</td>';
                }
                row += '<td>' + name + '</td>';
                row += '</tr>';

                return row;
            };
        },
        index: function() {
            $('.resetsorting').on('click', function() {
                $('table').trigger('filterReset');
            });

            $('#massUpdateTable:has(tbody tr)').tablesorter({
                sortList: [[1, 0]],
                textExtraction: {
                    2: function(node) { return $(node).find('span').text().toLowerCase(); }, // eslint-disable-line brace-style
                    3: function(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
                    4: function(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
                    5: function(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
                    6: function(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
                    7: function(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
                    8: function(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
                    9: function(node) { return $(node).find('img').attr('alt'); } // eslint-disable-line brace-style
                },
                widgets: ['zebra', 'filter', 'columnSelector'],
                headers: {
                    0: {sorter: false, filter: false},
                    1: {sorter: 'showNames'},
                    2: {sorter: 'quality'},
                    3: {sorter: 'sports'},
                    4: {sorter: 'scene'},
                    5: {sorter: 'anime'},
                    6: {sorter: 'flatfold'},
                    7: {sorter: 'paused'},
                    8: {sorter: 'subtitle'},
                    9: {sorter: 'default_ep_status'},
                    10: {sorter: 'status'},
                    11: {sorter: false},
                    12: {sorter: false},
                    13: {sorter: false},
                    14: {sorter: false},
                    15: {sorter: false},
                    16: {sorter: false}
                },
                widgetOptions: {
                    columnSelector_mediaquery: false // eslint-disable-line camelcase
                }
            });
            $('#popover').popover({
                placement: 'bottom',
                html: true, // required if content has HTML
                content: '<div id="popover-target"></div>'
            }).on('shown.bs.popover', function () { // bootstrap popover event triggered when the popover opens
                // call this function to copy the column selection code into the popover
                $.tablesorter.columnSelector.attachTo($('#massUpdateTable'), '#popover-target');
            });
        },
        backlogOverview: function() {
            $('#pickShow').on('change', function() {
                var id = $(this).val();
                if (id) {
                    $('html,body').animate({scrollTop: $('#show-' + id).offset().top - 25}, 'slow');
                }
            });
        },
        failedDownloads: function() {
            $('#failedTable:has(tbody tr)').tablesorter({
                widgets: ['zebra'],
                sortList: [[0, 0]],
                headers: {3: {sorter: false}}
            });
            $('#limit').on('change', function() {
                window.location.href = 'manage/failedDownloads/?limit=' + $(this).val();
            });

            $('#submitMassRemove').on('click', function() {
                var removeArr = [];

                $('.removeCheck').each(function() {
                    if (this.checked === true) {
                        removeArr.push($(this).attr('id').split('-')[1]);
                    }
                });

                if (removeArr.length === 0) {
                    return false;
                }

                window.location.href = 'manage/failedDownloads?toRemove=' + removeArr.join('|');
            });

            if ($('.removeCheck').length) {
                $('.removeCheck').each(function(name) {
                    var lastCheck = null;
                    $(name).click(function(event) {
                        if (!lastCheck || !event.shiftKey) {
                            lastCheck = this;
                            return;
                        }

                        var check = this;
                        var found = 0;

                        $(name + ':visible').each(function() {
                            if (found === 1) {
                                this.checked = lastCheck.checked;
                            }
                            if (found === 2) {
                                return false;
                            }

                            if (this === check || this === lastCheck) {
                                found++;
                            }
                        });
                    });
                });
            }
        },
        massEdit: function() {
            $('#location').fileBrowser({title: 'Select Show Location'});
        },
        episodeStatuses: function() {
            $('.allCheck').on('click', function() {
                var indexerId = $(this).attr('id').split('-')[1];
                $('.' + indexerId + '-epcheck').prop('checked', $(this).prop('checked'));
            });

            $('.get_more_eps').on('click', function() {
                var curIndexerId = $(this).attr('id');
                var checked = $('#allCheck-' + curIndexerId).prop('checked');
                var lastRow = $('tr#' + curIndexerId);
                var clicked = $(this).attr('data-clicked');
                var action = $(this).attr('value');

                if (clicked) {
                    if (action.toLowerCase() === 'collapse') {
                        $('table tr').filter('.show-' + curIndexerId).hide();
                        $(this).prop('value', 'Expand');
                    } else if (action.toLowerCase() === 'expand') {
                        $('table tr').filter('.show-' + curIndexerId).show();
                        $(this).prop('value', 'Collapse');
                    }
                } else {
                    $.getJSON('manage/showEpisodeStatuses', {
                        indexer_id: curIndexerId, // eslint-disable-line camelcase
                        whichStatus: $('#oldStatus').val()
                    }, function (data) {
                        $.each(data, function(season, eps) {
                            $.each(eps, function(episode, name) {
                                lastRow.after($.makeEpisodeRow(curIndexerId, season, episode, name, checked));
                            });
                        });
                    });
                    $(this).prop('data-clicked', 1);
                    $(this).prop('value', 'Collapse');
                }
            });

            // selects all visible episode checkboxes.
            $('.selectAllShows').on('click', function() {
                $('.allCheck').each(function() {
                    this.checked = true;
                });
                $('input[class*="-epcheck"]').each(function() {
                    this.checked = true;
                });
            });

            // clears all visible episode checkboxes and the season selectors
            $('.unselectAllShows').on('click', function() {
                $('.allCheck').each(function() {
                    this.checked = false;
                });
                $('input[class*="-epcheck"]').each(function() {
                    this.checked = false;
                });
            });
        },
        subtitleMissed: function() {
            $('.allCheck').on('click', function() {
                var indexerId = $(this).attr('id').split('-')[1];
                $('.' + indexerId + '-epcheck').prop('checked', $(this).prop('checked'));
            });

            $('.get_more_eps').on('click', function() {
                var indexerId = $(this).attr('id');
                var checked = $('#allCheck-' + indexerId).prop('checked');
                var lastRow = $('tr#' + indexerId);
                var clicked = $(this).attr('data-clicked');
                var action = $(this).attr('value');

                if (clicked) {
                    if (action === 'Collapse') {
                        $('table tr').filter('.show-' + indexerId).hide();
                        $(this).prop('value', 'Expand');
                    } else if (action === 'Expand') {
                        $('table tr').filter('.show-' + indexerId).show();
                        $(this).prop('value', 'Collapse');
                    }
                } else {
                    $.getJSON('manage/showSubtitleMissed', {
                        indexer_id: indexerId, // eslint-disable-line camelcase
                        whichSubs: $('#selectSubLang').val()
                    }, function(data) {
                        $.each(data, function(season, eps) {
                            $.each(eps, function(episode, data) {
                                lastRow.after($.makeSubtitleRow(indexerId, season, episode, data.name, data.subtitles, checked));
                            });
                        });
                    });
                    $(this).prop('data-clicked', 1);
                    $(this).prop('value', 'Collapse');
                }
            });

            // selects all visible episode checkboxes.
            $('.selectAllShows').on('click', function() {
                $('.allCheck').each(function() {
                    this.checked = true;
                });
                $('input[class*="-epcheck"]').each(function() {
                    this.checked = true;
                });
            });

            // clears all visible episode checkboxes and the season selectors
            $('.unselectAllShows').on('click', function() {
                $('.allCheck').each(function() {
                    this.checked = false;
                });
                $('input[class*="-epcheck"]').each(function() {
                    this.checked = false;
                });
            });
        }
    },
    history: {
        init: function() {

        },
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
        init: function() {

        },
        index: function() {

        },
        viewlogs: function() {
            $('#minLevel,#logFilter,#logSearch').on('keyup change', _.debounce(function () {
                if ($('#logSearch').val().length > 0) {
                    $('#logFilter option[value="<NONE>"]').prop('selected', true);
                    $('#minLevel option[value=5]').prop('selected', true);
                }
                $('#minLevel').prop('disabled', true);
                $('#logFilter').prop('disabled', true);
                document.body.style.cursor = 'wait';
                var params = $.param({
                    minLevel: $('select[name=minLevel]').val(),
                    logFilter: $('select[name=logFilter]').val(),
                    logSearch: $('#logSearch').val()
                });
                $.get('errorlogs/viewlog/?' + params, function(data) {
                    history.pushState('data', '', 'errorlogs/viewlog/?' + params);
                    $('pre').html($(data).find('pre').html());
                    $('#minLevel').prop('disabled', false);
                    $('#logFilter').prop('disabled', false);
                    document.body.style.cursor = 'default';
                });
            }, 500));
        }
    },
    schedule: {
        init: function() {

        },
        index: function() {
            if (isMeta('comingEpsLayout', ['list'])) {
                var sortCodes = {
                    date: 0,
                    show: 2,
                    network: 5
                };
                var sort = SICKRAGE.info.comingEpsSort;
                var sortList = (sort in sortCodes) ? [[sortCodes[sort], 0]] : [[0, 0]];

                $('#showListTable:has(tbody tr)').tablesorter({
                    widgets: ['stickyHeaders', 'filter', 'columnSelector', 'saveSort'],
                    sortList: sortList,
                    textExtraction: {
                        0: function(node) { return $(node).find('time').attr('datetime'); },
                        1: function(node) { return $(node).find('time').attr('datetime'); },
                        7: function(node) { return $(node).find('span').text().toLowerCase(); }
                    },
                    headers: {
                        0: {sorter: 'realISODate'},
                        1: {sorter: 'realISODate'},
                        2: {sorter: 'loadingNames'},
                        4: {sorter: 'loadingNames'},
                        7: {sorter: 'quality'},
                        8: {sorter: false},
                        9: {sorter: false}
                    },
                    widgetOptions: {
                        filter_columnFilters: true, // eslint-disable-line camelcase
                        filter_hideFilters: true, // eslint-disable-line camelcase
                        filter_saveFilters: true, // eslint-disable-line camelcase
                        columnSelector_mediaquery: false // eslint-disable-line camelcase
                    }
                });

                $.ajaxEpSearch();
            }

            if (isMeta('comingEpsLayout', ['banner', 'poster'])) {
                $.ajaxEpSearch({
                    size: 16,
                    loadingImage: 'loading16' + themeSpinner + '.gif'
                });
                $('.ep_summary').hide();
                $('.ep_summaryTrigger').on('click', function() {
                    $(this).next('.ep_summary').slideToggle('normal', function() {
                        $(this).prev('.ep_summaryTrigger').prop('src', function(i, src) {
                            return $(this).next('.ep_summary').is(':visible') ? src.replace('plus', 'minus') : src.replace('minus', 'plus');
                        });
                    });
                });
            }

            $('#popover').popover({
                placement: 'bottom',
                html: true, // required if content has HTML
                content: '<div id="popover-target"></div>'
            }).on('shown.bs.popover', function () { // bootstrap popover event triggered when the popover opens
                // call this function to copy the column selection code into the popover
                $.tablesorter.columnSelector.attachTo($('#showListTable'), '#popover-target');
            });
        }
    },
    addShows: {
        init: function() {
            $('#tabs').tabs({
                collapsible: true,
                selected: (SICKRAGE.info.sortArticle ? -1 : 0)
            });

            $.initRemoteShowGrid = function() {
                // Set defaults on page load
                $('#showsort').val('original');
                $('#showsortdirection').val('asc');

                $('#showsort').on('change', function() {
                    var sortCriteria;
                    switch (this.value) {
                        case 'original':
                            sortCriteria = 'original-order';
                            break;
                        case 'rating':
                            /* randomise, else the rating_votes can already
                             * have sorted leaving this with nothing to do.
                             */
                            $('#container').isotope({sortBy: 'random'});
                            sortCriteria = 'rating';
                            break;
                        case 'rating_votes':
                            sortCriteria = ['rating', 'votes'];
                            break;
                        case 'votes':
                            sortCriteria = 'votes';
                            break;
                        default:
                            sortCriteria = 'name';
                            break;
                    }
                    $('#container').isotope({
                        sortBy: sortCriteria
                    });
                });

                $('#showsortdirection').on('change', function() {
                    $('#container').isotope({
                        sortAscending: (this.value === 'asc')
                    });
                });

                $('#container').isotope({
                    sortBy: 'original-order',
                    layoutMode: 'fitRows',
                    getSortData: {
                        name: function(itemElem) {
                            var name = $(itemElem).attr('data-name') || '';
                            return (SICKRAGE.info.sortArticle ? name : name.replace(/^((?:The|A|An)\s)/i, '')).toLowerCase();
                        },
                        rating: '[data-rating] parseInt',
                        votes: '[data-votes] parseInt'
                    }
                });
            };

            $.fn.loadRemoteShows = function(path, loadingTxt, errorTxt) {
                $(this).html('<img id="searchingAnim" src="images/loading32' + themeSpinner + '.gif" height="32" width="32" />&nbsp;' + loadingTxt);
                $(this).load(path + ' #container', function(response, status) {
                    if (status === 'error') {
                        $(this).empty().html(errorTxt);
                    } else {
                        $.initRemoteShowGrid();
                    }
                });
            };

            /*
             * Blacklist a show by indexer and indexer_id
             */
            $.initBlackListShowById = function() {
                $(document.body).on('click', 'button[data-blacklist-show]', function(e) {
                    e.preventDefault();

                    if ($(this).is(':disabled')) {
                        return false;
                    }

                    $(this).html('Blacklisted').prop('disabled', true);
                    $(this).parent().find('button[data-add-show]').prop('disabled', true);

                    $.get('addShows/addShowToBlacklist?indexer_id=' + $(this).attr('data-indexer-id'));
                    return false;
                });
            };

            /*
             * Adds show by indexer and indexer_id with a number of optional parameters
             * The show can be added as an anime show by providing the data attribute: data-isanime="1"
             */
            $.initAddShowById = function() {
                $(document.body).on('click', 'button[data-add-show]', function(e) {
                    e.preventDefault();

                    if ($(this).is(':disabled')) {
                        return false;
                    }

                    $(this).html('Added').prop('disabled', true);
                    $(this).parent().find('button[data-blacklist-show]').prop('disabled', true);

                    var anyQualArray = [];
                    var bestQualArray = [];
                    $('#anyQualities option:selected').each(function (i, d) {
                        anyQualArray.push($(d).val());
                    });
                    $('#bestQualities option:selected').each(function (i, d) {
                        bestQualArray.push($(d).val());
                    });

                    // If we are going to add an anime, let's by default configure it as one
                    var anime = $('#anime').prop('checked');
                    var configureShowOptions = $('#configure_show_options').prop('checked');

                    $.get('addShows/addShowByID?indexer_id=' + $(this).attr('data-indexer-id'), {
                        root_dir: $('#rootDirs option:selected').val(), // eslint-disable-line camelcase
                        configure_show_options: configureShowOptions, // eslint-disable-line camelcase
                        indexer: $(this).attr('data-indexer'),
                        show_name: $(this).attr('data-show-name'), // eslint-disable-line camelcase
                        quality_preset: $('#qualityPreset').val(), // eslint-disable-line camelcase
                        default_status: $('#statusSelect').val(), // eslint-disable-line camelcase
                        any_qualities: anyQualArray.join(','), // eslint-disable-line camelcase
                        best_qualities: bestQualArray.join(','), // eslint-disable-line camelcase
                        default_flatten_folders: $('#flatten_folders').prop('checked'), // eslint-disable-line camelcase
                        subtitles: $('#subtitles').prop('checked'),
                        anime: anime,
                        scene: $('#scene').prop('checked'),
                        default_status_after: $('#statusSelectAfter').val() // eslint-disable-line camelcase
                    });
                    return false;
                });

                $('#saveDefaultsButton').on('click', function() {
                    var anyQualArray = [];
                    var bestQualArray = [];
                    $('#anyQualities option:selected').each(function (i, d) {
                        anyQualArray.push($(d).val());
                    });
                    $('#bestQualities option:selected').each(function (i, d) {
                        bestQualArray.push($(d).val());
                    });

                    $.get('config/general/saveAddShowDefaults', {
                        defaultStatus: $('#statusSelect').val(),
                        anyQualities: anyQualArray.join(','),
                        bestQualities: bestQualArray.join(','),
                        defaultFlattenFolders: $('#flatten_folders').prop('checked'),
                        subtitles: $('#subtitles').prop('checked'),
                        anime: $('#anime').prop('checked'),
                        scene: $('#scene').prop('checked'),
                        defaultStatusAfter: $('#statusSelectAfter').val()
                    });

                    $(this).prop('disabled', true);
                    new PNotify({
                        title: 'Saved Defaults',
                        text: 'Your "add show" defaults have been set to your current selections.',
                        shadow: false
                    });
                });

                $('#statusSelect, #qualityPreset, #flatten_folders, #anyQualities, #bestQualities, #subtitles, #scene, #anime, #statusSelectAfter').change(function () {
                    $('#saveDefaultsButton').prop('disabled', false);
                });

                $('#qualityPreset').on('change', function() {
                    // fix issue #181 - force re-render to correct the height of the outer div
                    $('span.prev').click();
                    $('span.next').click();
                });
            };
            $.updateBlackWhiteList = function (showName) {
                $('#white').children().remove();
                $('#black').children().remove();
                $('#pool').children().remove();

                if ($('#anime').prop('checked') && showName) {
                    $('#blackwhitelist').show();
                    if (showName) {
                        $.getJSON('home/fetch_releasegroups', {
                            show_name: showName // eslint-disable-line camelcase
                        }, function (data) {
                            if (data.result === 'success') {
                                $.each(data.groups, function(i, group) {
                                    var option = $('<option>');
                                    option.prop('value', group.name);
                                    option.html(group.name + ' | ' + group.rating + ' | ' + group.range);
                                    option.appendTo('#pool');
                                });
                            }
                        });
                    }
                } else {
                    $('#blackwhitelist').hide();
                }
            };
        },
        index: function() {

        },
        newShow: function() {
            function updateSampleText() {
                // if something's selected then we have some behavior to figure out

                var showName;
                var sepChar;
                // if they've picked a radio button then use that
                if ($('input:radio[name=whichSeries]:checked').length) {
                    showName = $('input:radio[name=whichSeries]:checked').val().split('|')[4];
                } else if ($('input:hidden[name=whichSeries]').length && $('input:hidden[name=whichSeries]').val().length) { // if we provided a show in the hidden field, use that
                    showName = $('#providedName').val();
                } else {
                    showName = '';
                }
                $.updateBlackWhiteList(showName);
                var sampleText = 'Adding show <b>' + showName + '</b> into <b>';

                // if we have a root dir selected, figure out the path
                if ($('#rootDirs option:selected').length) {
                    var rootDirectoryText = $('#rootDirs option:selected').val();
                    if (rootDirectoryText.indexOf('/') >= 0) {
                        sepChar = '/';
                    } else if (rootDirectoryText.indexOf('\\') >= 0) {
                        sepChar = '\\';
                    } else {
                        sepChar = '';
                    }

                    if (rootDirectoryText.substr(sampleText.length - 1) !== sepChar) {
                        rootDirectoryText += sepChar;
                    }
                    rootDirectoryText += '<i>||</i>' + sepChar;

                    sampleText += rootDirectoryText;
                } else if ($('#fullShowPath').length && $('#fullShowPath').val().length) {
                    sampleText += $('#fullShowPath').val();
                } else {
                    sampleText += 'unknown dir.';
                }

                sampleText += '</b>';

                // if we have a show name then sanitize and use it for the dir name
                if (showName.length) {
                    $.get('addShows/sanitizeFileName', {name: showName}, function (data) {
                        $('#displayText').html(sampleText.replace('||', data));
                    });
                // if not then it's unknown
                } else {
                    $('#displayText').html(sampleText.replace('||', '??'));
                }

                // also toggle the add show button
                if (($('#rootDirs option:selected').length || ($('#fullShowPath').length && $('#fullShowPath').val().length)) && ($('input:radio[name=whichSeries]:checked').length) || ($('input:hidden[name=whichSeries]').length && $('input:hidden[name=whichSeries]').val().length)) {
                    $('#addShowButton').prop('disabled', false);
                } else {
                    $('#addShowButton').prop('disabled', true);
                }
            }

            var searchRequestXhr = null;
            function searchIndexers() {
                if (!$('#nameToSearch').val().length) {
                    return;
                }

                if (searchRequestXhr) {
                    searchRequestXhr.abort();
                }

                var searchingFor = $('#nameToSearch').val().trim() + ' on ' + $('#providedIndexer option:selected').text() + ' in ' + $('#indexerLangSelect').val();
                $('#searchResults').empty().html('<img id="searchingAnim" src="images/loading32' + themeSpinner + '.gif" height="32" width="32" /> searching ' + searchingFor + '...');

                searchRequestXhr = $.ajax({
                    url: 'addShows/searchIndexersForShowName',
                    data: {
                        search_term: $('#nameToSearch').val().trim(), // eslint-disable-line camelcase
                        lang: $('#indexerLangSelect').val(),
                        indexer: $('#providedIndexer').val()
                    },
                    timeout: parseInt($('#indexer_timeout').val(), 10) * 1000,
                    dataType: 'json',
                    error: function () {
                        $('#searchResults').empty().html('search timed out, try again or try another indexer');
                    },
                    success: function (data) {
                        var firstResult = true;
                        var resultStr = '<fieldset>\n<legend class="legendStep">Search Results:</legend>\n';
                        var checked = '';

                        if (data.results.length === 0) {
                            resultStr += '<b>No results found, try a different search.</b>';
                        } else {
                            $.each(data.results, function(index, obj) {
                                if (firstResult) {
                                    checked = ' checked';
                                    firstResult = false;
                                } else {
                                    checked = '';
                                }

                                var whichSeries = obj.join('|');

                                resultStr += '<input type="radio" id="whichSeries" name="whichSeries" value="' + whichSeries.replace(/"/g, '') + '"' + checked + ' /> ';
                                if (data.langid && data.langid !== '') {
                                    resultStr += '<a href="' + anonRedirect + obj[2] + obj[3] + '&lid=' + data.langid + '" onclick=\"window.open(this.href, \'_blank\'); return false;\" ><b>' + obj[4] + '</b></a>';
                                } else {
                                    resultStr += '<a href="' + anonRedirect + obj[2] + obj[3] + '" onclick=\"window.open(this.href, \'_blank\'); return false;\" ><b>' + obj[4] + '</b></a>';
                                }

                                if (obj[5] !== null) {
                                    var startDate = new Date(obj[5]);
                                    var today = new Date();
                                    if (startDate > today) {
                                        resultStr += ' (will debut on ' + obj[5] + ')';
                                    } else {
                                        resultStr += ' (started on ' + obj[5] + ')';
                                    }
                                }

                                if (obj[0] !== null) {
                                    resultStr += ' [' + obj[0] + ']';
                                }

                                resultStr += '<br>';
                            });
                            resultStr += '</ul>';
                        }
                        resultStr += '</fieldset>';
                        $('#searchResults').html(resultStr);
                        updateSampleText();
                        myform.loadsection(0);
                    }
                });
            }

            $('#searchName').on('click', function () {
                searchIndexers();
            });

            if ($('#nameToSearch').length && $('#nameToSearch').val().length) {
                $('#searchName').click();
            }

            $('#addShowButton').click(function () {
                // if they haven't picked a show don't let them submit
                if (!$('input:radio[name="whichSeries"]:checked').val() && !$('input:hidden[name="whichSeries"]').val().length) {
                    alert('You must choose a show to continue');
                    return false;
                }
                generateBlackWhiteList();
                $('#addShowForm').submit();
            });

            $('#skipShowButton').click(function () {
                $('#skipShow').val('1');
                $('#addShowForm').submit();
            });

            $('#qualityPreset').on('change', function () {
                myform.loadsection(2);
            });

            /** *********************************************
            * jQuery Form to Form Wizard- (c) Dynamic Drive (www.dynamicdrive.com)
            * This notice MUST stay intact for legal use
            * Visit http://www.dynamicdrive.com/ for this script and 100s more.
            ***********************************************/

            function goToStep(num) {
                $('.step').each(function () {
                    if ($.data(this, 'section') + 1 === num) {
                        $(this).click();
                    }
                });
            }

            $('#nameToSearch').focus();

            // @TODO we need to move to real forms instead of this
            var myform = new formtowizard({
                formid: 'addShowForm',
                revealfx: ['slide', 500],
                oninit: function () {
                    updateSampleText();
                    if ($('input:hidden[name=whichSeries]').length && $('#fullShowPath').length) {
                        goToStep(3);
                    }
                }
            });

            $('#rootDirText').change(updateSampleText);
            $('#searchResults').on('change', '#whichSeries', updateSampleText);

            $('#nameToSearch').keyup(function(event) {
                if (event.keyCode === 13) {
                    $('#searchName').click();
                }
            });

            $('#anime').change(function() {
                updateSampleText();
                myform.loadsection(2);
            });
        },
        addExistingShow: function() {
            $('#tableDiv').on('click', '#checkAll', function() {
                var seasCheck = this;
                $('.dirCheck').each(function() {
                    this.checked = seasCheck.checked;
                });
            });

            $('#submitShowDirs').on('click', function() {
                var dirArr = [];
                $('.dirCheck').each(function() {
                    if (this.checked === true) {
                        var show = $(this).attr('id');
                        var indexer = $(this).closest('tr').find('select').val();
                        dirArr.push(encodeURIComponent(indexer + '|' + show));
                    }
                });

                if (dirArr.length === 0) {
                    return false;
                }

                window.location.href = 'addShows/addExistingShows?promptForSettings=' + ($('#promptForSettings').prop('checked') ? 'on' : 'off') + '&shows_to_add=' + dirArr.join('&shows_to_add=');
            });

            function loadContent() {
                var url = '';
                $('.dir_check').each(function(i, w) {
                    if ($(w).is(':checked')) {
                        if (url.length) {
                            url += '&';
                        }
                        url += 'rootDir=' + encodeURIComponent($(w).attr('id'));
                    }
                });

                $('#tableDiv').html('<img id="searchingAnim" src="images/loading32.gif" height="32" width="32" /> loading folders...');
                $.get('addShows/massAddTable/', url, function(data) {
                    $('#tableDiv').html(data);
                    $('#addRootDirTable').tablesorter({
                        // sortList: [[1,0]],
                        widgets: ['zebra'],
                        headers: {
                            0: {sorter: false}
                        }
                    });
                });
            }

            var lastTxt = '';
            // @TODO this needs a real name, for now this fixes the issue of the page not loading at all,
            //       before I added this I couldn't get the directories to show in the table
            var a = function() {
                if (lastTxt === $('#rootDirText').val()) {
                    return false;
                }
                lastTxt = $('#rootDirText').val();
                $('#rootDirStaticList').html('');
                $('#rootDirs option').each(function(i, w) {
                    $('#rootDirStaticList').append('<li class="ui-state-default ui-corner-all"><input type="checkbox" class="cb dir_check" id="' + $(w).val() + '" checked=checked> <label for="' + $(w).val() + '"><b>' + $(w).val() + '</b></label></li>');
                });
                loadContent();
            };

            a();

            $('#rootDirText').on('change', a);

            $('#rootDirStaticList').on('click', '.dir_check', loadContent);

            $('#tableDiv').on('click', '.showManage', function(event) {
                event.preventDefault();
                $('#tabs').tabs('option', 'active', 0);
                $('html,body').animate({scrollTop: 0}, 1000);
            });
        },
        recommendedShows: function() {
            // Cleanest way of not showing the black/whitelist, when there isn't a show to show it for
            $.updateBlackWhiteList(undefined);
            $('#recommendedShows').loadRemoteShows(
                'addShows/getRecommendedShows/',
                'Loading recommended shows...',
                'Trakt timed out, refresh page to try again'
            );

            $.initAddShowById();
            $.initBlackListShowById();
            $.initRemoteShowGrid();
        },

        trendingShows: function() {
            // Cleanest way of not showing the black/whitelist, when there isn't a show to show it for
            $.updateBlackWhiteList(undefined);
            $('#trendingShows').loadRemoteShows(
                'addShows/getTrendingShows/?traktList=' + $('#traktList').val(),
                'Loading trending shows...',
                'Trakt timed out, refresh page to try again'
            );

            $('#traktlistselection').on('change', function(e) {
                var traktList = e.target.value;
                window.history.replaceState({}, document.title, 'addShows/trendingShows/?traktList=' + traktList);
                $('#trendingShows').loadRemoteShows(
                    'addShows/getTrendingShows/?traktList=' + traktList,
                    'Loading trending shows...',
                    'Trakt timed out, refresh page to try again'
                );
                $('h1.header').text('Trakt ' + $('option[value="' + e.target.value + '"]')[0].innerText);
            });

            $.initAddShowById();
            $.initBlackListShowById();
        },
        popularShows: function() {
            $.initRemoteShowGrid();
        }
    }
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
        themeSpinner = SICKRAGE.info.themeName === 'dark' ? '-dark' : '';
        anonRedirect = SICKRAGE.info.anonRedirect;
        loading = '<img src="images/loading16' + themeSpinner + '.gif" height="16" width="16" />';

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
