# coding=utf-8
"""Tests for medusa.tv identifiers."""
from __future__ import unicode_literals

import re
from medusa.server.api.v2.base import BaseRequestHandler
import pytest


@pytest.mark.parametrize('p', [
    {  # p0
        'url': '/foo/bar/123/a1b2c3/done',
        'expected': {
            'path1': 'bar',
            'path2': '123',
            'path3': 'a1b2c3',
            'path4': 'done',
        }
    },
    {  # p1
        'url': '/foo/bar/123/a1b2c3/done/',
        'expected': {
            'path1': 'bar',
            'path2': '123',
            'path3': 'a1b2c3',
            'path4': 'done',
        },
    },
    {  # p2
        'url': '/foo',
        'expected': {
            'path1': None,
            'path2': None,
            'path3': None,
            'path4': None,
        },
    },
    {  # p3
        'url': '/foo/',
        'expected': {
            'path1': None,
            'path2': None,
            'path3': None,
            'path4': None,
        },
    },
    {  # p4
        'url': '/foo/bar',
        'expected': {
            'path1': 'bar',
            'path2': None,
            'path3': None,
            'path4': None,
        },
    },
    {  # p5
        'url': '/foo/bar/',
        'expected': {
            'path1': 'bar',
            'path2': None,
            'path3': None,
            'path4': None,
        },
    },
    {  # p6
        'url': '/foo/bar/123',
        'expected': {
            'path1': 'bar',
            'path2': '123',
            'path3': None,
            'path4': None,
        },
    },
    {  # p7
        'url': '/foo/bar/123/',
        'expected': {
            'path1': 'bar',
            'path2': '123',
            'path3': None,
            'path4': None,
        },
    },
    {  # p8
        'url': '/foo/bar/123/a1b2c3',
        'expected': {
            'path1': 'bar',
            'path2': '123',
            'path3': 'a1b2c3',
            'path4': None,
        },
    },
    {  # p9
        'url': '/foo/bar/123/a1b2c3/',
        'expected': {
            'path1': 'bar',
            'path2': '123',
            'path3': 'a1b2c3',
            'path4': None,
        },
    },
    {  # p10
        'url': '/foo/bar/123/a1b2c3/done//',
        'expected': None,
    },
    {  # p11
        'url': '/foo/bar/123/a1b2c3/done1',
        'expected': None,
    },
    {  # p12
        'url': '/foo/bar/123/a1b2c3/done/more',
        'expected': None,
    },
])
def test_match_url(p):
    # Given
    sut = BaseRequestHandler
    resource = 'foo'
    paths = [
        ('path1', r'[a-z]+'),
        ('path2', r'\d+'),
        ('path3', r'\w+'),
        ('path4', r'[a-z]+'),
    ]

    regex = re.compile(sut.create_url('', resource, *paths))
    url = p['url']
    expected = p['expected']

    # When
    m = regex.match(url)
    actual = m.groupdict() if m else None

    # Then
    assert expected == actual
