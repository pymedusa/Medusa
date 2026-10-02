# coding=utf-8
"""Tests for month name helpers used by parsing and search templates."""
from __future__ import unicode_literals

from datetime import date

import pytest

from medusa.helper.month_names import (
    get_month_name,
    month_from_name,
    normalize_lang,
)


@pytest.mark.parametrize('name,expected', [
    ('Mai', 5),
    ('mai', 5),
    ('Aout', 8),
    ('août', 8),
    ('August', 8),
    ('Fevrier', 2),
    ('février', 2),
    ('Enero', 1),
    ('unknown', None),
])
def test_month_from_name(name, expected):
    assert month_from_name(name) == expected


@pytest.mark.parametrize('month,lang,abbreviated,expected', [
    (5, 'fr', False, 'Mai'),
    (8, 'fr', False, 'Aout'),
    (2, 'fr', False, 'Fevrier'),
    (8, 'en', False, 'August'),
    (8, 'en', True, 'Aug'),
    (5, 'fr', True, 'Mai'),
    (5, 'fr_FR', False, 'Mai'),
    (1, None, False, 'January'),
    (5, 'pl', False, 'Maj'),
    (8, 'tr', False, 'Agustos'),
    (1, 'ru', False, 'Yanvar'),
    (6, 'fi', False, 'Kesakuu'),
    (12, 'no', False, 'Desember'),
    (5, 'sv', False, 'Maj'),
    (3, 'da', False, 'Marts'),
    (8, 'ja', False, '8月'),
    (1, 'zh', False, '一月'),
    (5, 'ko', False, '5월'),
    (8, 'jp', False, '8月'),  # alias to ja
])
def test_get_month_name(month, lang, abbreviated, expected):
    assert get_month_name(month, lang, abbreviated=abbreviated) == expected


def test_all_medusa_indexer_languages_have_month_names():
    from medusa.indexers.config import init_config
    from medusa.helper.month_names import MONTH_NAMES_ABBR, MONTH_NAMES_FULL

    for lang in init_config['valid_languages']:
        assert lang in MONTH_NAMES_FULL, lang
        assert lang in MONTH_NAMES_ABBR, lang
        assert len(MONTH_NAMES_FULL[lang]) == 13
        assert len(MONTH_NAMES_ABBR[lang]) == 13
        for month in range(1, 13):
            assert get_month_name(month, lang)
            assert get_month_name(month, lang, abbreviated=True)


def test_listopad_prefers_polish_czech_november():
    """Croatian October shares 'listopad' with PL/CS November; lookup is one-way."""
    assert month_from_name('listopad') == 11
    assert get_month_name(10, 'hr') == 'Listopad'
    assert month_from_name(get_month_name(10, 'hr')) == 11
    assert month_from_name('studeni') == 11


def test_normalize_lang():
    assert normalize_lang('fr_FR') == 'fr'
    assert normalize_lang('EN') == 'en'
    assert normalize_lang(None) == 'en'


def test_formatted_search_string_monthly_templates(create_tvshow, create_tvepisode):
    series = create_tvshow(name='Show Name', lang='fr')
    episode = create_tvepisode(series, 1, 1)
    episode.airdate = date(2016, 5, 15)

    assert episode.formatted_search_string('%SN %MM %Y') == 'Show Name Mai 2016'
    assert episode.formatted_search_string('%SN %0M.%Y') == 'Show Name 05.2016'
    assert episode.formatted_search_string('%SN %Y.%0M') == 'Show Name 2016.05'
    assert episode.formatted_search_string('%SN %Mm %Y') == 'Show Name Mai 2016'
