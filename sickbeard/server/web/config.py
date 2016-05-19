# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# Git: https://github.com/PyMedusa/SickRage.git
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.

# pylint: disable=abstract-method,too-many-lines

import os
import time
from tornado.routes import route
from unrar2 import RarFile

import sickbeard
from sickbeard import (
    config, helpers, logger, naming,
    subtitles, ui,
)
from sickbeard.common import (
    Quality, WANTED,
)
from sickbeard.providers import newznab, rsstorrent
from sickbeard.versionChecker import CheckVersion
from sickrage.helper.common import try_int
from sickrage.helper.encoding import ek
from sickrage.helper.exceptions import ex
from sickrage.providers.GenericProvider import GenericProvider
from sickbeard.server.web.core import WebRoot, PageTemplate

# Conditional imports
try:
    import json
except ImportError:
    import simplejson as json


@route('/config(/?.*)')
class Config(WebRoot):
    def __init__(self, *args, **kwargs):
        super(Config, self).__init__(*args, **kwargs)

    @staticmethod
    def ConfigMenu():
        menu = [
            {'title': 'General', 'path': 'config/general/', 'icon': 'menu-icon-config'},
            {'title': 'Backup/Restore', 'path': 'config/backuprestore/', 'icon': 'menu-icon-backup'},
            {'title': 'Search Settings', 'path': 'config/search/', 'icon': 'menu-icon-manage-searches'},
            {'title': 'Search Providers', 'path': 'config/providers/', 'icon': 'menu-icon-provider'},
            {'title': 'Subtitles Settings', 'path': 'config/subtitles/', 'icon': 'menu-icon-backlog'},
            {'title': 'Post Processing', 'path': 'config/postProcessing/', 'icon': 'menu-icon-postprocess'},
            {'title': 'Notifications', 'path': 'config/notifications/', 'icon': 'menu-icon-notification'},
            {'title': 'Anime', 'path': 'config/anime/', 'icon': 'menu-icon-anime'},
        ]

        return menu

    def index(self):
        t = PageTemplate(rh=self, filename="config.mako")

        try:
            import pwd
            sr_user = pwd.getpwuid(os.getuid()).pw_name
        except ImportError:
            try:
                import getpass
                sr_user = getpass.getuser()
            except StandardError:
                sr_user = 'Unknown'

        try:
            import locale
            sr_locale = locale.getdefaultlocale()
        except StandardError:
            sr_locale = 'Unknown', 'Unknown'

        try:
            import ssl
            ssl_version = ssl.OPENSSL_VERSION
        except StandardError:
            ssl_version = 'Unknown'

        sr_version = ''
        if sickbeard.VERSION_NOTIFY:
            updater = CheckVersion().updater
            if updater:
                sr_version = updater.get_cur_version()

        return t.render(
            submenu=self.ConfigMenu(), title='Medusa Configuration',
            header='Medusa Configuration', topmenu="config",
            sr_user=sr_user, sr_locale=sr_locale, ssl_version=ssl_version,
            sr_version=sr_version
        )


@route('/config/general(/?.*)')
class ConfigGeneral(Config):
    def __init__(self, *args, **kwargs):
        super(ConfigGeneral, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename="config_general.mako")

        return t.render(title='Config - General', header='General Configuration',
                        topmenu='config', submenu=self.ConfigMenu(),
                        controller="config", action="index")

    @staticmethod
    def generateApiKey():
        return helpers.generateApiKey()

    @staticmethod
    def saveRootDirs(rootDirString=None):
        sickbeard.ROOT_DIRS = rootDirString

    @staticmethod
    def saveAddShowDefaults(defaultStatus, anyQualities, bestQualities, defaultFlattenFolders, subtitles=False,
                            anime=False, scene=False, defaultStatusAfter=WANTED):

        if anyQualities:
            anyQualities = anyQualities.split(',')
        else:
            anyQualities = []

        if bestQualities:
            bestQualities = bestQualities.split(',')
        else:
            bestQualities = []

        newQuality = Quality.combineQualities([int(quality) for quality in anyQualities], [int(quality) for quality in bestQualities])

        sickbeard.STATUS_DEFAULT = int(defaultStatus)
        sickbeard.STATUS_DEFAULT_AFTER = int(defaultStatusAfter)
        sickbeard.QUALITY_DEFAULT = int(newQuality)

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
                    git_reset=None, git_username=None, git_password=None, display_all_seasons=None, subliminal_log=None):

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
            sickbeard.TIME_PRESET = sickbeard.TIME_PRESET_W_SECONDS.replace(u":%S", u"")

        sickbeard.TIMEZONE_DISPLAY = timezone_display

        if not config.change_LOG_DIR(log_dir, web_log):
            results += ["Unable to create directory " + ek(os.path.normpath, log_dir) + ", log directory not changed."]

        sickbeard.API_KEY = api_key

        sickbeard.ENABLE_HTTPS = config.checkbox_to_value(enable_https)

        if not config.change_HTTPS_CERT(https_cert):
            results += [
                "Unable to create directory " + ek(os.path.normpath, https_cert) + ", https cert directory not changed."]

        if not config.change_HTTPS_KEY(https_key):
            results += [
                "Unable to create directory " + ek(os.path.normpath, https_key) + ", https key directory not changed."]

        sickbeard.HANDLE_REVERSE_PROXY = config.checkbox_to_value(handle_reverse_proxy)

        sickbeard.THEME_NAME = theme_name

        sickbeard.DEFAULT_PAGE = default_page

        sickbeard.save_config()

        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                                   '<br>\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', ek(os.path.join, sickbeard.CONFIG_FILE))

        return self.redirect("/config/general/")


@route('/config/backuprestore(/?.*)')
class ConfigBackupRestore(Config):
    def __init__(self, *args, **kwargs):
        super(ConfigBackupRestore, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename="config_backuprestore.mako")

        return t.render(submenu=self.ConfigMenu(), title='Config - Backup/Restore',
                        header='Backup/Restore', topmenu='config',
                        controller="config", action="backupRestore")

    @staticmethod
    def backup(backupDir=None):

        finalResult = ''

        if backupDir:
            source = [ek(os.path.join, sickbeard.DATA_DIR, 'sickbeard.db'), sickbeard.CONFIG_FILE,
                      ek(os.path.join, sickbeard.DATA_DIR, 'failed.db'),
                      ek(os.path.join, sickbeard.DATA_DIR, 'cache.db')]
            target = ek(os.path.join, backupDir, 'medusa-' + time.strftime('%Y%m%d%H%M%S') + '.zip')

            for (path, dirs, files) in ek(os.walk, sickbeard.CACHE_DIR, topdown=True):
                for dirname in dirs:
                    if path == sickbeard.CACHE_DIR and dirname not in ['images']:
                        dirs.remove(dirname)
                for filename in files:
                    source.append(ek(os.path.join, path, filename))

            if helpers.backupConfigZip(source, target, sickbeard.DATA_DIR):
                finalResult += "Successful backup to " + target
            else:
                finalResult += "Backup FAILED"
        else:
            finalResult += "You need to choose a folder to save your backup to!"

        finalResult += "<br>\n"

        return finalResult

    @staticmethod
    def restore(backupFile=None):

        finalResult = ''

        if backupFile:
            source = backupFile
            target_dir = ek(os.path.join, sickbeard.DATA_DIR, 'restore')

            if helpers.restoreConfigZip(source, target_dir):
                finalResult += "Successfully extracted restore files to " + target_dir
                finalResult += "<br>Restart Medusa to complete the restore."
            else:
                finalResult += "Restore FAILED"
        else:
            finalResult += "You need to select a backup file to restore!"

        finalResult += "<br>\n"

        return finalResult


