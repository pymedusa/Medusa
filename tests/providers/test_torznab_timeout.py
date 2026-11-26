# coding=utf-8
"""Regression tests for slow Torznab search responses."""
from __future__ import unicode_literals

import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from types import SimpleNamespace
from unittest.mock import Mock, patch

from medusa import app
from medusa.helper.exceptions import ProviderSearchTimeout
from medusa.indexers.config import INDEXER_TVDBV2
from medusa.providers.torrent.torrent_provider import TorrentProvider
from medusa.providers.torrent.torznab.torznab import TorznabProvider
from medusa.server.api.v2.providers import ProvidersHandler

import pytest

import requests

from urllib3.exceptions import ReadTimeoutError


@pytest.mark.parametrize('configured, expected', [
    (None, 30),
    ('invalid', 30),
    ('180.5', 30),
    (180.5, 30),
    ([], 30),
    (-10, 30),
    (30, 30),
    (29, 30),
    (180, 180),
    ('480', 480),
    (600, 600),
    (601, 600),
    (9999, 600),
])
def test_torznab_search_timeout_is_bounded(configured, expected, monkeypatch):
    provider = TorznabProvider('Test Torznab', url='http://localhost/indexer/amule/',
                               api_key='test', search_timeout=configured)
    seen = []

    def get(url, **kwargs):
        seen.append((url, kwargs))
        return None

    monkeypatch.setattr(provider.session, 'get', get)

    assert provider.search({'Episode': ['Example.Show.S01E01']}, force_query=True) == []
    assert len(seen) == 1
    assert seen[0][1]['timeout'] == (30, expected)
    assert seen[0][1]['params']['t'] == 'search'


def test_torznab_timeout_exposed_in_provider_json(monkeypatch):
    monkeypatch.setattr(app, 'THEME_DATA_ROOT', '')
    provider = TorznabProvider('Test Torznab', search_timeout=180)
    assert provider.to_json()['config']['search']['timeout'] == 180

    ordinary = TorrentProvider('Ordinary')
    ProvidersHandler._set_common_settings(ordinary, {'search': {'timeout': 180}})
    assert 'timeout' not in ordinary.to_json()['config']['search']


def test_torznab_timeout_patch_normalizes_and_preserves_missing_field():
    provider = TorznabProvider('Test Torznab', search_timeout=180)
    ProvidersHandler._set_common_settings(provider, {'search': {'timeout': 1000}})
    assert provider.search_timeout == 600

    ProvidersHandler._set_common_settings(provider, {'search': {}})
    assert provider.search_timeout == 600


def _run_config_start(data_dir, expected):
    """Run normal initialization and stop before the web server and schedulers start."""
    from medusa.__main__ import Application

    application = Application()
    with patch.object(application, 'load_shows_from_db', side_effect=StopIteration), pytest.raises(StopIteration):
        application.start(['--datadir', data_dir, '--quiet', '--nolaunch'])
    slow, ordinary, invalid = app.torznab_providers_list
    assert slow.search_timeout == expected
    assert ordinary.search_timeout == invalid.search_timeout == 30
    assert slow.cat_ids == ['5030', '5040']
    assert slow.enable_backlog and slow.minseed == 9
    slow.search_timeout = 180
    application.save_config()


def test_search_timeout_survives_restart(tmp_path):
    from configobj import ConfigObj

    filename = tmp_path / 'config.ini'
    filename.write_text('[Torznab]\ntorznab_providers = Slow, Ordinary, Invalid\n'
                        '[SLOW]\nslow_cat_ids = 5030, 5040\nslow_enable_backlog = 1\n'
                        'slow_minseed = 9\nslow_search_timeout = 601\n'
                        '[INVALID]\ninvalid_search_timeout = broken\n', encoding='utf-8')
    for expected in (600, 180):
        subprocess.run([sys.executable, '-B', '-c',
                        'import sys; from tests.providers.test_torznab_timeout import _run_config_start; '
                        '_run_config_start(sys.argv[1], int(sys.argv[2]))',
                        str(tmp_path), str(expected)], check=True, timeout=120)
        saved = ConfigObj(str(filename))
        assert saved['SLOW']['slow_search_timeout'] == '180'
        assert saved['ORDINARY']['ordinary_search_timeout'] == '30'
        assert saved['INVALID']['invalid_search_timeout'] == '30'


