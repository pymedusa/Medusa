# coding=utf-8
"""Tests for series name comparison normalization."""
from __future__ import unicode_literals

import pytest

from medusa.name_parser.series_name import normalize_series_name_for_comparison


@pytest.mark.parametrize('raw,library', [
    ('11.22.63', '11 22 63'),
    ('11.22.63', '11.22.63'),
    ('R-15', 'R 15'),
    ('R-15', 'R-15'),
    ('9-1-1', '9 1 1'),
    ('9-1-1', '9-1-1'),
    ('12 Monkeys', '12.Monkeys'),
    ('3 Show på (abc2)', '3 Show pa (abc2)'),
    ('1923 (2022)', '1923 2022'),
    ('1883 (2021)', '1883 2021'),
])
def test_normalize_series_name_for_comparison_matches_guessit4_titles(raw, library):
    """Punctuated GuessIt 4 titles must still match library / alias forms."""
    assert normalize_series_name_for_comparison(raw) == normalize_series_name_for_comparison(library)


@pytest.mark.parametrize('left,right', [
    ('11.22.63', 'The 100'),
    ('R-15', 'R-16'),
    ('9-1-1', '911'),
    ('1923', '1883'),
    ('1923 (2022)', '1883 (2021)'),
])
def test_normalize_series_name_for_comparison_keeps_distinct_shows(left, right):
    """Normalization must not collapse clearly different series names."""
    assert normalize_series_name_for_comparison(left) != normalize_series_name_for_comparison(right)


def test_normalize_preserves_empty():
    assert normalize_series_name_for_comparison('') == ''
    assert normalize_series_name_for_comparison(None) == ''