@route('/config/search(/?.*)')
class ConfigSearch(Config):
    def __init__(self, *args, **kwargs):
        super(ConfigSearch, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename="config_search.mako")

        return t.render(submenu=self.ConfigMenu(), title='Config - Episode Search',
                        header='Search Settings', topmenu='config',
                        controller="config", action="search")

    def saveSearch(self, use_nzbs=None, use_torrents=None, nzb_dir=None, sab_username=None, sab_password=None,
                   sab_apikey=None, sab_category=None, sab_category_anime=None, sab_category_backlog=None, sab_category_anime_backlog=None, sab_host=None, nzbget_username=None,
                   nzbget_password=None, nzbget_category=None, nzbget_category_backlog=None, nzbget_category_anime=None, nzbget_category_anime_backlog=None, nzbget_priority=None,
                   nzbget_host=None, nzbget_use_https=None, backlog_days=None, backlog_frequency=None,
                   dailysearch_frequency=None, nzb_method=None, torrent_method=None, usenet_retention=None,
                   download_propers=None, check_propers_interval=None, allow_high_priority=None, sab_forced=None,
                   randomize_providers=None, use_failed_downloads=None, delete_failed=None,
                   torrent_dir=None, torrent_username=None, torrent_password=None, torrent_host=None,
                   torrent_label=None, torrent_label_anime=None, torrent_path=None, torrent_verify_cert=None,
                   torrent_seed_time=None, torrent_paused=None, torrent_high_bandwidth=None,
                   torrent_rpcurl=None, torrent_auth_type=None, ignore_words=None, preferred_words=None, undesired_words=None, trackers_list=None, require_words=None, ignored_subs_list=None, ignore_und_subs=None):

        results = []

        if not config.change_NZB_DIR(nzb_dir):
            results += ["Unable to create directory " + ek(os.path.normpath, nzb_dir) + ", dir not changed."]

        if not config.change_TORRENT_DIR(torrent_dir):
            results += ["Unable to create directory " + ek(os.path.normpath, torrent_dir) + ", dir not changed."]

        config.change_DAILYSEARCH_FREQUENCY(dailysearch_frequency)

        config.change_BACKLOG_FREQUENCY(backlog_frequency)
        sickbeard.BACKLOG_DAYS = try_int(backlog_days, 7)

        sickbeard.USE_NZBS = config.checkbox_to_value(use_nzbs)
        sickbeard.USE_TORRENTS = config.checkbox_to_value(use_torrents)

        sickbeard.NZB_METHOD = nzb_method
        sickbeard.TORRENT_METHOD = torrent_method
        sickbeard.USENET_RETENTION = try_int(usenet_retention, 500)

        sickbeard.IGNORE_WORDS = ignore_words if ignore_words else ""
        sickbeard.PREFERRED_WORDS = preferred_words if preferred_words else ""
        sickbeard.UNDESIRED_WORDS = undesired_words if undesired_words else ""
        sickbeard.TRACKERS_LIST = trackers_list if trackers_list else ""
        sickbeard.REQUIRE_WORDS = require_words if require_words else ""
        sickbeard.IGNORED_SUBS_LIST = ignored_subs_list if ignored_subs_list else ""
        sickbeard.IGNORE_UND_SUBS = config.checkbox_to_value(ignore_und_subs)

        sickbeard.RANDOMIZE_PROVIDERS = config.checkbox_to_value(randomize_providers)

        config.change_DOWNLOAD_PROPERS(download_propers)

        sickbeard.CHECK_PROPERS_INTERVAL = check_propers_interval

        sickbeard.ALLOW_HIGH_PRIORITY = config.checkbox_to_value(allow_high_priority)

        sickbeard.USE_FAILED_DOWNLOADS = config.checkbox_to_value(use_failed_downloads)
        sickbeard.DELETE_FAILED = config.checkbox_to_value(delete_failed)

        sickbeard.SAB_USERNAME = sab_username
        sickbeard.SAB_PASSWORD = sab_password
        sickbeard.SAB_APIKEY = sab_apikey.strip()
        sickbeard.SAB_CATEGORY = sab_category
        sickbeard.SAB_CATEGORY_BACKLOG = sab_category_backlog
        sickbeard.SAB_CATEGORY_ANIME = sab_category_anime
        sickbeard.SAB_CATEGORY_ANIME_BACKLOG = sab_category_anime_backlog
        sickbeard.SAB_HOST = config.clean_url(sab_host)
        sickbeard.SAB_FORCED = config.checkbox_to_value(sab_forced)

        sickbeard.NZBGET_USERNAME = nzbget_username
        sickbeard.NZBGET_PASSWORD = nzbget_password
        sickbeard.NZBGET_CATEGORY = nzbget_category
        sickbeard.NZBGET_CATEGORY_BACKLOG = nzbget_category_backlog
        sickbeard.NZBGET_CATEGORY_ANIME = nzbget_category_anime
        sickbeard.NZBGET_CATEGORY_ANIME_BACKLOG = nzbget_category_anime_backlog
        sickbeard.NZBGET_HOST = config.clean_host(nzbget_host)
        sickbeard.NZBGET_USE_HTTPS = config.checkbox_to_value(nzbget_use_https)
        sickbeard.NZBGET_PRIORITY = try_int(nzbget_priority, 100)

        sickbeard.TORRENT_USERNAME = torrent_username
        sickbeard.TORRENT_PASSWORD = torrent_password
        sickbeard.TORRENT_LABEL = torrent_label
        sickbeard.TORRENT_LABEL_ANIME = torrent_label_anime
        sickbeard.TORRENT_VERIFY_CERT = config.checkbox_to_value(torrent_verify_cert)
        sickbeard.TORRENT_PATH = torrent_path.rstrip('/\\')
        sickbeard.TORRENT_SEED_TIME = torrent_seed_time
        sickbeard.TORRENT_PAUSED = config.checkbox_to_value(torrent_paused)
        sickbeard.TORRENT_HIGH_BANDWIDTH = config.checkbox_to_value(torrent_high_bandwidth)
        sickbeard.TORRENT_HOST = config.clean_url(torrent_host)
        sickbeard.TORRENT_RPCURL = torrent_rpcurl
        sickbeard.TORRENT_AUTH_TYPE = torrent_auth_type

        sickbeard.save_config()

        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                                   '<br>\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', ek(os.path.join, sickbeard.CONFIG_FILE))

        return self.redirect("/config/search/")


