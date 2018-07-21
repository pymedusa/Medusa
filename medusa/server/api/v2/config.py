# coding=utf-8
"""Request handler for configuration."""
from __future__ import unicode_literals

import inspect
import logging
import platform
import pkgutil
import sys

from medusa import (
    app,
    classes,
    common,
    config,
    db,
    logger,
    ws,
)
from medusa.helper.mappings import NonEmptyDict
from medusa.indexers.indexer_config import get_indexer_config
from medusa.logger.adapters.style import BraceAdapter
from medusa.server.api.v2.base import (
    BaseRequestHandler,
    BooleanField,
    MetadataStructureField,
    EnumField,
    IntegerField,
    ListField,
    StringField,
    iter_nested_items,
    set_nested_value,
)

from six import iteritems, itervalues, text_type

from tornado.escape import json_decode

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


def layout_schedule_post_processor(v):
    """Calendar layout should sort by date."""
    if v == 'calendar':
        app.COMING_EPS_SORT = 'date'


def theme_name_setter(object, name, value):
    """Hot-swap theme."""
    config.change_theme(value)


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
        'torrents.authType': StringField(app, 'TORRENT_AUTH_TYPE'),
        'torrents.dir': StringField(app, 'TORRENT_DIR'),
        'torrents.enabled': BooleanField(app, 'USE_TORRENTS'),
        'torrents.highBandwidth': StringField(app, 'TORRENT_HIGH_BANDWIDTH'),
        'torrents.host': StringField(app, 'TORRENT_HOST'),
        'torrents.label': StringField(app, 'TORRENT_LABEL'),
        'torrents.labelAnime': StringField(app, 'TORRENT_LABEL_ANIME'),
        'torrents.method': StringField(app, 'TORRENT_METHOD'),
        'torrents.password': StringField(app, 'TORRENT_PASSWORD'),
        'torrents.path': BooleanField(app, 'TORRENT_PATH'),
        'torrents.paused': BooleanField(app, 'TORRENT_PAUSED'),
        'torrents.rpcurl': StringField(app, 'TORRENT_RPCURL'),
        'torrents.seedLocation': StringField(app, 'TORRENT_SEED_LOCATION'),
        'torrents.seedTime': StringField(app, 'TORRENT_SEED_TIME'),
        'torrents.username': StringField(app, 'TORRENT_USERNAME'),
        'torrents.verifySSL': BooleanField(app, 'TORRENT_VERIFY_CERT'),
        'nzb.enabled': BooleanField(app, 'USE_NZBS'),
        'nzb.dir': StringField(app, 'NZB_DIR'),
        'nzb.method': StringField(app, 'NZB_METHOD'),
        'nzb.nzbget.category': StringField(app, 'NZBGET_CATEGORY'),
        'nzb.nzbget.categoryAnime': StringField(app, 'NZBGET_CATEGORY_ANIME'),
        'nzb.nzbget.categoryAnimeBacklog': StringField(app, 'NZBGET_CATEGORY_ANIME_BACKLOG'),
        'nzb.nzbget.categoryBacklog': StringField(app, 'NZBGET_CATEGORY_BACKLOG'),
        'nzb.nzbget.host': StringField(app, 'NZBGET_HOST'),
        'nzb.nzbget.password': StringField(app, 'NZBGET_PASSWORD'),
        'nzb.nzbget.priority': StringField(app, 'NZBGET_PRIORITY'),
        'nzb.nzbget.useHttps': BooleanField(app, 'NZBGET_USE_HTTPS'),
        'nzb.nzbget.username': StringField(app, 'NZBGET_USERNAME'),
        'nzb.sabnzbd.apiKey': StringField(app, 'SAB_APIKEY'),
        'nzb.sabnzbd.category': StringField(app, 'SAB_CATEGORY'),
        'nzb.sabnzbd.categoryAnime': StringField(app, 'SAB_CATEGORY_ANIME'),
        'nzb.sabnzbd.categoryAnimeBacklog': StringField(app, 'SAB_CATEGORY_ANIME_BACKLOG'),
        'nzb.sabnzbd.categoryBacklog': StringField(app, 'SAB_CATEGORY_BACKLOG'),
        'nzb.sabnzbd.forced': BooleanField(app, 'SAB_FORCED'),
        'nzb.sabnzbd.host': StringField(app, 'SAB_HOST'),
        'nzb.sabnzbd.password': StringField(app, 'SAB_PASSWORD'),
        'nzb.sabnzbd.username': StringField(app, 'SAB_USERNAME'),
        'selectedRootIndex': IntegerField(app, 'SELECTED_ROOT'),
        'layout.schedule': EnumField(app, 'COMING_EPS_LAYOUT', ('poster', 'banner', 'list', 'calendar'),
                                     default_value='banner', post_processor=layout_schedule_post_processor),
        'layout.history': EnumField(app, 'HISTORY_LAYOUT', ('compact', 'detailed'), default_value='detailed'),
        'layout.home': EnumField(app, 'HOME_LAYOUT', ('poster', 'small', 'banner', 'simple', 'coverflow'),
                                 default_value='poster'),
        'layout.show.allSeasons': BooleanField(app, 'DISPLAY_ALL_SEASONS'),
        'layout.show.specials': BooleanField(app, 'DISPLAY_SHOW_SPECIALS'),
        'layout.show.showListOrder': ListField(app, 'SHOW_LIST_ORDER'),
        'theme.name': StringField(app, 'THEME_NAME', setter=theme_name_setter),
        'backlogOverview.period': StringField(app, 'BACKLOG_PERIOD'),
        'backlogOverview.status': StringField(app, 'BACKLOG_STATUS'),
        'rootDirs': ListField(app, 'ROOT_DIRS'),
        'postProcessing.seriesDownloadDir': StringField(app, 'TV_DOWNLOAD_DIR'),
        'postProcessing.processAutomatically': BooleanField(app, 'PROCESS_AUTOMATICALLY'),
        'postProcessing.processMethod': StringField(app, 'PROCESS_METHOD'),
        'postProcessing.deleteRarContent': BooleanField(app, 'DELRARCONTENTS'),
        'postProcessing.unpack': BooleanField(app, 'UNPACK'),
        'postProcessing.noDelete': BooleanField(app, 'NO_DELETE'),
        'postProcessing.postponeIfSyncFiles': BooleanField(app, 'POSTPONE_IF_SYNC_FILES'),
        'postProcessing.autoPostprocessorFrequency': IntegerField(app, 'AUTOPOSTPROCESSOR_FREQUENCY'),
        'postProcessing.airdateEpisodes': BooleanField(app, 'AIRDATE_EPISODES'),

        'postProcessing.moveAssociatedFiles': BooleanField(app, 'MOVE_ASSOCIATED_FILES'),
        'postProcessing.allowedExtensions': ListField(app, 'ALLOWED_EXTENSIONS'),
        'postProcessing.addShowsWithoutDir': BooleanField(app, 'ADD_SHOWS_WO_DIR'),
        'postProcessing.createMissingShowDirs': BooleanField(app, 'CREATE_MISSING_SHOW_DIRS'),
        'postProcessing.renameEpisodes': BooleanField(app, 'RENAME_EPISODES'),
        'postProcessing.postponeIfNoSubs': BooleanField(app, 'POSTPONE_IF_NO_SUBS'),
        'postProcessing.nfoRename': BooleanField(app, 'NFO_RENAME'),
        'postProcessing.syncFiles': ListField(app, 'SYNC_FILES'),
        'postProcessing.fileTimestampTimezone': StringField(app, 'FILE_TIMESTAMP_TIMEZONE'),
        'postProcessing.extraScripts': ListField(app, 'EXTRA_SCRIPTS'),
        'postProcessing.extraScriptsUrl': StringField(app, 'EXTRA_SCRIPTS_URL'),
        'postProcessing.naming.pattern': StringField(app, 'NAMING_PATTERN'),
        'postProcessing.naming.enableCustomNamingAnime': BooleanField(app, 'NAMING_CUSTOM_ANIME'),
        'postProcessing.naming.enableCustomNamingSports': BooleanField(app, 'NAMING_CUSTOM_SPORTS'),
        'postProcessing.naming.enableCustomNamingAirByDate': BooleanField(app, 'NAMING_CUSTOM_ABD'),
        'postProcessing.naming.patternSports': StringField(app, 'NAMING_SPORTS_PATTERN'),
        'postProcessing.naming.patternAirByDate': StringField(app, 'NAMING_ABD_PATTERN'),
        'postProcessing.naming.patternAnime': StringField(app, 'NAMING_ANIME_PATTERN'),
        'postProcessing.naming.animeMultiEp': IntegerField(app, 'NAMING_ANIME_MULTI_EP'),
        'postProcessing.naming.animeNamingType': IntegerField(app, 'NAMING_ANIME'),
        'postProcessing.naming.multiEp': IntegerField(app, 'NAMING_MULTI_EP'),
        'postProcessing.naming.stripYear': BooleanField(app, 'NAMING_STRIP_YEAR')
    }

    def get(self, identifier, path_param=None):
        """Query general configuration.

        :param identifier:
        :param path_param:
        :type path_param: str
        """
        config_sections = DataGenerator.sections()

        if identifier and identifier not in config_sections:
            return self._not_found('Config not found')

        if not identifier:
            config_data = NonEmptyDict()

            for section in config_sections:
                config_data[section] = DataGenerator.get_data(section)

            return self._ok(data=config_data)

        config_data = DataGenerator.get_data(identifier)

        if path_param:
            if path_param not in config_data:
                return self._bad_request('{key} is a invalid path'.format(key=path_param))

            config_data = config_data[path_param]

        return self._ok(data=config_data)

    # def patchMetadata(selfs):
    #     """Patch the metadata config."""


    def patch(self, identifier, *args, **kwargs):
        """Patch general configuration."""
        if not identifier:
            return self._bad_request('Config identifier not specified')

        if identifier != 'main':
            return self._not_found('Config not found')

        data = json_decode(self.request.body)
        accepted = {}
        ignored = {}

        # Remove the metadata providers from the nested items.
        # It's ugly but I don't see a better solution for it right now.
        if data.get('metadata'):
            metadata_providers = data['metadata'].pop('metadataProviders')

            if metadata_providers:
                patch_metadata_providers = MetadataStructureField(app, 'metadata_provider_dict')
                if patch_metadata_providers and patch_metadata_providers.patch(app, metadata_providers):
                    set_nested_value(accepted, 'metadata.metadataProviders', metadata_providers)
                else:
                    set_nested_value(ignored, 'metadata.metadataProviders', metadata_providers)

        for key, value in iter_nested_items(data):
            patch_field = self.patches.get(key)
            if patch_field and patch_field.patch(app, value):
                set_nested_value(accepted, key, value)
            else:
                set_nested_value(ignored, key, value)

        if ignored:
            log.warning('Config patch ignored {items!r}', {'items': ignored})

        # Make sure to update the config file after everything is updated
        app.instance.save_config()

        # Push an update to any open Web UIs through the WebSocket
        msg = ws.Message('configUpdated', {
            'section': identifier,
            'config': DataGenerator.get_data(identifier)
        })
        msg.push()

        self._ok(data=accepted)


