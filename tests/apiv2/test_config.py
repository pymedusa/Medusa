# coding=utf-8
"""Test /config route."""
from __future__ import unicode_literals

import json
import platform
import pkgutil
import sys

from medusa import app, classes, common, db, helpers, logger, metadata
from medusa.indexers.config import INDEXER_TVDBV2
from medusa.common import cpu_presets
from medusa.helpers.utils import int_default
from medusa.sbdatetime import date_presets, time_presets
from medusa.schedulers.utils import all_schedulers
from tests.apiv2.conftest import TEST_API_KEY

import pytest

from six import integer_types, iteritems, itervalues, string_types, text_type

from tornado.httpclient import HTTPError


@pytest.fixture
def config_main(monkeypatch, app_config):
    python_version = 'Python Test v1.2.3.4'
    monkeypatch.setattr(sys, 'version', python_version)
    app_config('PID', 4321)
    app_config('LOCALE', (None, 'ABC'))

    # postProcessing.naming
    app_config('NAMING_ANIME', 3)

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
    section_data['randomShowSlug'] = ''

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
    section_data['webInterface']['apiKey'] = TEST_API_KEY
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


@pytest.mark.gen_test
def test_config_get(http_client, create_url, auth_headers, config_main):
    # given
    expected = config_main

    url = create_url('/config/main')

    # when
    response = yield http_client.fetch(url, **auth_headers)

    # then
    assert response.code == 200
    assert expected == json.loads(response.body)


@pytest.mark.gen_test
@pytest.mark.parametrize('query', [
    'defaultPage',
    'subtitlesMulti',
    'wikiUrl',
    'sslVerify'
])
def test_config_get_detailed(http_client, create_url, auth_headers, config_main, query):
    # given
    expected = config_main[query]
    url = create_url('/config/main/{0}/'.format(query))

    # when
    response = yield http_client.fetch(url, **auth_headers)

    # then
    assert response.code == 200
    assert expected == json.loads(response.body)


@pytest.mark.gen_test
def test_config_get_detailed_bad_request(http_client, create_url, auth_headers):
    # given
    url = create_url('/config/main/abcdef/')

    # when
    with pytest.raises(HTTPError) as error:
        yield http_client.fetch(url, **auth_headers)

    # then
    assert 400 == error.value.code


@pytest.mark.gen_test
def test_config_get_not_found(http_client, create_url, auth_headers):
    # given
    url = create_url('/config/abcdef/')

    # when
    with pytest.raises(HTTPError) as error:
        yield http_client.fetch(url, **auth_headers)

    # then
    assert 404 == error.value.code


@pytest.mark.gen_test
def test_config_get_consts(http_client, create_url, auth_headers):
    # given

    def gen_schema(data):
        if isinstance(data, dict):
            return {k: gen_schema(v) for (k, v) in iteritems(data)}
        if isinstance(data, list):
            return [json.loads(v) for v in set([json.dumps(gen_schema(v)) for v in data])]
        if isinstance(data, string_types):
            return 'str'
        if isinstance(data, integer_types):
            return 'int'
        return type(data).__name__

    expected_schema = gen_schema({
        'qualities': {
            'values': [{'value': 8, 'key': 'hdtv', 'name': 'HDTV'}],
            'anySets': [{'value': 40, 'key': 'anyhdtv', 'name': 'ANYHDTV'}],
            'presets': [{'value': 65518, 'key': 'any', 'name': 'ANY'}],
        },
        'statuses': [{'value': 3, 'key': 'wanted', 'name': 'Wanted'}],
    })

    url = create_url('/config/consts')

    # when
    response = yield http_client.fetch(url, **auth_headers)
    data = json.loads(response.body)

    # then
    assert response.code == 200
    assert expected_schema == gen_schema(data)
    assert len(common.Quality.qualityStrings) == len(data['qualities']['values'])
    assert len(common.Quality.combined_quality_strings) == len(data['qualities']['anySets'])
    assert len(common.qualityPresetStrings) == len(data['qualities']['presets'])
    assert len(common.statusStrings) == len(data['statuses'])


