# coding=utf-8

"""Configure notifications."""

from __future__ import unicode_literals

import os

from medusa import app, config, logger, ui
from medusa.helper.common import try_int
from medusa.server.web.config.handler import Config
from medusa.server.web.core import PageTemplate

from tornroutes import route


@route('/config/notifications(/?.*)')
class ConfigNotifications(Config):
    """
    Handler for notification configuration
    """
    def __init__(self, *args, **kwargs):
        super(ConfigNotifications, self).__init__(*args, **kwargs)

    def index(self):
        """
        Render the notification configuration page
        """
        t = PageTemplate(rh=self, filename='config_notifications.mako')

        return t.render(submenu=self.ConfigMenu(),
                        controller='config', action='notifications')

    def saveNotifications(self, use_kodi=None, kodi_always_on=None, kodi_notify_onsnatch=None,
                          kodi_notify_ondownload=None,
                          kodi_notify_onsubtitledownload=None, kodi_update_onlyfirst=None,
                          kodi_update_library=None, kodi_update_full=None, kodi_host=None, kodi_username=None,
                          kodi_password=None, kodi_clean_library=None,
                          use_plex_server=None, plex_notify_onsnatch=None, plex_notify_ondownload=None,
                          plex_notify_onsubtitledownload=None, plex_update_library=None,
                          plex_server_host=None, plex_server_token=None, plex_client_host=None, plex_server_username=None, plex_server_password=None,
                          use_plex_client=None, plex_client_username=None, plex_client_password=None,
                          plex_server_https=None, use_emby=None, emby_host=None, emby_apikey=None,
                          use_growl=None, growl_notify_onsnatch=None, growl_notify_ondownload=None,
                          growl_notify_onsubtitledownload=None, growl_host=None, growl_password=None,
                          use_freemobile=None, freemobile_notify_onsnatch=None, freemobile_notify_ondownload=None,
                          freemobile_notify_onsubtitledownload=None, freemobile_id=None, freemobile_apikey=None,
                          use_telegram=None, telegram_notify_onsnatch=None, telegram_notify_ondownload=None,
                          telegram_notify_onsubtitledownload=None, telegram_id=None, telegram_apikey=None,
                          use_prowl=None, prowl_notify_onsnatch=None, prowl_notify_ondownload=None,
                          prowl_notify_onsubtitledownload=None, prowl_api=None, prowl_priority=0,
                          prowl_show_list=None, prowl_show=None, prowl_message_title=None,
                          use_twitter=None, twitter_notify_onsnatch=None, twitter_notify_ondownload=None,
                          twitter_notify_onsubtitledownload=None, twitter_usedm=None, twitter_dmto=None,
                          use_boxcar2=None, boxcar2_notify_onsnatch=None, boxcar2_notify_ondownload=None,
                          boxcar2_notify_onsubtitledownload=None, boxcar2_accesstoken=None,
                          use_pushover=None, pushover_notify_onsnatch=None, pushover_notify_ondownload=None,
                          pushover_notify_onsubtitledownload=None, pushover_userkey=None, pushover_apikey=None, pushover_device=None, pushover_sound=None,
                          use_libnotify=None, libnotify_notify_onsnatch=None, libnotify_notify_ondownload=None,
                          libnotify_notify_onsubtitledownload=None,
                          use_nmj=None, nmj_host=None, nmj_database=None, nmj_mount=None, use_synoindex=None,
                          use_nmjv2=None, nmjv2_host=None, nmjv2_dbloc=None, nmjv2_database=None,
                          use_trakt=None, trakt_username=None, trakt_pin=None,
                          trakt_remove_watchlist=None, trakt_sync_watchlist=None, trakt_remove_show_from_application=None, trakt_method_add=None,
                          trakt_start_paused=None, trakt_use_recommended=None, trakt_sync=None, trakt_sync_remove=None,
                          trakt_default_indexer=None, trakt_remove_serieslist=None, trakt_timeout=None, trakt_blacklist_name=None,
                          use_synologynotifier=None, synologynotifier_notify_onsnatch=None,
                          synologynotifier_notify_ondownload=None, synologynotifier_notify_onsubtitledownload=None,
                          use_pytivo=None, pytivo_notify_onsnatch=None, pytivo_notify_ondownload=None,
                          pytivo_notify_onsubtitledownload=None, pytivo_update_library=None,
                          pytivo_host=None, pytivo_share_name=None, pytivo_tivo_name=None,
                          use_pushalot=None, pushalot_notify_onsnatch=None, pushalot_notify_ondownload=None,
                          pushalot_notify_onsubtitledownload=None, pushalot_authorizationtoken=None,
                          use_pushbullet=None, pushbullet_notify_onsnatch=None, pushbullet_notify_ondownload=None,
                          pushbullet_notify_onsubtitledownload=None, pushbullet_api=None, pushbullet_device=None,
                          pushbullet_device_list=None,
                          use_email=None, email_notify_onsnatch=None, email_notify_ondownload=None,
                          email_notify_onsubtitledownload=None, email_host=None, email_port=25, email_from=None,
                          email_tls=None, email_user=None, email_password=None, email_list=None, email_subject=None, email_show_list=None,
                          email_show=None,
                          use_slack=None, slack_notify_onsnatch=None, slack_notify_ondownload=None, slack_notify_onsubtitledownload=None,
                          slack_webhook=None):
        """
        Save notification related settings
        """

        results = []

        app.USE_KODI = config.checkbox_to_value(use_kodi)
        app.KODI_ALWAYS_ON = config.checkbox_to_value(kodi_always_on)
        app.KODI_NOTIFY_ONSNATCH = config.checkbox_to_value(kodi_notify_onsnatch)
        app.KODI_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(kodi_notify_ondownload)
        app.KODI_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(kodi_notify_onsubtitledownload)
        app.KODI_UPDATE_LIBRARY = config.checkbox_to_value(kodi_update_library)
        app.KODI_UPDATE_FULL = config.checkbox_to_value(kodi_update_full)
        app.KODI_UPDATE_ONLYFIRST = config.checkbox_to_value(kodi_update_onlyfirst)
        app.KODI_HOST = config.clean_hosts(kodi_host)
        app.KODI_USERNAME = kodi_username
        app.KODI_PASSWORD = kodi_password
        app.KODI_CLEAN_LIBRARY = config.checkbox_to_value(kodi_clean_library)

        app.USE_PLEX_SERVER = config.checkbox_to_value(use_plex_server)
        app.PLEX_NOTIFY_ONSNATCH = config.checkbox_to_value(plex_notify_onsnatch)
        app.PLEX_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(plex_notify_ondownload)
        app.PLEX_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(plex_notify_onsubtitledownload)
        app.PLEX_UPDATE_LIBRARY = config.checkbox_to_value(plex_update_library)
        app.PLEX_CLIENT_HOST = config.clean_hosts(plex_client_host)
        app.PLEX_SERVER_HOST = config.clean_hosts(plex_server_host)
        app.PLEX_SERVER_TOKEN = config.clean_host(plex_server_token)
        app.PLEX_SERVER_USERNAME = plex_server_username
        if plex_server_password != '*' * len(app.PLEX_SERVER_PASSWORD):
            app.PLEX_SERVER_PASSWORD = plex_server_password

        app.USE_PLEX_CLIENT = config.checkbox_to_value(use_plex_client)
        app.PLEX_CLIENT_USERNAME = plex_client_username
        if plex_client_password != '*' * len(app.PLEX_CLIENT_PASSWORD):
            app.PLEX_CLIENT_PASSWORD = plex_client_password
        app.PLEX_SERVER_HTTPS = config.checkbox_to_value(plex_server_https)

        app.USE_EMBY = config.checkbox_to_value(use_emby)
        app.EMBY_HOST = config.clean_host(emby_host)
        app.EMBY_APIKEY = emby_apikey

        app.USE_GROWL = config.checkbox_to_value(use_growl)
        app.GROWL_NOTIFY_ONSNATCH = config.checkbox_to_value(growl_notify_onsnatch)
        app.GROWL_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(growl_notify_ondownload)
        app.GROWL_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(growl_notify_onsubtitledownload)
        app.GROWL_HOST = config.clean_host(growl_host, default_port=23053)
        app.GROWL_PASSWORD = growl_password

        app.USE_FREEMOBILE = config.checkbox_to_value(use_freemobile)
        app.FREEMOBILE_NOTIFY_ONSNATCH = config.checkbox_to_value(freemobile_notify_onsnatch)
        app.FREEMOBILE_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(freemobile_notify_ondownload)
        app.FREEMOBILE_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(freemobile_notify_onsubtitledownload)
        app.FREEMOBILE_ID = freemobile_id
        app.FREEMOBILE_APIKEY = freemobile_apikey

        app.USE_TELEGRAM = config.checkbox_to_value(use_telegram)
        app.TELEGRAM_NOTIFY_ONSNATCH = config.checkbox_to_value(telegram_notify_onsnatch)
        app.TELEGRAM_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(telegram_notify_ondownload)
        app.TELEGRAM_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(telegram_notify_onsubtitledownload)
        app.TELEGRAM_ID = telegram_id
        app.TELEGRAM_APIKEY = telegram_apikey

        app.USE_PROWL = config.checkbox_to_value(use_prowl)
        app.PROWL_NOTIFY_ONSNATCH = config.checkbox_to_value(prowl_notify_onsnatch)
        app.PROWL_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(prowl_notify_ondownload)
        app.PROWL_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(prowl_notify_onsubtitledownload)
        app.PROWL_API = [_.strip() for _ in prowl_api.split(',')]
        app.PROWL_PRIORITY = prowl_priority
        app.PROWL_MESSAGE_TITLE = prowl_message_title

        app.USE_TWITTER = config.checkbox_to_value(use_twitter)
        app.TWITTER_NOTIFY_ONSNATCH = config.checkbox_to_value(twitter_notify_onsnatch)
        app.TWITTER_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(twitter_notify_ondownload)
        app.TWITTER_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(twitter_notify_onsubtitledownload)
        app.TWITTER_USEDM = config.checkbox_to_value(twitter_usedm)
        app.TWITTER_DMTO = twitter_dmto

        app.USE_BOXCAR2 = config.checkbox_to_value(use_boxcar2)
        app.BOXCAR2_NOTIFY_ONSNATCH = config.checkbox_to_value(boxcar2_notify_onsnatch)
        app.BOXCAR2_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(boxcar2_notify_ondownload)
        app.BOXCAR2_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(boxcar2_notify_onsubtitledownload)
        app.BOXCAR2_ACCESSTOKEN = boxcar2_accesstoken

        app.USE_PUSHOVER = config.checkbox_to_value(use_pushover)
        app.PUSHOVER_NOTIFY_ONSNATCH = config.checkbox_to_value(pushover_notify_onsnatch)
        app.PUSHOVER_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(pushover_notify_ondownload)
        app.PUSHOVER_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(pushover_notify_onsubtitledownload)
        app.PUSHOVER_USERKEY = pushover_userkey
        app.PUSHOVER_APIKEY = pushover_apikey
        app.PUSHOVER_DEVICE = [_.strip() for _ in pushover_device.split(',')]
        app.PUSHOVER_SOUND = pushover_sound

        app.USE_LIBNOTIFY = config.checkbox_to_value(use_libnotify)
        app.LIBNOTIFY_NOTIFY_ONSNATCH = config.checkbox_to_value(libnotify_notify_onsnatch)
        app.LIBNOTIFY_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(libnotify_notify_ondownload)
        app.LIBNOTIFY_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(libnotify_notify_onsubtitledownload)

        app.USE_NMJ = config.checkbox_to_value(use_nmj)
        app.NMJ_HOST = config.clean_host(nmj_host)
        app.NMJ_DATABASE = nmj_database
        app.NMJ_MOUNT = nmj_mount

        app.USE_NMJv2 = config.checkbox_to_value(use_nmjv2)
        app.NMJv2_HOST = config.clean_host(nmjv2_host)
        app.NMJv2_DATABASE = nmjv2_database
        app.NMJv2_DBLOC = nmjv2_dbloc

        app.USE_SYNOINDEX = config.checkbox_to_value(use_synoindex)

        app.USE_SYNOLOGYNOTIFIER = config.checkbox_to_value(use_synologynotifier)
        app.SYNOLOGYNOTIFIER_NOTIFY_ONSNATCH = config.checkbox_to_value(synologynotifier_notify_onsnatch)
        app.SYNOLOGYNOTIFIER_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(synologynotifier_notify_ondownload)
        app.SYNOLOGYNOTIFIER_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(
            synologynotifier_notify_onsubtitledownload)

        app.USE_SLACK = config.checkbox_to_value(use_slack)
        app.SLACK_NOTIFY_DOWNLOAD = config.checkbox_to_value(slack_notify_ondownload)
        app.SLACK_NOTIFY_SNATCH = config.checkbox_to_value(slack_notify_onsnatch)
        app.SLACK_NOTIFY_SUBTITLEDOWNLOAD = config.checkbox_to_value(slack_notify_onsubtitledownload)
        app.SLACK_WEBHOOK = slack_webhook

        config.change_USE_TRAKT(use_trakt)
        app.TRAKT_USERNAME = trakt_username
        app.TRAKT_REMOVE_WATCHLIST = config.checkbox_to_value(trakt_remove_watchlist)
        app.TRAKT_REMOVE_SERIESLIST = config.checkbox_to_value(trakt_remove_serieslist)
        app.TRAKT_REMOVE_SHOW_FROM_APPLICATION = config.checkbox_to_value(trakt_remove_show_from_application)
        app.TRAKT_SYNC_WATCHLIST = config.checkbox_to_value(trakt_sync_watchlist)
        app.TRAKT_METHOD_ADD = int(trakt_method_add)
        app.TRAKT_START_PAUSED = config.checkbox_to_value(trakt_start_paused)
        app.TRAKT_USE_RECOMMENDED = config.checkbox_to_value(trakt_use_recommended)
        app.TRAKT_SYNC = config.checkbox_to_value(trakt_sync)
        app.TRAKT_SYNC_REMOVE = config.checkbox_to_value(trakt_sync_remove)
        app.TRAKT_DEFAULT_INDEXER = int(trakt_default_indexer)
        app.TRAKT_TIMEOUT = int(trakt_timeout)
        app.TRAKT_BLACKLIST_NAME = trakt_blacklist_name

        app.USE_EMAIL = config.checkbox_to_value(use_email)
        app.EMAIL_NOTIFY_ONSNATCH = config.checkbox_to_value(email_notify_onsnatch)
        app.EMAIL_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(email_notify_ondownload)
        app.EMAIL_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(email_notify_onsubtitledownload)
        app.EMAIL_HOST = config.clean_host(email_host)
        app.EMAIL_PORT = try_int(email_port, 25)
        app.EMAIL_FROM = email_from
        app.EMAIL_TLS = config.checkbox_to_value(email_tls)
        app.EMAIL_USER = email_user
        app.EMAIL_PASSWORD = email_password
        app.EMAIL_LIST = [_.strip() for _ in email_list.split(',')]
        app.EMAIL_SUBJECT = email_subject

        app.USE_PYTIVO = config.checkbox_to_value(use_pytivo)
        app.PYTIVO_NOTIFY_ONSNATCH = config.checkbox_to_value(pytivo_notify_onsnatch)
        app.PYTIVO_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(pytivo_notify_ondownload)
        app.PYTIVO_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(pytivo_notify_onsubtitledownload)
        app.PYTIVO_UPDATE_LIBRARY = config.checkbox_to_value(pytivo_update_library)
        app.PYTIVO_HOST = config.clean_host(pytivo_host)
        app.PYTIVO_SHARE_NAME = pytivo_share_name
        app.PYTIVO_TIVO_NAME = pytivo_tivo_name

        app.USE_PUSHALOT = config.checkbox_to_value(use_pushalot)
        app.PUSHALOT_NOTIFY_ONSNATCH = config.checkbox_to_value(pushalot_notify_onsnatch)
        app.PUSHALOT_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(pushalot_notify_ondownload)
        app.PUSHALOT_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(pushalot_notify_onsubtitledownload)
        app.PUSHALOT_AUTHORIZATIONTOKEN = pushalot_authorizationtoken

        app.USE_PUSHBULLET = config.checkbox_to_value(use_pushbullet)
        app.PUSHBULLET_NOTIFY_ONSNATCH = config.checkbox_to_value(pushbullet_notify_onsnatch)
        app.PUSHBULLET_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(pushbullet_notify_ondownload)
        app.PUSHBULLET_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(pushbullet_notify_onsubtitledownload)
        app.PUSHBULLET_API = pushbullet_api
        app.PUSHBULLET_DEVICE = pushbullet_device_list

        app.instance.save_config()

        if results:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                                   '<br>\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', os.path.join(app.CONFIG_FILE))

        return self.redirect('/config/notifications/')