@route('/config/postProcessing(/?.*)')
class ConfigPostProcessing(Config):
    def __init__(self, *args, **kwargs):
        super(ConfigPostProcessing, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename="config_postProcessing.mako")

        return t.render(submenu=self.ConfigMenu(), title='Config - Post Processing',
                        header='Post Processing', topmenu='config',
                        controller="config", action="postProcessing")

    def savePostProcessing(self, kodi_data=None, kodi_12plus_data=None,
                           mediabrowser_data=None, sony_ps3_data=None,
                           wdtv_data=None, tivo_data=None, mede8er_data=None,
                           keep_processed_dir=None, process_method=None,
                           del_rar_contents=None, process_automatically=None,
                           no_delete=None, rename_episodes=None, airdate_episodes=None,
                           file_timestamp_timezone=None, unpack=None,
                           move_associated_files=None, sync_files=None,
                           postpone_if_sync_files=None, postpone_if_no_subs=None,
                           allowed_extensions=None, tv_download_dir=None,
                           create_missing_show_dirs=None, add_shows_wo_dir=None,
                           extra_scripts=None, nfo_rename=None,
                           naming_pattern=None, naming_multi_ep=None,
                           naming_custom_abd=None, naming_anime=None,
                           naming_abd_pattern=None, naming_strip_year=None,
                           naming_custom_sports=None, naming_sports_pattern=None,
                           naming_custom_anime=None, naming_anime_pattern=None,
                           naming_anime_multi_ep=None, autopostprocesser_frequency=None):

        results = []

        if not config.change_TV_DOWNLOAD_DIR(tv_download_dir):
            results += ["Unable to create directory " + ek(os.path.normpath, tv_download_dir) + ", dir not changed."]

        config.change_AUTOPOSTPROCESSER_FREQUENCY(autopostprocesser_frequency)
        config.change_PROCESS_AUTOMATICALLY(process_automatically)

        if unpack:
            if self.isRarSupported() != 'not supported':
                sickbeard.UNPACK = config.checkbox_to_value(unpack)
            else:
                sickbeard.UNPACK = 0
                results.append("Unpacking Not Supported, disabling unpack setting")
        else:
            sickbeard.UNPACK = config.checkbox_to_value(unpack)
        sickbeard.NO_DELETE = config.checkbox_to_value(no_delete)
        sickbeard.KEEP_PROCESSED_DIR = config.checkbox_to_value(keep_processed_dir)
        sickbeard.CREATE_MISSING_SHOW_DIRS = config.checkbox_to_value(create_missing_show_dirs)
        sickbeard.ADD_SHOWS_WO_DIR = config.checkbox_to_value(add_shows_wo_dir)
        sickbeard.PROCESS_METHOD = process_method
        sickbeard.DELRARCONTENTS = config.checkbox_to_value(del_rar_contents)
        sickbeard.EXTRA_SCRIPTS = [x.strip() for x in extra_scripts.split('|') if x.strip()]
        sickbeard.RENAME_EPISODES = config.checkbox_to_value(rename_episodes)
        sickbeard.AIRDATE_EPISODES = config.checkbox_to_value(airdate_episodes)
        sickbeard.FILE_TIMESTAMP_TIMEZONE = file_timestamp_timezone
        sickbeard.MOVE_ASSOCIATED_FILES = config.checkbox_to_value(move_associated_files)
        sickbeard.SYNC_FILES = sync_files
        sickbeard.POSTPONE_IF_SYNC_FILES = config.checkbox_to_value(postpone_if_sync_files)
        sickbeard.POSTPONE_IF_NO_SUBS = config.checkbox_to_value(postpone_if_no_subs)
        # If 'postpone if no subs' is enabled, we must have SRT in allowed extensions list
        if sickbeard.POSTPONE_IF_NO_SUBS:
            allowed_extensions += ',srt'
            # Auto PP must be disabled because FINDSUBTITLE thread that calls manual PP (like nzbtomedia)
            #sickbeard.PROCESS_AUTOMATICALLY = 0
        sickbeard.ALLOWED_EXTENSIONS = ','.join({x.strip() for x in allowed_extensions.split(',') if x.strip()})
        sickbeard.NAMING_CUSTOM_ABD = config.checkbox_to_value(naming_custom_abd)
        sickbeard.NAMING_CUSTOM_SPORTS = config.checkbox_to_value(naming_custom_sports)
        sickbeard.NAMING_CUSTOM_ANIME = config.checkbox_to_value(naming_custom_anime)
        sickbeard.NAMING_STRIP_YEAR = config.checkbox_to_value(naming_strip_year)
        sickbeard.NFO_RENAME = config.checkbox_to_value(nfo_rename)

        sickbeard.METADATA_KODI = kodi_data
        sickbeard.METADATA_KODI_12PLUS = kodi_12plus_data
        sickbeard.METADATA_MEDIABROWSER = mediabrowser_data
        sickbeard.METADATA_PS3 = sony_ps3_data
        sickbeard.METADATA_WDTV = wdtv_data
        sickbeard.METADATA_TIVO = tivo_data
        sickbeard.METADATA_MEDE8ER = mede8er_data

        sickbeard.metadata_provider_dict['KODI'].set_config(sickbeard.METADATA_KODI)
        sickbeard.metadata_provider_dict['KODI 12+'].set_config(sickbeard.METADATA_KODI_12PLUS)
        sickbeard.metadata_provider_dict['MediaBrowser'].set_config(sickbeard.METADATA_MEDIABROWSER)
        sickbeard.metadata_provider_dict['Sony PS3'].set_config(sickbeard.METADATA_PS3)
        sickbeard.metadata_provider_dict['WDTV'].set_config(sickbeard.METADATA_WDTV)
        sickbeard.metadata_provider_dict['TIVO'].set_config(sickbeard.METADATA_TIVO)
        sickbeard.metadata_provider_dict['Mede8er'].set_config(sickbeard.METADATA_MEDE8ER)

        if self.isNamingValid(naming_pattern, naming_multi_ep, anime_type=naming_anime) != "invalid":
            sickbeard.NAMING_PATTERN = naming_pattern
            sickbeard.NAMING_MULTI_EP = int(naming_multi_ep)
            sickbeard.NAMING_ANIME = int(naming_anime)
            sickbeard.NAMING_FORCE_FOLDERS = naming.check_force_season_folders()
        else:
            if int(naming_anime) in [1, 2]:
                results.append("You tried saving an invalid anime naming config, not saving your naming settings")
            else:
                results.append("You tried saving an invalid naming config, not saving your naming settings")

        if self.isNamingValid(naming_anime_pattern, naming_anime_multi_ep, anime_type=naming_anime) != "invalid":
            sickbeard.NAMING_ANIME_PATTERN = naming_anime_pattern
            sickbeard.NAMING_ANIME_MULTI_EP = int(naming_anime_multi_ep)
            sickbeard.NAMING_ANIME = int(naming_anime)
            sickbeard.NAMING_FORCE_FOLDERS = naming.check_force_season_folders()
        else:
            if int(naming_anime) in [1, 2]:
                results.append("You tried saving an invalid anime naming config, not saving your naming settings")
            else:
                results.append("You tried saving an invalid naming config, not saving your naming settings")

        if self.isNamingValid(naming_abd_pattern, None, abd=True) != "invalid":
            sickbeard.NAMING_ABD_PATTERN = naming_abd_pattern
        else:
            results.append(
                "You tried saving an invalid air-by-date naming config, not saving your air-by-date settings")

        if self.isNamingValid(naming_sports_pattern, None, sports=True) != "invalid":
            sickbeard.NAMING_SPORTS_PATTERN = naming_sports_pattern
        else:
            results.append(
                "You tried saving an invalid sports naming config, not saving your sports settings")

        sickbeard.save_config()

        if len(results) > 0:
            for x in results:
                logger.log(x, logger.WARNING)
            ui.notifications.error('Error(s) Saving Configuration',
                                   '<br>\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', ek(os.path.join, sickbeard.CONFIG_FILE))

        return self.redirect("/config/postProcessing/")

    @staticmethod
    def testNaming(pattern=None, multi=None, abd=False, sports=False, anime_type=None):

        if multi is not None:
            multi = int(multi)

        if anime_type is not None:
            anime_type = int(anime_type)

        result = naming.test_name(pattern, multi, abd, sports, anime_type)

        result = ek(os.path.join, result['dir'], result['name'])

        return result

    @staticmethod
    def isNamingValid(pattern=None, multi=None, abd=False, sports=False, anime_type=None):
        if pattern is None:
            return "invalid"

        if multi is not None:
            multi = int(multi)

        if anime_type is not None:
            anime_type = int(anime_type)

        # air by date shows just need one check, we don't need to worry about season folders
        if abd:
            is_valid = naming.check_valid_abd_naming(pattern)
            require_season_folders = False

        # sport shows just need one check, we don't need to worry about season folders
        elif sports:
            is_valid = naming.check_valid_sports_naming(pattern)
            require_season_folders = False

        else:
            # check validity of single and multi ep cases for the whole path
            is_valid = naming.check_valid_naming(pattern, multi, anime_type)

            # check validity of single and multi ep cases for only the file name
            require_season_folders = naming.check_force_season_folders(pattern, multi, anime_type)

        if is_valid and not require_season_folders:
            return "valid"
        elif is_valid and require_season_folders:
            return "seasonfolders"
        else:
            return "invalid"

    @staticmethod
    def isRarSupported():
        """
        Test Packing Support:
            - Simulating in memory rar extraction on test.rar file
        """

        try:
            rar_path = ek(os.path.join, sickbeard.PROG_DIR, 'lib', 'unrar2', 'test.rar')
            testing = RarFile(rar_path).read_files('*test.txt')
            if testing[0][1] == 'This is only a test.':
                return 'supported'
            logger.log(u'Rar Not Supported: Can not read the content of test file', logger.ERROR)
            return 'not supported'
        except Exception as e:
            logger.log(u'Rar Not Supported: ' + ex(e), logger.ERROR)
            return 'not supported'


