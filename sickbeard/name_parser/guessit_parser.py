#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Guessit Name Parser."""
from __future__ import unicode_literals

import six

from guessit.api import default_api


expected_titles = {
    # guessit doesn't add dots for this show
    '11.22.63',

    # guessit gets confused because of the numbers (only in some special cases)
    # (?<![^/\\]) means -> it matches nothing but path separators  (negative lookbehind)
    r're:(?<![^/\\])12 Monkeys\b',
    r're:(?<![^/\\])500 Bus Stops\b',
    r're:(?<![^/\\])60 Minutes\b',
    r're:(?<![^/\\])Star Trek DS9\b',
    r're:(?<![^/\\])The 100\b',

    # guessit: conflicts with italian language
    r're:(?<![^/\\])\w+ it\b',
}

# release group exception list
expected_groups = {
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
}

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


def guessit(name, options):
    """Guess the episode information from a given release name.

    :param name: the release name
    :type name: str
    :param options:
    :type options: dict
    :return: the guessed properties
    :rtype: dict
    """
    final_options = dict(options)
    final_options.update(dict(type='episode', implicit=True,
                              episode_prefer_number=options.get('show_type') == 'anime',
                              expected_title=normalize(expected_titles),
                              expected_group=normalize(expected_groups),
                              allowed_languages=normalize(allowed_languages),
                              allowed_countries=normalize(allowed_countries)))
    return default_api.guessit(name, options=final_options)


def normalize(strings):
    """Normalize string as expected by guessit.

    Remove when https://github.com/guessit-io/guessit/issues/326 is fixed.
    :param strings:
    :rtype: list of str
    """
    result = []
    for string in strings:
        if six.PY2 and isinstance(string, six.text_type):
            string = string.encode('utf-8')
        elif six.PY3 and isinstance(string, six.binary_type):
            string = string.decode('ascii')
        result.append(string)
    return result
