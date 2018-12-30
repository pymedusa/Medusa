# coding=utf-8
"""Tests for medusa.clients.torrent module."""
from __future__ import unicode_literals

import medusa.clients.torrent as sut
from medusa.clients.torrent import (
    deluge_client, deluged_client, downloadstation_client, mlnet_client,
    qbittorrent_client, rtorrent_client, transmission_client, utorrent_client
)
import pytest


@pytest.mark.parametrize('p', [
    {  # p0
        'client': 'deluge',
        'expected': deluge_client
    },
    {  # p1
        'client': 'deluged',
        'expected': deluged_client
    },
    {  # p2
        'client': 'downloadstation',
        'expected': downloadstation_client
    },
    {  # p3
        'client': 'mlnet',
        'expected': mlnet_client
    },
    {  # p4
        'client': 'qbittorrent',
        'expected': qbittorrent_client
    },
    {  # p5
        'client': 'rtorrent',
        'expected': rtorrent_client
    },
    {  # p6
        'client': 'transmission',
        'expected': transmission_client
    },
    {  # p7
        'client': 'utorrent',
        'expected': utorrent_client
    }
])
def test_get_client_module(p):
    # Given
    client_name = p['client']
    expected = p['expected']

    # When
    actual = sut.get_client_module(client_name)

    # Then
    assert expected == actual


def test_get_client_module__non_existent():
    # Given
    client_name = 'strangeonehere'

    with pytest.raises(ImportError):  # Then
        # When
        sut.get_client_module(client_name)


@pytest.mark.parametrize('p', [
    {  # p0
        'client': 'deluge',
        'expected': deluge_client.DelugeAPI
    },
    {  # p1
        'client': 'deluged',
        'expected': deluged_client.DelugeDAPI
    },
    {  # p2
        'client': 'downloadstation',
        'expected': downloadstation_client.DownloadStationAPI
    },
    {  # p3
        'client': 'mlnet',
        'expected': mlnet_client.MLNetAPI
    },
    {  # p4
        'client': 'qbittorrent',
        'expected': qbittorrent_client.QBittorrentAPI
    },
    {  # p5
        'client': 'rtorrent',
        'expected': rtorrent_client.RTorrentAPI
    },
    {  # p6
        'client': 'transmission',
        'expected': transmission_client.TransmissionAPI
    },
    {  # p7
        'client': 'utorrent',
        'expected': utorrent_client.UTorrentAPI
    }
])
def test_get_client_class(p):
    # Given
    client_name = p['client']
    expected = p['expected']

    # When
    actual = sut.get_client_class(client_name)

    # Then
    assert expected == actual
