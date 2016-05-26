# coding=utf-8

from __future__ import unicode_literals

import os
from tornado.routes import route
import sickbeard
from sickbeard import (
    config, helpers, logger, ui,
)
from sickbeard.common import (
    Quality, WANTED,
)
from sickrage.helper.common import try_int
from sickrage.helper.encoding import ek
from sickbeard.server.web.core import PageTemplate
from sickbeard.server.web.config.handler import Config


@route('/config/general(/?.*)')
class ConfigGeneral(Config):
    def __init__(self, *args, **kwargs):
        super(ConfigGeneral, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename='config_general.mako')

        return t.render(title='Config - General', header='General Configuration',
                        topmenu='config', submenu=self.ConfigMenu(),
                        controller='config', action='index')

    @staticmethod
    def generateApiKey():
        return helpers.generateApiKey()

    @staticmethod
    def saveRootDirs(rootDirString=None):
        sickbeard.ROOT_DIRS = rootDirString

    @staticmethod
    def saveAddShowDefaults(defaultStatus, anyQualities, bestQualities, defaultFlattenFolders, subtitles=False,
                            anime=False, scene=False, defaultStatusAfter=WANTED):

        allowed_qualities = anyQualities.split(',') if anyQualities else []
        preferred_qualities = bestQualities.split(',') if bestQualities else []

        new_quality = Quality.combineQualities([int(quality) for quality in allowed_qualities], [int(quality) for quality in preferred_qualities])

        sickbeard.STATUS_DEFAULT = int(defaultStatus)
        sickbeard.STATUS_DEFAULT_AFTER = int(defaultStatusAfter)
        sickbeard.QUALITY_DEFAULT = int(new_quality)

        sickbeard.FLATTEN_FOLDERS_DEFAULT = config.checkbox_to_value(defaultFlattenFolders)
        sickbeard.SUBTITLES_DEFAULT = config.checkbox_to_value(subtitles)

        sickbeard.ANIME_DEFAULT = config.checkbox_to_value(anime)

        sickbeard.SCENE_DEFAULT = config.checkbox_to_value(scene)
        sickbeard.save_config()

    def saveGeneral(self, log_dir=None, log_nr=5, log_size=1, web_port=None, notify_on_login=None, web_log=None, encryption_version=None, web_ipv6=None,
                    trash_remove_show=None, trash_rotate_logs=None, update_frequency=None, skip_removed_files=None,
                    indexerDefaultLang='en', ep_default_deleted_status=None, launch_browser=None, showupdate_hour=3, web_username=None,
                    api_key=None, indexer_default=None, timezone_display=None, cpu_preset='NORMAL',
                    web_password=None, version_notify=None, enable_https=None, https_cert=None, https_key=None,
                    handle_reverse_proxy=None, sort_article=None, auto_update=None, notify_on_update=None,
                    proxy_setting=None, proxy_indexers=None, anon_redirect=None, git_path=None, git_remote=None,
                    calendar_unprotected=None, calendar_icons=None, debug=None, ssl_verify=None, no_restart=None, coming_eps_missed_range=None,
                    fuzzy_dating=None, trim_zero=None, date_preset=None, date_preset_na=None, time_preset=None,
                    indexer_timeout=None, download_url=None, rootDir=None, theme_name=None, default_page=None,
                    git_reset=None, git_username=None, git_password=None, display_all_seasons=None, subliminal_log=None, privacy_level='normal'):

        results = []

        # Misc
        sickbeard.DOWNLOAD_URL = download_url
        sickbeard.INDEXER_DEFAULT_LANGUAGE = indexerDefaultLang
        sickbeard.EP_DEFAULT_DELETED_STATUS = ep_default_deleted_status
        sickbeard.SKIP_REMOVED_FILES = config.checkbox_to_value(skip_removed_files)
        sickbeard.LAUNCH_BROWSER = config.checkbox_to_value(launch_browser)
        config.change_SHOWUPDATE_HOUR(showupdate_hour)
        config.change_VERSION_NOTIFY(config.checkbox_to_value(version_notify))
        sickbeard.AUTO_UPDATE = config.checkbox_to_value(auto_update)
        sickbeard.NOTIFY_ON_UPDATE = config.checkbox_to_value(notify_on_update)
        # sickbeard.LOG_DIR is set in config.change_LOG_DIR()
        sickbeard.LOG_NR = log_nr
        sickbeard.LOG_SIZE = float(log_size)

        sickbeard.TRASH_REMOVE_SHOW = config.checkbox_to_value(trash_remove_show)
        sickbeard.TRASH_ROTATE_LOGS = config.checkbox_to_value(trash_rotate_logs)
        config.change_UPDATE_FREQUENCY(update_frequency)
        sickbeard.LAUNCH_BROWSER = config.checkbox_to_value(launch_browser)
        sickbeard.SORT_ARTICLE = config.checkbox_to_value(sort_article)
        sickbeard.CPU_PRESET = cpu_preset
        sickbeard.ANON_REDIRECT = anon_redirect
        sickbeard.PROXY_SETTING = proxy_setting
        sickbeard.PROXY_INDEXERS = config.checkbox_to_value(proxy_indexers)
        sickbeard.GIT_USERNAME = git_username
        sickbeard.GIT_PASSWORD = git_password
        # sickbeard.GIT_RESET = config.checkbox_to_value(git_reset)
        # Force GIT_RESET
        sickbeard.GIT_RESET = 1
        sickbeard.GIT_PATH = git_path
        sickbeard.GIT_REMOTE = git_remote
        sickbeard.CALENDAR_UNPROTECTED = config.checkbox_to_value(calendar_unprotected)
        sickbeard.CALENDAR_ICONS = config.checkbox_to_value(calendar_icons)
        sickbeard.NO_RESTART = config.checkbox_to_value(no_restart)
        sickbeard.DEBUG = config.checkbox_to_value(debug)
        sickbeard.SSL_VERIFY = config.checkbox_to_value(ssl_verify)
        # sickbeard.LOG_DIR is set in config.change_LOG_DIR()
        sickbeard.COMING_EPS_MISSED_RANGE = try_int(coming_eps_missed_range, 7)
        sickbeard.DISPLAY_ALL_SEASONS = config.checkbox_to_value(display_all_seasons)
        sickbeard.NOTIFY_ON_LOGIN = config.checkbox_to_value(notify_on_login)
        sickbeard.WEB_PORT = try_int(web_port)
        sickbeard.WEB_IPV6 = config.checkbox_to_value(web_ipv6)
        # sickbeard.WEB_LOG is set in config.change_LOG_DIR()
        if config.checkbox_to_value(encryption_version) == 1:
            sickbeard.ENCRYPTION_VERSION = 2
        else:
            sickbeard.ENCRYPTION_VERSION = 0
        sickbeard.WEB_USERNAME = web_username
        sickbeard.WEB_PASSWORD = web_password

        # Reconfigure the logger only if subliminal setting changed
        if sickbeard.SUBLIMINAL_LOG != config.checkbox_to_value(subliminal_log):
            logger.reconfigure_levels()
        sickbeard.SUBLIMINAL_LOG = config.checkbox_to_value(subliminal_log)

        sickbeard.PRIVACY_LEVEL = privacy_level.lower()

        sickbeard.FUZZY_DATING = config.checkbox_to_value(fuzzy_dating)
        sickbeard.TRIM_ZERO = config.checkbox_to_value(trim_zero)

        if date_preset:
            sickbeard.DATE_PRESET = date_preset

        if indexer_default:
            sickbeard.INDEXER_DEFAULT = try_int(indexer_default)

        if indexer_timeout:
            sickbeard.INDEXER_TIMEOUT = try_int(indexer_timeout)

        if time_preset:
            sickbeard.TIME_PRESET_W_SECONDS = time_preset
            sickbeard.TIME_PRESET = sickbeard.TIME_PRESET_W_SECONDS.replace(u':%S', u'')

        sickbeard.TIMEZONE_DISPLAY = timezone_display

        if not config.change_LOG_DIR(log_dir, web_log):
            results += ['Unable to create directory {dir}, '
                        'log directory not changed.'.format(dir=ek(os.path.normpath, log_dir))]

        sickbeard.API_KEY = api_key

        sickbeard.ENABLE_HTTPS = config.checkbox_to_value(enable_https)

        if not config.change_HTTPS_CERT(https_cert):
            results += ['Unable to create directory {dir}, '
                        'https cert directory not changed.'.format(dir=ek(os.path.normpath, https_cert))]

        if not config.change_HTTPS_KEY(https_key):
            results += ['Unable to create directory {dir}, '
                        'https key directory not changed.'.format(dir=ek(os.path.normpath, https_key))]

        sickbeard.HANDLE_REVERSE_PROXY = config.checkbox_to_value(handle_reverse_proxy)

        sickbeard.THEME_NAME = theme_name

        sickbeard.DEFAULT_PAGE = default_page

        sickbeard.save_config()

        if results:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                                   '<br>\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', ek(os.path.join, sickbeard.CONFIG_FILE))

        return self.redirect('/config/general/')
