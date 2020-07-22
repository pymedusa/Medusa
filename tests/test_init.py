# coding=utf-8
"""Tests for monkeypatches/workarounds from medusa/init/*.py."""

from __future__ import unicode_literals

from bencodepy import BencodeDecodeError, DEFAULT as BENCODE

from medusa import init  # noqa: F401 [unused]

import pytest


TEST_TORRENT_CONTENT = (
    b'd8:announce23:udp://explodie.org:696913:announce-listll23:udp://explodie.org:6969el34:udp://tracker.coppersurfer'
    b'.tk:6969el31:udp://tracker.empire-js.us:1337el40:udp://tracker.leechers-paradise.org:6969el33:udp://tracker.open'
    b'trackr.org:1337el26:wss://tracker.btorrent.xyzel25:wss://tracker.fastcast.nzel32:wss://tracker.openwebtorrent.co'
    b'mee7:comment23:This is a test torrent.10:created by18:qBittorrent v4.2.513:creation datei1595424635e4:infod6:len'
    b'gthi8525e4:name9:readme.md12:piece lengthi16384e6:pieces20:\n_y\x0c\xfa\xb9^&2\xe3`!\x12\x1f\x14&z7AIe8:url-list'
    b'31:https://webtorrent.io/torrents/e'
)
TEST_TORRENT_DECODED = {
    'announce': 'udp://explodie.org:6969',
    'announce-list': [
        ['udp://explodie.org:6969'],
        ['udp://tracker.coppersurfer.tk:6969'],
        ['udp://tracker.empire-js.us:1337'],
        ['udp://tracker.leechers-paradise.org:6969'],
        ['udp://tracker.opentrackr.org:1337'],
        ['wss://tracker.btorrent.xyz'],
        ['wss://tracker.fastcast.nz'],
        ['wss://tracker.openwebtorrent.com'],
    ],
    'comment': 'This is a test torrent.',
    'created by': 'qBittorrent v4.2.5',
    'creation date': 1595424635,
    'info': {
        'length': 8525,
        'name': 'readme.md',
        'piece length': 16384,
        'pieces': b'\n_y\x0c\xfa\xb9^&2\xe3`!\x12\x1f\x14&z7AI',
    },
    'url-list': 'https://webtorrent.io/torrents/',
}


@pytest.mark.parametrize('p', [
    {  # p0: bytes with *allowed* extra data
        'value': b'd5:hello5:world7:numbersli1ei2eeeEXTRA_DATA_HERE',
        'expected': {'hello': 'world', 'numbers': [1, 2]},
        'allow_extra_data': True,
        'raises_exc': None,
        'exc_message': r''
    },
    {  # p1: bytes with *disallowed* extra data
        'value': b'd5:hello5:world7:numbersli1ei2eeeEXTRA_DATA_HERE',
        'expected': None,
        'allow_extra_data': False,
        'raises_exc': BencodeDecodeError,
        'exc_message': r'.+\(data after valid prefix\)'
    },
    {  # p2: unicode with *allowed* extra data
        'value': 'd5:hello5:world7:numbersli1ei2eeeEXTRA_DATA_HERE',
        'expected': {'hello': 'world', 'numbers': [1, 2]},
        'allow_extra_data': True,
        'raises_exc': None,
        'exc_message': r''
    },
    {  # p3: unicode with *disallowed* extra data
        'value': 'd5:hello5:world7:numbersli1ei2eeeEXTRA_DATA_HERE',
        'expected': None,
        'allow_extra_data': False,
        'raises_exc': BencodeDecodeError,
        'exc_message': r'.+\(data after valid prefix\)'
    },
    {  # p4: invalid data
        'value': 'Heythere',
        'expected': None,
        'allow_extra_data': False,
        'raises_exc': BencodeDecodeError,
        'exc_message': r'not a valid bencoded string'
    },
    {  # p5: none
        'value': None,
        'expected': None,
        'allow_extra_data': False,
        'raises_exc': BencodeDecodeError,
        'exc_message': r'not a valid bencoded string'
    },
    {  # p6: example torrent
        'value': TEST_TORRENT_CONTENT,
        'expected': TEST_TORRENT_DECODED,
        'allow_extra_data': True,
        'raises_exc': None,
        'exc_message': r''
    }
])
def test_bdecode_monkeypatch(p):
    """Test the monkeypatched `bencode.bdecode` function."""
    # Given
    value = p['value']
    allow_extra_data = p['allow_extra_data']
    expected = p['expected']
    exc_message = p['exc_message']
    raises_exc = p['raises_exc']

    # When + Then
    if raises_exc is not None:
        with pytest.raises(raises_exc, match=exc_message):
            actual = BENCODE.decode(value, allow_extra_data=allow_extra_data)
    else:
        actual = BENCODE.decode(value, allow_extra_data=allow_extra_data)
        assert expected == actual
