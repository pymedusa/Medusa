# coding=utf-8

import json
import os

from medusa.clients.torrent.qbittorrent import QBittorrentAPI

import pytest


def test_auth_v2_empty_204_response_is_success(requests_mock):
    # Given
    requests_mock.post('http://localhost/api/v2/auth/login', text='', status_code=204)
    requests_mock.get('http://localhost/api/v2/app/webapiVersion', text='2.14.0')

    # When
    client = QBittorrentAPI(host='http://localhost')

    # Then
    assert client.auth is True
    assert client.api == (2, 14, 0)


def test_auth_v2_legacy_ok_response_is_success(requests_mock):
    # Given
    requests_mock.post('http://localhost/api/v2/auth/login', text='Ok.', status_code=200)
    requests_mock.get('http://localhost/api/v2/app/webapiVersion', text='2.13.1')

    # When
    client = QBittorrentAPI(host='http://localhost')

    # Then
    assert client.auth == 'Ok.'
    assert client.api == (2, 13, 1)


def test_auth_v2_legacy_fails_response_is_invalid_credentials(requests_mock):
    # Given
    requests_mock.post('http://localhost/api/v2/auth/login', text='Fails.', status_code=200)

    # When
    client = QBittorrentAPI(host='http://localhost')

    # Then
    assert client.auth is None
    assert client.api is None


def test_auth_v2_401_response_is_invalid_credentials(requests_mock):
    # Given
    requests_mock.post('http://localhost/api/v2/auth/login', text='', status_code=401)

    # When
    client = QBittorrentAPI(host='http://localhost')

    # Then
    assert client.auth is None
    assert client.api is None


def test_add_torrent_uri_accepts_async_response(requests_mock, monkeypatch):
    # Given
    class Series(object):
        is_anime = False

    class Result(object):
        url = 'magnet:?xt=urn:btih:aabbcc'
        series = Series()

    monkeypatch.setattr('medusa.app.TORRENT_PATH', '')
    monkeypatch.setattr('medusa.app.TORRENT_LABEL', '')

    requests_mock.post('http://localhost/api/v2/auth/login', text='', status_code=200)
    requests_mock.get('http://localhost/api/v2/app/webapiVersion', text='2.14.0')
    client = QBittorrentAPI(host='http://localhost')
    client.api = (2, 14, 0)
    requests_mock.post(
        'http://localhost/api/v2/torrents/add',
        json={
            'success_count': 0,
            'failure_count': 0,
            'pending_count': 1,
            'added_torrent_ids': [],
        },
        status_code=202,
    )

    # When
    actual = client._add_torrent_uri(Result())

    # Then
    assert actual is True


def test_add_torrent_uri_accepts_legacy_ok_response(requests_mock, monkeypatch):
    # Given
    class Series(object):
        is_anime = False

    class Result(object):
        url = 'magnet:?xt=urn:btih:aabbcc'
        series = Series()

    monkeypatch.setattr('medusa.app.TORRENT_PATH', '')
    monkeypatch.setattr('medusa.app.TORRENT_LABEL', '')

    requests_mock.post('http://localhost/api/v2/auth/login', text='Ok.', status_code=200)
    requests_mock.get('http://localhost/api/v2/app/webapiVersion', text='2.13.1')
    client = QBittorrentAPI(host='http://localhost')
    requests_mock.post('http://localhost/api/v2/torrents/add', text='Ok.', status_code=200)

    # When
    actual = client._add_torrent_uri(Result())

    # Then
    assert actual is True


@pytest.mark.parametrize('p', [
    {  # p0
        'method': 'properties',
        'uri': 'http://localhost/api/v2/torrents/properties',
        'expected': True
    },
])
def test_torrent_completed(p, response_mock):
    # Given
    expected = p['expected']

    # When
    client = QBittorrentAPI(host='http://localhost')
    client.api = (2, 0, 0)
    client.auth = True
    response_mock(client.name, p['method'], p['uri'])

    actual = client.torrent_completed('aabbcc')

    # Then
    assert expected == actual
