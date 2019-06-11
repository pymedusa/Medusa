# coding=utf-8
"""Test /config route."""
from __future__ import unicode_literals

import json
import pkgutil
import platform
import sys

from medusa import app, classes, common, db, helpers, logger, metadata
from medusa.indexers.indexer_config import get_indexer_config
from medusa.system.schedulers import all_schedulers

import pytest

from six import integer_types, iteritems, itervalues, string_types, text_type

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

    config_data = {}
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
    config_data['gitUsername'] = app.GIT_USERNAME
    config_data['branch'] = app.BRANCH
    config_data['commitHash'] = app.CUR_COMMIT_HASH
    config_data['release'] = app.APP_VERSION
    config_data['sslVersion'] = app.OPENSSL_VERSION
    config_data['pythonVersion'] = sys.version
    config_data['databaseVersion'] = {}
    config_data['databaseVersion']['major'] = app.MAJOR_DB_VERSION
    config_data['databaseVersion']['minor'] = app.MINOR_DB_VERSION
    config_data['os'] = platform.platform()
    config_data['pid'] = app.PID
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
    config_data['runsInDocker'] = bool(app.RUNS_IN_DOCKER)
    config_data['githubUrl'] = app.GITHUB_IO_URL
    config_data['wikiUrl'] = app.WIKI_URL
    config_data['donationsUrl'] = app.DONATIONS_URL
    config_data['sourceUrl'] = app.APPLICATION_URL
    config_data['downloadUrl'] = app.DOWNLOAD_URL
    config_data['subtitlesMulti'] = bool(app.SUBTITLES_MULTI)
    config_data['namingForceFolders'] = bool(app.NAMING_FORCE_FOLDERS)
    config_data['subtitles'] = {}
    config_data['subtitles']['enabled'] = bool(app.USE_SUBTITLES)
    config_data['recentShows'] = app.SHOWS_RECENT

    # Pick a random series to show as background.
    # TODO: Recreate this in Vue when the webapp has a reliable list of shows to choose from.
    config_data['randomShowSlug'] = ''

    config_data['showDefaults'] = {}
    config_data['showDefaults']['status'] = app.STATUS_DEFAULT
    config_data['showDefaults']['statusAfter'] = app.STATUS_DEFAULT_AFTER
    config_data['showDefaults']['quality'] = app.QUALITY_DEFAULT
    config_data['showDefaults']['subtitles'] = bool(app.SUBTITLES_DEFAULT)
    config_data['showDefaults']['seasonFolders'] = bool(app.SEASON_FOLDERS_DEFAULT)
    config_data['showDefaults']['anime'] = bool(app.ANIME_DEFAULT)
    config_data['showDefaults']['scene'] = bool(app.SCENE_DEFAULT)

    config_data['news'] = {}
    config_data['news']['lastRead'] = app.NEWS_LAST_READ
    config_data['news']['latest'] = app.NEWS_LATEST
    config_data['news']['unread'] = app.NEWS_UNREAD

    config_data['logs'] = {}
    config_data['logs']['debug'] = bool(app.DEBUG)
    config_data['logs']['dbDebug'] = bool(app.DBDEBUG)
    config_data['logs']['loggingLevels'] = {k.lower(): v for k, v in iteritems(logger.LOGGING_LEVELS)}
    config_data['logs']['numErrors'] = len(classes.ErrorViewer.errors)
    config_data['logs']['numWarnings'] = len(classes.WarningViewer.errors)

    config_data['failedDownloads'] = {}
    config_data['failedDownloads']['enabled'] = bool(app.USE_FAILED_DOWNLOADS)
    config_data['failedDownloads']['deleteFailed'] = bool(app.DELETE_FAILED)

    config_data['layout'] = {}
    config_data['layout']['schedule'] = app.COMING_EPS_LAYOUT
    config_data['layout']['history'] = app.HISTORY_LAYOUT
    config_data['layout']['home'] = app.HOME_LAYOUT
    config_data['layout']['show'] = {}
    config_data['layout']['show']['specials'] = bool(app.DISPLAY_SHOW_SPECIALS)
    config_data['layout']['show']['showListOrder'] = app.SHOW_LIST_ORDER

    config_data['selectedRootIndex'] = int(app.SELECTED_ROOT) if app.SELECTED_ROOT is not None else -1  # All paths

    config_data['backlogOverview'] = {}
    config_data['backlogOverview']['period'] = app.BACKLOG_PERIOD
    config_data['backlogOverview']['status'] = app.BACKLOG_STATUS

    config_data['indexers'] = {}
    config_data['indexers']['config'] = get_indexer_config()

    config_data['postProcessing'] = {}
    config_data['postProcessing']['naming'] = {}
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
    config_data['postProcessing']['autoPostprocessorFrequency'] = int(app.AUTOPOSTPROCESSOR_FREQUENCY)
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
def config_system(monkeypatch, app_config):
    def memory_usage_mock(*args, **kwargs):
        return '124.86 MB'
    monkeypatch.setattr(helpers, 'memory_usage', memory_usage_mock)

    section_data = {}
    section_data['memoryUsage'] = memory_usage_mock()
    section_data['schedulers'] = [{'key': scheduler[0], 'name': scheduler[1]} for scheduler in all_schedulers]
    section_data['showQueue'] = []

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