def test_id_search_and_caps_use_their_own_timeouts(monkeypatch):
    provider = TorznabProvider('Indexer', 'http://localhost/', api_key='test', search_timeout=180,
                               cap_tv_search=['tvdbid', 'season', 'ep'])
    provider.series = SimpleNamespace(indexer=INDEXER_TVDBV2, indexerid=123)
    episode = SimpleNamespace(series=SimpleNamespace(air_by_date=False, sports=False), scene_season=2, scene_episode=3)
    send = Mock(return_value=None)
    monkeypatch.setattr(provider.session, 'get', send)
    provider.get_capabilities()
    provider.search({'Episode': ['Example.S02E03']}, ep_obj=episode)
    caps, indexed, text = [call.kwargs for call in send.call_args_list]
    assert caps['params']['t'] == 'caps' and 'timeout' not in caps
    assert indexed['params'] == dict(apikey='test', t='tvsearch', limit=100, offset=0,
                                     cat=','.join(provider.cat_ids), tvdbid=123, season=2, ep=3)
    assert text['params']['t'] == 'search' and text['params']['q'] == 'Example.S02E03'
    assert indexed['timeout'] == text['timeout'] == (30, 180)


@pytest.mark.parametrize('error', [
    requests.ReadTimeout(),
    requests.ConnectionError(ReadTimeoutError(None, '/api', 'timed out')),
])
def test_search_timeout_is_reported_without_retry(monkeypatch, error):
    provider = TorznabProvider('Indexer', 'http://localhost/', api_key='test')
    send = Mock(side_effect=error)
    monkeypatch.setattr(provider.session, 'send', send)
    with pytest.raises(ProviderSearchTimeout):
        provider.search({'Episode': ['Example.S01E01', 'Alias.S01E01']})
    send.assert_called_once()


def test_connect_timeout_is_not_reported_as_search_timeout(monkeypatch):
    """A connect timeout is a connectivity failure, not a slow search response."""
    provider = TorznabProvider('Indexer', 'http://localhost/', api_key='test')
    monkeypatch.setattr(provider.session, 'send', Mock(side_effect=requests.ConnectTimeout()))
    assert provider.search({'Episode': ['Example.S01E01']}) == []


def test_rss_timeout_preserves_provider_cache(monkeypatch):
    provider = TorznabProvider('Indexer', 'http://localhost/', api_key='test')
    monkeypatch.setattr(provider.session, 'send', Mock(side_effect=requests.ReadTimeout()))
    monkeypatch.setattr(provider.cache, 'should_update', lambda started: True)
    clear_cache = Mock()
    monkeypatch.setattr(provider.cache, '_clear_cache', clear_cache)
    provider.cache.update_cache(123)
    clear_cache.assert_not_called()


def test_slow_search_returns_real_rss_result(monkeypatch):
    class SlowIndexer(BaseHTTPRequestHandler):
        def do_GET(self):
            time.sleep(31)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'<rss><channel><item><title>Example.S01E01</title>'
                             b'<enclosure url="magnet:?xt=urn:btih:test"/>'
                             b'<size>1024</size><pubDate>Fri, 02 Jan 2026 00:00:00 GMT</pubDate>'
                             b'</item></channel></rss>')

        def log_message(self, *args):
            pass

    with HTTPServer(('127.0.0.1', 0), SlowIndexer) as server:
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            provider = TorznabProvider('Slow indexer', f'http://127.0.0.1:{server.server_port}/',
                                       api_key='test', search_timeout=180)
            provider.session.trust_env = False
            monkeypatch.setattr(app, 'PROXY_PROVIDERS', False)
            adapter = provider.session.get_adapter(provider.url)
            send = Mock(wraps=adapter.send)
            monkeypatch.setattr(adapter, 'send', send)
            results = provider.search({'Episode': ['Example.S01E01']})
            send.assert_called_once()
            assert send.call_args.kwargs['timeout'] == (30, 180)
            assert [item['title'] for item in results] == ['Example.S01E01']
        finally:
            server.shutdown()
            worker.join()
