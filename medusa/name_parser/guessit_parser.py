#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Guessit Name Parser."""
from __future__ import unicode_literals

import logging
import re
from datetime import timedelta
from time import time

from medusa import app
from medusa.logger.adapters.style import BraceAdapter
from medusa.name_parser.cache import BaseCache
from medusa.name_parser.rules import default_api

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

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

series_re = re.compile(r'^(?P<series>.*?)(?: ?(?:(?P<year>\(\d{4}\))|(?P<country>[A-Z]{2}))?)?$')


def guessit(name, options=None, cached=True):
    """Guess the episode information from a given release name.

    :param name: the release name
    :type name: str
    :param options:
    :type options: dict
    :param cached:
    :type cached: Boolean
    :return: the guessed properties
    :rtype: dict
    """
    start_time = time()
    final_options = dict(options) if options else dict(show_type='normal')
    final_options.update(dict(type='episode', implicit=True,
                              episode_prefer_number=final_options.get('show_type') == 'anime',
                              expected_title=get_expected_titles(app.showList),
                              expected_group=expected_groups,
                              allowed_languages=allowed_languages,
                              allowed_countries=allowed_countries))

    result = None
    if cached:
        result = guessit_cache.get_or_invalidate(name, final_options)
    if not result:
        log.debug('New guessit parse for item {name}', {'name': name})
        result = default_api.guessit(name, options=final_options)
        # We don't want to cache at this point. As this is a bare guessit result.
        # Meaning we haven't been able to calculate any season scene exception at this point.

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
        show_title = show.name
        exceptions = {alias.title for alias in show.aliases}
        for exception in exceptions:
            # Do not add only numbers to expected titles.
            if exception.isdigit():
                continue

            match = series_re.match(exception)
            if not match:
                continue

            # Add when show exception has a year (without brackets),
            # a number or '-' in its title.
            if any(char.isdigit() or char == '-' for char in match.group(1)):
                expected_titles.append(exception)
                continue

            # Add when show name is the same as exception,
            # to allow an explicit match.
            if show_title.casefold() == exception.casefold():
                expected_titles.append(exception)
                continue

        # Do not add only numbers to expected titles.
        if show_title.isdigit():
            continue

        match = series_re.match(show_title)
        if not match:
            continue

        # Add when show exception has a year (without brackets),
        # a number or '-' in its title.
        if any(char.isdigit() or char == '-' for char in match.group(1)):
            expected_titles.append(show_title)
            continue

    return expected_titles


class GuessItCache(BaseCache):
    """GuessIt cache."""

    def __init__(self):
        """Initialize the cache with a maximum size."""
        super().__init__(25000)
        self.invalidation_object = None

    def get_or_invalidate(self, name, obj):
        """Return an item from the cache if the obj matches the previous invalidation object. Clears the cache and returns None if not."""
        if not self.invalidation_object:
            self.invalidation_object = obj

        if self.invalidation_object == obj:
            log.debug('Trying guessit cache for item {name}', {'name': name})
            return self.get(name)

        log.debug('GuessIt cache was cleared due to invalidation object change: previous={previous} new={new}',
                  {'previous': self.invalidation_object, 'new': obj})
        self.invalidation_object = obj
        self.clear()
        return None


guessit_cache = GuessItCache()
