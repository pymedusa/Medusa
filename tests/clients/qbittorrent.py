# coding=utf-8

import json
import os

from medusa.clients.torrent.qbittorrent import QBittorrentAPI

import pytest


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
