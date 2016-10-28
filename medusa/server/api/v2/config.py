# coding=utf-8
"""Request handler for configuration."""

import platform
import sys

import medusa as app

from six import text_type
from .base import BaseRequestHandler


class ConfigHandler(BaseRequestHandler):
    """Config request handler."""

    def get(self, query=''):
        """Query general configuration.

        :param query:
        :type query: str
        """
        query = query.split('/')[0]

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
            'release': app.APP_VERSION,
            'sslVersion': app.OPENSSL_VERSION,
            'pythonVersion': sys.version[:120],
            'databaseVersion': {
                'major': app.MAJOR_DB_VERSION,
                'minor': app.MINOR_DB_VERSION
            },
            'os': platform.platform(),
            'locale': '.'.join([text_type(loc or 'Unknown') for loc in app.LOCALE]),
            'localUser': app.OS_USER or 'Unknown',
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
