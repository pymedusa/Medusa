# coding=utf-8
"""Test /config route."""
import json
import platform
import sys

import medusa as app
import pytest
from tornado.httpclient import HTTPError


@pytest.fixture
def config(monkeypatch, app_config):
    python_version = 'Python Test v1.2.3.4'
    monkeypatch.setattr(sys, 'version', python_version)
    os_user = app_config('OS_USER', 'superuser')
    app_config('LOCALE', (None, 'ABC'))
    app_locale = 'Unknown.ABC'

    return {
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
        'pythonVersion': python_version,
        'databaseVersion': {
            'major': app.MAJOR_DB_VERSION,
            'minor': app.MINOR_DB_VERSION
        },
        'os': platform.platform(),
        'locale': app_locale,
        'localUser': os_user,
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
                            (app.ENABLE_HTTPS and app.TORRENT_HOST[:5] == 'https' or
                             not app.ENABLE_HTTPS and app.TORRENT_HOST[:5] == 'http:'))
        }
    }


@pytest.mark.gen_test
def test_config(http_client, create_url, auth_headers, config):
    # given
    expected = config

    url = create_url('/config')

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
    'dbFilename',
])
def test_config_detailed(http_client, create_url, auth_headers, config, query):
    # given
    expected = config[query]
    url = create_url('/config/{0}/'.format(query))

    # when
    response = yield http_client.fetch(url, **auth_headers)

    # then
    assert response.code == 200
    assert expected == json.loads(response.body)


@pytest.mark.gen_test
def test_config_detailed_not_found(http_client, create_url, auth_headers, config):
    # given
    url = create_url('/config/abcdef/')

    # when
    with pytest.raises(HTTPError) as error:
        yield http_client.fetch(url, **auth_headers)

    # then
    assert 404 == error.value.code
