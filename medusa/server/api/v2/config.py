# coding=utf-8
"""Request handler for configuration."""

import os
import platform
import sys

import medusa as app

from six import text_type
from .base import BaseRequestHandler
from ....versionChecker import CheckVersion


class ConfigHandler(BaseRequestHandler):
    """Config request handler."""

    def get(self, query=''):
        """Query general configuration.

        :param query:
        :type query: str
        """
        query = query.split('/')[0]

        try:
            import pwd
            app_user = pwd.getpwuid(os.getuid()).pw_name
        except ImportError:
            try:
                import getpass
                app_user = getpass.getuser()
            except StandardError:
                app_user = 'Unknown'

        try:
            import locale
            app_locale = locale.getdefaultlocale()
        except StandardError:
            app_locale = 'Unknown', 'Unknown'

        try:
            import ssl
            ssl_version = ssl.OPENSSL_VERSION
        except StandardError:
            ssl_version = 'Unknown'

        app_version = ''
        if app.VERSION_NOTIFY:
            updater = CheckVersion().updater
            if updater:
                app_version = updater.get_cur_version()

        main_db_con = app.db.DBConnection()
        cur_branch_major_db_version, cur_branch_minor_db_version = main_db_con.checkDBVersion()

        config_data = {
            'anonRedirect': app.ANON_REDIRECT,
            'anonSplitHome': app.ANIME_SPLIT_HOME,
            'comingEpsLayout': app.COMING_EPS_LAYOUT,
            'comingEpsSort': app.COMING_EPS_SORT,
            'datePreset': app.DATE_PRESET,
            'fuzzyDating': app.FUZZY_DATING,
            'historyLayout': app.HISTORY_LAYOUT,
            'homeLayout': app.HOME_LAYOUT,
            'themeName': app.THEME_NAME,
            'posterSortby': app.POSTER_SORTBY,
            'posterSortdir': app.POSTER_SORTDIR,
            'rootDirs': app.ROOT_DIRS,
            'sortArticle': app.SORT_ARTICLE,
            'timePreset': app.TIME_PRESET,
            'trimZero': app.TRIM_ZERO,
            'fanartBackground': app.FANART_BACKGROUND,
            'fanartBackgroundOpacity': app.FANART_BACKGROUND_OPACITY,
            'branch': app.BRANCH,
            'commitHash': app.CUR_COMMIT_HASH,
            'release': app_version,
            'sslVersion': ssl_version,
            'pythonVersion': sys.version[:120],
            'databaseVersion': {
                'major': cur_branch_major_db_version,
                'minor': cur_branch_minor_db_version
            },
            'os': platform.platform(),
            'locale': '.'.join([text_type(loc) for loc in app_locale]),
            'localUser': app_user,
            'programDir': app.PROG_DIR,
            'configFile': app.CONFIG_FILE,
            'dbFilename': app.db.dbFilename(),
            'cacheDir': app.CACHE_DIR,
            'logDir': app.LOG_DIR,
            'appArgs': app.MY_ARGS,
            'webRoot': app.WEB_ROOT,
            'githubUrl': app.GITHUB_IO_URL,
            'wikiUrl': app.WIKI_URL,
            'sourceUrl': app.APPLICATION_URL,
            'displayAllSeasons': app.DISPLAY_ALL_SEASONS,
            'displayShowSpecials': app.DISPLAY_SHOW_SPECIALS,
            'useSubtitles': app.USE_SUBTITLES,
            'downloadUrl': app.DOWNLOAD_URL,
            'subtitlesMulti': app.SUBTITLES_MULTI,
            'kodi': {
                'enabled': bool(app.USE_KODI and app.KODI_UPDATE_LIBRARY)
            },
            'plex': {
                'enabled': bool(app.USE_PLEX_SERVER and app.PLEX_UPDATE_LIBRARY)
            },
            'emby': {
                'enabled': bool(app.USE_EMBY)
            },
            'torrents': {
                'enabled': bool(app.USE_TORRENTS and app.TORRENT_METHOD != 'blackhole' and
                                (app.ENABLE_HTTPS and app.TORRENT_HOST[:5] == 'https' or not
                                 app.ENABLE_HTTPS and app.TORRENT_HOST[:5] == 'http:'))
            }
        }

        if query:
            if query not in config_data:
                return self.api_finish(status=404, error='{key} not found'.format(key=query))

        self.api_finish(data=config_data[query] if query else config_data)
