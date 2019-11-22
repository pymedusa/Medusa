# coding=utf-8
"""Test /config route."""
from __future__ import unicode_literals

import json
import sys

from medusa import app, classes, common, db, helpers, logger, metadata
from medusa.sbdatetime import date_presets, time_presets
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
    # Can't get rid of this because of the usage of themeName in MEDUSA.config.themeName.
    config_data['themeName'] = app.THEME_NAME
    config_data['anonRedirect'] = app.ANON_REDIRECT
    config_data['rootDirs'] = app.ROOT_DIRS
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

    config_data['logs'] = {}
    config_data['logs']['debug'] = bool(app.DEBUG)
    config_data['logs']['dbDebug'] = bool(app.DBDEBUG)
    config_data['logs']['loggingLevels'] = {k.lower(): v for k, v in iteritems(logger.LOGGING_LEVELS)}
    config_data['logs']['numErrors'] = len(classes.ErrorViewer.errors)
    config_data['logs']['numWarnings'] = len(classes.WarningViewer.errors)
    config_data['logs']['actualLogDir'] = app.ACTUAL_LOG_DIR
    config_data['logs']['nr'] = int(app.LOG_NR)
    config_data['logs']['size'] = float(app.LOG_SIZE)
    config_data['logs']['subliminalLog'] = bool(app.SUBLIMINAL_LOG)
    config_data['logs']['privacyLevel'] = app.PRIVACY_LEVEL

    config_data['selectedRootIndex'] = int(app.SELECTED_ROOT) if app.SELECTED_ROOT is not None else -1  # All paths

    # Added for config - main, needs refactoring in the structure.
    config_data['launchBrowser'] = bool(app.LAUNCH_BROWSER)
    config_data['defaultPage'] = app.DEFAULT_PAGE
    config_data['trashRemoveShow'] = bool(app.TRASH_REMOVE_SHOW)
    config_data['trashRotateLogs'] = bool(app.TRASH_ROTATE_LOGS)

    config_data['indexerDefaultLanguage'] = app.INDEXER_DEFAULT_LANGUAGE
    config_data['showUpdateHour'] = int(app.SHOWUPDATE_HOUR) if app.SHOWUPDATE_HOUR is not None else 0
    config_data['indexerTimeout'] = int(app.INDEXER_TIMEOUT) if app.INDEXER_TIMEOUT is not None else 0
    config_data['indexerDefault'] = app.INDEXER_DEFAULT

    config_data['plexFallBack'] = {}
    config_data['plexFallBack']['enable'] = bool(app.FALLBACK_PLEX_ENABLE)
    config_data['plexFallBack']['notifications'] = bool(app.FALLBACK_PLEX_NOTIFICATIONS)
    config_data['plexFallBack']['timeout'] = int(app.FALLBACK_PLEX_TIMEOUT)

    config_data['versionNotify'] = bool(app.VERSION_NOTIFY)
    config_data['autoUpdate'] = bool(app.AUTO_UPDATE)
    config_data['updateFrequency'] = int(app.UPDATE_FREQUENCY) if app.UPDATE_FREQUENCY is not None else 1
    config_data['notifyOnUpdate'] = bool(app.NOTIFY_ON_UPDATE)
    config_data['availableThemes'] = [{'name': theme.name,
                                        'version': theme.version,
                                        'author': theme.author}
                                       for theme in app.AVAILABLE_THEMES]

    config_data['timePresets'] = list(time_presets)
    config_data['datePresets'] = list(date_presets)

    config_data['webInterface'] = {}
    config_data['webInterface']['apiKey'] = app.API_KEY
    config_data['webInterface']['log'] = bool(app.WEB_LOG)
    config_data['webInterface']['username'] = app.WEB_USERNAME
    config_data['webInterface']['password'] = app.WEB_PASSWORD
    config_data['webInterface']['port'] = int(app.WEB_PORT) if app.WEB_PORT is not None else 8080
    config_data['webInterface']['notifyOnLogin'] = bool(app.NOTIFY_ON_LOGIN)
    config_data['webInterface']['ipv6'] = bool(app.WEB_IPV6)
    config_data['webInterface']['httpsEnable'] = bool(app.ENABLE_HTTPS)
    config_data['webInterface']['httpsCert'] = app.HTTPS_CERT
    config_data['webInterface']['httpsKey'] = app.HTTPS_KEY
    config_data['webInterface']['handleReverseProxy'] = bool(app.HANDLE_REVERSE_PROXY)

    config_data['cpuPreset'] = app.CPU_PRESET
    config_data['sslVerify'] = bool(app.SSL_VERIFY)
    config_data['sslCaBundle'] = app.SSL_CA_BUNDLE
    config_data['noRestart'] = bool(app.NO_RESTART)
    config_data['encryptionVersion'] = bool(app.ENCRYPTION_VERSION)
    config_data['calendarUnprotected'] = bool(app.CALENDAR_UNPROTECTED)
    config_data['calendarIcons'] = bool(app.CALENDAR_ICONS)
    config_data['proxySetting'] = app.PROXY_SETTING
    config_data['proxyIndexers'] = bool(app.PROXY_INDEXERS)
    config_data['skipRemovedFiles'] = bool(app.SKIP_REMOVED_FILES)
    config_data['epDefaultDeletedStatus'] = app.EP_DEFAULT_DELETED_STATUS
    config_data['developer'] = bool(app.DEVELOPER)

    config_data['git'] = {}
    config_data['git']['username'] = app.GIT_USERNAME
    config_data['git']['password'] = app.GIT_PASSWORD
    config_data['git']['token'] = app.GIT_TOKEN
    config_data['git']['authType'] = int(app.GIT_AUTH_TYPE)
    config_data['git']['remote'] = app.GIT_REMOTE
    config_data['git']['path'] = app.GIT_PATH
    config_data['git']['org'] = app.GIT_ORG
    config_data['git']['reset'] = bool(app.GIT_RESET)
    config_data['git']['resetBranches'] = app.GIT_RESET_BRANCHES
    config_data['git']['url'] = app.GITHUB_IO_URL

    # backlogOverview has been moved to layout. It's still located here, because manage_backlogOvervew uses it
    # and still needs to be vieuified. After vueifying it, remove this.
    config_data['backlogOverview'] = {}
    config_data['backlogOverview']['status'] = app.BACKLOG_STATUS
    config_data['backlogOverview']['period'] = app.BACKLOG_PERIOD
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
    'defaultPage',
    'subtitlesMulti',
    'showDefaults',
    'wikiUrl',
    'cpuPreset'
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

    config_data = {}

    config_data['metadataProviders'] = {}

    for provider in itervalues(app.metadata_provider_dict):
        json_repr = provider.to_json()
        config_data['metadataProviders'][json_repr['id']] = json_repr

    return config_data


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

    config_data = {}
    config_data['memoryUsage'] = memory_usage_mock()
    config_data['schedulers'] = [{'key': scheduler[0], 'name': scheduler[1]} for scheduler in all_schedulers]
    config_data['showQueue'] = []

    return config_data


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