@route('/config/providers(/?.*)')
class ConfigProviders(Config):
    def __init__(self, *args, **kwargs):
        super(ConfigProviders, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename="config_providers.mako")

        return t.render(submenu=self.ConfigMenu(), title='Config - Providers',
                        header='Search Providers', topmenu='config',
                        controller="config", action="providers")

    @staticmethod
    def canAddNewznabProvider(name):

        if not name:
            return json.dumps({'error': 'No Provider Name specified'})

        providerDict = dict(zip([x.get_id() for x in sickbeard.newznabProviderList], sickbeard.newznabProviderList))

        tempProvider = newznab.NewznabProvider(name, '')

        if tempProvider.get_id() in providerDict:
            return json.dumps({'error': 'Provider Name already exists as ' + providerDict[tempProvider.get_id()].name})
        else:
            return json.dumps({'success': tempProvider.get_id()})

    @staticmethod
    def saveNewznabProvider(name, url, key=''):

        if not name or not url:
            return '0'

        providerDict = dict(zip([x.name for x in sickbeard.newznabProviderList], sickbeard.newznabProviderList))

        if name in providerDict:
            if not providerDict[name].default:
                providerDict[name].name = name
                providerDict[name].url = config.clean_url(url)

            providerDict[name].key = key
            # a 0 in the key spot indicates that no key is needed
            if key == '0':
                providerDict[name].needs_auth = False
            else:
                providerDict[name].needs_auth = True

            return providerDict[name].get_id() + '|' + providerDict[name].configStr()

        else:
            newProvider = newznab.NewznabProvider(name, url, key=key)
            sickbeard.newznabProviderList.append(newProvider)
            return newProvider.get_id() + '|' + newProvider.configStr()

    @staticmethod
    def getNewznabCategories(name, url, key):
        """
        Retrieves a list of possible categories with category id's
        Using the default url/api?cat
        http://yournewznaburl.com/api?t=caps&apikey=yourapikey
        """
        error = ""

        if not name:
            error += "\nNo Provider Name specified"
        if not url:
            error += "\nNo Provider Url specified"
        if not key:
            error += "\nNo Provider Api key specified"

        if error != "":
            return json.dumps({'success': False, 'error': error})

        # Get list with Newznabproviders
        # providerDict = dict(zip([x.get_id() for x in sickbeard.newznabProviderList], sickbeard.newznabProviderList))

        # Get newznabprovider obj with provided name
        tempProvider = newznab.NewznabProvider(name, url, key)

        success, tv_categories, error = tempProvider.get_newznab_categories()

        return json.dumps({'success': success, 'tv_categories': tv_categories, 'error': error})

    @staticmethod
    def deleteNewznabProvider(nnid):

        providerDict = dict(zip([x.get_id() for x in sickbeard.newznabProviderList], sickbeard.newznabProviderList))

        if nnid not in providerDict or providerDict[nnid].default:
            return '0'

        # delete it from the list
        sickbeard.newznabProviderList.remove(providerDict[nnid])

        if nnid in sickbeard.PROVIDER_ORDER:
            sickbeard.PROVIDER_ORDER.remove(nnid)

        return '1'

    @staticmethod
    def canAddTorrentRssProvider(name, url, cookies, titleTAG):

        if not name:
            return json.dumps({'error': 'Invalid name specified'})

        providerDict = dict(
            zip([x.get_id() for x in sickbeard.torrentRssProviderList], sickbeard.torrentRssProviderList))

        tempProvider = rsstorrent.TorrentRssProvider(name, url, cookies, titleTAG)

        if tempProvider.get_id() in providerDict:
            return json.dumps({'error': 'Exists as ' + providerDict[tempProvider.get_id()].name})
        else:
            (succ, errMsg) = tempProvider.validateRSS()
            if succ:
                return json.dumps({'success': tempProvider.get_id()})
            else:
                return json.dumps({'error': errMsg})

    @staticmethod
    def saveTorrentRssProvider(name, url, cookies, titleTAG):

        if not name or not url:
            return '0'

        providerDict = dict(zip([x.name for x in sickbeard.torrentRssProviderList], sickbeard.torrentRssProviderList))

        if name in providerDict:
            providerDict[name].name = name
            providerDict[name].url = config.clean_url(url)
            providerDict[name].cookies = cookies
            providerDict[name].titleTAG = titleTAG

            return providerDict[name].get_id() + '|' + providerDict[name].configStr()

        else:
            newProvider = rsstorrent.TorrentRssProvider(name, url, cookies, titleTAG)
            sickbeard.torrentRssProviderList.append(newProvider)
            return newProvider.get_id() + '|' + newProvider.configStr()

    @staticmethod
    def deleteTorrentRssProvider(id):

        providerDict = dict(
            zip([x.get_id() for x in sickbeard.torrentRssProviderList], sickbeard.torrentRssProviderList))

        if id not in providerDict:
            return '0'

        # delete it from the list
        sickbeard.torrentRssProviderList.remove(providerDict[id])

        if id in sickbeard.PROVIDER_ORDER:
            sickbeard.PROVIDER_ORDER.remove(id)

        return '1'

    def saveProviders(self, newznab_string='', torrentrss_string='', provider_order=None, **kwargs):
        results = []

        provider_str_list = provider_order.split()
        provider_list = []

        newznabProviderDict = dict(
            zip([x.get_id() for x in sickbeard.newznabProviderList], sickbeard.newznabProviderList))

        finishedNames = []

        # add all the newznab info we got into our list
        if newznab_string:
            for curNewznabProviderStr in newznab_string.split('!!!'):

                if not curNewznabProviderStr:
                    continue

                cur_name, cur_url, cur_key, cur_cat = curNewznabProviderStr.split('|')
                cur_url = config.clean_url(cur_url)

                newProvider = newznab.NewznabProvider(cur_name, cur_url, key=cur_key, catIDs=cur_cat)

                cur_id = newProvider.get_id()

                # if it already exists then update it
                if cur_id in newznabProviderDict:
                    newznabProviderDict[cur_id].name = cur_name
                    newznabProviderDict[cur_id].url = cur_url
                    newznabProviderDict[cur_id].key = cur_key
                    newznabProviderDict[cur_id].catIDs = cur_cat
                    # a 0 in the key spot indicates that no key is needed
                    if cur_key == '0':
                        newznabProviderDict[cur_id].needs_auth = False
                    else:
                        newznabProviderDict[cur_id].needs_auth = True

                    try:
                        newznabProviderDict[cur_id].search_mode = str(kwargs[cur_id + '_search_mode']).strip()
                    except (AttributeError, KeyError):
                        pass  # these exceptions are actually catching unselected checkboxes

                    try:
                        newznabProviderDict[cur_id].search_fallback = config.checkbox_to_value(
                            kwargs[cur_id + '_search_fallback'])
                    except (AttributeError, KeyError):
                        newznabProviderDict[cur_id].search_fallback = 0  # these exceptions are actually catching unselected checkboxes

                    try:
                        newznabProviderDict[cur_id].enable_daily = config.checkbox_to_value(
                            kwargs[cur_id + '_enable_daily'])
                    except (AttributeError, KeyError):
                        newznabProviderDict[cur_id].enable_daily = 0  # these exceptions are actually catching unselected checkboxes

                    try:
                        newznabProviderDict[cur_id].enable_manualsearch = config.checkbox_to_value(
                            kwargs[cur_id + '_enable_manualsearch'])
                    except (AttributeError, KeyError):
                        newznabProviderDict[cur_id].enable_manualsearch = 0  # these exceptions are actually catching unselected checkboxes

                    try:
                        newznabProviderDict[cur_id].enable_backlog = config.checkbox_to_value(
                            kwargs[cur_id + '_enable_backlog'])
                    except (AttributeError, KeyError):
                        newznabProviderDict[cur_id].enable_backlog = 0  # these exceptions are actually catching unselected checkboxes
                else:
                    sickbeard.newznabProviderList.append(newProvider)

                finishedNames.append(cur_id)

        # delete anything that is missing
        for cur_provider in sickbeard.newznabProviderList:
            if cur_provider.get_id() not in finishedNames:
                sickbeard.newznabProviderList.remove(cur_provider)

        torrentRssProviderDict = dict(
            zip([x.get_id() for x in sickbeard.torrentRssProviderList], sickbeard.torrentRssProviderList))
        finishedNames = []

        if torrentrss_string:
            for curTorrentRssProviderStr in torrentrss_string.split('!!!'):

                if not curTorrentRssProviderStr:
                    continue

                curName, curURL, curCookies, curTitleTAG = curTorrentRssProviderStr.split('|')
                curURL = config.clean_url(curURL)

                newProvider = rsstorrent.TorrentRssProvider(curName, curURL, curCookies, curTitleTAG)

                curID = newProvider.get_id()

                # if it already exists then update it
                if curID in torrentRssProviderDict:
                    torrentRssProviderDict[curID].name = curName
                    torrentRssProviderDict[curID].url = curURL
                    torrentRssProviderDict[curID].cookies = curCookies
                    torrentRssProviderDict[curID].curTitleTAG = curTitleTAG
                else:
                    sickbeard.torrentRssProviderList.append(newProvider)

                finishedNames.append(curID)

        # delete anything that is missing
        for cur_provider in sickbeard.torrentRssProviderList:
            if cur_provider.get_id() not in finishedNames:
                sickbeard.torrentRssProviderList.remove(cur_provider)

        disabled_list = []
        # do the enable/disable
        for cur_providerStr in provider_str_list:
            cur_provider, curEnabled = cur_providerStr.split(':')
            curEnabled = try_int(curEnabled)

            curProvObj = [x for x in sickbeard.providers.sortedProviderList() if
                          x.get_id() == cur_provider and hasattr(x, 'enabled')]
            if curProvObj:
                curProvObj[0].enabled = bool(curEnabled)

            if curEnabled:
                provider_list.append(cur_provider)
            else:
                disabled_list.append(cur_provider)

            if cur_provider in newznabProviderDict:
                newznabProviderDict[cur_provider].enabled = bool(curEnabled)
            elif cur_provider in torrentRssProviderDict:
                torrentRssProviderDict[cur_provider].enabled = bool(curEnabled)

        provider_list = provider_list + disabled_list

        # dynamically load provider settings
        for curTorrentProvider in [prov for prov in sickbeard.providers.sortedProviderList() if
                                   prov.provider_type == GenericProvider.TORRENT]:

            if hasattr(curTorrentProvider, 'custom_url'):
                try:
                    curTorrentProvider.custom_url = str(kwargs[curTorrentProvider.get_id() + '_custom_url']).strip()
                except (AttributeError, KeyError):
                    curTorrentProvider.custom_url = None  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'minseed'):
                try:
                    curTorrentProvider.minseed = int(str(kwargs[curTorrentProvider.get_id() + '_minseed']).strip())
                except (AttributeError, KeyError):
                    curTorrentProvider.minseed = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'minleech'):
                try:
                    curTorrentProvider.minleech = int(str(kwargs[curTorrentProvider.get_id() + '_minleech']).strip())
                except (AttributeError, KeyError):
                    curTorrentProvider.minleech = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'ratio'):
                try:
                    ratio = float(str(kwargs[curTorrentProvider.get_id() + '_ratio']).strip())
                    curTorrentProvider.ratio = (ratio, -1)[ratio < 0]
                except (AttributeError, KeyError, ValueError):
                    curTorrentProvider.ratio = None  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'digest'):
                try:
                    curTorrentProvider.digest = str(kwargs[curTorrentProvider.get_id() + '_digest']).strip()
                except (AttributeError, KeyError):
                    curTorrentProvider.digest = None  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'hash'):
                try:
                    curTorrentProvider.hash = str(kwargs[curTorrentProvider.get_id() + '_hash']).strip()
                except (AttributeError, KeyError):
                    curTorrentProvider.hash = None  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'api_key'):
                try:
                    curTorrentProvider.api_key = str(kwargs[curTorrentProvider.get_id() + '_api_key']).strip()
                except (AttributeError, KeyError):
                    curTorrentProvider.api_key = None  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'username'):
                try:
                    curTorrentProvider.username = str(kwargs[curTorrentProvider.get_id() + '_username']).strip()
                except (AttributeError, KeyError):
                    curTorrentProvider.username = None  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'password'):
                try:
                    curTorrentProvider.password = str(kwargs[curTorrentProvider.get_id() + '_password']).strip()
                except (AttributeError, KeyError):
                    curTorrentProvider.password = None  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'passkey'):
                try:
                    curTorrentProvider.passkey = str(kwargs[curTorrentProvider.get_id() + '_passkey']).strip()
                except (AttributeError, KeyError):
                    curTorrentProvider.passkey = None  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'pin'):
                try:
                    curTorrentProvider.pin = str(kwargs[curTorrentProvider.get_id() + '_pin']).strip()
                except (AttributeError, KeyError):
                    curTorrentProvider.pin = None  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'confirmed'):
                try:
                    curTorrentProvider.confirmed = config.checkbox_to_value(
                        kwargs[curTorrentProvider.get_id() + '_confirmed'])
                except (AttributeError, KeyError):
                    curTorrentProvider.confirmed = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'ranked'):
                try:
                    curTorrentProvider.ranked = config.checkbox_to_value(
                        kwargs[curTorrentProvider.get_id() + '_ranked'])
                except (AttributeError, KeyError):
                    curTorrentProvider.ranked = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'engrelease'):
                try:
                    curTorrentProvider.engrelease = config.checkbox_to_value(
                        kwargs[curTorrentProvider.get_id() + '_engrelease'])
                except (AttributeError, KeyError):
                    curTorrentProvider.engrelease = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'onlyspasearch'):
                try:
                    curTorrentProvider.onlyspasearch = config.checkbox_to_value(
                        kwargs[curTorrentProvider.get_id() + '_onlyspasearch'])
                except (AttributeError, KeyError):
                    curTorrentProvider.onlyspasearch = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'sorting'):
                try:
                    curTorrentProvider.sorting = str(kwargs[curTorrentProvider.get_id() + '_sorting']).strip()
                except (AttributeError, KeyError):
                    curTorrentProvider.sorting = 'seeders'  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'freeleech'):
                try:
                    curTorrentProvider.freeleech = config.checkbox_to_value(
                        kwargs[curTorrentProvider.get_id() + '_freeleech'])
                except (AttributeError, KeyError):
                    curTorrentProvider.freeleech = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'search_mode'):
                try:
                    curTorrentProvider.search_mode = str(kwargs[curTorrentProvider.get_id() + '_search_mode']).strip()
                except (AttributeError, KeyError):
                    curTorrentProvider.search_mode = 'eponly'  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'search_fallback'):
                try:
                    curTorrentProvider.search_fallback = config.checkbox_to_value(
                        kwargs[curTorrentProvider.get_id() + '_search_fallback'])
                except (AttributeError, KeyError):
                    curTorrentProvider.search_fallback = 0  # these exceptions are catching unselected checkboxes

            if hasattr(curTorrentProvider, 'enable_daily'):
                try:
                    curTorrentProvider.enable_daily = config.checkbox_to_value(
                        kwargs[curTorrentProvider.get_id() + '_enable_daily'])
                except (AttributeError, KeyError):
                    curTorrentProvider.enable_daily = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'enable_manualsearch'):
                try:
                    curTorrentProvider.enable_manualsearch = config.checkbox_to_value(
                        kwargs[curTorrentProvider.get_id() + '_enable_manualsearch'])
                except (AttributeError, KeyError):
                    curTorrentProvider.enable_manualsearch = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'enable_backlog'):
                try:
                    curTorrentProvider.enable_backlog = config.checkbox_to_value(
                        kwargs[curTorrentProvider.get_id() + '_enable_backlog'])
                except (AttributeError, KeyError):
                    curTorrentProvider.enable_backlog = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'cat'):
                try:
                    curTorrentProvider.cat = int(str(kwargs[curTorrentProvider.get_id() + '_cat']).strip())
                except (AttributeError, KeyError):
                    curTorrentProvider.cat = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curTorrentProvider, 'subtitle'):
                try:
                    curTorrentProvider.subtitle = config.checkbox_to_value(
                        kwargs[curTorrentProvider.get_id() + '_subtitle'])
                except (AttributeError, KeyError):
                    curTorrentProvider.subtitle = 0  # these exceptions are actually catching unselected checkboxes

        for curNzbProvider in [prov for prov in sickbeard.providers.sortedProviderList() if
                               prov.provider_type == GenericProvider.NZB]:

            if hasattr(curNzbProvider, 'api_key'):
                try:
                    curNzbProvider.api_key = str(kwargs[curNzbProvider.get_id() + '_api_key']).strip()
                except (AttributeError, KeyError):
                    curNzbProvider.api_key = None  # these exceptions are actually catching unselected checkboxes

            if hasattr(curNzbProvider, 'username'):
                try:
                    curNzbProvider.username = str(kwargs[curNzbProvider.get_id() + '_username']).strip()
                except (AttributeError, KeyError):
                    curNzbProvider.username = None  # these exceptions are actually catching unselected checkboxes

            if hasattr(curNzbProvider, 'search_mode'):
                try:
                    curNzbProvider.search_mode = str(kwargs[curNzbProvider.get_id() + '_search_mode']).strip()
                except (AttributeError, KeyError):
                    curNzbProvider.search_mode = 'eponly'  # these exceptions are actually catching unselected checkboxes

            if hasattr(curNzbProvider, 'search_fallback'):
                try:
                    curNzbProvider.search_fallback = config.checkbox_to_value(
                        kwargs[curNzbProvider.get_id() + '_search_fallback'])
                except (AttributeError, KeyError):
                    curNzbProvider.search_fallback = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curNzbProvider, 'enable_daily'):
                try:
                    curNzbProvider.enable_daily = config.checkbox_to_value(
                        kwargs[curNzbProvider.get_id() + '_enable_daily'])
                except (AttributeError, KeyError):
                    curNzbProvider.enable_daily = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curNzbProvider, 'enable_manualsearch'):
               try:
                   curNzbProvider.enable_manualsearch = config.checkbox_to_value(
                       kwargs[curNzbProvider.get_id() + '_enable_manualsearch'])
               except (AttributeError, KeyError):
                   curNzbProvider.enable_manualsearch = 0  # these exceptions are actually catching unselected checkboxes

            if hasattr(curNzbProvider, 'enable_backlog'):
                try:
                    curNzbProvider.enable_backlog = config.checkbox_to_value(
                        kwargs[curNzbProvider.get_id() + '_enable_backlog'])
                except (AttributeError, KeyError):
                    curNzbProvider.enable_backlog = 0  # these exceptions are actually catching unselected checkboxes

        sickbeard.NEWZNAB_DATA = '!!!'.join([x.configStr() for x in sickbeard.newznabProviderList])
        sickbeard.PROVIDER_ORDER = provider_list

        sickbeard.save_config()

        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                                   '<br>\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', ek(os.path.join, sickbeard.CONFIG_FILE))

        return self.redirect("/config/providers/")


