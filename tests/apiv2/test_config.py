# coding=utf-8
"""Test /config route."""
from __future__ import unicode_literals

import json
import platform
import pkgutil
import sys

from medusa import app, classes, common, db, logger, metadata
from medusa.helper.mappings import NonEmptyDict
from medusa.indexers.indexer_config import get_indexer_config

import pytest

from six import iteritems, itervalues, text_type

from tornado.httpclient import HTTPError


@pytest.fixture
def config_main(monkeypatch, app_config):
    python_version = 'Python Test v1.2.3.4'
    monkeypatch.setattr(sys, 'version', python_version)
    app_config('PID', 4321)
    os_user = app_config('OS_USER', 'superuser')
    app_config('LOCALE', (None, 'ABC'))
    app_locale = 'Unknown.ABC'

    # postProcessing.naming
    app_config('NAMING_ANIME', 3)

    config_data = NonEmptyDict()
    config_data['anonRedirect'] = app.ANON_REDIRECT
    config_data['animeSplitHome'] = bool(app.ANIME_SPLIT_HOME)
    config_data['animeSplitHomeInTabs'] = bool(app.ANIME_SPLIT_HOME_IN_TABS)
    config_data['comingEpsSort'] = app.COMING_EPS_SORT
    config_data['comingEpsDisplayPaused'] = bool(app.COMING_EPS_DISPLAY_PAUSED)
    config_data['datePreset'] = app.DATE_PRESET
    config_data['fuzzyDating'] = bool(app.FUZZY_DATING)
    config_data['themeName'] = app.THEME_NAME
    config_data['posterSortby'] = app.POSTER_SORTBY
    config_data['posterSortdir'] = app.POSTER_SORTDIR
    config_data['rootDirs'] = app.ROOT_DIRS
    config_data['sortArticle'] = bool(app.SORT_ARTICLE)
    config_data['timePreset'] = app.TIME_PRESET
    config_data['trimZero'] = bool(app.TRIM_ZERO)
    config_data['fanartBackground'] = bool(app.FANART_BACKGROUND)
    config_data['fanartBackgroundOpacity'] = float(app.FANART_BACKGROUND_OPACITY or 0)
    config_data['branch'] = app.BRANCH
    config_data['commitHash'] = app.CUR_COMMIT_HASH
    config_data['release'] = app.APP_VERSION
    config_data['sslVersion'] = app.OPENSSL_VERSION
    config_data['pythonVersion'] = sys.version
    config_data['databaseVersion'] = NonEmptyDict()
    config_data['databaseVersion']['major'] = app.MAJOR_DB_VERSION
    config_data['databaseVersion']['minor'] = app.MINOR_DB_VERSION
    config_data['pid'] = app.PID
    config_data['os'] = platform.platform()
    config_data['locale'] = app_locale
    config_data['localUser'] = os_user
    config_data['programDir'] = app.PROG_DIR
    config_data['dataDir'] = app.DATA_DIR
    config_data['configFile'] = app.CONFIG_FILE
    config_data['dbPath'] = db.DBConnection().path
    config_data['cacheDir'] = app.CACHE_DIR
    config_data['logDir'] = app.LOG_DIR
    config_data['appArgs'] = app.MY_ARGS
    config_data['webRoot'] = app.WEB_ROOT
    config_data['githubUrl'] = app.GITHUB_IO_URL
    config_data['wikiUrl'] = app.WIKI_URL
    config_data['donationsUrl'] = app.DONATIONS_URL
    config_data['sourceUrl'] = app.APPLICATION_URL
    config_data['downloadUrl'] = app.DOWNLOAD_URL
    config_data['subtitlesMulti'] = bool(app.SUBTITLES_MULTI)
    config_data['namingForceFolders'] = bool(app.NAMING_FORCE_FOLDERS)
    config_data['subtitles'] = NonEmptyDict()
    config_data['subtitles']['enabled'] = bool(app.USE_SUBTITLES)
    config_data['recentShows'] = app.SHOWS_RECENT

    config_data['news'] = NonEmptyDict()
    config_data['news']['lastRead'] = app.NEWS_LAST_READ
    config_data['news']['latest'] = app.NEWS_LATEST
    config_data['news']['unread'] = app.NEWS_UNREAD

    config_data['logs'] = NonEmptyDict()
    config_data['logs']['loggingLevels'] = {k.lower(): v for k, v in iteritems(logger.LOGGING_LEVELS)}
    config_data['logs']['numErrors'] = len(classes.ErrorViewer.errors)
    config_data['logs']['numWarnings'] = len(classes.WarningViewer.errors)

    config_data['failedDownloads'] = NonEmptyDict()
    config_data['failedDownloads']['enabled'] = bool(app.USE_FAILED_DOWNLOADS)
    config_data['failedDownloads']['deleteFailed'] = bool(app.DELETE_FAILED)

    config_data['kodi'] = NonEmptyDict()
    config_data['kodi']['enabled'] = bool(app.USE_KODI)
    config_data['kodi']['alwaysOn'] = bool(app.KODI_ALWAYS_ON)
    config_data['kodi']['notify'] = NonEmptyDict()
    config_data['kodi']['notify']['snatch'] = bool(app.KODI_NOTIFY_ONSNATCH)
    config_data['kodi']['notify']['download'] = bool(app.KODI_NOTIFY_ONDOWNLOAD)
    config_data['kodi']['notify']['subtitleDownload'] = bool(app.KODI_NOTIFY_ONSUBTITLEDOWNLOAD)
    config_data['kodi']['update'] = NonEmptyDict()
    config_data['kodi']['update']['library'] = bool(app.KODI_UPDATE_LIBRARY)
    config_data['kodi']['update']['full'] = bool(app.KODI_UPDATE_FULL)
    config_data['kodi']['update']['onlyFirst'] = bool(app.KODI_UPDATE_ONLYFIRST)
    config_data['kodi']['host'] = app.KODI_HOST
    config_data['kodi']['username'] = app.KODI_USERNAME
    # config_data['kodi']['password'] = app.KODI_PASSWORD
    config_data['kodi']['libraryCleanPending'] = bool(app.KODI_LIBRARY_CLEAN_PENDING)
    config_data['kodi']['cleanLibrary'] = bool(app.KODI_CLEAN_LIBRARY)

    config_data['plex'] = NonEmptyDict()
    config_data['plex']['server'] = NonEmptyDict()
    config_data['plex']['server']['enabled'] = bool(app.USE_PLEX_SERVER)
    config_data['plex']['server']['notify'] = NonEmptyDict()
    config_data['plex']['server']['notify']['snatch'] = bool(app.PLEX_NOTIFY_ONSNATCH)
    config_data['plex']['server']['notify']['download'] = bool(app.PLEX_NOTIFY_ONDOWNLOAD)
    config_data['plex']['server']['notify']['subtitleDownload'] = bool(app.PLEX_NOTIFY_ONSUBTITLEDOWNLOAD)
    config_data['plex']['server']['updateLibrary'] = bool(app.PLEX_UPDATE_LIBRARY)
    config_data['plex']['server']['host'] = app.PLEX_SERVER_HOST
    # config_data['plex']['server']['token'] = app.PLEX_SERVER_TOKEN
    config_data['plex']['server']['username'] = app.PLEX_SERVER_USERNAME
    # config_data['plex']['server']['password'] = app.PLEX_SERVER_PASSWORD
    config_data['plex']['client'] = NonEmptyDict()
    config_data['plex']['client']['enabled'] = bool(app.USE_PLEX_CLIENT)
    config_data['plex']['client']['username'] = app.PLEX_CLIENT_USERNAME
    # config_data['plex']['client']['password'] = app.PLEX_CLIENT_PASSWORD
    config_data['plex']['client']['host'] = app.PLEX_CLIENT_HOST

    config_data['emby'] = NonEmptyDict()
    config_data['emby']['enabled'] = bool(app.USE_EMBY)
    config_data['emby']['host'] = app.EMBY_HOST

    config_data['torrents'] = NonEmptyDict()
    config_data['torrents']['authType'] = app.TORRENT_AUTH_TYPE
    config_data['torrents']['dir'] = app.TORRENT_DIR
    config_data['torrents']['enabled'] = bool(app.USE_TORRENTS)
    config_data['torrents']['highBandwidth'] = app.TORRENT_HIGH_BANDWIDTH
    config_data['torrents']['host'] = app.TORRENT_HOST
    config_data['torrents']['label'] = app.TORRENT_LABEL
    config_data['torrents']['labelAnime'] = app.TORRENT_LABEL_ANIME
    config_data['torrents']['method'] = app.TORRENT_METHOD
    # config_data['torrents']['password'] = app.TORRENT_PASSWORD
    config_data['torrents']['path'] = app.TORRENT_PATH
    config_data['torrents']['paused'] = bool(app.TORRENT_PAUSED)
    config_data['torrents']['rpcurl'] = app.TORRENT_RPCURL
    config_data['torrents']['seedLocation'] = app.TORRENT_SEED_LOCATION
    config_data['torrents']['seedTime'] = app.TORRENT_SEED_TIME
    config_data['torrents']['username'] = app.TORRENT_USERNAME
    config_data['torrents']['verifySSL'] = bool(app.TORRENT_VERIFY_CERT)

    config_data['nzb'] = NonEmptyDict()
    config_data['nzb']['enabled'] = bool(app.USE_NZBS)
    config_data['nzb']['dir'] = app.NZB_DIR
    config_data['nzb']['method'] = app.NZB_METHOD
    config_data['nzb']['nzbget'] = NonEmptyDict()
    config_data['nzb']['nzbget']['category'] = app.NZBGET_CATEGORY
    config_data['nzb']['nzbget']['categoryAnime'] = app.NZBGET_CATEGORY_ANIME
    config_data['nzb']['nzbget']['categoryAnimeBacklog'] = app.NZBGET_CATEGORY_ANIME_BACKLOG
    config_data['nzb']['nzbget']['categoryBacklog'] = app.NZBGET_CATEGORY_BACKLOG
    config_data['nzb']['nzbget']['host'] = app.NZBGET_HOST
    # config_data['nzb']['nzbget']['password'] = app.NZBGET_PASSWORD
    config_data['nzb']['nzbget']['priority'] = app.NZBGET_PRIORITY
    config_data['nzb']['nzbget']['useHttps'] = bool(app.NZBGET_USE_HTTPS)
    config_data['nzb']['nzbget']['username'] = app.NZBGET_USERNAME

    config_data['nzb']['sabnzbd'] = NonEmptyDict()
    # config_data['nzb']['sabnzbd']['apiKey'] = app.SAB_APIKEY
    config_data['nzb']['sabnzbd']['category'] = app.SAB_CATEGORY
    config_data['nzb']['sabnzbd']['categoryAnime'] = app.SAB_CATEGORY_ANIME
    config_data['nzb']['sabnzbd']['categoryAnimeBacklog'] = app.SAB_CATEGORY_ANIME_BACKLOG
    config_data['nzb']['sabnzbd']['categoryBacklog'] = app.SAB_CATEGORY_BACKLOG
    config_data['nzb']['sabnzbd']['forced'] = bool(app.SAB_FORCED)
    config_data['nzb']['sabnzbd']['host'] = app.SAB_HOST
    # config_data['nzb']['sabnzbd']['password'] = app.SAB_PASSWORD
    config_data['nzb']['sabnzbd']['username'] = app.SAB_USERNAME

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

    config_data['postProcessing'] = NonEmptyDict()
    config_data['postProcessing']['naming'] = NonEmptyDict()
    config_data['postProcessing']['naming']['pattern'] = app.NAMING_PATTERN
    config_data['postProcessing']['naming']['multiEp'] = int(app.NAMING_MULTI_EP)
    config_data['postProcessing']['naming']['patternAirByDate'] = app.NAMING_ABD_PATTERN
    config_data['postProcessing']['naming']['patternSports'] = app.NAMING_SPORTS_PATTERN
    config_data['postProcessing']['naming']['patternAnime'] = app.NAMING_ANIME_PATTERN
    config_data['postProcessing']['naming']['enableCustomNamingAirByDate'] = bool(app.NAMING_CUSTOM_ABD)
    config_data['postProcessing']['naming']['enableCustomNamingSports'] = bool(app.NAMING_CUSTOM_SPORTS)
    config_data['postProcessing']['naming']['enableCustomNamingAnime'] = bool(app.NAMING_CUSTOM_ANIME)
    config_data['postProcessing']['naming']['animeMultiEp'] = int(app.NAMING_ANIME_MULTI_EP)
    config_data['postProcessing']['naming']['animeNamingType'] = int(app.NAMING_ANIME)
    config_data['postProcessing']['naming']['stripYear'] = bool(app.NAMING_STRIP_YEAR)
    config_data['postProcessing']['showDownloadDir'] = app.TV_DOWNLOAD_DIR
    config_data['postProcessing']['processAutomatically'] = bool(app.PROCESS_AUTOMATICALLY)
    config_data['postProcessing']['postponeIfSyncFiles'] = bool(app.POSTPONE_IF_SYNC_FILES)
    config_data['postProcessing']['postponeIfNoSubs'] = bool(app.POSTPONE_IF_NO_SUBS)
    config_data['postProcessing']['renameEpisodes'] = bool(app.RENAME_EPISODES)
    config_data['postProcessing']['createMissingShowDirs'] = bool(app.CREATE_MISSING_SHOW_DIRS)
    config_data['postProcessing']['addShowsWithoutDir'] = bool(app.ADD_SHOWS_WO_DIR)
    config_data['postProcessing']['moveAssociatedFiles'] = bool(app.MOVE_ASSOCIATED_FILES)
    config_data['postProcessing']['nfoRename'] = bool(app.NFO_RENAME)
    config_data['postProcessing']['airdateEpisodes'] = bool(app.AIRDATE_EPISODES)
    config_data['postProcessing']['unpack'] = bool(app.UNPACK)
    config_data['postProcessing']['deleteRarContent'] = bool(app.DELRARCONTENTS)
    config_data['postProcessing']['noDelete'] = bool(app.NO_DELETE)
    config_data['postProcessing']['processMethod'] = app.PROCESS_METHOD
    config_data['postProcessing']['reflinkAvailable'] = bool(pkgutil.find_loader('reflink'))
    config_data['postProcessing']['autoPostprocessorFrequency'] = app.AUTOPOSTPROCESSOR_FREQUENCY
    config_data['postProcessing']['syncFiles'] = app.SYNC_FILES
    config_data['postProcessing']['fileTimestampTimezone'] = app.FILE_TIMESTAMP_TIMEZONE
    config_data['postProcessing']['allowedExtensions'] = list(app.ALLOWED_EXTENSIONS)
    config_data['postProcessing']['extraScripts'] = app.EXTRA_SCRIPTS
    config_data['postProcessing']['extraScriptsUrl'] = app.EXTRA_SCRIPTS_URL
    config_data['postProcessing']['multiEpStrings'] = {text_type(k): v for k, v in iteritems(common.MULTI_EP_STRINGS)}

    return config_data


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
    'pythonVersion',
    'locale',
    'localUser',
    'githubUrl',
    'dbPath',
    'postProcessing'
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
def test_config_get_detailed_bad_request(http_client, create_url, auth_headers, config_main):
    # given
    url = create_url('/config/main/abcdef/')

    # when
    with pytest.raises(HTTPError) as error:
        yield http_client.fetch(url, **auth_headers)

    # then
    assert 400 == error.value.code


@pytest.mark.gen_test
def test_config_get_not_found(http_client, create_url, auth_headers, config_main):
    # given
    url = create_url('/config/abcdef/')

    # when
    with pytest.raises(HTTPError) as error:
        yield http_client.fetch(url, **auth_headers)

    # then
    assert 404 == error.value.code


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

    section_data = NonEmptyDict()

    section_data['metadataProviders'] = NonEmptyDict()

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
