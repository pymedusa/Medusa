# coding=utf-8
"""Tests for medusa.clients.torrent module."""
from __future__ import unicode_literals

import medusa.clients.torrent as sut
from medusa.clients.torrent import (
    deluge, deluged, downloadstation, mlnet,
    qbittorrent, rtorrent, transmission, utorrent
)

import pytest


@pytest.mark.parametrize('p', [
    {  # p0
        'client': 'deluge',
        'expected': deluge
    },
    {  # p1
        'client': 'deluged',
        'expected': deluged
    },
    {  # p2
        'client': 'downloadstation',
        'expected': downloadstation
    },
    {  # p3
        'client': 'mlnet',
        'expected': mlnet
    },
    {  # p4
        'client': 'qbittorrent',
        'expected': qbittorrent
    },
    {  # p5
        'client': 'rtorrent',
        'expected': rtorrent
    },
    {  # p6
        'client': 'transmission',
        'expected': transmission
    },
    {  # p7
        'client': 'utorrent',
        'expected': utorrent
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
        'expected': deluge.DelugeAPI
    },
    {  # p1
        'client': 'deluged',
        'expected': deluged.DelugeDAPI
    },
    {  # p2
        'client': 'downloadstation',
        'expected': downloadstation.DownloadStationAPI
    },
    {  # p3
        'client': 'mlnet',
        'expected': mlnet.MLNetAPI
    },
    {  # p4
        'client': 'qbittorrent',
        'expected': qbittorrent.QBittorrentAPI
    },
    {  # p5
        'client': 'rtorrent',
        'expected': rtorrent.RTorrentAPI
    },
    {  # p6
        'client': 'transmission',
        'expected': transmission.TransmissionAPI
    },
    {  # p7
        'client': 'utorrent',
        'expected': utorrent.UTorrentAPI
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
