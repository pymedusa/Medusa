# coding=utf-8
"""Test /config route."""
from __future__ import unicode_literals

import json
import platform
import sys

from medusa import app, db
from medusa.helper.mappings import NonEmptyDict
from medusa.indexers.indexer_config import get_indexer_config

import pytest

from tornado.httpclient import HTTPError


@pytest.fixture
def config(monkeypatch, app_config):
    python_version = 'Python Test v1.2.3.4'
    monkeypatch.setattr(sys, 'version', python_version)
    os_user = app_config('OS_USER', 'superuser')
    app_config('LOCALE', (None, 'ABC'))
    app_locale = 'Unknown.ABC'

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
    config_data['locale'] = app_locale
    config_data['localUser'] = os_user
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

    return config_data


@pytest.mark.gen_test
def test_config_get(http_client, create_url, auth_headers, config):
    # given
    expected = config

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
    'dbFilename',
])
def test_config_get_detailed(http_client, create_url, auth_headers, config, query):
    # given
    expected = config[query]
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
