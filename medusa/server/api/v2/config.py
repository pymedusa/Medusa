# coding=utf-8
"""Request handler for configuration."""
from __future__ import unicode_literals

import logging
import platform
import sys

from medusa import (
    app,
    db,
)
from medusa.helper.mappings import NonEmptyDict
from medusa.indexers.indexer_config import get_indexer_config
from medusa.server.api.v2.base import (
    BaseRequestHandler,
    BooleanField,
    EnumField,
    IntegerField,
    ListField,
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
        'layout.show.showListOrder': ListField(app, 'SHOW_LIST_ORDER'),
        'theme.name': StringField(app, 'THEME_NAME'),
        'backlogOverview.period': StringField(app, 'BACKLOG_PERIOD'),
        'backlogOverview.status': StringField(app, 'BACKLOG_STATUS'),
        'rootDirs': ListField(app, 'ROOT_DIRS'),
    }

    def get(self, identifier, path_param=None):
        """Query general configuration.

        :param identifier:
        :param path_param:
        :type path_param: str
        """
        if identifier and identifier != 'main':
            return self._not_found('Config not found')

        config_data = NonEmptyDict()
        config_data['anonRedirect'] = app.ANON_REDIRECT
        config_data['animeSplitHome'] = app.ANIME_SPLIT_HOME
        config_data['animeSplitHomeInTabs'] = app.ANIME_SPLIT_HOME_IN_TABS
        config_data['comingEpsSort'] = app.COMING_EPS_SORT
        config_data['datePreset'] = app.DATE_PRESET
        config_data['fuzzyDating'] = app.FUZZY_DATING
        config_data['themeName'] = app.THEME_NAME
        config_data['posterSortby'] = app.POSTER_SORTBY
        config_data['posterSortdir'] = app.POSTER_SORTDIR
        config_data['rootDirs'] = app.ROOT_DIRS
        config_data['sortArticle'] = app.SORT_ARTICLE
        config_data['timePreset'] = app.TIME_PRESET
        config_data['trimZero'] = app.TRIM_ZERO
        config_data['fanartBackground'] = app.FANART_BACKGROUND
        config_data['fanartBackgroundOpacity'] = float(app.FANART_BACKGROUND_OPACITY or 0)
        config_data['branch'] = app.BRANCH
        config_data['commitHash'] = app.CUR_COMMIT_HASH
        config_data['release'] = app.APP_VERSION
        config_data['sslVersion'] = app.OPENSSL_VERSION
        config_data['pythonVersion'] = sys.version
        config_data['databaseVersion'] = NonEmptyDict()
        config_data['databaseVersion']['major'] = app.MAJOR_DB_VERSION
        config_data['databaseVersion']['minor'] = app.MINOR_DB_VERSION
        config_data['os'] = platform.platform()
        config_data['locale'] = '.'.join([text_type(loc or 'Unknown') for loc in app.LOCALE])
        config_data['localUser'] = app.OS_USER or 'Unknown'
        config_data['programDir'] = app.PROG_DIR
        config_data['configFile'] = app.CONFIG_FILE
        config_data['dbFilename'] = db.dbFilename()
        config_data['cacheDir'] = app.CACHE_DIR
        config_data['logDir'] = app.LOG_DIR
        config_data['appArgs'] = app.MY_ARGS
        config_data['webRoot'] = app.WEB_ROOT
        config_data['githubUrl'] = app.GITHUB_IO_URL
        config_data['wikiUrl'] = app.WIKI_URL
        config_data['sourceUrl'] = app.APPLICATION_URL
        config_data['downloadUrl'] = app.DOWNLOAD_URL
        config_data['subtitlesMulti'] = app.SUBTITLES_MULTI
        config_data['namingForceFolders'] = app.NAMING_FORCE_FOLDERS
        config_data['subtitles'] = NonEmptyDict()
        config_data['subtitles']['enabled'] = bool(app.USE_SUBTITLES)
        config_data['kodi'] = NonEmptyDict()
        config_data['kodi']['enabled'] = bool(app.USE_KODI and app.KODI_UPDATE_LIBRARY)
        config_data['plex'] = NonEmptyDict()
        config_data['plex']['server'] = NonEmptyDict()
        config_data['plex']['server']['enabled'] = bool(app.USE_PLEX_SERVER)
        config_data['plex']['server']['notify'] = NonEmptyDict()
        config_data['plex']['server']['notify']['snatch'] = bool(app.PLEX_NOTIFY_ONSNATCH)
        config_data['plex']['server']['notify']['download'] = bool(app.PLEX_NOTIFY_ONDOWNLOAD)
        config_data['plex']['server']['notify']['subtitleDownload'] = bool(app.PLEX_NOTIFY_ONSUBTITLEDOWNLOAD)

        config_data['plex']['server']['updateLibrary'] = bool(app.PLEX_UPDATE_LIBRARY)
        config_data['plex']['server']['host'] = app.PLEX_SERVER_HOST
        config_data['plex']['server']['token'] = app.PLEX_SERVER_TOKEN
        config_data['plex']['server']['username'] = app.PLEX_SERVER_USERNAME
        config_data['plex']['server']['password'] = app.PLEX_SERVER_PASSWORD
        config_data['plex']['client'] = NonEmptyDict()
        config_data['plex']['client']['enabled'] = bool(app.USE_PLEX_CLIENT)
        config_data['plex']['client']['username'] = app.PLEX_CLIENT_USERNAME
        config_data['plex']['client']['password'] = app.PLEX_CLIENT_PASSWORD
        config_data['plex']['client']['host'] = app.PLEX_CLIENT_HOST
        config_data['emby'] = NonEmptyDict()
        config_data['emby']['enabled'] = bool(app.USE_EMBY)
        config_data['torrents'] = NonEmptyDict()
        config_data['torrents']['enabled'] = bool(app.USE_TORRENTS)
        config_data['torrents']['method'] = app.TORRENT_METHOD
        config_data['torrents']['username'] = app.TORRENT_USERNAME
        config_data['torrents']['password'] = app.TORRENT_PASSWORD
        config_data['torrents']['label'] = app.TORRENT_LABEL
        config_data['torrents']['labelAnime'] = app.TORRENT_LABEL_ANIME
        config_data['torrents']['verifySSL'] = app.TORRENT_VERIFY_CERT
        config_data['torrents']['path'] = app.TORRENT_PATH
        config_data['torrents']['seedTime'] = app.TORRENT_SEED_TIME
        config_data['torrents']['paused'] = app.TORRENT_PAUSED
        config_data['torrents']['highBandwidth'] = app.TORRENT_HIGH_BANDWIDTH
        config_data['torrents']['host'] = app.TORRENT_HOST
        config_data['torrents']['rpcurl'] = app.TORRENT_RPCURL
        config_data['torrents']['authType'] = app.TORRENT_AUTH_TYPE
        config_data['nzb'] = NonEmptyDict()
        config_data['nzb']['enabled'] = bool(app.USE_NZBS)
        config_data['nzb']['username'] = app.NZBGET_USERNAME
        config_data['nzb']['password'] = app.NZBGET_PASSWORD
        # app.NZBGET_CATEGORY
        # app.NZBGET_CATEGORY_BACKLOG
        # app.NZBGET_CATEGORY_ANIME
        # app.NZBGET_CATEGORY_ANIME_BACKLOG
        config_data['nzb']['host'] = app.NZBGET_HOST
        config_data['nzb']['priority'] = app.NZBGET_PRIORITY
        config_data['layout'] = NonEmptyDict()
        config_data['layout']['schedule'] = app.COMING_EPS_LAYOUT
        config_data['layout']['history'] = app.HISTORY_LAYOUT
        config_data['layout']['home'] = app.HOME_LAYOUT
        config_data['layout']['show'] = NonEmptyDict()
        config_data['layout']['show']['allSeasons'] = bool(app.DISPLAY_ALL_SEASONS)
        config_data['layout']['show']['specials'] = bool(app.DISPLAY_SHOW_SPECIALS)
        config_data['layout']['show']['showListOrder'] = app.SHOW_LIST_ORDER
        config_data['selectedRootIndex'] = int(app.SELECTED_ROOT) if app.SELECTED_ROOT is not None else -1  # All paths
        config_data['backlogOverview'] = NonEmptyDict()
        config_data['backlogOverview']['period'] = app.BACKLOG_PERIOD
        config_data['backlogOverview']['status'] = app.BACKLOG_STATUS
        config_data['indexers'] = NonEmptyDict()
        config_data['indexers']['config'] = get_indexer_config()

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
