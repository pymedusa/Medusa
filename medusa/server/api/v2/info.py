# coding=utf-8
"""Request handler for general information."""

import os
import platform
import sys

import medusa as app

from .base import BaseRequestHandler
from ....versionChecker import CheckVersion


class InfoHandler(BaseRequestHandler):
    """Info request handler."""

    def get(self, query=''):
        """Query general information.

        :param query:
        :type query: str
        """
        info_query = query.split('/')[0]

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

        info_data = {
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
            'locale': '.'.join([str(loc) for loc in app_locale]),
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
            'subtitlesMulti': app.SUBTITLES_MULTI
        }

        if info_query:
            if info_query not in info_data:
                return self.api_finish(status=404, error='{key} not found'.format(key=info_query))

        self.api_finish(data=info_data[info_query] if info_query else info_data)
