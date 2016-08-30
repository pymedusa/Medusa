#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Guessit Name Parser."""
from __future__ import unicode_literals

import re
from datetime import timedelta

from dogpile.cache.region import make_region

from guessit.rules.common.date import valid_year
import sickbeard
from sickbeard.helpers import normalize
from .rules import default_api


region = make_region()
region.configure('dogpile.cache.memory')

EXPECTED_TITLES_EXPIRATION_TIME = timedelta(days=1).total_seconds()

# hardcoded expected titles
fixed_expected_titles = {
    # guessit: conflicts with italian language
    r're:(?<![^/\\])\w+ it\b',
}

# release group exception list
expected_groups = normalize({
    # https://github.com/guessit-io/guessit/issues/297
    # guessit blacklists parts of the name for the following groups
    r're:\bbyEMP\b',
    r're:\bELITETORRENT\b',
    r're:\bNovaRip\b',
    r're:\bPARTiCLE\b',
    r're:\bPOURMOi\b',
    r're:\bRipPourBox\b',
    r're:\bRiPRG\b',

    # https://github.com/guessit-io/guessit/issues/316
    r're:\bCDP\b',
    r're:\bCDD\b',

    # https://github.com/guessit-io/guessit/issues/317
    r're:\bHDD\b',

    # release groups with numbers
    r're:\b4EVERHD\b',  # remove after guessit #313 is fixed
    r're:\bF4ST3R\b',
    r're:\bF4ST\b',
    r're:\bPtM\b',
    r're:\bTGNF4ST\b',
    r're:\bTV2LAX9\b',
})

allowed_languages = normalize({
    'de',
    'en',
    'es',
    'fr',
    'he',
    'hu',
    'it',
    'jp',
    'nl',
    'pl',
    'pt',
    'ro',
    'ru',
    'sv',
    'uk',
})

allowed_countries = normalize({
    'us',
    'gb',
})

series_re = re.compile(r'^(?P<series>.*?)(?: \(?(?:(?P<year>\d{4})|(?P<country>[A-Z]{2}))\)?)?$')


def guessit(name, options=None):
    """Guess the episode information from a given release name.

    :param name: the release name
    :type name: str
    :param options:
    :type options: dict
    :return: the guessed properties
    :rtype: dict
    """
    final_options = dict(options) if options else dict()
    final_options.update(dict(type='episode', implicit=True,
                              episode_prefer_number=final_options.get('show_type') == 'anime',
                              expected_title=get_expected_titles(sickbeard.showList),
                              expected_group=expected_groups,
                              allowed_languages=allowed_languages,
                              allowed_countries=allowed_countries))
    return default_api.guessit(name, options=final_options)


@region.cache_on_arguments(expiration_time=EXPECTED_TITLES_EXPIRATION_TIME)
def get_expected_titles(show_list):
    """Return expected titles to be used by guessit.

    It iterates over user's show list and only returns a regex for titles that contains numbers
    (since they can confuse guessit).

    :param show_list:
    :type show_list: list of sickbeard.tv.TVShow
    :return:
    :rtype: list of str
    """
    expected_titles = list(fixed_expected_titles)
    for show in show_list:
        names = [show.name] + show.exceptions
        for name in names:
            match = series_re.match(name)
            if not match:
                continue

            series, year, _ = match.groups()
            if year and not valid_year(int(year)):
                series = name

            if not any([char.isdigit() for char in series]):
                continue

            if not any([char.isalpha() for char in series]):
                # if no alpha chars then add series name 'as-is'
                expected_titles.append(series)

            # (?<![^/\\]) means -> it matches nothing but path separators and dot (negative lookbehind)
            fmt = r're:\b{name}\b' if show.is_anime else r're:(?<![^/\\\.]){name}\b'
            expected_titles.append(fmt.format(name=prepare(series)))

    return normalize(expected_titles)


def prepare(string):
    """Prepare a string to be used as a regex in guessit expected_title.

    :param string:
    :type string: str
    :return:
    :rtype: str
    """
    # replace some special characters with space
    characters = {'-', '.', ',', '*', '(', ')'}
    string = re.sub(r'[%s]' % re.escape(''.join(characters)), ' ', string)

    # replace unicode characters with period
    string = re.sub(r'[^\x00-\x7F]+', '.', string)

    # escape other characters that might be problematic
    string = re.escape(string)

    # dots (the replacement of unicode characters) shouldn't be escaped and should match 1 or more characters
    string = string.replace('\.', '.+')

    # ' should be optional
    string = string.replace(r"\'", r"'?")

    # spaces shouldn't be escaped
    string = string.replace('\ ', ' ')

    # replace multiple spaces with one
    string = re.sub(r'\s+', ' +', string.strip())

    # : should be optional or space
    string = string.replace(r"\:", r" ?")

    return string