@pytest.fixture
def config_metadata(monkeypatch, app_config):
    # initialize metadata_providers
    default_config = ['0'] * 10
    providers = [
        (default_config, metadata.kodi),
        (default_config, metadata.kodi_12plus),
        (default_config, metadata.media_browser),
        (default_config, metadata.ps3),
        (default_config, metadata.wdtv),
        (default_config, metadata.tivo),
        (default_config, metadata.mede8er)
    ]

    metadata_provider_dict = app_config('metadata_provider_dict', metadata.get_metadata_generator_dict())
    for cur_metadata_tuple in providers:
        (cur_metadata_config, cur_metadata_class) = cur_metadata_tuple
        tmp_provider = cur_metadata_class.metadata_class()
        tmp_provider.set_config(cur_metadata_config)
        monkeypatch.setitem(metadata_provider_dict, tmp_provider.name, tmp_provider)

    section_data = {}

    section_data['metadataProviders'] = {}

    for provider in itervalues(app.metadata_provider_dict):
        json_repr = provider.to_json()
        section_data['metadataProviders'][json_repr['id']] = json_repr

    return section_data


@pytest.mark.gen_test
def test_config_get_metadata(http_client, create_url, auth_headers, config_metadata):
    # given
    expected = config_metadata

    url = create_url('/config/metadata')

    # when
    response = yield http_client.fetch(url, **auth_headers)

    # then
    assert response.code == 200
    assert expected == json.loads(response.body)


@pytest.fixture
def config_system(monkeypatch):
    def memory_usage_mock(*args, **kwargs):
        return '124.86 MB'
    monkeypatch.setattr(helpers, 'memory_usage', memory_usage_mock)

    section_data = {}
    section_data['memoryUsage'] = memory_usage_mock()
    section_data['schedulers'] = [{'key': scheduler[0], 'name': scheduler[1]} for scheduler in all_schedulers]
    section_data['showQueue'] = []

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


@pytest.mark.gen_test
def test_config_get_system(http_client, create_url, auth_headers, config_system):
    # given
    expected = config_system

    url = create_url('/config/system')

    # when
    response = yield http_client.fetch(url, **auth_headers)

    # then
    assert response.code == 200
    assert expected == json.loads(response.body)


@pytest.fixture
def config_postprocessing():
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
    section_data['multiEpStrings'] = {str(k): v for k, v in iteritems(common.MULTI_EP_STRINGS)}

    return section_data


@pytest.mark.gen_test
def test_config_get_postprocessing(http_client, create_url, auth_headers, config_postprocessing):
    # given
    expected = config_postprocessing

    url = create_url('/config/postprocessing')

    # when
    response = yield http_client.fetch(url, **auth_headers)

    # then
    assert response.code == 200
    assert expected == json.loads(response.body)


@pytest.fixture
def config_clients():

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


@pytest.mark.gen_test
def test_config_get_clients(http_client, create_url, auth_headers, config_clients):
    # given
    expected = config_clients

    url = create_url('/config/clients')

    # when
    response = yield http_client.fetch(url, **auth_headers)

    # then
    assert response.code == 200
    assert expected == json.loads(response.body)


@pytest.fixture
def config_notifiers():

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


@pytest.mark.gen_test
def test_config_get_notifiers(http_client, create_url, auth_headers, config_notifiers):
    # given
    expected = config_notifiers

    url = create_url('/config/notifiers')

    # when
    response = yield http_client.fetch(url, **auth_headers)

    # then
    assert response.code == 200
    assert expected == json.loads(response.body)


@pytest.fixture
def config_search():

    section_data = {}

    section_data['general'] = {}
    section_data['general']['randomizeProviders'] = bool(app.RANDOMIZE_PROVIDERS)
    section_data['general']['downloadPropers'] = bool(app.DOWNLOAD_PROPERS)
    section_data['general']['checkPropersInterval'] = app.CHECK_PROPERS_INTERVAL
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


@pytest.mark.gen_test
def test_config_get_search(http_client, create_url, auth_headers, config_search):
    # given
    expected = config_search

    url = create_url('/config/search')

    # when
    response = yield http_client.fetch(url, **auth_headers)

    # then
    assert response.code == 200
    assert expected == json.loads(response.body)


@pytest.fixture
def config_layout():
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


@pytest.mark.gen_test
def test_config_get_layout(http_client, create_url, auth_headers, config_layout):
    # given
    expected = config_layout

    url = create_url('/config/layout')

    # when
    response = yield http_client.fetch(url, **auth_headers)

    # then
    assert response.code == 200
    assert expected == json.loads(response.body)
