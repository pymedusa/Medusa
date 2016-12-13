#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Guessit Name Parser."""

import re
from datetime import timedelta
from time import time

from guessit.rules.common.date import valid_year
from .rules import default_api
from .. import app


EXPECTED_TITLES_EXPIRATION_TIME = timedelta(days=1).total_seconds()

# release group exception list
expected_groups = [
    # https://github.com/guessit-io/guessit/issues/297
    # guessit blacklists parts of the name for the following groups
    'byEMP',
    'ELITETORRENT',
    'NovaRip',
    'PARTiCLE',
    'POURMOi',
    'RipPourBox',
    'RiPRG',
    'NBY',

    # release groups with numbers
    # https://github.com/guessit-io/guessit/issues/294
    '4EVERHD',
    'F4ST3R',
    'F4ST',
    'TGNF4ST',
    'TV2LAX9',

    # https://github.com/guessit-io/guessit/issues/352
    'S4L',

    # https://github.com/guessit-io/guessit/issues/356
    'DHD',
]

allowed_languages = {
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
}

allowed_countries = {
    'us',
    'gb',
}

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
    start_time = time()
    final_options = dict(options) if options else dict()
    final_options.update(dict(type='episode', implicit=True,
                              episode_prefer_number=final_options.get('show_type') == 'anime',
                              expected_title=get_expected_titles(app.showList),
                              expected_group=expected_groups,
                              allowed_languages=allowed_languages,
                              allowed_countries=allowed_countries))
    result = default_api.guessit(name, options=final_options)
    result['parsing_time'] = time() - start_time
    return result


def get_expected_titles(show_list):
    """Return expected titles to be used by guessit.

    It iterates over user's show list and only returns a regex for titles that contains numbers
    (since they can confuse guessit).

    :param show_list:
    :type show_list: list of medusa.tv.TVShow
    :return:
    :rtype: list of str
    """
    expected_titles = []
    for show in show_list:
        names = [show.name] + show.exceptions
        for name in names:
            if name.isdigit():
                # do not add numbers to expected titles.
                continue

            match = series_re.match(name)
            if not match:
                continue

            series, year, _ = match.groups()
            if year and not valid_year(int(year)):
                series = name

            if not any([char.isdigit() for char in series]):
                continue

            expected_titles.append(series)

    return expected_titles
