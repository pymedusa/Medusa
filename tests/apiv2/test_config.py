# coding=utf-8
"""Test /config route."""
import json
import platform
import sys

from medusa import app, db
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
        'dbFilename': db.dbFilename(),
        'cacheDir': app.CACHE_DIR,
        'logDir': app.LOG_DIR,
        'appArgs': app.MY_ARGS,
        'webRoot': app.WEB_ROOT,
        'githubUrl': app.GITHUB_IO_URL,
        'wikiUrl': app.WIKI_URL,
        'sourceUrl': app.APPLICATION_URL,
        'displayAllSeasons': app.DISPLAY_ALL_SEASONS,
        'displayShowSpecials': app.DISPLAY_SHOW_SPECIALS,
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
            'home': app.HOME_LAYOUT
        }
    }


@pytest.mark.gen_test
def test_config_get(http_client, create_url, auth_headers, config):
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
def test_config_get_detailed(http_client, create_url, auth_headers, config, query):
    # given
    expected = config[query]
    url = create_url('/config/{0}/'.format(query))

    # when
    response = yield http_client.fetch(url, **auth_headers)

    # then
    assert response.code == 200
    assert expected == json.loads(response.body)


@pytest.mark.gen_test
def test_config_get_detailed_not_found(http_client, create_url, auth_headers):
    # given
    url = create_url('/config/abcdef/')

    # when
    with pytest.raises(HTTPError) as error:
        yield http_client.fetch(url, **auth_headers)

    # then
    assert 404 == error.value.code
