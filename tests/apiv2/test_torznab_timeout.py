"""Torznab provider configuration and timeout responses over the v2 API."""
import json
from unittest.mock import Mock

from medusa import app
from medusa.providers.torrent.torznab.torznab import TorznabProvider

import pytest

import requests


@pytest.mark.gen_test
async def test_torznab_timeout_patch_and_get(http_client, create_url, auth_headers, monkeypatch):
    monkeypatch.setattr(app, 'THEME_DATA_ROOT', '')
    provider = TorznabProvider('Indexer', 'http://localhost/', api_key='test',
                               search_mode='sponly', enable_backlog=True, cat_ids=['5030'])
    provider.minseed = 9
    monkeypatch.setattr(app, 'torznab_providers_list', [provider])
    monkeypatch.setattr(app, 'instance', Mock())
    url = create_url('/providers/indexer')
    initial = await http_client.fetch(url, **auth_headers)
    expected = json.loads(initial.body)['config']
    assert expected['search']['timeout'] == 30
    for body in ({'search': {'timeout': 180}}, {'search': {'daily': {'enabled': False}}, 'minseed': 7}):
        await http_client.fetch(url, method='PATCH', body=json.dumps(body), **auth_headers)
        if 'minseed' in body:
            expected['minseed'] = 7
            expected['search']['daily']['enabled'] = False
        expected['search']['timeout'] = 180
        response = await http_client.fetch(url, **auth_headers)
        assert json.loads(response.body)['config'] == expected
    assert app.instance.save_config.call_count == 2

    monkeypatch.setattr(provider.session, 'send', Mock(side_effect=requests.ReadTimeout()))
    response = await http_client.fetch(create_url('/providers/internal/operation'), method='POST',
                                       body=json.dumps({'type': 'TESTPROVIDER', 'providerId': 'indexer'}),
                                       raise_error=False, **auth_headers)
    assert response.code == 504
    assert json.loads(response.body)['error'] == 'Provider search timed out'