@route('/config/notifications(/?.*)')
class ConfigNotifications(Config):
    def __init__(self, *args, **kwargs):
        super(ConfigNotifications, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename="config_notifications.mako")

        return t.render(submenu=self.ConfigMenu(), title='Config - Notifications',
                        header='Notifications', topmenu='config',
                        controller="config", action="notifications")

    def saveNotifications(self, use_kodi=None, kodi_always_on=None, kodi_notify_onsnatch=None,
                          kodi_notify_ondownload=None,
                          kodi_notify_onsubtitledownload=None, kodi_update_onlyfirst=None,
                          kodi_update_library=None, kodi_update_full=None, kodi_host=None, kodi_username=None,
                          kodi_password=None,
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
                          trakt_remove_watchlist=None, trakt_sync_watchlist=None, trakt_remove_show_from_sickrage=None, trakt_method_add=None,
                          trakt_start_paused=None, trakt_use_recommended=None, trakt_sync=None, trakt_sync_remove=None,
                          trakt_default_indexer=None, trakt_remove_serieslist=None, trakt_timeout=None, trakt_blacklist_name=None,
                          use_synologynotifier=None, synologynotifier_notify_onsnatch=None,
                          synologynotifier_notify_ondownload=None, synologynotifier_notify_onsubtitledownload=None,
                          use_pytivo=None, pytivo_notify_onsnatch=None, pytivo_notify_ondownload=None,
                          pytivo_notify_onsubtitledownload=None, pytivo_update_library=None,
                          pytivo_host=None, pytivo_share_name=None, pytivo_tivo_name=None,
                          use_nma=None, nma_notify_onsnatch=None, nma_notify_ondownload=None,
                          nma_notify_onsubtitledownload=None, nma_api=None, nma_priority=0,
                          use_pushalot=None, pushalot_notify_onsnatch=None, pushalot_notify_ondownload=None,
                          pushalot_notify_onsubtitledownload=None, pushalot_authorizationtoken=None,
                          use_pushbullet=None, pushbullet_notify_onsnatch=None, pushbullet_notify_ondownload=None,
                          pushbullet_notify_onsubtitledownload=None, pushbullet_api=None, pushbullet_device=None,
                          pushbullet_device_list=None,
                          use_email=None, email_notify_onsnatch=None, email_notify_ondownload=None,
                          email_notify_onsubtitledownload=None, email_host=None, email_port=25, email_from=None,
                          email_tls=None, email_user=None, email_password=None, email_list=None, email_subject=None, email_show_list=None,
                          email_show=None):

        results = []

        sickbeard.USE_KODI = config.checkbox_to_value(use_kodi)
        sickbeard.KODI_ALWAYS_ON = config.checkbox_to_value(kodi_always_on)
        sickbeard.KODI_NOTIFY_ONSNATCH = config.checkbox_to_value(kodi_notify_onsnatch)
        sickbeard.KODI_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(kodi_notify_ondownload)
        sickbeard.KODI_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(kodi_notify_onsubtitledownload)
        sickbeard.KODI_UPDATE_LIBRARY = config.checkbox_to_value(kodi_update_library)
        sickbeard.KODI_UPDATE_FULL = config.checkbox_to_value(kodi_update_full)
        sickbeard.KODI_UPDATE_ONLYFIRST = config.checkbox_to_value(kodi_update_onlyfirst)
        sickbeard.KODI_HOST = config.clean_hosts(kodi_host)
        sickbeard.KODI_USERNAME = kodi_username
        sickbeard.KODI_PASSWORD = kodi_password

        sickbeard.USE_PLEX_SERVER = config.checkbox_to_value(use_plex_server)
        sickbeard.PLEX_NOTIFY_ONSNATCH = config.checkbox_to_value(plex_notify_onsnatch)
        sickbeard.PLEX_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(plex_notify_ondownload)
        sickbeard.PLEX_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(plex_notify_onsubtitledownload)
        sickbeard.PLEX_UPDATE_LIBRARY = config.checkbox_to_value(plex_update_library)
        sickbeard.PLEX_CLIENT_HOST = config.clean_hosts(plex_client_host)
        sickbeard.PLEX_SERVER_HOST = config.clean_hosts(plex_server_host)
        sickbeard.PLEX_SERVER_TOKEN = config.clean_host(plex_server_token)
        sickbeard.PLEX_SERVER_USERNAME = plex_server_username
        if plex_server_password != '*' * len(sickbeard.PLEX_SERVER_PASSWORD):
            sickbeard.PLEX_SERVER_PASSWORD = plex_server_password

        sickbeard.USE_PLEX_CLIENT = config.checkbox_to_value(use_plex_client)
        sickbeard.PLEX_CLIENT_USERNAME = plex_client_username
        if plex_client_password != '*' * len(sickbeard.PLEX_CLIENT_PASSWORD):
            sickbeard.PLEX_CLIENT_PASSWORD = plex_client_password
        sickbeard.PLEX_SERVER_HTTPS = config.checkbox_to_value(plex_server_https)

        sickbeard.USE_EMBY = config.checkbox_to_value(use_emby)
        sickbeard.EMBY_HOST = config.clean_host(emby_host)
        sickbeard.EMBY_APIKEY = emby_apikey

        sickbeard.USE_GROWL = config.checkbox_to_value(use_growl)
        sickbeard.GROWL_NOTIFY_ONSNATCH = config.checkbox_to_value(growl_notify_onsnatch)
        sickbeard.GROWL_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(growl_notify_ondownload)
        sickbeard.GROWL_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(growl_notify_onsubtitledownload)
        sickbeard.GROWL_HOST = config.clean_host(growl_host, default_port=23053)
        sickbeard.GROWL_PASSWORD = growl_password

        sickbeard.USE_FREEMOBILE = config.checkbox_to_value(use_freemobile)
        sickbeard.FREEMOBILE_NOTIFY_ONSNATCH = config.checkbox_to_value(freemobile_notify_onsnatch)
        sickbeard.FREEMOBILE_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(freemobile_notify_ondownload)
        sickbeard.FREEMOBILE_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(freemobile_notify_onsubtitledownload)
        sickbeard.FREEMOBILE_ID = freemobile_id
        sickbeard.FREEMOBILE_APIKEY = freemobile_apikey

        sickbeard.USE_TELEGRAM = config.checkbox_to_value(use_telegram)
        sickbeard.TELEGRAM_NOTIFY_ONSNATCH = config.checkbox_to_value(telegram_notify_onsnatch)
        sickbeard.TELEGRAM_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(telegram_notify_ondownload)
        sickbeard.TELEGRAM_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(telegram_notify_onsubtitledownload)
        sickbeard.TELEGRAM_ID = telegram_id
        sickbeard.TELEGRAM_APIKEY = telegram_apikey

        sickbeard.USE_PROWL = config.checkbox_to_value(use_prowl)
        sickbeard.PROWL_NOTIFY_ONSNATCH = config.checkbox_to_value(prowl_notify_onsnatch)
        sickbeard.PROWL_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(prowl_notify_ondownload)
        sickbeard.PROWL_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(prowl_notify_onsubtitledownload)
        sickbeard.PROWL_API = prowl_api
        sickbeard.PROWL_PRIORITY = prowl_priority
        sickbeard.PROWL_MESSAGE_TITLE = prowl_message_title

        sickbeard.USE_TWITTER = config.checkbox_to_value(use_twitter)
        sickbeard.TWITTER_NOTIFY_ONSNATCH = config.checkbox_to_value(twitter_notify_onsnatch)
        sickbeard.TWITTER_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(twitter_notify_ondownload)
        sickbeard.TWITTER_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(twitter_notify_onsubtitledownload)
        sickbeard.TWITTER_USEDM = config.checkbox_to_value(twitter_usedm)
        sickbeard.TWITTER_DMTO = twitter_dmto

        sickbeard.USE_BOXCAR2 = config.checkbox_to_value(use_boxcar2)
        sickbeard.BOXCAR2_NOTIFY_ONSNATCH = config.checkbox_to_value(boxcar2_notify_onsnatch)
        sickbeard.BOXCAR2_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(boxcar2_notify_ondownload)
        sickbeard.BOXCAR2_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(boxcar2_notify_onsubtitledownload)
        sickbeard.BOXCAR2_ACCESSTOKEN = boxcar2_accesstoken

        sickbeard.USE_PUSHOVER = config.checkbox_to_value(use_pushover)
        sickbeard.PUSHOVER_NOTIFY_ONSNATCH = config.checkbox_to_value(pushover_notify_onsnatch)
        sickbeard.PUSHOVER_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(pushover_notify_ondownload)
        sickbeard.PUSHOVER_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(pushover_notify_onsubtitledownload)
        sickbeard.PUSHOVER_USERKEY = pushover_userkey
        sickbeard.PUSHOVER_APIKEY = pushover_apikey
        sickbeard.PUSHOVER_DEVICE = pushover_device
        sickbeard.PUSHOVER_SOUND = pushover_sound

        sickbeard.USE_LIBNOTIFY = config.checkbox_to_value(use_libnotify)
        sickbeard.LIBNOTIFY_NOTIFY_ONSNATCH = config.checkbox_to_value(libnotify_notify_onsnatch)
        sickbeard.LIBNOTIFY_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(libnotify_notify_ondownload)
        sickbeard.LIBNOTIFY_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(libnotify_notify_onsubtitledownload)

        sickbeard.USE_NMJ = config.checkbox_to_value(use_nmj)
        sickbeard.NMJ_HOST = config.clean_host(nmj_host)
        sickbeard.NMJ_DATABASE = nmj_database
        sickbeard.NMJ_MOUNT = nmj_mount

        sickbeard.USE_NMJv2 = config.checkbox_to_value(use_nmjv2)
        sickbeard.NMJv2_HOST = config.clean_host(nmjv2_host)
        sickbeard.NMJv2_DATABASE = nmjv2_database
        sickbeard.NMJv2_DBLOC = nmjv2_dbloc

        sickbeard.USE_SYNOINDEX = config.checkbox_to_value(use_synoindex)

        sickbeard.USE_SYNOLOGYNOTIFIER = config.checkbox_to_value(use_synologynotifier)
        sickbeard.SYNOLOGYNOTIFIER_NOTIFY_ONSNATCH = config.checkbox_to_value(synologynotifier_notify_onsnatch)
        sickbeard.SYNOLOGYNOTIFIER_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(synologynotifier_notify_ondownload)
        sickbeard.SYNOLOGYNOTIFIER_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(
            synologynotifier_notify_onsubtitledownload)

        config.change_USE_TRAKT(use_trakt)
        sickbeard.TRAKT_USERNAME = trakt_username
        sickbeard.TRAKT_REMOVE_WATCHLIST = config.checkbox_to_value(trakt_remove_watchlist)
        sickbeard.TRAKT_REMOVE_SERIESLIST = config.checkbox_to_value(trakt_remove_serieslist)
        sickbeard.TRAKT_REMOVE_SHOW_FROM_SICKRAGE = config.checkbox_to_value(trakt_remove_show_from_sickrage)
        sickbeard.TRAKT_SYNC_WATCHLIST = config.checkbox_to_value(trakt_sync_watchlist)
        sickbeard.TRAKT_METHOD_ADD = int(trakt_method_add)
        sickbeard.TRAKT_START_PAUSED = config.checkbox_to_value(trakt_start_paused)
        sickbeard.TRAKT_USE_RECOMMENDED = config.checkbox_to_value(trakt_use_recommended)
        sickbeard.TRAKT_SYNC = config.checkbox_to_value(trakt_sync)
        sickbeard.TRAKT_SYNC_REMOVE = config.checkbox_to_value(trakt_sync_remove)
        sickbeard.TRAKT_DEFAULT_INDEXER = int(trakt_default_indexer)
        sickbeard.TRAKT_TIMEOUT = int(trakt_timeout)
        sickbeard.TRAKT_BLACKLIST_NAME = trakt_blacklist_name

        sickbeard.USE_EMAIL = config.checkbox_to_value(use_email)
        sickbeard.EMAIL_NOTIFY_ONSNATCH = config.checkbox_to_value(email_notify_onsnatch)
        sickbeard.EMAIL_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(email_notify_ondownload)
        sickbeard.EMAIL_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(email_notify_onsubtitledownload)
        sickbeard.EMAIL_HOST = config.clean_host(email_host)
        sickbeard.EMAIL_PORT = try_int(email_port, 25)
        sickbeard.EMAIL_FROM = email_from
        sickbeard.EMAIL_TLS = config.checkbox_to_value(email_tls)
        sickbeard.EMAIL_USER = email_user
        sickbeard.EMAIL_PASSWORD = email_password
        sickbeard.EMAIL_LIST = email_list
        sickbeard.EMAIL_SUBJECT = email_subject

        sickbeard.USE_PYTIVO = config.checkbox_to_value(use_pytivo)
        sickbeard.PYTIVO_NOTIFY_ONSNATCH = config.checkbox_to_value(pytivo_notify_onsnatch)
        sickbeard.PYTIVO_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(pytivo_notify_ondownload)
        sickbeard.PYTIVO_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(pytivo_notify_onsubtitledownload)
        sickbeard.PYTIVO_UPDATE_LIBRARY = config.checkbox_to_value(pytivo_update_library)
        sickbeard.PYTIVO_HOST = config.clean_host(pytivo_host)
        sickbeard.PYTIVO_SHARE_NAME = pytivo_share_name
        sickbeard.PYTIVO_TIVO_NAME = pytivo_tivo_name

        sickbeard.USE_NMA = config.checkbox_to_value(use_nma)
        sickbeard.NMA_NOTIFY_ONSNATCH = config.checkbox_to_value(nma_notify_onsnatch)
        sickbeard.NMA_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(nma_notify_ondownload)
        sickbeard.NMA_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(nma_notify_onsubtitledownload)
        sickbeard.NMA_API = nma_api
        sickbeard.NMA_PRIORITY = nma_priority

        sickbeard.USE_PUSHALOT = config.checkbox_to_value(use_pushalot)
        sickbeard.PUSHALOT_NOTIFY_ONSNATCH = config.checkbox_to_value(pushalot_notify_onsnatch)
        sickbeard.PUSHALOT_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(pushalot_notify_ondownload)
        sickbeard.PUSHALOT_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(pushalot_notify_onsubtitledownload)
        sickbeard.PUSHALOT_AUTHORIZATIONTOKEN = pushalot_authorizationtoken

        sickbeard.USE_PUSHBULLET = config.checkbox_to_value(use_pushbullet)
        sickbeard.PUSHBULLET_NOTIFY_ONSNATCH = config.checkbox_to_value(pushbullet_notify_onsnatch)
        sickbeard.PUSHBULLET_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(pushbullet_notify_ondownload)
        sickbeard.PUSHBULLET_NOTIFY_ONSUBTITLEDOWNLOAD = config.checkbox_to_value(pushbullet_notify_onsubtitledownload)
        sickbeard.PUSHBULLET_API = pushbullet_api
        sickbeard.PUSHBULLET_DEVICE = pushbullet_device_list

        sickbeard.save_config()

        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                                   '<br>\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', ek(os.path.join, sickbeard.CONFIG_FILE))

        return self.redirect("/config/notifications/")


