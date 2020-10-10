#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Guessit Name Parser."""
from __future__ import unicode_literals

import re
from datetime import timedelta
from time import time

from medusa import app
from medusa.name_parser.rules import default_api


EXPECTED_TITLES_EXPIRATION_TIME = timedelta(days=1).total_seconds()

# release group exception list
expected_groups = [
    # release groups with numbers
    'TV2LAX9',

    # episode titles in the wrong place
    'DHD',

    # The.Good.Wife.Season.6.480p.HDTV.H264-20-40.WEB-DL
    '20-40',

    # Scene release group confused with episode.
    'E7',
]

allowed_languages = [
    'de',
    'en',
    'es',
    'ca',
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
    'mul',  # multi language
    'und',  # undetermined
]

allowed_countries = [
    'us',
    'gb',
]

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
    or dashes (since they can confuse guessit).

    :param show_list:
    :type show_list: list of medusa.tv.Series
    :return:
    :rtype: list of str
    """
    expected_titles = []
    for show in show_list:
        exceptions = {show.name}.union({alias.title for alias in show.aliases})
        for exception in exceptions:
            if exception.isdigit():
                # do not add numbers to expected titles.
                continue

            match = series_re.match(exception)
            if not match:
                continue

            if not any(char.isdigit() or char == '-' for char in exception):
                continue

            expected_titles.append(exception)

    return expected_titles
