# coding=utf-8
"""Request handler for configuration."""
from __future__ import unicode_literals

import inspect
import logging
import pkgutil
import platform
import sys
from random import choice

from medusa import (
    app,
    classes,
    common,
    config,
    db,
    helpers,
    logger,
    ws,
)
from medusa.common import IGNORED, Quality, SKIPPED, WANTED, cpu_presets
from medusa.helpers.utils import int_default, to_camel_case
from medusa.indexers.config import INDEXER_TVDBV2, get_indexer_config
from medusa.logger.adapters.style import BraceAdapter
from medusa.queues.utils import generate_show_queue
from medusa.sbdatetime import date_presets, time_presets
from medusa.schedulers.utils import generate_schedulers
from medusa.server.api.v2.base import (
    BaseRequestHandler,
    BooleanField,
    EnumField,
    FloatField,
    IntegerField,
    ListField,
    MetadataStructureField,
    StringField,
    iter_nested_items,
    set_nested_value,
)

from six import iteritems, itervalues, text_type
from six.moves import map

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


def season_folders_validator(value):
    """Validate default season folders setting."""
    return not (app.NAMING_FORCE_FOLDERS and value is False)


class ConfigHandler(BaseRequestHandler):
    """Config request handler."""

    #: resource name
    name = 'config'
    #: identifier
    identifier = ('identifier', r'\w+')
    #: path param
    path_param = ('path_param', r'\w+')
    #: allowed HTTP methods
    allowed_methods = ('GET', 'PATCH',)
    #: patch mapping
    patches = {
        # Main
        'rootDirs': ListField(app, 'ROOT_DIRS'),

        'showDefaults.status': EnumField(app, 'STATUS_DEFAULT', (SKIPPED, WANTED, IGNORED), int),
        'showDefaults.statusAfter': EnumField(app, 'STATUS_DEFAULT_AFTER', (SKIPPED, WANTED, IGNORED), int),
        'showDefaults.quality': IntegerField(app, 'QUALITY_DEFAULT', validator=Quality.is_valid_combined_quality),
        'showDefaults.subtitles': BooleanField(app, 'SUBTITLES_DEFAULT', converter=bool),
        'showDefaults.seasonFolders': BooleanField(app, 'SEASON_FOLDERS_DEFAULT', validator=season_folders_validator,
                                                   converter=bool),
        'showDefaults.anime': BooleanField(app, 'ANIME_DEFAULT', converter=bool),
        'showDefaults.scene': BooleanField(app, 'SCENE_DEFAULT', converter=bool),
        'showDefaults.showLists': ListField(app, 'SHOWLISTS_DEFAULT'),
        'anonRedirect': StringField(app, 'ANON_REDIRECT'),
        'emby.enabled': BooleanField(app, 'USE_EMBY'),

        'launchBrowser': BooleanField(app, 'LAUNCH_BROWSER'),
        'defaultPage': StringField(app, 'DEFAULT_PAGE'),
        'trashRemoveShow': BooleanField(app, 'TRASH_REMOVE_SHOW'),
        'trashRotateLogs': BooleanField(app, 'TRASH_ROTATE_LOGS'),

        'indexerDefaultLanguage': StringField(app, 'INDEXER_DEFAULT_LANGUAGE'),
        'showUpdateHour': IntegerField(app, 'SHOWUPDATE_HOUR'),
        'indexerTimeout': IntegerField(app, 'INDEXER_TIMEOUT'),
        'indexerDefault': IntegerField(app, 'INDEXER_DEFAULT'),
        'plexFallBack.enable': BooleanField(app, 'FALLBACK_PLEX_ENABLE'),
        'plexFallBack.notifications': BooleanField(app, 'FALLBACK_PLEX_NOTIFICATIONS'),
        'plexFallBack.timeout': IntegerField(app, 'FALLBACK_PLEX_TIMEOUT'),
        'versionNotify': BooleanField(app, 'VERSION_NOTIFY'),
        'autoUpdate': BooleanField(app, 'AUTO_UPDATE'),
        'updateFrequency': IntegerField(app, 'UPDATE_FREQUENCY'),
        'notifyOnUpdate': BooleanField(app, 'NOTIFY_ON_UPDATE'),
        # 'availableThemes': IgnoreField(app, 'AVAILABLE_THEMES'),
        # 'timePresets': IgnoreField(app, 'time_presets'),
        # 'datePresets': IgnoreField(app, 'date_presets'),

        'webInterface.apiKey': StringField(app, 'API_KEY'),
        'webInterface.log': BooleanField(app, 'WEB_LOG'),
        'webInterface.username': StringField(app, 'WEB_USERNAME'),
        'webInterface.password': StringField(app, 'WEB_PASSWORD'),
        'webInterface.port': IntegerField(app, 'WEB_PORT'),
        'webInterface.notifyOnLogin': BooleanField(app, 'NOTIFY_ON_LOGIN'),
        'webInterface.ipv6': BooleanField(app, 'WEB_IPV6'),
        'webInterface.httpsEnable': BooleanField(app, 'ENABLE_HTTPS'),
        'webInterface.httpsCert': StringField(app, 'HTTPS_CERT'),
        'webInterface.httpsKey': StringField(app, 'HTTPS_KEY'),
        'webInterface.handleReverseProxy': BooleanField(app, 'HANDLE_REVERSE_PROXY'),

        'webRoot': StringField(app, 'WEB_ROOT'),
        'cpuPreset': StringField(app, 'CPU_PRESET'),
        'sslVerify': BooleanField(app, 'SSL_VERIFY'),
        'sslCaBundle': StringField(app, 'SSL_CA_BUNDLE'),
        'noRestart': BooleanField(app, 'NO_RESTART'),
        'encryptionVersion': BooleanField(app, 'ENCRYPTION_VERSION'),
        'calendarUnprotected': BooleanField(app, 'CALENDAR_UNPROTECTED'),
        'calendarIcons': BooleanField(app, 'CALENDAR_ICONS'),
        'proxySetting': StringField(app, 'PROXY_SETTING'),
        'proxyIndexers': BooleanField(app, 'PROXY_INDEXERS'),

        'skipRemovedFiles': BooleanField(app, 'SKIP_REMOVED_FILES'),
        'epDefaultDeletedStatus': IntegerField(app, 'EP_DEFAULT_DELETED_STATUS'),

        'logs.debug': BooleanField(app, 'DEBUG'),
        'logs.dbDebug': BooleanField(app, 'DBDEBUG'),
        'logs.actualLogDir': StringField(app, 'ACTUAL_LOG_DIR'),
        'logs.nr': IntegerField(app, 'LOG_NR'),
        'logs.size': FloatField(app, 'LOG_SIZE'),
        'logs.subliminalLog': BooleanField(app, 'SUBLIMINAL_LOG'),
        'logs.privacyLevel': StringField(app, 'PRIVACY_LEVEL'),
        'logs.custom': ListField(app, 'CUSTOM_LOGS'),

        'developer': BooleanField(app, 'DEVELOPER'),

        'git.username': StringField(app, 'GIT_USERNAME'),
        'git.password': StringField(app, 'GIT_PASSWORD'),
        'git.token': StringField(app, 'GIT_TOKEN'),
        'git.authType': IntegerField(app, 'GIT_AUTH_TYPE'),
        'git.remote': StringField(app, 'GIT_REMOTE'),
        'git.path': StringField(app, 'GIT_PATH'),
        'git.org': StringField(app, 'GIT_ORG'),
        'git.reset': BooleanField(app, 'GIT_RESET'),
        'git.resetBranches': ListField(app, 'GIT_RESET_BRANCHES'),
        'git.url': StringField(app, 'GITHUB_IO_URL'),

        'wikiUrl': StringField(app, 'WIKI_URL'),
        'donationsUrl': StringField(app, 'DONATIONS_URL'),
        'sourceUrl': StringField(app, 'APPLICATION_URL'),
        'downloadUrl': StringField(app, 'DOWNLOAD_URL'),
        'subtitlesMulti': BooleanField(app, 'SUBTITLES_MULTI'),
        'namingForceFolders': BooleanField(app, 'NAMING_FORCE_FOLDERS'),
        'subtitles.enabled': BooleanField(app, 'USE_SUBTITLES'),
        'recentShows': ListField(app, 'SHOWS_RECENT'),

        # Sections
        'clients.torrents.authType': StringField(app, 'TORRENT_AUTH_TYPE'),
        'clients.torrents.dir': StringField(app, 'TORRENT_DIR'),
        'clients.torrents.enabled': BooleanField(app, 'USE_TORRENTS'),
        'clients.torrents.highBandwidth': BooleanField(app, 'TORRENT_HIGH_BANDWIDTH'),
        'clients.torrents.host': StringField(app, 'TORRENT_HOST'),
        'clients.torrents.label': StringField(app, 'TORRENT_LABEL'),
        'clients.torrents.labelAnime': StringField(app, 'TORRENT_LABEL_ANIME'),
        'clients.torrents.method': StringField(app, 'TORRENT_METHOD'),
        'clients.torrents.password': StringField(app, 'TORRENT_PASSWORD'),
        'clients.torrents.path': StringField(app, 'TORRENT_PATH'),
        'clients.torrents.paused': BooleanField(app, 'TORRENT_PAUSED'),
        'clients.torrents.rpcUrl': StringField(app, 'TORRENT_RPCURL'),
        'clients.torrents.seedLocation': StringField(app, 'TORRENT_SEED_LOCATION'),
        'clients.torrents.seedTime': IntegerField(app, 'TORRENT_SEED_TIME'),
        'clients.torrents.username': StringField(app, 'TORRENT_USERNAME'),
        'clients.torrents.verifySSL': BooleanField(app, 'TORRENT_VERIFY_CERT'),
        'clients.nzb.enabled': BooleanField(app, 'USE_NZBS'),
        'clients.nzb.dir': StringField(app, 'NZB_DIR'),
        'clients.nzb.method': StringField(app, 'NZB_METHOD'),
        'clients.nzb.nzbget.category': StringField(app, 'NZBGET_CATEGORY'),
        'clients.nzb.nzbget.categoryAnime': StringField(app, 'NZBGET_CATEGORY_ANIME'),
        'clients.nzb.nzbget.categoryAnimeBacklog': StringField(app, 'NZBGET_CATEGORY_ANIME_BACKLOG'),
        'clients.nzb.nzbget.categoryBacklog': StringField(app, 'NZBGET_CATEGORY_BACKLOG'),
        'clients.nzb.nzbget.host': StringField(app, 'NZBGET_HOST'),
        'clients.nzb.nzbget.password': StringField(app, 'NZBGET_PASSWORD'),
        'clients.nzb.nzbget.priority': IntegerField(app, 'NZBGET_PRIORITY'),
        'clients.nzb.nzbget.useHttps': BooleanField(app, 'NZBGET_USE_HTTPS'),
        'clients.nzb.nzbget.username': StringField(app, 'NZBGET_USERNAME'),
        'clients.nzb.sabnzbd.apiKey': StringField(app, 'SAB_APIKEY'),
        'clients.nzb.sabnzbd.category': StringField(app, 'SAB_CATEGORY'),
        'clients.nzb.sabnzbd.categoryAnime': StringField(app, 'SAB_CATEGORY_ANIME'),
        'clients.nzb.sabnzbd.categoryAnimeBacklog': StringField(app, 'SAB_CATEGORY_ANIME_BACKLOG'),
        'clients.nzb.sabnzbd.categoryBacklog': StringField(app, 'SAB_CATEGORY_BACKLOG'),
        'clients.nzb.sabnzbd.forced': BooleanField(app, 'SAB_FORCED'),
        'clients.nzb.sabnzbd.host': StringField(app, 'SAB_HOST'),
        'clients.nzb.sabnzbd.password': StringField(app, 'SAB_PASSWORD'),
        'clients.nzb.sabnzbd.username': StringField(app, 'SAB_USERNAME'),


        'postProcessing.showDownloadDir': StringField(app, 'TV_DOWNLOAD_DIR'),
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
        'postProcessing.naming.stripYear': BooleanField(app, 'NAMING_STRIP_YEAR'),

        'search.general.randomizeProviders': BooleanField(app, 'RANDOMIZE_PROVIDERS'),
        'search.general.downloadPropers': BooleanField(app, 'DOWNLOAD_PROPERS'),
        'search.general.checkPropersInterval': StringField(app, 'CHECK_PROPERS_INTERVAL'),
        # 'search.general.propersIntervalLabels': IntegerField(app, 'PROPERS_INTERVAL_LABELS'),
        'search.general.propersSearchDays': IntegerField(app, 'PROPERS_SEARCH_DAYS'),
        'search.general.backlogDays': IntegerField(app, 'BACKLOG_DAYS'),
        'search.general.backlogFrequency': IntegerField(app, 'BACKLOG_FREQUENCY'),
        'search.general.minBacklogFrequency': IntegerField(app, 'MIN_BACKLOG_FREQUENCY'),
        'search.general.dailySearchFrequency': IntegerField(app, 'DAILYSEARCH_FREQUENCY'),
        'search.general.minDailySearchFrequency': IntegerField(app, 'MIN_DAILYSEARCH_FREQUENCY'),
        'search.general.removeFromClient': BooleanField(app, 'REMOVE_FROM_CLIENT'),
        'search.general.torrentCheckerFrequency': IntegerField(app, 'TORRENT_CHECKER_FREQUENCY'),
        'search.general.minTorrentCheckerFrequency': IntegerField(app, 'MIN_TORRENT_CHECKER_FREQUENCY'),
        'search.general.usenetRetention': IntegerField(app, 'USENET_RETENTION'),
        'search.general.trackersList': ListField(app, 'TRACKERS_LIST'),
        'search.general.allowHighPriority': BooleanField(app, 'ALLOW_HIGH_PRIORITY'),
        'search.general.cacheTrimming': BooleanField(app, 'CACHE_TRIMMING'),
        'search.general.maxCacheAge': IntegerField(app, 'MAX_CACHE_AGE'),
        'search.general.failedDownloads.enabled': BooleanField(app, 'USE_FAILED_DOWNLOADS'),
        'search.general.failedDownloads.deleteFailed': BooleanField(app, 'DELETE_FAILED'),

        'search.filters.ignored': ListField(app, 'IGNORE_WORDS'),
        'search.filters.undesired': ListField(app, 'UNDESIRED_WORDS'),
        'search.filters.preferred': ListField(app, 'PREFERRED_WORDS'),
        'search.filters.required': ListField(app, 'REQUIRE_WORDS'),
        'search.filters.ignoredSubsList': ListField(app, 'IGNORED_SUBS_LIST'),
        'search.filters.ignoreUnknownSubs': BooleanField(app, 'IGNORE_UND_SUBS'),

        'notifiers.kodi.enabled': BooleanField(app, 'USE_KODI'),
        'notifiers.kodi.alwaysOn': BooleanField(app, 'KODI_ALWAYS_ON'),
        'notifiers.kodi.notifyOnSnatch': BooleanField(app, 'KODI_NOTIFY_ONSNATCH'),
        'notifiers.kodi.notifyOnDownload': BooleanField(app, 'KODI_NOTIFY_ONDOWNLOAD'),
        'notifiers.kodi.notifyOnSubtitleDownload': BooleanField(app, 'KODI_NOTIFY_ONSUBTITLEDOWNLOAD'),
        'notifiers.kodi.update.library': BooleanField(app, 'KODI_UPDATE_LIBRARY'),
        'notifiers.kodi.update.full': BooleanField(app, 'KODI_UPDATE_FULL'),
        'notifiers.kodi.update.onlyFirst': BooleanField(app, 'KODI_UPDATE_ONLYFIRST'),
        'notifiers.kodi.host': ListField(app, 'KODI_HOST'),
        'notifiers.kodi.username': StringField(app, 'KODI_USERNAME'),
        'notifiers.kodi.password': StringField(app, 'KODI_PASSWORD'),
        'notifiers.kodi.libraryCleanPending': BooleanField(app, 'KODI_LIBRARY_CLEAN_PENDING'),
        'notifiers.kodi.cleanLibrary': BooleanField(app, 'KODI_CLEAN_LIBRARY'),

        'notifiers.plex.server.enabled': BooleanField(app, 'USE_PLEX_SERVER'),
        'notifiers.plex.server.updateLibrary': BooleanField(app, 'PLEX_UPDATE_LIBRARY'),
        'notifiers.plex.server.host': ListField(app, 'PLEX_SERVER_HOST'),
        'notifiers.plex.server.https': BooleanField(app, 'PLEX_SERVER_HTTPS'),
        'notifiers.plex.server.username': StringField(app, 'PLEX_SERVER_USERNAME'),
        'notifiers.plex.server.password': StringField(app, 'PLEX_SERVER_PASSWORD'),
        'notifiers.plex.server.token': StringField(app, 'PLEX_SERVER_TOKEN'),
        'notifiers.plex.client.enabled': BooleanField(app, 'USE_PLEX_CLIENT'),
        'notifiers.plex.client.username': StringField(app, 'PLEX_CLIENT_USERNAME'),
        'notifiers.plex.client.host': ListField(app, 'PLEX_CLIENT_HOST'),
        'notifiers.plex.client.notifyOnSnatch': BooleanField(app, 'PLEX_NOTIFY_ONSNATCH'),
        'notifiers.plex.client.notifyOnDownload': BooleanField(app, 'PLEX_NOTIFY_ONDOWNLOAD'),
        'notifiers.plex.client.notifyOnSubtitleDownload': BooleanField(app, 'PLEX_NOTIFY_ONSUBTITLEDOWNLOAD'),

        'notifiers.emby.enabled': BooleanField(app, 'USE_EMBY'),
        'notifiers.emby.host': StringField(app, 'EMBY_HOST'),
        'notifiers.emby.apiKey': StringField(app, 'EMBY_APIKEY'),

        'notifiers.nmj.enabled': BooleanField(app, 'USE_NMJ'),
        'notifiers.nmj.host': StringField(app, 'NMJ_HOST'),
        'notifiers.nmj.database': StringField(app, 'NMJ_DATABASE'),
        'notifiers.nmj.mount': StringField(app, 'NMJ_MOUNT'),

        'notifiers.nmjv2.enabled': BooleanField(app, 'USE_NMJv2'),
        'notifiers.nmjv2.host': StringField(app, 'NMJv2_HOST'),
        'notifiers.nmjv2.dbloc': StringField(app, 'NMJv2_DBLOC'),
        'notifiers.nmjv2.database': StringField(app, 'NMJv2_DATABASE'),

        'notifiers.synologyIndex.enabled': BooleanField(app, 'USE_SYNOINDEX'),

        'notifiers.synology.enabled': BooleanField(app, 'USE_SYNOLOGYNOTIFIER'),
        'notifiers.synology.notifyOnSnatch': BooleanField(app, 'SYNOLOGYNOTIFIER_NOTIFY_ONSNATCH'),
        'notifiers.synology.notifyOnDownload': BooleanField(app, 'SYNOLOGYNOTIFIER_NOTIFY_ONDOWNLOAD'),
        'notifiers.synology.notifyOnSubtitleDownload': BooleanField(app, 'SYNOLOGYNOTIFIER_NOTIFY_ONSUBTITLEDOWNLOAD'),

        'notifiers.pyTivo.enabled': BooleanField(app, 'USE_PYTIVO'),
        'notifiers.pyTivo.host': StringField(app, 'PYTIVO_HOST'),
        'notifiers.pyTivo.name': StringField(app, 'PYTIVO_TIVO_NAME'),
        'notifiers.pyTivo.shareName': StringField(app, 'PYTIVO_SHARE_NAME'),

        'notifiers.growl.enabled': BooleanField(app, 'USE_GROWL'),
        'notifiers.growl.host': StringField(app, 'GROWL_HOST'),
        'notifiers.growl.password': StringField(app, 'GROWL_PASSWORD'),
        'notifiers.growl.notifyOnSnatch': BooleanField(app, 'GROWL_NOTIFY_ONSNATCH'),
        'notifiers.growl.notifyOnDownload': BooleanField(app, 'GROWL_NOTIFY_ONDOWNLOAD'),
        'notifiers.growl.notifyOnSubtitleDownload': BooleanField(app, 'GROWL_NOTIFY_ONSUBTITLEDOWNLOAD'),

        'notifiers.prowl.enabled': BooleanField(app, 'USE_PROWL'),
        'notifiers.prowl.api': ListField(app, 'PROWL_API'),
        'notifiers.prowl.messageTitle': StringField(app, 'PROWL_MESSAGE_TITLE'),
        'notifiers.prowl.priority': IntegerField(app, 'PROWL_PRIORITY'),
        'notifiers.prowl.notifyOnSnatch': BooleanField(app, 'PROWL_NOTIFY_ONSNATCH'),
        'notifiers.prowl.notifyOnDownload': BooleanField(app, 'PROWL_NOTIFY_ONDOWNLOAD'),
        'notifiers.prowl.notifyOnSubtitleDownload': BooleanField(app, 'PROWL_NOTIFY_ONSUBTITLEDOWNLOAD'),

        'notifiers.libnotify.enabled': BooleanField(app, 'USE_LIBNOTIFY'),
        'notifiers.libnotify.notifyOnSnatch': BooleanField(app, 'LIBNOTIFY_NOTIFY_ONSNATCH'),
        'notifiers.libnotify.notifyOnDownload': BooleanField(app, 'LIBNOTIFY_NOTIFY_ONDOWNLOAD'),
        'notifiers.libnotify.notifyOnSubtitleDownload': BooleanField(app, 'LIBNOTIFY_NOTIFY_ONSUBTITLEDOWNLOAD'),

        'notifiers.pushover.enabled': BooleanField(app, 'USE_PUSHOVER'),
        'notifiers.pushover.apiKey': StringField(app, 'PUSHOVER_APIKEY'),
        'notifiers.pushover.userKey': StringField(app, 'PUSHOVER_USERKEY'),
        'notifiers.pushover.device': ListField(app, 'PUSHOVER_DEVICE'),
        'notifiers.pushover.sound': StringField(app, 'PUSHOVER_SOUND'),
        'notifiers.pushover.priority': IntegerField(app, 'PUSHOVER_PRIORITY'),
        'notifiers.pushover.notifyOnSnatch': BooleanField(app, 'PUSHOVER_NOTIFY_ONSNATCH'),
        'notifiers.pushover.notifyOnDownload': BooleanField(app, 'PUSHOVER_NOTIFY_ONDOWNLOAD'),
        'notifiers.pushover.notifyOnSubtitleDownload': BooleanField(app, 'PUSHOVER_NOTIFY_ONSUBTITLEDOWNLOAD'),

        'notifiers.boxcar2.enabled': BooleanField(app, 'USE_BOXCAR2'),
        'notifiers.boxcar2.accessToken': StringField(app, 'BOXCAR2_ACCESSTOKEN'),
        'notifiers.boxcar2.notifyOnSnatch': BooleanField(app, 'BOXCAR2_NOTIFY_ONSNATCH'),
        'notifiers.boxcar2.notifyOnDownload': BooleanField(app, 'BOXCAR2_NOTIFY_ONDOWNLOAD'),
        'notifiers.boxcar2.notifyOnSubtitleDownload': BooleanField(app, 'BOXCAR2_NOTIFY_ONSUBTITLEDOWNLOAD'),

        'notifiers.pushalot.enabled': BooleanField(app, 'USE_PUSHALOT'),
        'notifiers.pushalot.authToken': StringField(app, 'PUSHALOT_AUTHORIZATIONTOKEN'),
        'notifiers.pushalot.notifyOnSnatch': BooleanField(app, 'PUSHALOT_NOTIFY_ONSNATCH'),
        'notifiers.pushalot.notifyOnDownload': BooleanField(app, 'PUSHALOT_NOTIFY_ONDOWNLOAD'),
        'notifiers.pushalot.notifyOnSubtitleDownload': BooleanField(app, 'PUSHALOT_NOTIFY_ONSUBTITLEDOWNLOAD'),

        'notifiers.pushbullet.enabled': BooleanField(app, 'USE_PUSHBULLET'),
        'notifiers.pushbullet.api': StringField(app, 'PUSHBULLET_API'),
        'notifiers.pushbullet.device': StringField(app, 'PUSHBULLET_DEVICE'),
        'notifiers.pushbullet.notifyOnSnatch': BooleanField(app, 'PUSHBULLET_NOTIFY_ONSNATCH'),
        'notifiers.pushbullet.notifyOnDownload': BooleanField(app, 'PUSHBULLET_NOTIFY_ONDOWNLOAD'),
        'notifiers.pushbullet.notifyOnSubtitleDownload': BooleanField(app, 'PUSHBULLET_NOTIFY_ONSUBTITLEDOWNLOAD'),

        'notifiers.join.enabled': BooleanField(app, 'USE_JOIN'),
        'notifiers.join.api': StringField(app, 'JOIN_API'),
        'notifiers.join.device': StringField(app, 'JOIN_DEVICE'),
        'notifiers.join.notifyOnSnatch': BooleanField(app, 'JOIN_NOTIFY_ONSNATCH'),
        'notifiers.join.notifyOnDownload': BooleanField(app, 'JOIN_NOTIFY_ONDOWNLOAD'),
        'notifiers.join.notifyOnSubtitleDownload': BooleanField(app, 'JOIN_NOTIFY_ONSUBTITLEDOWNLOAD'),

        'notifiers.freemobile.enabled': BooleanField(app, 'USE_FREEMOBILE'),
        'notifiers.freemobile.api': StringField(app, 'FREEMOBILE_APIKEY'),
        'notifiers.freemobile.id': StringField(app, 'FREEMOBILE_ID'),
        'notifiers.freemobile.notifyOnSnatch': BooleanField(app, 'FREEMOBILE_NOTIFY_ONSNATCH'),
        'notifiers.freemobile.notifyOnDownload': BooleanField(app, 'FREEMOBILE_NOTIFY_ONDOWNLOAD'),
        'notifiers.freemobile.notifyOnSubtitleDownload': BooleanField(app, 'FREEMOBILE_NOTIFY_ONSUBTITLEDOWNLOAD'),

        'notifiers.telegram.enabled': BooleanField(app, 'USE_TELEGRAM'),
        'notifiers.telegram.api': StringField(app, 'TELEGRAM_APIKEY'),
        'notifiers.telegram.id': StringField(app, 'TELEGRAM_ID'),
        'notifiers.telegram.notifyOnSnatch': BooleanField(app, 'TELEGRAM_NOTIFY_ONSNATCH'),
        'notifiers.telegram.notifyOnDownload': BooleanField(app, 'TELEGRAM_NOTIFY_ONDOWNLOAD'),
        'notifiers.telegram.notifyOnSubtitleDownload': BooleanField(app, 'TELEGRAM_NOTIFY_ONSUBTITLEDOWNLOAD'),

        'notifiers.discord.enabled': BooleanField(app, 'USE_DISCORD'),
        'notifiers.discord.webhook': StringField(app, 'DISCORD_WEBHOOK'),
        'notifiers.discord.tts': BooleanField(app, 'DISCORD_TTS'),
        'notifiers.discord.notifyOnSnatch': BooleanField(app, 'DISCORD_NOTIFY_ONSNATCH'),
        'notifiers.discord.notifyOnDownload': BooleanField(app, 'DISCORD_NOTIFY_ONDOWNLOAD'),
        'notifiers.discord.notifyOnSubtitleDownload': BooleanField(app, 'DISCORD_NOTIFY_ONSUBTITLEDOWNLOAD'),
        'notifiers.discord.name': StringField(app, 'DISCORD_NAME'),

        'notifiers.twitter.enabled': BooleanField(app, 'USE_TWITTER'),
        'notifiers.twitter.dmto': StringField(app, 'TWITTER_DMTO'),
        'notifiers.twitter.prefix': StringField(app, 'TWITTER_PREFIX'),
        'notifiers.twitter.directMessage': BooleanField(app, 'TWITTER_USEDM'),
        'notifiers.twitter.notifyOnSnatch': BooleanField(app, 'TWITTER_NOTIFY_ONSNATCH'),
        'notifiers.twitter.notifyOnDownload': BooleanField(app, 'TWITTER_NOTIFY_ONDOWNLOAD'),
        'notifiers.twitter.notifyOnSubtitleDownload': BooleanField(app, 'TWITTER_NOTIFY_ONSUBTITLEDOWNLOAD'),

        'notifiers.trakt.enabled': BooleanField(app, 'USE_TRAKT'),
        'notifiers.trakt.pinUrl': StringField(app, 'TRAKT_PIN_URL'),
        'notifiers.trakt.username': StringField(app, 'TRAKT_USERNAME'),
        'notifiers.trakt.accessToken': StringField(app, 'TRAKT_ACCESS_TOKEN'),
        'notifiers.trakt.timeout': IntegerField(app, 'TRAKT_TIMEOUT'),
        'notifiers.trakt.defaultIndexer': IntegerField(app, 'TRAKT_DEFAULT_INDEXER'),
        'notifiers.trakt.sync': BooleanField(app, 'TRAKT_SYNC'),
        'notifiers.trakt.syncRemove': BooleanField(app, 'TRAKT_SYNC_REMOVE'),
        'notifiers.trakt.syncWatchlist': BooleanField(app, 'TRAKT_SYNC_WATCHLIST'),
        'notifiers.trakt.methodAdd': IntegerField(app, 'TRAKT_METHOD_ADD'),
        'notifiers.trakt.removeWatchlist': BooleanField(app, 'TRAKT_REMOVE_WATCHLIST'),
        'notifiers.trakt.removeSerieslist': BooleanField(app, 'TRAKT_REMOVE_SERIESLIST'),
        'notifiers.trakt.removeShowFromApplication': BooleanField(app, 'TRAKT_REMOVE_SHOW_FROM_APPLICATION'),
        'notifiers.trakt.startPaused': BooleanField(app, 'TRAKT_START_PAUSED'),
        'notifiers.trakt.blacklistName': StringField(app, 'TRAKT_BLACKLIST_NAME'),

        'notifiers.email.enabled': BooleanField(app, 'USE_EMAIL'),
        'notifiers.email.host': StringField(app, 'EMAIL_HOST'),
        'notifiers.email.port': IntegerField(app, 'EMAIL_PORT'),
        'notifiers.email.from': StringField(app, 'EMAIL_FROM'),
        'notifiers.email.tls': BooleanField(app, 'EMAIL_TLS'),
        'notifiers.email.username': StringField(app, 'EMAIL_USER'),
        'notifiers.email.password': StringField(app, 'EMAIL_PASSWORD'),
        'notifiers.email.addressList': ListField(app, 'EMAIL_LIST'),
        'notifiers.email.subject': StringField(app, 'EMAIL_SUBJECT'),
        'notifiers.email.notifyOnSnatch': BooleanField(app, 'EMAIL_NOTIFY_ONSNATCH'),
        'notifiers.email.notifyOnDownload': BooleanField(app, 'EMAIL_NOTIFY_ONDOWNLOAD'),
        'notifiers.email.notifyOnSubtitleDownload': BooleanField(app, 'EMAIL_NOTIFY_ONSUBTITLEDOWNLOAD'),

        'notifiers.slack.enabled': BooleanField(app, 'USE_SLACK'),
        'notifiers.slack.webhook': StringField(app, 'SLACK_WEBHOOK'),
        'notifiers.slack.notifyOnSnatch': BooleanField(app, 'SLACK_NOTIFY_SNATCH'),
        'notifiers.slack.notifyOnDownload': BooleanField(app, 'SLACK_NOTIFY_DOWNLOAD'),
        'notifiers.slack.notifyOnSubtitleDownload': BooleanField(app, 'SLACK_NOTIFY_SUBTITLEDOWNLOAD'),

        'layout.comingEps.missedRange': IntegerField(app, 'COMING_EPS_MISSED_RANGE'),
        'layout.comingEps.layout': StringField(app, 'COMING_EPS_LAYOUT'),
        'layout.comingEps.sort': StringField(app, 'COMING_EPS_SORT'),
        'layout.comingEps.displayPaused': BooleanField(app, 'COMING_EPS_DISPLAY_PAUSED'),
        'layout.schedule': EnumField(app, 'COMING_EPS_LAYOUT', ('poster', 'banner', 'list', 'calendar'),
                                     default_value='banner', post_processor=layout_schedule_post_processor),
        'layout.history': EnumField(app, 'HISTORY_LAYOUT', ('compact', 'detailed'), default_value='detailed'),
        'layout.home': EnumField(app, 'HOME_LAYOUT', ('poster', 'small', 'banner', 'simple', 'coverflow'),
                                 default_value='poster'),
        'layout.show.specials': BooleanField(app, 'DISPLAY_SHOW_SPECIALS'),
        'layout.show.showListOrder': ListField(app, 'SHOW_LIST_ORDER'),
        'layout.show.pagination.enable': BooleanField(app, 'SHOW_USE_PAGINATION'),
        'layout.wide': BooleanField(app, 'LAYOUT_WIDE'),
        'layout.posterSortdir': IntegerField(app, 'POSTER_SORTDIR'),
        'layout.themeName': StringField(app, 'THEME_NAME', setter=theme_name_setter),
        'layout.timezoneDisplay': StringField(app, 'TIMEZONE_DISPLAY'),
        'layout.trimZero': BooleanField(app, 'TRIM_ZERO'),
        'layout.sortArticle': BooleanField(app, 'SORT_ARTICLE'),
        'layout.fuzzyDating': BooleanField(app, 'FUZZY_DATING'),
        'layout.posterSortby': StringField(app, 'POSTER_SORTBY'),
        'layout.historyLimit': StringField(app, 'HISTORY_LIMIT'),
        'layout.fanartBackground': BooleanField(app, 'FANART_BACKGROUND'),
        'layout.fanartBackgroundOpacity': FloatField(app, 'FANART_BACKGROUND_OPACITY'),
        'layout.backlogOverview.period': StringField(app, 'BACKLOG_PERIOD'),
        'layout.backlogOverview.status': StringField(app, 'BACKLOG_STATUS'),
        'layout.timeStyle': StringField(app, 'TIME_PRESET_W_SECONDS'),
        'layout.dateStyle': StringField(app, 'DATE_PRESET'),
        'layout.selectedRootIndex': IntegerField(app, 'SELECTED_ROOT'),

        'layout.animeSplitHome': BooleanField(app, 'ANIME_SPLIT_HOME'),
        'layout.splitHomeInTabs': BooleanField(app, 'ANIME_SPLIT_HOME_IN_TABS'),

        'anime.anidb.enabled': BooleanField(app, 'USE_ANIDB'),
        'anime.anidb.username': StringField(app, 'ANIDB_USERNAME'),
        'anime.anidb.password': StringField(app, 'ANIDB_PASSWORD'),
        'anime.anidb.useMylist': BooleanField(app, 'ANIDB_USE_MYLIST'),
        'anime.autoAnimeToList': BooleanField(app, 'AUTO_ANIME_TO_LIST'),
        'anime.showlistDefaultAnime': ListField(app, 'SHOWLISTS_DEFAULT_ANIME')
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
            config_data = {}

            for section in config_sections:
                config_data[section] = DataGenerator.get_data(section)

            return self._ok(data=config_data)

        config_data = DataGenerator.get_data(identifier)

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
        ws.Message('configUpdated', {
            'section': identifier,
            'config': DataGenerator.get_data(identifier)
        }).push()

        return self._ok(data=accepted)


class DataGenerator(object):
    """Generate the requested config data on demand."""

    @classmethod
    def sections(cls):
        """Get the available section names."""
        return [
            name[5:]
            for (name, function)
            in inspect.getmembers(cls, predicate=lambda f: inspect.isfunction(f) or inspect.ismethod(f))
            if name.startswith('data_')
        ]

    @classmethod
    def get_data(cls, section):
        """Return the requested section data."""
        return getattr(cls, 'data_' + section)()

    @staticmethod
    def data_main():
        """Main."""
        section_data = {}

        # Can't get rid of this because of the usage of themeName in MEDUSA.config.themeName.
        section_data['themeName'] = app.THEME_NAME
        section_data['anonRedirect'] = app.ANON_REDIRECT
        section_data['rootDirs'] = app.ROOT_DIRS
        section_data['wikiUrl'] = app.WIKI_URL
        section_data['donationsUrl'] = app.DONATIONS_URL
        section_data['sourceUrl'] = app.APPLICATION_URL
        section_data['downloadUrl'] = app.DOWNLOAD_URL
        section_data['subtitlesMulti'] = bool(app.SUBTITLES_MULTI)
        section_data['namingForceFolders'] = bool(app.NAMING_FORCE_FOLDERS)
        section_data['subtitles'] = {}
        section_data['subtitles']['enabled'] = bool(app.USE_SUBTITLES)
        section_data['recentShows'] = app.SHOWS_RECENT

        # Pick a random series to show as background.
        # TODO: Recreate this in Vue when the webapp has a reliable list of shows to choose from.
        section_data['randomShowSlug'] = getattr(choice(app.showList), 'slug', None) if app.FANART_BACKGROUND and app.showList else ''

        section_data['showDefaults'] = {}
        section_data['showDefaults']['status'] = app.STATUS_DEFAULT
        section_data['showDefaults']['statusAfter'] = app.STATUS_DEFAULT_AFTER
        section_data['showDefaults']['quality'] = app.QUALITY_DEFAULT
        section_data['showDefaults']['subtitles'] = bool(app.SUBTITLES_DEFAULT)
        section_data['showDefaults']['seasonFolders'] = bool(app.SEASON_FOLDERS_DEFAULT)
        section_data['showDefaults']['anime'] = bool(app.ANIME_DEFAULT)
        section_data['showDefaults']['scene'] = bool(app.SCENE_DEFAULT)
        section_data['showDefaults']['showLists'] = list(app.SHOWLISTS_DEFAULT)

        section_data['logs'] = {}
        section_data['logs']['debug'] = bool(app.DEBUG)
        section_data['logs']['dbDebug'] = bool(app.DBDEBUG)
        section_data['logs']['loggingLevels'] = {k.lower(): v for k, v in iteritems(logger.LOGGING_LEVELS)}
        section_data['logs']['numErrors'] = len(classes.ErrorViewer.errors)
        section_data['logs']['numWarnings'] = len(classes.WarningViewer.errors)
        section_data['logs']['actualLogDir'] = app.ACTUAL_LOG_DIR
        section_data['logs']['nr'] = int(app.LOG_NR)
        section_data['logs']['size'] = float(app.LOG_SIZE)
        section_data['logs']['subliminalLog'] = bool(app.SUBLIMINAL_LOG)
        section_data['logs']['privacyLevel'] = app.PRIVACY_LEVEL
        section_data['logs']['custom'] = app.CUSTOM_LOGS

        # Added for config - main, needs refactoring in the structure.
        section_data['launchBrowser'] = bool(app.LAUNCH_BROWSER)
        section_data['defaultPage'] = app.DEFAULT_PAGE
        section_data['trashRemoveShow'] = bool(app.TRASH_REMOVE_SHOW)
        section_data['trashRotateLogs'] = bool(app.TRASH_ROTATE_LOGS)

        section_data['indexerDefaultLanguage'] = app.INDEXER_DEFAULT_LANGUAGE
        section_data['showUpdateHour'] = int_default(app.SHOWUPDATE_HOUR, app.DEFAULT_SHOWUPDATE_HOUR)
        section_data['indexerTimeout'] = int_default(app.INDEXER_TIMEOUT, 20)
        section_data['indexerDefault'] = app.INDEXER_DEFAULT

        section_data['plexFallBack'] = {}
        section_data['plexFallBack']['enable'] = bool(app.FALLBACK_PLEX_ENABLE)
        section_data['plexFallBack']['notifications'] = bool(app.FALLBACK_PLEX_NOTIFICATIONS)
        section_data['plexFallBack']['timeout'] = int(app.FALLBACK_PLEX_TIMEOUT)

        section_data['versionNotify'] = bool(app.VERSION_NOTIFY)
        section_data['autoUpdate'] = bool(app.AUTO_UPDATE)
        section_data['updateFrequency'] = int_default(app.UPDATE_FREQUENCY, app.DEFAULT_UPDATE_FREQUENCY)
        section_data['notifyOnUpdate'] = bool(app.NOTIFY_ON_UPDATE)
        section_data['availableThemes'] = [{'name': theme.name,
                                            'version': theme.version,
                                            'author': theme.author}
                                           for theme in app.AVAILABLE_THEMES]

        section_data['timePresets'] = list(time_presets)
        section_data['datePresets'] = list(date_presets)

        section_data['webInterface'] = {}
        section_data['webInterface']['apiKey'] = app.API_KEY
        section_data['webInterface']['log'] = bool(app.WEB_LOG)
        section_data['webInterface']['username'] = app.WEB_USERNAME
        section_data['webInterface']['password'] = app.WEB_PASSWORD
        section_data['webInterface']['port'] = int_default(app.WEB_PORT, 8081)
        section_data['webInterface']['notifyOnLogin'] = bool(app.NOTIFY_ON_LOGIN)
        section_data['webInterface']['ipv6'] = bool(app.WEB_IPV6)
        section_data['webInterface']['httpsEnable'] = bool(app.ENABLE_HTTPS)
        section_data['webInterface']['httpsCert'] = app.HTTPS_CERT
        section_data['webInterface']['httpsKey'] = app.HTTPS_KEY
        section_data['webInterface']['handleReverseProxy'] = bool(app.HANDLE_REVERSE_PROXY)

        section_data['webRoot'] = app.WEB_ROOT
        section_data['cpuPreset'] = app.CPU_PRESET
        section_data['sslVerify'] = bool(app.SSL_VERIFY)
        section_data['sslCaBundle'] = app.SSL_CA_BUNDLE
        section_data['noRestart'] = bool(app.NO_RESTART)
        section_data['encryptionVersion'] = bool(app.ENCRYPTION_VERSION)
        section_data['calendarUnprotected'] = bool(app.CALENDAR_UNPROTECTED)
        section_data['calendarIcons'] = bool(app.CALENDAR_ICONS)
        section_data['proxySetting'] = app.PROXY_SETTING
        section_data['proxyIndexers'] = bool(app.PROXY_INDEXERS)
        section_data['skipRemovedFiles'] = bool(app.SKIP_REMOVED_FILES)
        section_data['epDefaultDeletedStatus'] = app.EP_DEFAULT_DELETED_STATUS
        section_data['developer'] = bool(app.DEVELOPER)

        section_data['git'] = {}
        section_data['git']['username'] = app.GIT_USERNAME
        section_data['git']['password'] = app.GIT_PASSWORD
        section_data['git']['token'] = app.GIT_TOKEN
        section_data['git']['authType'] = int(app.GIT_AUTH_TYPE)
        section_data['git']['remote'] = app.GIT_REMOTE
        section_data['git']['path'] = app.GIT_PATH
        section_data['git']['org'] = app.GIT_ORG
        section_data['git']['reset'] = bool(app.GIT_RESET)
        section_data['git']['resetBranches'] = app.GIT_RESET_BRANCHES
        section_data['git']['url'] = app.GITHUB_IO_URL

        # backlogOverview has been moved to layout. It's still located here, because manage_backlogOvervew uses it
        # and still needs to be vieuified. After vueifying it, remove this.
        section_data['backlogOverview'] = {}
        section_data['backlogOverview']['status'] = app.BACKLOG_STATUS
        section_data['backlogOverview']['period'] = app.BACKLOG_PERIOD

        return section_data

    # The consts info only needs to be generated once.
    _generated_data_consts = {}

    @classmethod
    def data_consts(cls):
        """Constant values - values that will never change during runtime."""
        if cls._generated_data_consts:
            return cls._generated_data_consts

        section_data = {}

        section_data['qualities'] = {}

        def make_quality(value, name, key=None):
            return {
                'value': value,
                'key': key or Quality.quality_keys.get(value),
                'name': name
            }

        section_data['qualities']['values'] = [
            make_quality(value, name)
            for (value, name)
            in sorted(iteritems(common.Quality.qualityStrings))
        ]

        section_data['qualities']['anySets'] = [
            make_quality(value, name)
            for (value, name)
            in sorted(iteritems(common.Quality.combined_quality_strings))
        ]

        section_data['qualities']['presets'] = [
            make_quality(value, name, name.lower().replace('-', ''))
            for (value, name)
            in sorted(
                iteritems(common.qualityPresetStrings),
                # Sort presets based on the order defined in `qualityPresets`
                key=lambda i: common.qualityPresets.index(i[0])
            )
        ]

        section_data['statuses'] = [
            {
                'value': value,
                'key': to_camel_case(key.lower()),
                'name': common.statusStrings[value],
            }
            for (value, key)
            in map(
                lambda key: (getattr(common, key), key),
                # Sorted by value
                ('UNSET', 'UNAIRED', 'SNATCHED', 'WANTED', 'DOWNLOADED', 'SKIPPED', 'ARCHIVED',
                 'IGNORED', 'SNATCHED_PROPER', 'SUBTITLED', 'FAILED', 'SNATCHED_BEST')
            )
        ]

        # Save it for next time
        cls._generated_data_consts = section_data

        return section_data

    @staticmethod
    def data_metadata():
        """Metadata."""
        section_data = {}

        section_data['metadataProviders'] = {}

        for provider in itervalues(app.metadata_provider_dict):
            json_repr = provider.to_json()
            section_data['metadataProviders'][json_repr['id']] = json_repr

        return section_data

    @staticmethod
    def data_search():
        """Search filters."""
        section_data = {}

        section_data['general'] = {}
        section_data['general']['randomizeProviders'] = bool(app.RANDOMIZE_PROVIDERS)
        section_data['general']['downloadPropers'] = bool(app.DOWNLOAD_PROPERS)
        section_data['general']['checkPropersInterval'] = app.CHECK_PROPERS_INTERVAL
        # This can be moved to the frontend. No need to keep in config. The selected option is stored in CHECK_PROPERS_INTERVAL.
        # {u'45m': u'45 mins', u'15m': u'15 mins', u'4h': u'4 hours', u'daily': u'24 hours', u'90m': u'90 mins'}
        # section_data['general']['propersIntervalLabels'] = app.PROPERS_INTERVAL_LABELS
        section_data['general']['propersSearchDays'] = int(app.PROPERS_SEARCH_DAYS)
        section_data['general']['backlogDays'] = int(app.BACKLOG_DAYS)
        section_data['general']['backlogFrequency'] = int_default(app.BACKLOG_FREQUENCY, app.DEFAULT_BACKLOG_FREQUENCY)
        section_data['general']['minBacklogFrequency'] = int(app.MIN_BACKLOG_FREQUENCY)
        section_data['general']['dailySearchFrequency'] = int_default(app.DAILYSEARCH_FREQUENCY, app.DEFAULT_DAILYSEARCH_FREQUENCY)
        section_data['general']['minDailySearchFrequency'] = int(app.MIN_DAILYSEARCH_FREQUENCY)
        section_data['general']['removeFromClient'] = bool(app.REMOVE_FROM_CLIENT)
        section_data['general']['torrentCheckerFrequency'] = int_default(app.TORRENT_CHECKER_FREQUENCY, app.DEFAULT_TORRENT_CHECKER_FREQUENCY)
        section_data['general']['minTorrentCheckerFrequency'] = int(app.MIN_TORRENT_CHECKER_FREQUENCY)
        section_data['general']['usenetRetention'] = int_default(app.USENET_RETENTION, 500)
        section_data['general']['trackersList'] = app.TRACKERS_LIST
        section_data['general']['allowHighPriority'] = bool(app.ALLOW_HIGH_PRIORITY)
        section_data['general']['cacheTrimming'] = bool(app.CACHE_TRIMMING)
        section_data['general']['maxCacheAge'] = int_default(app.MAX_CACHE_AGE, 30)

        section_data['general']['failedDownloads'] = {}
        section_data['general']['failedDownloads']['enabled'] = bool(app.USE_FAILED_DOWNLOADS)
        section_data['general']['failedDownloads']['deleteFailed'] = bool(app.DELETE_FAILED)

        section_data['filters'] = {}
        section_data['filters']['ignored'] = app.IGNORE_WORDS
        section_data['filters']['undesired'] = app.UNDESIRED_WORDS
        section_data['filters']['preferred'] = app.PREFERRED_WORDS
        section_data['filters']['required'] = app.REQUIRE_WORDS
        section_data['filters']['ignoredSubsList'] = app.IGNORED_SUBS_LIST
        section_data['filters']['ignoreUnknownSubs'] = bool(app.IGNORE_UND_SUBS)

        return section_data

    @staticmethod
    def data_notifiers():
        """Notifications."""
        section_data = {}

        section_data['kodi'] = {}
        section_data['kodi']['enabled'] = bool(app.USE_KODI)
        section_data['kodi']['alwaysOn'] = bool(app.KODI_ALWAYS_ON)
        section_data['kodi']['notifyOnSnatch'] = bool(app.KODI_NOTIFY_ONSNATCH)
        section_data['kodi']['notifyOnDownload'] = bool(app.KODI_NOTIFY_ONDOWNLOAD)
        section_data['kodi']['notifyOnSubtitleDownload'] = bool(app.KODI_NOTIFY_ONSUBTITLEDOWNLOAD)
        section_data['kodi']['update'] = {}
        section_data['kodi']['update']['library'] = bool(app.KODI_UPDATE_LIBRARY)
        section_data['kodi']['update']['full'] = bool(app.KODI_UPDATE_FULL)
        section_data['kodi']['update']['onlyFirst'] = bool(app.KODI_UPDATE_ONLYFIRST)
        section_data['kodi']['host'] = app.KODI_HOST
        section_data['kodi']['username'] = app.KODI_USERNAME
        section_data['kodi']['password'] = app.KODI_PASSWORD
        section_data['kodi']['libraryCleanPending'] = bool(app.KODI_LIBRARY_CLEAN_PENDING)
        section_data['kodi']['cleanLibrary'] = bool(app.KODI_CLEAN_LIBRARY)

        section_data['plex'] = {}
        section_data['plex']['server'] = {}
        section_data['plex']['server']['enabled'] = bool(app.USE_PLEX_SERVER)
        section_data['plex']['server']['updateLibrary'] = bool(app.PLEX_UPDATE_LIBRARY)
        section_data['plex']['server']['host'] = app.PLEX_SERVER_HOST
        section_data['plex']['server']['https'] = bool(app.PLEX_SERVER_HTTPS)
        section_data['plex']['server']['username'] = app.PLEX_SERVER_USERNAME
        section_data['plex']['server']['password'] = app.PLEX_SERVER_PASSWORD
        section_data['plex']['server']['token'] = app.PLEX_SERVER_TOKEN
        section_data['plex']['client'] = {}
        section_data['plex']['client']['enabled'] = bool(app.USE_PLEX_CLIENT)
        section_data['plex']['client']['username'] = app.PLEX_CLIENT_USERNAME
        section_data['plex']['client']['host'] = app.PLEX_CLIENT_HOST
        section_data['plex']['client']['notifyOnSnatch'] = bool(app.PLEX_NOTIFY_ONSNATCH)
        section_data['plex']['client']['notifyOnDownload'] = bool(app.PLEX_NOTIFY_ONDOWNLOAD)
        section_data['plex']['client']['notifyOnSubtitleDownload'] = bool(app.PLEX_NOTIFY_ONSUBTITLEDOWNLOAD)

        section_data['emby'] = {}
        section_data['emby']['enabled'] = bool(app.USE_EMBY)
        section_data['emby']['host'] = app.EMBY_HOST
        section_data['emby']['apiKey'] = app.EMBY_APIKEY

        section_data['nmj'] = {}
        section_data['nmj']['enabled'] = bool(app.USE_NMJ)
        section_data['nmj']['host'] = app.NMJ_HOST
        section_data['nmj']['database'] = app.NMJ_DATABASE
        section_data['nmj']['mount'] = app.NMJ_MOUNT

        section_data['nmjv2'] = {}
        section_data['nmjv2']['enabled'] = bool(app.USE_NMJv2)
        section_data['nmjv2']['host'] = app.NMJv2_HOST
        section_data['nmjv2']['dbloc'] = app.NMJv2_DBLOC
        section_data['nmjv2']['database'] = app.NMJv2_DATABASE

        section_data['synologyIndex'] = {}
        section_data['synologyIndex']['enabled'] = bool(app.USE_SYNOINDEX)

        section_data['synology'] = {}
        section_data['synology']['enabled'] = bool(app.USE_SYNOLOGYNOTIFIER)
        section_data['synology']['notifyOnSnatch'] = bool(app.SYNOLOGYNOTIFIER_NOTIFY_ONSNATCH)
        section_data['synology']['notifyOnDownload'] = bool(app.SYNOLOGYNOTIFIER_NOTIFY_ONDOWNLOAD)
        section_data['synology']['notifyOnSubtitleDownload'] = bool(app.SYNOLOGYNOTIFIER_NOTIFY_ONSUBTITLEDOWNLOAD)

        section_data['pyTivo'] = {}
        section_data['pyTivo']['enabled'] = bool(app.USE_PYTIVO)
        section_data['pyTivo']['host'] = app.PYTIVO_HOST
        section_data['pyTivo']['name'] = app.PYTIVO_TIVO_NAME
        section_data['pyTivo']['shareName'] = app.PYTIVO_SHARE_NAME

        section_data['growl'] = {}
        section_data['growl']['enabled'] = bool(app.USE_GROWL)
        section_data['growl']['host'] = app.GROWL_HOST
        section_data['growl']['password'] = app.GROWL_PASSWORD
        section_data['growl']['notifyOnSnatch'] = bool(app.GROWL_NOTIFY_ONSNATCH)
        section_data['growl']['notifyOnDownload'] = bool(app.GROWL_NOTIFY_ONDOWNLOAD)
        section_data['growl']['notifyOnSubtitleDownload'] = bool(app.GROWL_NOTIFY_ONSUBTITLEDOWNLOAD)

        section_data['prowl'] = {}
        section_data['prowl']['enabled'] = bool(app.USE_PROWL)
        section_data['prowl']['api'] = app.PROWL_API
        section_data['prowl']['messageTitle'] = app.PROWL_MESSAGE_TITLE
        section_data['prowl']['priority'] = int(app.PROWL_PRIORITY)
        section_data['prowl']['notifyOnSnatch'] = bool(app.PROWL_NOTIFY_ONSNATCH)
        section_data['prowl']['notifyOnDownload'] = bool(app.PROWL_NOTIFY_ONDOWNLOAD)
        section_data['prowl']['notifyOnSubtitleDownload'] = bool(app.PROWL_NOTIFY_ONSUBTITLEDOWNLOAD)

        section_data['libnotify'] = {}
        section_data['libnotify']['enabled'] = bool(app.USE_LIBNOTIFY)
        section_data['libnotify']['notifyOnSnatch'] = bool(app.LIBNOTIFY_NOTIFY_ONSNATCH)
        section_data['libnotify']['notifyOnDownload'] = bool(app.LIBNOTIFY_NOTIFY_ONDOWNLOAD)
        section_data['libnotify']['notifyOnSubtitleDownload'] = bool(app.LIBNOTIFY_NOTIFY_ONSUBTITLEDOWNLOAD)

        section_data['pushover'] = {}
        section_data['pushover']['enabled'] = bool(app.USE_PUSHOVER)
        section_data['pushover']['apiKey'] = app.PUSHOVER_APIKEY
        section_data['pushover']['userKey'] = app.PUSHOVER_USERKEY
        section_data['pushover']['device'] = app.PUSHOVER_DEVICE
        section_data['pushover']['sound'] = app.PUSHOVER_SOUND
        section_data['pushover']['priority'] = int(app.PUSHOVER_PRIORITY)
        section_data['pushover']['notifyOnSnatch'] = bool(app.PUSHOVER_NOTIFY_ONSNATCH)
        section_data['pushover']['notifyOnDownload'] = bool(app.PUSHOVER_NOTIFY_ONDOWNLOAD)
        section_data['pushover']['notifyOnSubtitleDownload'] = bool(app.PUSHOVER_NOTIFY_ONSUBTITLEDOWNLOAD)

        section_data['boxcar2'] = {}
        section_data['boxcar2']['enabled'] = bool(app.USE_BOXCAR2)
        section_data['boxcar2']['notifyOnSnatch'] = bool(app.BOXCAR2_NOTIFY_ONSNATCH)
        section_data['boxcar2']['notifyOnDownload'] = bool(app.BOXCAR2_NOTIFY_ONDOWNLOAD)
        section_data['boxcar2']['notifyOnSubtitleDownload'] = bool(app.BOXCAR2_NOTIFY_ONSUBTITLEDOWNLOAD)
        section_data['boxcar2']['accessToken'] = app.BOXCAR2_ACCESSTOKEN

        section_data['pushalot'] = {}
        section_data['pushalot']['enabled'] = bool(app.USE_PUSHALOT)
        section_data['pushalot']['notifyOnSnatch'] = bool(app.PUSHALOT_NOTIFY_ONSNATCH)
        section_data['pushalot']['notifyOnDownload'] = bool(app.PUSHALOT_NOTIFY_ONDOWNLOAD)
        section_data['pushalot']['notifyOnSubtitleDownload'] = bool(app.PUSHALOT_NOTIFY_ONSUBTITLEDOWNLOAD)
        section_data['pushalot']['authToken'] = app.PUSHALOT_AUTHORIZATIONTOKEN

        section_data['pushbullet'] = {}
        section_data['pushbullet']['enabled'] = bool(app.USE_PUSHBULLET)
        section_data['pushbullet']['notifyOnSnatch'] = bool(app.PUSHBULLET_NOTIFY_ONSNATCH)
        section_data['pushbullet']['notifyOnDownload'] = bool(app.PUSHBULLET_NOTIFY_ONDOWNLOAD)
        section_data['pushbullet']['notifyOnSubtitleDownload'] = bool(app.PUSHBULLET_NOTIFY_ONSUBTITLEDOWNLOAD)
        section_data['pushbullet']['api'] = app.PUSHBULLET_API
        section_data['pushbullet']['device'] = app.PUSHBULLET_DEVICE

        section_data['join'] = {}
        section_data['join']['enabled'] = bool(app.USE_JOIN)
        section_data['join']['notifyOnSnatch'] = bool(app.JOIN_NOTIFY_ONSNATCH)
        section_data['join']['notifyOnDownload'] = bool(app.JOIN_NOTIFY_ONDOWNLOAD)
        section_data['join']['notifyOnSubtitleDownload'] = bool(app.JOIN_NOTIFY_ONSUBTITLEDOWNLOAD)
        section_data['join']['api'] = app.JOIN_API
        section_data['join']['device'] = app.JOIN_DEVICE

        section_data['freemobile'] = {}
        section_data['freemobile']['enabled'] = bool(app.USE_FREEMOBILE)
        section_data['freemobile']['notifyOnSnatch'] = bool(app.FREEMOBILE_NOTIFY_ONSNATCH)
        section_data['freemobile']['notifyOnDownload'] = bool(app.FREEMOBILE_NOTIFY_ONDOWNLOAD)
        section_data['freemobile']['notifyOnSubtitleDownload'] = bool(app.FREEMOBILE_NOTIFY_ONSUBTITLEDOWNLOAD)
        section_data['freemobile']['api'] = app.FREEMOBILE_APIKEY
        section_data['freemobile']['id'] = app.FREEMOBILE_ID

        section_data['telegram'] = {}
        section_data['telegram']['enabled'] = bool(app.USE_TELEGRAM)
        section_data['telegram']['notifyOnSnatch'] = bool(app.TELEGRAM_NOTIFY_ONSNATCH)
        section_data['telegram']['notifyOnDownload'] = bool(app.TELEGRAM_NOTIFY_ONDOWNLOAD)
        section_data['telegram']['notifyOnSubtitleDownload'] = bool(app.TELEGRAM_NOTIFY_ONSUBTITLEDOWNLOAD)
        section_data['telegram']['api'] = app.TELEGRAM_APIKEY
        section_data['telegram']['id'] = app.TELEGRAM_ID

        section_data['discord'] = {}
        section_data['discord']['enabled'] = bool(app.USE_DISCORD)
        section_data['discord']['notifyOnSnatch'] = bool(app.DISCORD_NOTIFY_ONSNATCH)
        section_data['discord']['notifyOnDownload'] = bool(app.DISCORD_NOTIFY_ONDOWNLOAD)
        section_data['discord']['notifyOnSubtitleDownload'] = bool(app.DISCORD_NOTIFY_ONSUBTITLEDOWNLOAD)
        section_data['discord']['webhook'] = app.DISCORD_WEBHOOK
        section_data['discord']['tts'] = bool(app.DISCORD_TTS)
        section_data['discord']['name'] = app.DISCORD_NAME

        section_data['twitter'] = {}
        section_data['twitter']['enabled'] = bool(app.USE_TWITTER)
        section_data['twitter']['notifyOnSnatch'] = bool(app.TWITTER_NOTIFY_ONSNATCH)
        section_data['twitter']['notifyOnDownload'] = bool(app.TWITTER_NOTIFY_ONDOWNLOAD)
        section_data['twitter']['notifyOnSubtitleDownload'] = bool(app.TWITTER_NOTIFY_ONSUBTITLEDOWNLOAD)
        section_data['twitter']['dmto'] = app.TWITTER_DMTO
        section_data['twitter']['prefix'] = app.TWITTER_PREFIX
        section_data['twitter']['directMessage'] = bool(app.TWITTER_USEDM)

        section_data['trakt'] = {}
        section_data['trakt']['enabled'] = bool(app.USE_TRAKT)
        section_data['trakt']['pinUrl'] = app.TRAKT_PIN_URL
        section_data['trakt']['username'] = app.TRAKT_USERNAME
        section_data['trakt']['accessToken'] = app.TRAKT_ACCESS_TOKEN
        section_data['trakt']['timeout'] = int_default(app.TRAKT_TIMEOUT, 20)
        section_data['trakt']['defaultIndexer'] = int_default(app.TRAKT_DEFAULT_INDEXER, INDEXER_TVDBV2)
        section_data['trakt']['sync'] = bool(app.TRAKT_SYNC)
        section_data['trakt']['syncRemove'] = bool(app.TRAKT_SYNC_REMOVE)
        section_data['trakt']['syncWatchlist'] = bool(app.TRAKT_SYNC_WATCHLIST)
        section_data['trakt']['methodAdd'] = int_default(app.TRAKT_METHOD_ADD)
        section_data['trakt']['removeWatchlist'] = bool(app.TRAKT_REMOVE_WATCHLIST)
        section_data['trakt']['removeSerieslist'] = bool(app.TRAKT_REMOVE_SERIESLIST)
        section_data['trakt']['removeShowFromApplication'] = bool(app.TRAKT_REMOVE_SHOW_FROM_APPLICATION)
        section_data['trakt']['startPaused'] = bool(app.TRAKT_START_PAUSED)
        section_data['trakt']['blacklistName'] = app.TRAKT_BLACKLIST_NAME

        section_data['email'] = {}
        section_data['email']['enabled'] = bool(app.USE_EMAIL)
        section_data['email']['notifyOnSnatch'] = bool(app.EMAIL_NOTIFY_ONSNATCH)
        section_data['email']['notifyOnDownload'] = bool(app.EMAIL_NOTIFY_ONDOWNLOAD)
        section_data['email']['notifyOnSubtitleDownload'] = bool(app.EMAIL_NOTIFY_ONSUBTITLEDOWNLOAD)
        section_data['email']['host'] = app.EMAIL_HOST
        section_data['email']['port'] = app.EMAIL_PORT
        section_data['email']['from'] = app.EMAIL_FROM
        section_data['email']['tls'] = bool(app.EMAIL_TLS)
        section_data['email']['username'] = app.EMAIL_USER
        section_data['email']['password'] = app.EMAIL_PASSWORD
        section_data['email']['addressList'] = app.EMAIL_LIST
        section_data['email']['subject'] = app.EMAIL_SUBJECT

        section_data['slack'] = {}
        section_data['slack']['enabled'] = bool(app.USE_SLACK)
        section_data['slack']['notifyOnSnatch'] = bool(app.SLACK_NOTIFY_SNATCH)
        section_data['slack']['notifyOnDownload'] = bool(app.SLACK_NOTIFY_DOWNLOAD)
        section_data['slack']['notifyOnSubtitleDownload'] = bool(app.SLACK_NOTIFY_SUBTITLEDOWNLOAD)
        section_data['slack']['webhook'] = app.SLACK_WEBHOOK

        return section_data

    @staticmethod
    def data_system():
        """System information."""
        section_data = {}

        section_data['memoryUsage'] = helpers.memory_usage(pretty=True)
        section_data['schedulers'] = generate_schedulers()
        section_data['showQueue'] = generate_show_queue()

        section_data['branch'] = app.BRANCH
        section_data['commitHash'] = app.CUR_COMMIT_HASH
        section_data['release'] = app.APP_VERSION
        section_data['sslVersion'] = app.OPENSSL_VERSION
        section_data['pythonVersion'] = sys.version

        section_data['databaseVersion'] = {}
        section_data['databaseVersion']['major'] = app.MAJOR_DB_VERSION
        section_data['databaseVersion']['minor'] = app.MINOR_DB_VERSION

        section_data['os'] = platform.platform()
        section_data['pid'] = app.PID
        section_data['locale'] = '.'.join([text_type(loc or 'Unknown') for loc in app.LOCALE])
        section_data['localUser'] = app.OS_USER or 'Unknown'
        section_data['programDir'] = app.PROG_DIR
        section_data['dataDir'] = app.DATA_DIR
        section_data['configFile'] = app.CONFIG_FILE
        section_data['dbPath'] = db.DBConnection().path
        section_data['cacheDir'] = app.CACHE_DIR
        section_data['logDir'] = app.LOG_DIR
        section_data['appArgs'] = app.MY_ARGS
        section_data['webRoot'] = app.WEB_ROOT
        section_data['runsInDocker'] = bool(app.RUNS_IN_DOCKER)
        section_data['gitRemoteBranches'] = app.GIT_REMOTE_BRANCHES
        section_data['cpuPresets'] = cpu_presets

        section_data['news'] = {}
        section_data['news']['lastRead'] = app.NEWS_LAST_READ
        section_data['news']['latest'] = app.NEWS_LATEST
        section_data['news']['unread'] = app.NEWS_UNREAD

        return section_data

    @staticmethod
    def data_clients():
        """Notifications."""
        section_data = {}

        section_data['torrents'] = {}
        section_data['torrents']['authType'] = app.TORRENT_AUTH_TYPE
        section_data['torrents']['dir'] = app.TORRENT_DIR
        section_data['torrents']['enabled'] = bool(app.USE_TORRENTS)
        section_data['torrents']['highBandwidth'] = bool(app.TORRENT_HIGH_BANDWIDTH)
        section_data['torrents']['host'] = app.TORRENT_HOST
        section_data['torrents']['label'] = app.TORRENT_LABEL
        section_data['torrents']['labelAnime'] = app.TORRENT_LABEL_ANIME
        section_data['torrents']['method'] = app.TORRENT_METHOD
        section_data['torrents']['path'] = app.TORRENT_PATH
        section_data['torrents']['paused'] = bool(app.TORRENT_PAUSED)
        section_data['torrents']['rpcUrl'] = app.TORRENT_RPCURL
        section_data['torrents']['seedLocation'] = app.TORRENT_SEED_LOCATION
        section_data['torrents']['seedTime'] = app.TORRENT_SEED_TIME
        section_data['torrents']['username'] = app.TORRENT_USERNAME
        section_data['torrents']['password'] = app.TORRENT_PASSWORD
        section_data['torrents']['verifySSL'] = bool(app.TORRENT_VERIFY_CERT)

        section_data['nzb'] = {}
        section_data['nzb']['enabled'] = bool(app.USE_NZBS)
        section_data['nzb']['dir'] = app.NZB_DIR
        section_data['nzb']['method'] = app.NZB_METHOD
        section_data['nzb']['nzbget'] = {}
        section_data['nzb']['nzbget']['category'] = app.NZBGET_CATEGORY
        section_data['nzb']['nzbget']['categoryAnime'] = app.NZBGET_CATEGORY_ANIME
        section_data['nzb']['nzbget']['categoryAnimeBacklog'] = app.NZBGET_CATEGORY_ANIME_BACKLOG
        section_data['nzb']['nzbget']['categoryBacklog'] = app.NZBGET_CATEGORY_BACKLOG
        section_data['nzb']['nzbget']['host'] = app.NZBGET_HOST
        section_data['nzb']['nzbget']['priority'] = int(app.NZBGET_PRIORITY)
        section_data['nzb']['nzbget']['useHttps'] = bool(app.NZBGET_USE_HTTPS)
        section_data['nzb']['nzbget']['username'] = app.NZBGET_USERNAME
        section_data['nzb']['nzbget']['password'] = app.NZBGET_PASSWORD

        section_data['nzb']['sabnzbd'] = {}
        section_data['nzb']['sabnzbd']['category'] = app.SAB_CATEGORY
        section_data['nzb']['sabnzbd']['categoryAnime'] = app.SAB_CATEGORY_ANIME
        section_data['nzb']['sabnzbd']['categoryAnimeBacklog'] = app.SAB_CATEGORY_ANIME_BACKLOG
        section_data['nzb']['sabnzbd']['categoryBacklog'] = app.SAB_CATEGORY_BACKLOG
        section_data['nzb']['sabnzbd']['forced'] = bool(app.SAB_FORCED)
        section_data['nzb']['sabnzbd']['host'] = app.SAB_HOST
        section_data['nzb']['sabnzbd']['username'] = app.SAB_USERNAME
        section_data['nzb']['sabnzbd']['password'] = app.SAB_PASSWORD
        section_data['nzb']['sabnzbd']['apiKey'] = app.SAB_APIKEY

        return section_data

    @staticmethod
    def data_postprocessing():
        """Postprocessing information."""
        section_data = {}

        section_data['naming'] = {}
        section_data['naming']['pattern'] = app.NAMING_PATTERN
        section_data['naming']['multiEp'] = int(app.NAMING_MULTI_EP)
        section_data['naming']['patternAirByDate'] = app.NAMING_ABD_PATTERN
        section_data['naming']['patternSports'] = app.NAMING_SPORTS_PATTERN
        section_data['naming']['patternAnime'] = app.NAMING_ANIME_PATTERN
        section_data['naming']['enableCustomNamingAirByDate'] = bool(app.NAMING_CUSTOM_ABD)
        section_data['naming']['enableCustomNamingSports'] = bool(app.NAMING_CUSTOM_SPORTS)
        section_data['naming']['enableCustomNamingAnime'] = bool(app.NAMING_CUSTOM_ANIME)
        section_data['naming']['animeMultiEp'] = int(app.NAMING_ANIME_MULTI_EP)
        section_data['naming']['animeNamingType'] = int_default(app.NAMING_ANIME, 3)
        section_data['naming']['stripYear'] = bool(app.NAMING_STRIP_YEAR)
        section_data['showDownloadDir'] = app.TV_DOWNLOAD_DIR
        section_data['processAutomatically'] = bool(app.PROCESS_AUTOMATICALLY)
        section_data['postponeIfSyncFiles'] = bool(app.POSTPONE_IF_SYNC_FILES)
        section_data['postponeIfNoSubs'] = bool(app.POSTPONE_IF_NO_SUBS)
        section_data['renameEpisodes'] = bool(app.RENAME_EPISODES)
        section_data['createMissingShowDirs'] = bool(app.CREATE_MISSING_SHOW_DIRS)
        section_data['addShowsWithoutDir'] = bool(app.ADD_SHOWS_WO_DIR)
        section_data['moveAssociatedFiles'] = bool(app.MOVE_ASSOCIATED_FILES)
        section_data['nfoRename'] = bool(app.NFO_RENAME)
        section_data['airdateEpisodes'] = bool(app.AIRDATE_EPISODES)
        section_data['unpack'] = bool(app.UNPACK)
        section_data['deleteRarContent'] = bool(app.DELRARCONTENTS)
        section_data['noDelete'] = bool(app.NO_DELETE)
        section_data['processMethod'] = app.PROCESS_METHOD
        section_data['reflinkAvailable'] = bool(pkgutil.find_loader('reflink'))
        section_data['autoPostprocessorFrequency'] = int(app.AUTOPOSTPROCESSOR_FREQUENCY)
        section_data['syncFiles'] = app.SYNC_FILES
        section_data['fileTimestampTimezone'] = app.FILE_TIMESTAMP_TIMEZONE
        section_data['allowedExtensions'] = app.ALLOWED_EXTENSIONS
        section_data['extraScripts'] = app.EXTRA_SCRIPTS
        section_data['extraScriptsUrl'] = app.EXTRA_SCRIPTS_URL
        section_data['multiEpStrings'] = common.MULTI_EP_STRINGS

        return section_data

    @staticmethod
    def data_indexers():
        """Indexers config information."""
        return get_indexer_config()

    @staticmethod
    def data_layout():
        """Layout configuration."""
        section_data = {}

        section_data['schedule'] = app.COMING_EPS_LAYOUT
        section_data['history'] = app.HISTORY_LAYOUT
        section_data['historyLimit'] = app.HISTORY_LIMIT

        section_data['home'] = app.HOME_LAYOUT

        section_data['show'] = {}
        section_data['show']['specials'] = bool(app.DISPLAY_SHOW_SPECIALS)
        section_data['show']['showListOrder'] = app.SHOW_LIST_ORDER
        section_data['show']['pagination'] = {}
        section_data['show']['pagination']['enable'] = bool(app.SHOW_USE_PAGINATION)

        section_data['wide'] = bool(app.LAYOUT_WIDE)

        section_data['posterSortdir'] = int(app.POSTER_SORTDIR or 0)
        section_data['themeName'] = app.THEME_NAME
        section_data['splitHomeInTabs'] = bool(app.ANIME_SPLIT_HOME_IN_TABS)
        section_data['animeSplitHome'] = bool(app.ANIME_SPLIT_HOME)
        section_data['fanartBackground'] = bool(app.FANART_BACKGROUND)
        section_data['fanartBackgroundOpacity'] = float(app.FANART_BACKGROUND_OPACITY or 0)
        section_data['timezoneDisplay'] = app.TIMEZONE_DISPLAY
        section_data['dateStyle'] = app.DATE_PRESET
        section_data['timeStyle'] = app.TIME_PRESET_W_SECONDS

        section_data['trimZero'] = bool(app.TRIM_ZERO)
        section_data['sortArticle'] = bool(app.SORT_ARTICLE)
        section_data['fuzzyDating'] = bool(app.FUZZY_DATING)
        section_data['posterSortby'] = app.POSTER_SORTBY

        section_data['comingEps'] = {}
        section_data['comingEps']['displayPaused'] = bool(app.COMING_EPS_DISPLAY_PAUSED)
        section_data['comingEps']['sort'] = app.COMING_EPS_SORT
        section_data['comingEps']['missedRange'] = int(app.COMING_EPS_MISSED_RANGE or 0)
        section_data['comingEps']['layout'] = app.COMING_EPS_LAYOUT

        section_data['backlogOverview'] = {}
        section_data['backlogOverview']['status'] = app.BACKLOG_STATUS
        section_data['backlogOverview']['period'] = app.BACKLOG_PERIOD

        section_data['selectedRootIndex'] = int_default(app.SELECTED_ROOT, -1)  # All paths

        return section_data

    @staticmethod
    def data_anime():
        """Anime configuration."""
        return {
            'anidb': {
                'enabled': bool(app.USE_ANIDB),
                'username': app.ANIDB_USERNAME,
                'password': app.ANIDB_PASSWORD,
                'useMylist': bool(app.ANIDB_USE_MYLIST)
            },
            'autoAnimeToList': bool(app.AUTO_ANIME_TO_LIST),
            'showlistDefaultAnime': app.SHOWLISTS_DEFAULT_ANIME
        }