@route('/config/subtitles(/?.*)')
class ConfigSubtitles(Config):
    def __init__(self, *args, **kwargs):
        super(ConfigSubtitles, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename="config_subtitles.mako")

        return t.render(submenu=self.ConfigMenu(), title='Config - Subtitles',
                        header='Subtitles', topmenu='config',
                        controller="config", action="subtitles")

    def saveSubtitles(self, use_subtitles=None, subtitles_plugins=None, subtitles_languages=None, subtitles_dir=None, subtitles_perfect_match=None,
                      service_order=None, subtitles_history=None, subtitles_finder_frequency=None,
                      subtitles_multi=None, embedded_subtitles_all=None, subtitles_extra_scripts=None, subtitles_pre_scripts=None, subtitles_hearing_impaired=None,
                      addic7ed_user=None, addic7ed_pass=None, itasa_user=None, itasa_pass=None, legendastv_user=None, legendastv_pass=None, opensubtitles_user=None, opensubtitles_pass=None,
                      subtitles_download_in_pp=None, subtitles_keep_only_wanted=None):

        results = []

        config.change_SUBTITLES_FINDER_FREQUENCY(subtitles_finder_frequency)
        config.change_USE_SUBTITLES(use_subtitles)

        sickbeard.SUBTITLES_LANGUAGES = [code.strip() for code in subtitles_languages.split(',') if code.strip() in subtitles.subtitle_code_filter()] if subtitles_languages else []
        sickbeard.SUBTITLES_DIR = subtitles_dir
        sickbeard.SUBTITLES_PERFECT_MATCH = config.checkbox_to_value(subtitles_perfect_match)
        sickbeard.SUBTITLES_HISTORY = config.checkbox_to_value(subtitles_history)
        sickbeard.EMBEDDED_SUBTITLES_ALL = config.checkbox_to_value(embedded_subtitles_all)
        sickbeard.SUBTITLES_HEARING_IMPAIRED = config.checkbox_to_value(subtitles_hearing_impaired)
        sickbeard.SUBTITLES_MULTI = 1 if len(sickbeard.SUBTITLES_LANGUAGES) > 1 else config.checkbox_to_value(subtitles_multi)
        sickbeard.SUBTITLES_DOWNLOAD_IN_PP = config.checkbox_to_value(subtitles_download_in_pp)
        sickbeard.SUBTITLES_KEEP_ONLY_WANTED = config.checkbox_to_value(subtitles_keep_only_wanted)
        sickbeard.SUBTITLES_EXTRA_SCRIPTS = [x.strip() for x in subtitles_extra_scripts.split('|') if x.strip()]
        sickbeard.SUBTITLES_PRE_SCRIPTS = [x.strip() for x in subtitles_pre_scripts.split('|') if x.strip()]

        # Subtitles services
        services_str_list = service_order.split()
        subtitles_services_list = []
        subtitles_services_enabled = []
        for curServiceStr in services_str_list:
            curService, curEnabled = curServiceStr.split(':')
            subtitles_services_list.append(curService)
            subtitles_services_enabled.append(int(curEnabled))

        sickbeard.SUBTITLES_SERVICES_LIST = subtitles_services_list
        sickbeard.SUBTITLES_SERVICES_ENABLED = subtitles_services_enabled

        sickbeard.ADDIC7ED_USER = addic7ed_user or ''
        sickbeard.ADDIC7ED_PASS = addic7ed_pass or ''
        sickbeard.ITASA_USER = itasa_user or ''
        sickbeard.ITASA_PASS = itasa_pass or ''
        sickbeard.LEGENDASTV_USER = legendastv_user or ''
        sickbeard.LEGENDASTV_PASS = legendastv_pass or ''
        sickbeard.OPENSUBTITLES_USER = opensubtitles_user or ''
        sickbeard.OPENSUBTITLES_PASS = opensubtitles_pass or ''

        sickbeard.save_config()
        # Reset provider pool so next time we use the newest settings
        subtitles.get_provider_pool.invalidate()

        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                                   '<br>\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', ek(os.path.join, sickbeard.CONFIG_FILE))

        return self.redirect("/config/subtitles/")


@route('/config/anime(/?.*)')
class ConfigAnime(Config):
    def __init__(self, *args, **kwargs):
        super(ConfigAnime, self).__init__(*args, **kwargs)

    def index(self):

        t = PageTemplate(rh=self, filename="config_anime.mako")

        return t.render(submenu=self.ConfigMenu(), title='Config - Anime',
                        header='Anime', topmenu='config',
                        controller="config", action="anime")

    def saveAnime(self, use_anidb=None, anidb_username=None, anidb_password=None, anidb_use_mylist=None,
                  split_home=None):

        results = []

        sickbeard.USE_ANIDB = config.checkbox_to_value(use_anidb)
        sickbeard.ANIDB_USERNAME = anidb_username
        sickbeard.ANIDB_PASSWORD = anidb_password
        sickbeard.ANIDB_USE_MYLIST = config.checkbox_to_value(anidb_use_mylist)
        sickbeard.ANIME_SPLIT_HOME = config.checkbox_to_value(split_home)

        sickbeard.save_config()

        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                                   '<br>\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', ek(os.path.join, sickbeard.CONFIG_FILE))

        return self.redirect("/config/anime/")
