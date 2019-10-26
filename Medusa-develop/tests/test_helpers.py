# coding=utf-8
"""Tests for medusa.helpers.py."""
from __future__ import unicode_literals
from collections import OrderedDict

import medusa.helpers as sut
import pytest


@pytest.mark.parametrize('p', [
    {  # p0: single value
        'value': 0,
        'expected': [0],
    },
    {  # p1: multiple values
        'value': ['b', 'a', 'c'],
        'expected': ['a', 'b', 'c'],
    },
    {  # p2: none
        'value': None,
        'expected': [],
    }
])
def test_ensure_list(p):
    # Given
    value = p['value']

    # When
    actual = sut.ensure_list(value)

    # Then
    assert p['expected'] == actual


@pytest.mark.parametrize('p', [
    {  # p0: single value
        'value': 0,
        'expected': 0,
    },
    {  # p1: multiple values
        'value': ['b', 'a', 'c'],
        'expected': None,
    },
    {  # p2: none
        'value': None,
        'expected': None,
    },
    {  # p3: none
        'value': [0],
        'expected': 0,
    }
])
def test_single_or_list(p):
    # Given
    value = p['value']

    # When
    actual = sut.single_or_list(value)

    # Then
    assert p['expected'] == actual


@pytest.mark.parametrize('p', [
    {  # p0: localhost
        'ip': '127.0.0.1',
        'expected': True,
    },
    {  # p1: public one before 24 bit block start
        'ip': '9.255.255.255',
        'expected': False,
    },
    {  # p2: private 24 bit block start
        'ip': '10.0.0.0',
        'expected': True,
    },
    {  # p3: private 24 bit block end
        'ip': '10.255.255.255',
        'expected': True,
    },
    {  # p4: public one after 24 bit block
        'ip': '11.0.0.0',
        'expected': False,
    },
    {  # p5: public one before 20 bit block start
        'ip': '172.15.255.255',
        'expected': False,
    },
    {  # p6: private 20 bit block start
        'ip': '172.16.0.0',
        'expected': True,
    },
    {  # p7: private 20 bit block end
        'ip': '172.31.255.255',
        'expected': True,
    },
    {  # p8: public one after 24 bit block
        'ip': '172.32.0.0',
        'expected': False,
    },
    {  # p9: public one before 16 bit block start
        'ip': '192.167.255.255',
        'expected': False,
    },
    {  # p10: private 16 bit block start
        'ip': '192.168.0.0',
        'expected': True,
    },
    {  # p11: private 16 bit block end
        'ip': '192.168.255.255',
        'expected': True,
    },
    {  # p12: public one after 24 bit block
        'ip': '192.169.0.0',
        'expected': False,
    },
])
def test_is_ip_private(p):
    # Given
    ip = p['ip']

    # When
    actual = sut.is_ip_private(ip)

    # Then
    assert p['expected'] == actual


@pytest.mark.parametrize('p', [
    {  # p0: simple dict
        'input': [('a', 'one'), ('b', 'two')],
        'expected': u'a:one|b:two',
    },
    {  # p1: dict with special chars
        'input': [('a', 'one'), ('b', 'π')],
        'expected': u'a:one|b:π',
    },
    {  # p2: dict with unicode chars
        'input': [('a', 'one'), ('b', u'π')],
        'expected': u'a:one|b:π',
    },
])
def test_canonical_name(p):
    # Given
    obj = OrderedDict()
    for k, v in p['input']:
        obj[k] = v
    expected = p['expected']

    # When
    actual = sut.canonical_name(obj)

    # Then
    assert expected == actual
