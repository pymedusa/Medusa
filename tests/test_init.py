# coding=utf-8
"""Tests for monkeypatches/workarounds from medusa/init/*.py."""

from __future__ import unicode_literals

import bencode

from medusa import init  # noqa: F401 [unused]

import pytest


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
        'expected': {'hello': 'world', 'numbers': [1, 2]},
        'allow_extra_data': False,
        'raises_exc': bencode.BencodeDecodeError,
        'exc_message': r'.+\(data after valid prefix\)'
    },
    {  # p2: unicode with *allowed* extra data
        'value': b'd5:hello5:world7:numbersli1ei2eeeEXTRA_DATA_HERE',
        'expected': {'hello': 'world', 'numbers': [1, 2]},
        'allow_extra_data': True,
        'raises_exc': None,
        'exc_message': r''
    },
    {  # p3: unicode with *disallowed* extra data
        'value': b'd5:hello5:world7:numbersli1ei2eeeEXTRA_DATA_HERE',
        'expected': {'hello': 'world', 'numbers': [1, 2]},
        'allow_extra_data': False,
        'raises_exc': bencode.BencodeDecodeError,
        'exc_message': r'.+\(data after valid prefix\)'
    },
    {  # p4: invalid data
        'value': 'Heythere',
        'expected': None,
        'allow_extra_data': False,
        'raises_exc': bencode.BencodeDecodeError,
        'exc_message': r'not a valid bencoded string'
    },
    {  # p5: none
        'value': None,
        'expected': None,
        'allow_extra_data': False,
        'raises_exc': bencode.BencodeDecodeError,
        'exc_message': r'not a valid bencoded string'
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
            actual = bencode.bdecode(value, allow_extra_data=allow_extra_data)
    else:
        actual = bencode.bdecode(value, allow_extra_data=allow_extra_data)
        assert expected == actual
