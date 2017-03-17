# coding=utf-8
"""Request handler for configuration."""
import logging
import platform
import sys

from medusa import (
    app,
    db,
)
from medusa.server.api.v2.base import (
    BaseRequestHandler,
    BooleanField,
    EnumField,
    IntegerField,
    StringField,
    iter_nested_items,
    set_nested_value,
)
from six import text_type
from tornado.escape import json_decode

log = logging.getLogger(__name__)


def layout_schedule_post_processor(v):
    """Calendar layout should sort by date."""
    if v == 'calendar':
        app.COMING_EPS_SORT = 'date'


class ConfigHandler(BaseRequestHandler):
    """Config request handler."""

    #: resource name
    name = 'config'
    #: identifier
    identifier = ('identifier', r'\w+')
    #: path param
    path_param = ('path_param', r'\w+')
    #: allowed HTTP methods
    allowed_methods = ('GET', 'PATCH', )
    #: patch mapping
    patches = {
        'anonRedirect': StringField(app, 'ANON_REDIRECT'),
        'emby.enabled': BooleanField(app, 'USE_EMBY'),
        'torrents.enabled': BooleanField(app, 'USE_TORRENTS'),
        'torrents.username': StringField(app, 'TORRENT_USERNAME'),
        'torrents.password': StringField(app, 'TORRENT_PASSWORD'),
        'torrents.label': StringField(app, 'TORRENT_LABEL'),
        'torrents.labelAnime': StringField(app, 'TORRENT_LABEL_ANIME'),
        'torrents.verifySSL': BooleanField(app, 'TORRENT_VERIFY_CERT'),
        'torrents.path': BooleanField(app, 'TORRENT_PATH'),
        'selectedRootIndex': IntegerField(app, 'SELECTED_ROOT'),
        'layout.schedule': EnumField(app, 'COMING_EPS_LAYOUT', ('poster', 'banner', 'list', 'calendar'),
                                     default_value='banner', post_processor=layout_schedule_post_processor),
        'layout.history': EnumField(app, 'HISTORY_LAYOUT', ('compact', 'detailed'), default_value='detailed'),
        'layout.home': EnumField(app, 'HOME_LAYOUT', ('poster', 'small', 'banner', 'simple', 'coverflow'),
                                 default_value='poster'),
        'layout.show.allSeasons': BooleanField(app, 'DISPLAY_ALL_SEASONS'),
        'layout.show.specials': BooleanField(app, 'DISPLAY_SHOW_SPECIALS'),
        'theme.name': StringField(app, 'THEME_NAME'),
        'backlogOverview.period': StringField(app, 'BACKLOG_PERIOD'),
        'backlogOverview.status': StringField(app, 'BACKLOG_STATUS'),
    }

    def get(self, identifier, path_param=None):
        """Query general configuration.

        :param identifier:
        :param path_param:
        :type path_param: str
        """
        if identifier and identifier != 'main':
            return self._not_found('Config not found')

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
            'fanartBackgroundOpacity': float(app.FANART_BACKGROUND_OPACITY or 0),
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
                'priority': app.NZBGET_PRIORITY
            },
            'layout': {
                'schedule': app.COMING_EPS_LAYOUT,
                'history': app.HISTORY_LAYOUT,
                'home': app.HOME_LAYOUT,
                'show': {
                    'allSeasons': bool(app.DISPLAY_ALL_SEASONS),
                    'specials': bool(app.DISPLAY_SHOW_SPECIALS)
                }
            },
            'selectedRootIndex': int(app.SELECTED_ROOT) if app.SELECTED_ROOT else None,
            'backlogOverview': {
                'period': app.BACKLOG_PERIOD,
                'status': app.BACKLOG_STATUS
            }
        }

        if not identifier:
            return self._paginate([config_data])

        if path_param:
            if path_param not in config_data:
                return self._bad_request('{key} is a invalid path'.format(key=path_param))

            config_data = config_data[path_param]

        return self._ok(data=config_data)

    def patch(self, identifier, *args, **kwargs):
        """Patch general configuration."""
        if not identifier:
            return self._bad_request('Config identifier not specified')

        if identifier != 'main':
            return self._not_found('Config not found')

        data = json_decode(self.request.body)
        accepted = {}
        ignored = {}

        for key, value in iter_nested_items(data):
            patch_field = self.patches.get(key)
            if patch_field and patch_field.patch(app, value):
                set_nested_value(accepted, key, value)
            else:
                set_nested_value(ignored, key, value)

        if ignored:
            log.warning('Config patch ignored %r', ignored)

        # Make sure to update the config file after everything is updated
        app.instance.save_config()
        self._ok(data=accepted)
