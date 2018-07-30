# coding=utf-8

from __future__ import unicode_literals

import os

from github import GithubException

from medusa import (
    app,
    config,
    github_client,
    helpers,
    logger,
    ui,
)
from medusa.common import (
    Quality,
    WANTED,
)
from medusa.helper.common import try_int
from medusa.server.web.config.handler import Config
from medusa.server.web.core import PageTemplate

from tornroutes import route


@route('/config/general(/?.*)')
class ConfigGeneral(Config):
    def __init__(self, *args, **kwargs):
        super(ConfigGeneral, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename='config_general.mako')

        return t.render(submenu=self.ConfigMenu(),
                        controller='config', action='index')

    @staticmethod
    def generate_api_key():
        return helpers.generate_api_key()

    @staticmethod
    def saveAddShowDefaults(default_status, allowed_qualities, preferred_qualities, default_season_folders,
                            subtitles=False, anime=False, scene=False, default_status_after=WANTED):

        allowed_qualities = [_.strip() for _ in allowed_qualities.split(',')] if allowed_qualities else []
        preferred_qualities = [_.strip() for _ in preferred_qualities.split(',')] if preferred_qualities else []

        new_quality = Quality.combine_qualities([int(quality) for quality in allowed_qualities],
                                                [int(quality) for quality in preferred_qualities])

        app.STATUS_DEFAULT = int(default_status)
        app.STATUS_DEFAULT_AFTER = int(default_status_after)
        app.QUALITY_DEFAULT = int(new_quality)

        app.SEASON_FOLDERS_DEFAULT = config.checkbox_to_value(default_season_folders)
        app.SUBTITLES_DEFAULT = config.checkbox_to_value(subtitles)

        app.ANIME_DEFAULT = config.checkbox_to_value(anime)

        app.SCENE_DEFAULT = config.checkbox_to_value(scene)
        app.instance.save_config()

    def saveGeneral(self, log_dir=None, log_nr=5, log_size=1, web_port=None, notify_on_login=None, web_log=None, encryption_version=None, web_ipv6=None,
                    trash_remove_show=None, trash_rotate_logs=None, update_frequency=None, skip_removed_files=None,
                    indexerDefaultLang='en', ep_default_deleted_status=None, launch_browser=None, showupdate_hour=3, web_username=None,
                    api_key=None, indexer_default=None, timezone_display=None, cpu_preset='NORMAL', layout_wide=None,
                    web_password=None, version_notify=None, enable_https=None, https_cert=None, https_key=None,
                    handle_reverse_proxy=None, sort_article=None, auto_update=None, notify_on_update=None,
                    proxy_setting=None, proxy_indexers=None, anon_redirect=None, git_path=None, git_remote=None,
                    calendar_unprotected=None, calendar_icons=None, debug=None, ssl_verify=None, no_restart=None, coming_eps_missed_range=None,
                    fuzzy_dating=None, trim_zero=None, date_preset=None, date_preset_na=None, time_preset=None,
                    indexer_timeout=None, download_url=None, rootDir=None, theme_name=None, default_page=None,
                    git_reset=None, git_reset_branches=None, git_auth_type=0, git_username=None, git_password=None, git_token=None,
                    display_all_seasons=None, subliminal_log=None, privacy_level='normal', fanart_background=None, fanart_background_opacity=None,
                    dbdebug=None, fallback_plex_enable=1, fallback_plex_notifications=1, fallback_plex_timeout=3, web_root=None, ssl_ca_bundle=None):

        results = []

        # Misc
        app.DOWNLOAD_URL = download_url
        app.INDEXER_DEFAULT_LANGUAGE = indexerDefaultLang
        app.EP_DEFAULT_DELETED_STATUS = int(ep_default_deleted_status)
        app.SKIP_REMOVED_FILES = config.checkbox_to_value(skip_removed_files)
        app.LAUNCH_BROWSER = config.checkbox_to_value(launch_browser)
        config.change_SHOWUPDATE_HOUR(showupdate_hour)
        config.change_VERSION_NOTIFY(config.checkbox_to_value(version_notify))
        app.AUTO_UPDATE = config.checkbox_to_value(auto_update)
        app.NOTIFY_ON_UPDATE = config.checkbox_to_value(notify_on_update)
        # app.LOG_DIR is set in config.change_LOG_DIR()
        app.LOG_NR = log_nr
        app.LOG_SIZE = float(log_size)

        app.TRASH_REMOVE_SHOW = config.checkbox_to_value(trash_remove_show)
        app.TRASH_ROTATE_LOGS = config.checkbox_to_value(trash_rotate_logs)
        config.change_UPDATE_FREQUENCY(update_frequency)
        app.LAUNCH_BROWSER = config.checkbox_to_value(launch_browser)
        app.SORT_ARTICLE = config.checkbox_to_value(sort_article)
        app.CPU_PRESET = cpu_preset
        app.ANON_REDIRECT = anon_redirect
        app.PROXY_SETTING = proxy_setting
        app.PROXY_INDEXERS = config.checkbox_to_value(proxy_indexers)
        app.GIT_AUTH_TYPE = int(git_auth_type)
        app.GIT_USERNAME = git_username
        app.GIT_PASSWORD = git_password
        app.GIT_TOKEN = git_token
        app.GIT_RESET = config.checkbox_to_value(git_reset)
        app.GIT_RESET_BRANCHES = helpers.ensure_list(git_reset_branches)
        if app.GIT_PATH != git_path:
            app.GIT_PATH = git_path
            config.change_GIT_PATH()
        app.GIT_REMOTE = git_remote
        app.CALENDAR_UNPROTECTED = config.checkbox_to_value(calendar_unprotected)
        app.CALENDAR_ICONS = config.checkbox_to_value(calendar_icons)
        app.NO_RESTART = config.checkbox_to_value(no_restart)

        app.SSL_VERIFY = config.checkbox_to_value(ssl_verify)
        app.SSL_CA_BUNDLE = ssl_ca_bundle
        # app.LOG_DIR is set in config.change_LOG_DIR()
        app.COMING_EPS_MISSED_RANGE = int(coming_eps_missed_range)
        app.DISPLAY_ALL_SEASONS = config.checkbox_to_value(display_all_seasons)
        app.NOTIFY_ON_LOGIN = config.checkbox_to_value(notify_on_login)
        app.WEB_PORT = int(web_port)
        app.WEB_IPV6 = config.checkbox_to_value(web_ipv6)
        if config.checkbox_to_value(encryption_version) == 1:
            app.ENCRYPTION_VERSION = 2
        else:
            app.ENCRYPTION_VERSION = 0
        app.WEB_USERNAME = web_username
        app.WEB_PASSWORD = web_password
        app.WEB_ROOT = web_root

        app.DEBUG = config.checkbox_to_value(debug)
        app.DBDEBUG = config.checkbox_to_value(dbdebug)
        app.WEB_LOG = config.checkbox_to_value(web_log)
        app.SUBLIMINAL_LOG = config.checkbox_to_value(subliminal_log)

        # Added for tvdb / plex fallback
        app.FALLBACK_PLEX_ENABLE = config.checkbox_to_value(fallback_plex_enable)
        app.FALLBACK_PLEX_NOTIFICATIONS = config.checkbox_to_value(fallback_plex_notifications)
        app.FALLBACK_PLEX_TIMEOUT = try_int(fallback_plex_timeout)

        if not config.change_LOG_DIR(log_dir):
            results += ['Unable to create directory {dir}, '
                        'log directory not changed.'.format(dir=os.path.normpath(log_dir))]

        # Reconfigure the logger
        logger.reconfigure()

        # Validate github credentials
        try:
            if app.GIT_AUTH_TYPE == 0:
                github_client.authenticate(app.GIT_USERNAME, app.GIT_PASSWORD)
            else:
                github = github_client.token_authenticate(app.GIT_TOKEN)
                if app.GIT_USERNAME and app.GIT_USERNAME != github_client.get_user(gh=github):
                    app.GIT_USERNAME = github_client.get_user(gh=github)
        except (GithubException, IOError):
            logger.log('Error while validating your Github credentials.', logger.WARNING)

        app.PRIVACY_LEVEL = privacy_level.lower()

        app.FUZZY_DATING = config.checkbox_to_value(fuzzy_dating)
        app.TRIM_ZERO = config.checkbox_to_value(trim_zero)

        if date_preset:
            app.DATE_PRESET = date_preset

        if indexer_default:
            app.INDEXER_DEFAULT = try_int(indexer_default)

        if indexer_timeout:
            app.INDEXER_TIMEOUT = try_int(indexer_timeout)

        if time_preset:
            app.TIME_PRESET_W_SECONDS = time_preset
            app.TIME_PRESET = app.TIME_PRESET_W_SECONDS.replace(u':%S', u'')

        app.TIMEZONE_DISPLAY = timezone_display

        app.API_KEY = api_key

        app.ENABLE_HTTPS = config.checkbox_to_value(enable_https)

        if not config.change_HTTPS_CERT(https_cert):
            results += ['Unable to create directory {dir}, '
                        'https cert directory not changed.'.format(dir=os.path.normpath(https_cert))]

        if not config.change_HTTPS_KEY(https_key):
            results += ['Unable to create directory {dir}, '
                        'https key directory not changed.'.format(dir=os.path.normpath(https_key))]

        app.HANDLE_REVERSE_PROXY = config.checkbox_to_value(handle_reverse_proxy)

        config.change_theme(theme_name)

        app.LAYOUT_WIDE = config.checkbox_to_value(layout_wide)
        app.FANART_BACKGROUND = config.checkbox_to_value(fanart_background)
        app.FANART_BACKGROUND_OPACITY = fanart_background_opacity

        app.DEFAULT_PAGE = default_page

        app.instance.save_config()

        if results:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                                   '<br>\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', os.path.join(app.CONFIG_FILE))

        return self.redirect('/config/general/')
