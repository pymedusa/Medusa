# coding=utf-8
"""Request handler for configuration."""

import platform
import sys
from six import text_type
import tornado
import json

from .base import BaseRequestHandler
from .... import app, db


class ConfigHandler(BaseRequestHandler):
    """Config request handler."""

    def set_default_headers(self):
        """Set default CORS headers."""
        super(ConfigHandler, self).set_default_headers()
        self.set_header('Access-Control-Allow-Methods', 'GET, PATCH, OPTIONS')

    def get(self, query=''):
        """Query general configuration.

        :param query:
        :type query: str
        """
        config_data = {
            'anonRedirect': app.ANON_REDIRECT,
            'animeSplitHome': app.ANIME_SPLIT_HOME,
            'comingEpsSort': app.COMING_EPS_SORT,
            'datePreset': app.DATE_PRESET,
            'fuzzyDating': app.FUZZY_DATING,
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
            'pythonVersion': sys.version,
            'databaseVersion': {
                'major': app.MAJOR_DB_VERSION,
                'minor': app.MINOR_DB_VERSION
            },
            'os': platform.platform(),
            'locale': '.'.join([text_type(loc or 'Unknown') for loc in app.LOCALE]),
            'localUser': app.OS_USER or 'Unknown',
            'programDir': app.PROG_DIR,
            'configFile': app.CONFIG_FILE,
            'dbFilename': db.dbFilename(),
            'cacheDir': app.CACHE_DIR,
            'logDir': app.LOG_DIR,
            'appArgs': app.MY_ARGS,
            'webRoot': app.WEB_ROOT,
            'githubUrl': app.GITHUB_IO_URL,
            'wikiUrl': app.WIKI_URL,
            'sourceUrl': app.APPLICATION_URL,
            'downloadUrl': app.DOWNLOAD_URL,
            'subtitlesMulti': app.SUBTITLES_MULTI,
            'namingForceFolders': app.NAMING_FORCE_FOLDERS,
            'subtitles': {
                'enabled': bool(app.USE_SUBTITLES)
            },
            'kodi': {
                'enabled': bool(app.USE_KODI and app.KODI_UPDATE_LIBRARY)
            },
            'plex': {
                'server': {
                    'enabled': bool(app.USE_PLEX_SERVER),
                    'notify': {
                        'snatch': bool(app.PLEX_NOTIFY_ONSNATCH),
                        'download': bool(app.PLEX_NOTIFY_ONDOWNLOAD),
                        'subtitleDownload': bool(app.PLEX_NOTIFY_ONSUBTITLEDOWNLOAD)
                    },
                    'updateLibrary': bool(app.PLEX_UPDATE_LIBRARY),
                    'host': app.PLEX_SERVER_HOST,
                    'token': app.PLEX_SERVER_TOKEN,
                    'username': app.PLEX_SERVER_USERNAME,
                    'password': app.PLEX_SERVER_PASSWORD
                },
                'client': {
                    'enabled': bool(app.USE_PLEX_CLIENT),
                    'username': app.PLEX_CLIENT_USERNAME,
                    'password': app.PLEX_CLIENT_PASSWORD,
                    'host': app.PLEX_CLIENT_HOST
                }
            },
            'emby': {
                'enabled': bool(app.USE_EMBY)
            },
            'torrents': {
                'enabled': bool(app.USE_TORRENTS),
                'method': app.TORRENT_METHOD,
                'username': app.TORRENT_USERNAME,
                'password': app.TORRENT_PASSWORD,
                'label': app.TORRENT_LABEL,
                'labelAnime': app.TORRENT_LABEL_ANIME,
                'verifySSL': app.TORRENT_VERIFY_CERT,
                'path': app.TORRENT_PATH,
                'seedTime': app.TORRENT_SEED_TIME,
                'paused': app.TORRENT_PAUSED,
                'highBandwidth': app.TORRENT_HIGH_BANDWIDTH,
                'host': app.TORRENT_HOST,
                'rpcurl': app.TORRENT_RPCURL,
                'authType': app.TORRENT_AUTH_TYPE
            },
            'nzb': {
                'enabled': bool(app.USE_NZBS),
                'username': app.NZBGET_USERNAME,
                'password': app.NZBGET_PASSWORD,
                # app.NZBGET_CATEGORY
                # app.NZBGET_CATEGORY_BACKLOG
                # app.NZBGET_CATEGORY_ANIME
                # app.NZBGET_CATEGORY_ANIME_BACKLOG
                'host': app.NZBGET_HOST,
                'pririty': app.NZBGET_PRIORITY
            },
            'layout': {
                'schedule': app.COMING_EPS_LAYOUT,
                'history': app.HISTORY_LAYOUT,
                'home': app.HOME_LAYOUT,
                'show': {
                    'allSeasons': bool(app.DISPLAY_ALL_SEASONS),
                    'specials': bool(app.DISPLAY_SHOW_SPECIALS)
                }
            }
        }

        if query and query not in config_data:
            return self.api_finish(status=404, error='{key} not found'.format(key=query))

        self.api_finish(data=config_data[query] if query else config_data)

    def patch(self, *args, **kwargs):
        """Patch general configuration."""
        data = tornado.escape.json_decode(self.request.body)
        done_data = {}
        done_errors = []
        for key in data.keys():
            if key == 'anonRedirect':
                app.ANON_REDIRECT = data['anonRedirect']
                done_data.setdefault('anonRedirect', app.ANON_REDIRECT)
            # 'animeSplitHome': app.ANIME_SPLIT_HOME,
            # 'comingEpsSort': app.COMING_EPS_SORT,
            # 'datePreset': app.DATE_PRESET,
            # 'fuzzyDating': app.FUZZY_DATING,
            # 'themeName': app.THEME_NAME,
            # 'posterSortby': app.POSTER_SORTBY,
            # 'posterSortdir': app.POSTER_SORTDIR,
            # 'rootDirs': app.ROOT_DIRS,
            # 'sortArticle': app.SORT_ARTICLE,
            # 'timePreset': app.TIME_PRESET,
            # 'trimZero': app.TRIM_ZERO,
            # 'fanartBackground': app.FANART_BACKGROUND,
            # 'fanartBackgroundOpacity': app.FANART_BACKGROUND_OPACITY,
            # 'branch': app.BRANCH, # @TODO: If branch change we should checkout new branch and if success return 200 otherwise return error
            if key in ['commitHash', 'release', 'sslVersion', 'pythonVersion', 'databaseVersion', 'os', 'locale', 'localUser', ]:
                # This is for fields that are static within the API
                # For example you shouldn't be able to change the OS
                done_errors.append(key)
            # 'programDir': app.PROG_DIR,
            # 'configFile': app.CONFIG_FILE,
            # 'dbFilename': db.dbFilename(),
            # 'cacheDir': app.CACHE_DIR,
            # 'logDir': app.LOG_DIR,
            # 'appArgs': app.MY_ARGS,
            # 'webRoot': app.WEB_ROOT,
            # 'githubUrl': app.GITHUB_IO_URL,
            # 'wikiUrl': app.WIKI_URL,
            # 'sourceUrl': app.APPLICATION_URL,
            # 'downloadUrl': app.DOWNLOAD_URL,
            # 'subtitlesMulti': app.SUBTITLES_MULTI,
            # 'namingForceFolders': app.NAMING_FORCE_FOLDERS,
            # 'subtitles': {
            #     'enabled': bool(app.USE_SUBTITLES)
            # },
            # 'kodi': {
            #     'enabled': bool(app.USE_KODI and app.KODI_UPDATE_LIBRARY)
            # },
            # 'plex': {
            #     'server': {
            #         'enabled': bool(app.USE_PLEX_SERVER and app.PLEX_UPDATE_LIBRARY)
            #     },
            #     'client': {
            #         'enabled': False  # Replace this with plex client code
            #     }
            # },
            if key == 'emby':
                done_data.setdefault('emby', {})
                if 'enabled' in data['emby'] and str(data['emby']['enabled']).lower() in ['true', 'false']:
                    # @TODO: All booleans should be saved as booleans
                    app.USE_EMBY = int(data['emby']['enabled'])
                    done_data['emby'].setdefault('enabled', bool(app.USE_EMBY))
            if key == 'torrents':
                done_data.setdefault('torrents', {})
                if 'enabled' in data['torrents'] and str(data['torrents']['enabled']).lower() in ['true', 'false']:
                    # @TODO: All booleans should be saved as booleans
                    app.USE_TORRENTS = int(data['torrents']['enabled'])
                    done_data['torrents'].setdefault('enabled', bool(app.USE_TORRENTS))
                if 'username' in data['torrents']:
                    app.TORRENT_USERNAME = str(data['torrents']['username'])
                    done_data['torrents'].setdefault('username', app.TORRENT_USERNAME)
                if 'password' in data['torrents']:
                    app.TORRENT_PASSWORD = str(data['torrents']['password'])
                    done_data['torrents'].setdefault('password', app.TORRENT_PASSWORD)
                if 'label' in data['torrents']:
                    app.TORRENT_LABEL = str(data['torrents']['label'])
                    done_data['torrents'].setdefault('label', app.TORRENT_LABEL)
                if 'labelAnime' in data['torrents']:
                    app.TORRENT_LABEL_ANIME = str(data['torrents']['labelAnime'])
                    done_data['torrents'].setdefault('labelAnime', app.TORRENT_LABEL_ANIME)
                if 'verifySSL' in data['torrents'] and str(data['torrents']['verifySSL']).lower() in ['true', 'false']:
                    # @TODO: All booleans should be saved as booleans
                    app.TORRENT_VERIFY_CERT = int(data['torrents']['verifySSL'])
                    done_data['torrents'].setdefault('verifySSL', bool(app.TORRENT_VERIFY_CERT))
                if 'path' in data['torrents']:
                    app.TORRENT_PATH = str(data['torrents']['path'])
                    done_data['torrents'].setdefault('verifySSL', app.TORRENT_VERIFY_CERT)
                #     'path': app.TORRENT_PATH,
                #     'seedTime': app.TORRENT_SEED_TIME,
                #     'paused': app.TORRENT_PAUSED,
                #     'highBandwidth': app.TORRENT_HIGH_BANDWIDTH,
                #     'host': app.TORRENT_HOST,
                #     'rpcurl': app.TORRENT_RPCURL,
                #     'authType': app.TORRENT_AUTH_TYPE
                # if 'method' in data['torrents']:
                # if 'username' in data['torrents']:
                # if 'password' in data['torrents']:
                # if 'label' in data['torrents']:
                # if 'labelAnime' in data['torrents']:
                # if 'verifySSL' in data['torrents']:
                # if 'seedTime' in data['torrents']:
                # if 'highBandwidth' in data['torrents']:
                # if 'host' in data['torrents']:
                # if 'rpcurl' in data['torrents']:
                # if 'authType' in data['torrents']:
            if key == 'layout':
                done_data.setdefault('layout', {})
                if 'schedule' in data['layout']:
                    if data['layout']['schedule'] in ('poster', 'banner', 'list', 'calendar'):
                        if data['layout']['schedule'] == 'calendar':
                            app.COMING_EPS_SORT = 'date'
                        app.COMING_EPS_LAYOUT = data['layout']['schedule']
                    else:
                        app.COMING_EPS_LAYOUT = 'banner'
                    done_data['layout'].setdefault('schedule', app.COMING_EPS_LAYOUT)
                if 'history' in data['layout']:
                    if data['layout']['history'] in ('compact', 'detailed'):
                        app.HISTORY_LAYOUT = data['layout']['history']
                    else:
                        app.HISTORY_LAYOUT = 'detailed'
                    done_data['layout'].setdefault('history', app.HISTORY_LAYOUT)
                if 'home' in data['layout']:
                    if data['layout']['home'] in ('poster', 'small', 'banner', 'simple', 'coverflow'):
                        app.HOME_LAYOUT = data['layout']['home']
                    else:
                        app.HOME_LAYOUT = 'poster'
                    done_data['layout'].setdefault('home', app.HOME_LAYOUT)
                if 'show' in data['layout']:
                    done_data['layout'].setdefault('show', {})
                    if 'allSeasons' in data['layout']['show'] and str(data['layout']['show']['allSeasons']).lower() in ['true', 'false']:
                        app.DISPLAY_ALL_SEASONS = int(data['layout']['show']['allSeasons'])
                        done_data['layout']['show'].setdefault('allSeasons', bool(app.DISPLAY_ALL_SEASONS))
                    if 'specials' in data['layout']['show'] and str(data['layout']['show']['specials']).lower() in ['true', 'false']:
                        app.DISPLAY_SHOW_SPECIALS = int(data['layout']['show']['specials'])
                        done_data['layout']['show'].setdefault('specials', bool(app.DISPLAY_SHOW_SPECIALS))
        # Make sure to update the config file after everything is updated
        app.instance.save_config()
        if len(done_errors):
            print('Can\'t PATCH [' + ', '.join(done_errors) + '] since ' + ["it's a static field.", "they're static fields."][len(done_errors) > 1])
        self.api_finish(data=done_data)