class DataGenerator(object):
    """Generate the requested config data on demand."""

    @classmethod
    def sections(cls):
        """Get the available section names."""
        return [
            name[5:]
            for (name, function) in inspect.getmembers(cls, predicate=inspect.isfunction)
            if name.startswith('data_')
        ]

    @classmethod
    def get_data(cls, section):
        """Return the requested section data."""
        return getattr(cls, 'data_' + section)()

    @staticmethod
    def data_main():
        """Main."""
        section_data = NonEmptyDict()

        section_data['anonRedirect'] = app.ANON_REDIRECT
        section_data['animeSplitHome'] = bool(app.ANIME_SPLIT_HOME)
        section_data['animeSplitHomeInTabs'] = bool(app.ANIME_SPLIT_HOME_IN_TABS)
        section_data['comingEpsSort'] = app.COMING_EPS_SORT
        section_data['comingEpsDisplayPaused'] = bool(app.COMING_EPS_DISPLAY_PAUSED)
        section_data['datePreset'] = app.DATE_PRESET
        section_data['fuzzyDating'] = bool(app.FUZZY_DATING)
        section_data['themeName'] = app.THEME_NAME
        section_data['posterSortby'] = app.POSTER_SORTBY
        section_data['posterSortdir'] = app.POSTER_SORTDIR
        section_data['rootDirs'] = app.ROOT_DIRS
        section_data['sortArticle'] = bool(app.SORT_ARTICLE)
        section_data['timePreset'] = app.TIME_PRESET
        section_data['trimZero'] = bool(app.TRIM_ZERO)
        section_data['fanartBackground'] = bool(app.FANART_BACKGROUND)
        section_data['fanartBackgroundOpacity'] = float(app.FANART_BACKGROUND_OPACITY or 0)
        section_data['branch'] = app.BRANCH
        section_data['commitHash'] = app.CUR_COMMIT_HASH
        section_data['release'] = app.APP_VERSION
        section_data['sslVersion'] = app.OPENSSL_VERSION
        section_data['pythonVersion'] = sys.version
        section_data['databaseVersion'] = NonEmptyDict()
        section_data['databaseVersion']['major'] = app.MAJOR_DB_VERSION
        section_data['databaseVersion']['minor'] = app.MINOR_DB_VERSION
        section_data['os'] = platform.platform()
        section_data['pid'] = app.PID
        section_data['locale'] = '.'.join([text_type(loc or 'Unknown') for loc in app.LOCALE])
        section_data['localUser'] = app.OS_USER or 'Unknown'
        section_data['programDir'] = app.PROG_DIR
        section_data['configFile'] = app.CONFIG_FILE
        section_data['dbPath'] = db.DBConnection().path
        section_data['cacheDir'] = app.CACHE_DIR
        section_data['logDir'] = app.LOG_DIR
        section_data['appArgs'] = app.MY_ARGS
        section_data['webRoot'] = app.WEB_ROOT
        section_data['githubUrl'] = app.GITHUB_IO_URL
        section_data['wikiUrl'] = app.WIKI_URL
        section_data['donationsUrl'] = app.DONATIONS_URL
        section_data['sourceUrl'] = app.APPLICATION_URL
        section_data['downloadUrl'] = app.DOWNLOAD_URL
        section_data['subtitlesMulti'] = bool(app.SUBTITLES_MULTI)
        section_data['namingForceFolders'] = bool(app.NAMING_FORCE_FOLDERS)
        section_data['subtitles'] = NonEmptyDict()
        section_data['subtitles']['enabled'] = bool(app.USE_SUBTITLES)
        section_data['recentShows'] = app.SHOWS_RECENT

        section_data['news'] = NonEmptyDict()
        section_data['news']['lastRead'] = app.NEWS_LAST_READ
        section_data['news']['latest'] = app.NEWS_LATEST
        section_data['news']['unread'] = app.NEWS_UNREAD

        section_data['logs'] = NonEmptyDict()
        section_data['logs']['loggingLevels'] = {k.lower(): v for k, v in iteritems(logger.LOGGING_LEVELS)}
        section_data['logs']['numErrors'] = len(classes.ErrorViewer.errors)
        section_data['logs']['numWarnings'] = len(classes.WarningViewer.errors)

        section_data['failedDownloads'] = NonEmptyDict()
        section_data['failedDownloads']['enabled'] = bool(app.USE_FAILED_DOWNLOADS)
        section_data['failedDownloads']['deleteFailed'] = bool(app.DELETE_FAILED)

        section_data['kodi'] = NonEmptyDict()
        section_data['kodi']['enabled'] = bool(app.USE_KODI)
        section_data['kodi']['alwaysOn'] = bool(app.KODI_ALWAYS_ON)
        section_data['kodi']['notify'] = NonEmptyDict()
        section_data['kodi']['notify']['snatch'] = bool(app.KODI_NOTIFY_ONSNATCH)
        section_data['kodi']['notify']['download'] = bool(app.KODI_NOTIFY_ONDOWNLOAD)
        section_data['kodi']['notify']['subtitleDownload'] = bool(app.KODI_NOTIFY_ONSUBTITLEDOWNLOAD)
        section_data['kodi']['update'] = NonEmptyDict()
        section_data['kodi']['update']['library'] = bool(app.KODI_UPDATE_LIBRARY)
        section_data['kodi']['update']['full'] = bool(app.KODI_UPDATE_FULL)
        section_data['kodi']['update']['onlyFirst'] = bool(app.KODI_UPDATE_ONLYFIRST)
        section_data['kodi']['host'] = app.KODI_HOST
        section_data['kodi']['username'] = app.KODI_USERNAME
        section_data['kodi']['libraryCleanPending'] = bool(app.KODI_LIBRARY_CLEAN_PENDING)
        section_data['kodi']['cleanLibrary'] = bool(app.KODI_CLEAN_LIBRARY)

        section_data['plex'] = NonEmptyDict()
        section_data['plex']['server'] = NonEmptyDict()
        section_data['plex']['server']['enabled'] = bool(app.USE_PLEX_SERVER)
        section_data['plex']['server']['notify'] = NonEmptyDict()
        section_data['plex']['server']['notify']['snatch'] = bool(app.PLEX_NOTIFY_ONSNATCH)
        section_data['plex']['server']['notify']['download'] = bool(app.PLEX_NOTIFY_ONDOWNLOAD)
        section_data['plex']['server']['notify']['subtitleDownload'] = bool(app.PLEX_NOTIFY_ONSUBTITLEDOWNLOAD)
        section_data['plex']['server']['updateLibrary'] = bool(app.PLEX_UPDATE_LIBRARY)
        section_data['plex']['server']['host'] = app.PLEX_SERVER_HOST
        section_data['plex']['server']['username'] = app.PLEX_SERVER_USERNAME
        section_data['plex']['client'] = NonEmptyDict()
        section_data['plex']['client']['enabled'] = bool(app.USE_PLEX_CLIENT)
        section_data['plex']['client']['username'] = app.PLEX_CLIENT_USERNAME
        section_data['plex']['client']['host'] = app.PLEX_CLIENT_HOST

        section_data['emby'] = NonEmptyDict()
        section_data['emby']['enabled'] = bool(app.USE_EMBY)
        section_data['emby']['host'] = app.EMBY_HOST

        section_data['torrents'] = NonEmptyDict()
        section_data['torrents']['authType'] = app.TORRENT_AUTH_TYPE
        section_data['torrents']['dir'] = app.TORRENT_DIR
        section_data['torrents']['enabled'] = bool(app.USE_TORRENTS)
        section_data['torrents']['highBandwidth'] = app.TORRENT_HIGH_BANDWIDTH
        section_data['torrents']['host'] = app.TORRENT_HOST
        section_data['torrents']['label'] = app.TORRENT_LABEL
        section_data['torrents']['labelAnime'] = app.TORRENT_LABEL_ANIME
        section_data['torrents']['method'] = app.TORRENT_METHOD
        section_data['torrents']['path'] = app.TORRENT_PATH
        section_data['torrents']['paused'] = bool(app.TORRENT_PAUSED)
        section_data['torrents']['rpcurl'] = app.TORRENT_RPCURL
        section_data['torrents']['seedLocation'] = app.TORRENT_SEED_LOCATION
        section_data['torrents']['seedTime'] = app.TORRENT_SEED_TIME
        section_data['torrents']['username'] = app.TORRENT_USERNAME
        section_data['torrents']['verifySSL'] = bool(app.TORRENT_VERIFY_CERT)

        section_data['nzb'] = NonEmptyDict()
        section_data['nzb']['enabled'] = bool(app.USE_NZBS)
        section_data['nzb']['dir'] = app.NZB_DIR
        section_data['nzb']['method'] = app.NZB_METHOD
        section_data['nzb']['nzbget'] = NonEmptyDict()
        section_data['nzb']['nzbget']['category'] = app.NZBGET_CATEGORY
        section_data['nzb']['nzbget']['categoryAnime'] = app.NZBGET_CATEGORY_ANIME
        section_data['nzb']['nzbget']['categoryAnimeBacklog'] = app.NZBGET_CATEGORY_ANIME_BACKLOG
        section_data['nzb']['nzbget']['categoryBacklog'] = app.NZBGET_CATEGORY_BACKLOG
        section_data['nzb']['nzbget']['host'] = app.NZBGET_HOST
        section_data['nzb']['nzbget']['priority'] = app.NZBGET_PRIORITY
        section_data['nzb']['nzbget']['useHttps'] = bool(app.NZBGET_USE_HTTPS)
        section_data['nzb']['nzbget']['username'] = app.NZBGET_USERNAME

        section_data['nzb']['sabnzbd'] = NonEmptyDict()
        section_data['nzb']['sabnzbd']['category'] = app.SAB_CATEGORY
        section_data['nzb']['sabnzbd']['categoryAnime'] = app.SAB_CATEGORY_ANIME
        section_data['nzb']['sabnzbd']['categoryAnimeBacklog'] = app.SAB_CATEGORY_ANIME_BACKLOG
        section_data['nzb']['sabnzbd']['categoryBacklog'] = app.SAB_CATEGORY_BACKLOG
        section_data['nzb']['sabnzbd']['forced'] = bool(app.SAB_FORCED)
        section_data['nzb']['sabnzbd']['host'] = app.SAB_HOST
        section_data['nzb']['sabnzbd']['username'] = app.SAB_USERNAME

        section_data['layout'] = NonEmptyDict()
        section_data['layout']['schedule'] = app.COMING_EPS_LAYOUT
        section_data['layout']['history'] = app.HISTORY_LAYOUT
        section_data['layout']['home'] = app.HOME_LAYOUT
        section_data['layout']['show'] = NonEmptyDict()
        section_data['layout']['show']['allSeasons'] = bool(app.DISPLAY_ALL_SEASONS)
        section_data['layout']['show']['specials'] = bool(app.DISPLAY_SHOW_SPECIALS)
        section_data['layout']['show']['showListOrder'] = app.SHOW_LIST_ORDER

        section_data['selectedRootIndex'] = int(app.SELECTED_ROOT) if app.SELECTED_ROOT is not None else -1  # All paths

        section_data['backlogOverview'] = NonEmptyDict()
        section_data['backlogOverview']['period'] = app.BACKLOG_PERIOD
        section_data['backlogOverview']['status'] = app.BACKLOG_STATUS

        section_data['indexers'] = NonEmptyDict()
        section_data['indexers']['config'] = get_indexer_config()
        section_data['postProcessing'] = NonEmptyDict()
        section_data['postProcessing']['naming'] = NonEmptyDict()
        section_data['postProcessing']['naming']['stripYear'] = app.NAMING_STRIP_YEAR
        section_data['postProcessing']['naming']['pattern'] = app.NAMING_PATTERN
        section_data['postProcessing']['naming']['multiEp'] = app.NAMING_MULTI_EP
        section_data['postProcessing']['naming']['patternAirByDate'] = app.NAMING_ABD_PATTERN
        section_data['postProcessing']['naming']['patternSports'] = app.NAMING_SPORTS_PATTERN
        section_data['postProcessing']['naming']['patternAnime'] = app.NAMING_ANIME_PATTERN
        section_data['postProcessing']['naming']['enableCustomNamingAirByDate'] = bool(app.NAMING_CUSTOM_ABD)
        section_data['postProcessing']['naming']['enableCustomNamingSports'] = bool(app.NAMING_CUSTOM_SPORTS)
        section_data['postProcessing']['naming']['enableCustomNamingAnime'] = bool(app.NAMING_CUSTOM_ANIME)
        section_data['postProcessing']['naming']['animeMultiEp'] = int(app.NAMING_ANIME_MULTI_EP)
        section_data['postProcessing']['naming']['animeNamingType'] = int(app.NAMING_ANIME)
        section_data['postProcessing']['naming']['stripYear'] = bool(app.NAMING_STRIP_YEAR)
        section_data['postProcessing']['seriesDownloadDir'] = app.TV_DOWNLOAD_DIR
        section_data['postProcessing']['processAutomatically'] = bool(app.PROCESS_AUTOMATICALLY)
        section_data['postProcessing']['postponeIfSyncFiles'] = bool(app.POSTPONE_IF_SYNC_FILES)
        section_data['postProcessing']['postponeIfNoSubs'] = bool(app.POSTPONE_IF_NO_SUBS)
        section_data['postProcessing']['renameEpisodes'] = bool(app.RENAME_EPISODES)
        section_data['postProcessing']['createMissingShowDirs'] = bool(app.CREATE_MISSING_SHOW_DIRS)
        section_data['postProcessing']['addShowsWithoutDir'] = bool(app.ADD_SHOWS_WO_DIR)
        section_data['postProcessing']['moveAssociatedFiles'] = bool(app.MOVE_ASSOCIATED_FILES)
        section_data['postProcessing']['nfoRename'] = bool(app.NFO_RENAME)
        section_data['postProcessing']['airdateEpisodes'] = bool(app.AIRDATE_EPISODES)
        section_data['postProcessing']['unpack'] = bool(app.UNPACK)
        section_data['postProcessing']['deleteRarContent'] = bool(app.DELRARCONTENTS)
        section_data['postProcessing']['noDelete'] = bool(app.NO_DELETE)
        section_data['postProcessing']['processMethod'] = app.PROCESS_METHOD
        section_data['postProcessing']['reflinkAvailable'] = bool(pkgutil.find_loader('reflink'))
        section_data['postProcessing']['autoPostprocessorFrequency'] = app.AUTOPOSTPROCESSOR_FREQUENCY
        section_data['postProcessing']['syncFiles'] = app.SYNC_FILES
        section_data['postProcessing']['fileTimestampTimezone'] = app.FILE_TIMESTAMP_TIMEZONE
        section_data['postProcessing']['allowedExtensions'] = app.ALLOWED_EXTENSIONS
        section_data['postProcessing']['extraScripts'] = app.EXTRA_SCRIPTS
        section_data['postProcessing']['extraScriptsUrl'] = app.EXTRA_SCRIPTS_URL

        return section_data

    @staticmethod
    def data_qualities():
        """Qualities."""
        section_data = NonEmptyDict()

        section_data['values'] = NonEmptyDict()
        section_data['values']['na'] = common.Quality.NA
        section_data['values']['unknown'] = common.Quality.UNKNOWN
        section_data['values']['sdtv'] = common.Quality.SDTV
        section_data['values']['sddvd'] = common.Quality.SDDVD
        section_data['values']['hdtv'] = common.Quality.HDTV
        section_data['values']['rawhdtv'] = common.Quality.RAWHDTV
        section_data['values']['fullhdtv'] = common.Quality.FULLHDTV
        section_data['values']['hdwebdl'] = common.Quality.HDWEBDL
        section_data['values']['fullhdwebdl'] = common.Quality.FULLHDWEBDL
        section_data['values']['hdbluray'] = common.Quality.HDBLURAY
        section_data['values']['fullhdbluray'] = common.Quality.FULLHDBLURAY
        section_data['values']['uhd4ktv'] = common.Quality.UHD_4K_TV
        section_data['values']['uhd4kwebdl'] = common.Quality.UHD_4K_WEBDL
        section_data['values']['uhd4kbluray'] = common.Quality.UHD_4K_BLURAY
        section_data['values']['uhd8ktv'] = common.Quality.UHD_8K_TV
        section_data['values']['uhd8kwebdl'] = common.Quality.UHD_8K_WEBDL
        section_data['values']['uhd8kbluray'] = common.Quality.UHD_8K_BLURAY

        section_data['anySets'] = NonEmptyDict()
        section_data['anySets']['anyhdtv'] = common.Quality.ANYHDTV
        section_data['anySets']['anywebdl'] = common.Quality.ANYWEBDL
        section_data['anySets']['anybluray'] = common.Quality.ANYBLURAY

        section_data['presets'] = NonEmptyDict()
        section_data['presets']['any'] = common.ANY
        section_data['presets']['sd'] = common.SD
        section_data['presets']['hd'] = common.HD
        section_data['presets']['hd720p'] = common.HD720p
        section_data['presets']['hd1080p'] = common.HD1080p
        section_data['presets']['uhd'] = common.UHD
        section_data['presets']['uhd4k'] = common.UHD_4K
        section_data['presets']['uhd8k'] = common.UHD_8K

        section_data['strings'] = NonEmptyDict()
        section_data['strings']['values'] = common.Quality.qualityStrings
        section_data['strings']['anySets'] = common.Quality.combinedQualityStrings
        section_data['strings']['presets'] = common.qualityPresetStrings
        section_data['strings']['cssClass'] = common.Quality.cssClassStrings

        return section_data

    @staticmethod
    def data_statuses():
        """Statuses."""
        section_data = NonEmptyDict()

        section_data['values'] = NonEmptyDict()
        section_data['values']['unset'] = common.UNSET
        section_data['values']['unaired'] = common.UNAIRED
        section_data['values']['snatched'] = common.SNATCHED
        section_data['values']['wanted'] = common.WANTED
        section_data['values']['downloaded'] = common.DOWNLOADED
        section_data['values']['skipped'] = common.SKIPPED
        section_data['values']['archived'] = common.ARCHIVED
        section_data['values']['ignored'] = common.IGNORED
        section_data['values']['snatchedProper'] = common.SNATCHED_PROPER
        section_data['values']['subtitled'] = common.SUBTITLED
        section_data['values']['failed'] = common.FAILED
        section_data['values']['snatchedBest'] = common.SNATCHED_BEST
        section_data['strings'] = common.statusStrings

        return section_data

    @staticmethod
    def data_metadata():
        """Metadata."""
        section_data = NonEmptyDict()

        section_data['metadataProviders'] = NonEmptyDict()

        for provider in itervalues(app.metadata_provider_dict):
            json_repr = provider.to_json()
            section_data['metadataProviders'][json_repr['id']] = json_repr

        return section_data
