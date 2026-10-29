# coding=utf-8
"""Regression tests for IMDb identifier normalization."""
from __future__ import unicode_literals

import sys

from medusa.indexers.imdb.api import ImdbIdentifier

import pytest


@pytest.mark.parametrize('value, imdb_id, series_id', [
    (6135388, 'tt6135388', 6135388),
    (12, 'tt0000012', 12),
    (0, 'tt0000000', 0),
    ('6135388', 'tt6135388', 6135388),
    ('12', 'tt0000012', 12),
    ('00000012', 'tt00000012', 12),
    ('tt6135388', 'tt6135388', 6135388),
    ('tt12', 'tt12', 12),
    ('tt00000012', 'tt00000012', 12),
    ('tt30051064', 'tt30051064', 30051064),
    ('tt0000000', 'tt0000000', 0),
    ('  tt6135388  ', 'tt6135388', 6135388),
    ('  12  ', 'tt0000012', 12),
    ('/title/tt6135388/', 'tt6135388', 6135388),
    ('/legacy/tt6135388', 'tt6135388', 6135388),
    ('tt6135388/episodes/?season=2&ref_=ttep', 'tt6135388', 6135388),
    ('/title/tt6135388/episodes/?season=2#ttep', 'tt6135388', 6135388),
    ('https://www.imdb.com/title/tt6135388/', 'tt6135388', 6135388),
    ('https://www.imdb.com/title/tt30051064/episodes?season=2', 'tt30051064', 30051064),
    ('//www.imdb.com/title/tt6135388/#tt7654321', 'tt6135388', 6135388),
    ('/title/tt6135388/?id=tt7654321#tt7654321', 'tt6135388', 6135388),
])
def test_supported_identifiers(value, imdb_id, series_id):
    """Preserve supported identifiers, formatting and title-path extraction."""
    identifier = ImdbIdentifier(value)

    assert (imdb_id, series_id) == (identifier.imdb_id, identifier.series_id)


@pytest.mark.parametrize('value', [
    None, '', '   ', -1, '-1', 1.5, 1.0, True, False,
    [], {}, {'imdb_id': 'tt6135388'}, b'tt6135388', object(),
    'garbage', 'tt', 'ttgarbage', 'prefix-tt6135388', 'tt6135388junk',
    'tt6135388,tt7654321', 'tt6135388.0', 'tt-6135388', 'tt+6135388',
    '+6135388', '6135388.0', 'tt٦١٣٥٣٨٨', '６１３５３８８',
    'watch tt6135388', 'watch /title/tt6135388/',
    '?imdb_id=tt6135388', '#tt6135388',
    'https://www.imdb.com/?id=tt6135388', 'https://www.imdb.com/#tt6135388',
    'https://tt6135388/', '//tt6135388/', 'https://tt6135388.imdb.com/',
    'https://[broken/title/tt6135388/',
    'https:///title/tt6135388/', 'https://www.imdb.com:bad/title/tt6135388/',
    '/title/tt6135388junk/', '/title/prefixtt6135388/',
    '/title/tt6135388/title/tt7654321/',
    'tt613\n5388', 'tt613\t5388', 'tt613\r5388', 'tt613\x005388',
    'https://www.imdb.com/title/tt613\n5388/',
])
def test_invalid_identifiers_have_no_textual_or_numeric_id(value):
    """Reject unsupported types and incomplete or misleading identifier text."""
    identifier = ImdbIdentifier(value)

    assert (None, None) == (identifier.imdb_id, identifier.series_id)


@pytest.mark.parametrize('value', [None, '', 'ttinvalid', {}, True, -1])
def test_invalid_assignment_clears_previous_identifier(value):
    """Clear both representations when a previously valid identifier is replaced."""
    identifier = ImdbIdentifier('tt6135388')

    identifier.imdb_id = value

    assert (None, None) == (identifier.imdb_id, identifier.series_id)


@pytest.mark.parametrize('kind', ['numeric-string', 'prefixed-string', 'integer'])
def test_conversion_limit_does_not_raise_or_leave_an_identifier(kind):
    """Handle Python's integer conversion limit as an invalid identifier."""
    get_limit = getattr(sys, 'get_int_max_str_digits', None)
    if get_limit is None:
        pytest.skip('Integer string conversion limit is unavailable')
    limit = get_limit()
    if not limit:
        pytest.skip('Integer string conversion limit is disabled')
    value = 10 ** limit if kind == 'integer' else '1' * (limit + 1)
    if kind == 'prefixed-string':
        value = 'tt' + value

    identifier = ImdbIdentifier(value)

    assert (None, None) == (identifier.imdb_id, identifier.series_id)
