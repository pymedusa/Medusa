#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Properties: This section contains additional properties to be guessed by guessit."""
from __future__ import unicode_literals

import re

from guessit.reutils import build_or_pattern
from guessit.rules.common import dash
from guessit.rules.common.validators import seps_surround

from rebulk.processors import POST_PROCESS
from rebulk.rebulk import Rebulk
from rebulk.rules import RemoveMatch, Rule

import six


def blacklist():
    """Blacklisted patterns.

    All blacklisted patterns.
    :return:
    :rtype: Rebulk
    """
    rebulk = Rebulk().regex_defaults(flags=re.IGNORECASE, abbreviations=[dash])
    rebulk.defaults(name='blacklist', validator=seps_surround,
                    conflict_solver=lambda match, other: other if other.name != 'blacklist' else '__default__')

    rebulk.regex(r'(?:(?:\[\d+/\d+\])-+)?\.".+".*', tags=['blacklist-01'])
    rebulk.regex(r'vol\d{2,3}\+\d{2,3}.*', tags=['blacklist-02'])
    rebulk.regex(r'(?:nzb|par2)-+\d+\.of\.\d+.*', tags=['blacklist-03'])
    rebulk.regex(r'(?:(?:nzb|par2)-+)?\d+\.of\.\d+.*', tags=['blacklist-03', 'should-have-container-before'])

    rebulk.rules(ValidateBlacklist, RemoveBlacklisted)

    return rebulk


def source():
    """Source property.

    :return:
    :rtype: Rebulk
    """
    rebulk = Rebulk().regex_defaults(flags=re.IGNORECASE, abbreviations=[dash])
    rebulk.defaults(name='source', tags='video-codec-prefix')

    # More accurate sources
    rebulk.regex('BD-?Rip', 'BD(?=-?Mux)', value='BDRip',
                 conflict_solver=lambda match, other: other if other.name == 'source' else '__default__')
    rebulk.regex(r'BD(?!\d)', value='BDRip', validator=seps_surround,
                 conflict_solver=lambda match, other: other if other.name == 'source' else '__default__')
    rebulk.regex('BR-?Rip', 'BR(?=-?Mux)', value='BRRip',
                 conflict_solver=lambda match, other: other if other.name == 'source' else '__default__')
    rebulk.regex('DVD-?Rip', value='DVDRip',
                 conflict_solver=lambda match, other: other if other.name == 'source' else '__default__')

    rebulk.regex(r'DVD\d', value='DVD')

    return rebulk


def screen_size():
    """Screen size property.

    :return:
    :rtype: Rebulk
    """
    rebulk = Rebulk().regex_defaults(flags=re.IGNORECASE)
    rebulk.defaults(name='screen_size', validator=seps_surround)

    # Discarded:
    rebulk.regex(r'(?:\d{3,}(?:x|\*))?4320(?:p?x?)', value='4320p', private=True)

    return rebulk


def other():
    """Other property.

    :return:
    :rtype: Rebulk
    """
    rebulk = Rebulk().regex_defaults(flags=re.IGNORECASE, abbreviations=[dash])
    rebulk.defaults(name='other', validator=seps_surround)

    rebulk.regex('F1', value='Formula One',
                 conflict_solver=lambda match, other: other if other.name == 'film' else '__default__')

    # Discarded:
    rebulk.regex('DownRev', 'small-size', private=True)

    return rebulk


def container():
    """Builder for rebulk object.

    :return: Created Rebulk object
    :rtype: Rebulk
    """
    rebulk = Rebulk().regex_defaults(flags=re.IGNORECASE).string_defaults(ignore_case=True)
    rebulk.defaults(name='container',
                    tags=['extension'],
                    conflict_solver=lambda match, other: other
                    if other.name in ['source', 'video_codec'] or
                    other.name == 'container' and 'extension' not in other.tags
                    else '__default__')

    if six.PY3:
        nzb = ['nzb']
    else:
        nzb = [b'nzb']

    rebulk.regex(r'\.' + build_or_pattern(nzb) + '$', exts=nzb, tags=['extension', 'torrent'])

    rebulk.defaults(name='container',
                    validator=seps_surround,
                    formatter=lambda s: s.upper(),
                    conflict_solver=lambda match, other: match
                    if other.name in ['source', 'video_codec'] or
                    other.name == 'container' and 'extension' in other.tags
                    else '__default__')

    rebulk.string(*nzb, tags=['nzb'])

    return rebulk


class ValidateBlacklist(Rule):
    """Validate blacklist pattern 03. It should appear after a container."""

    priority = 10000
    consequence = RemoveMatch

    def when(self, matches, context):
        """Remove blacklist if it doesn't appear after a container.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        to_remove = []
        for bl in matches.tagged('should-have-container-before'):
            if not matches.previous(bl, predicate=lambda match: match.name == 'container', index=0):
                to_remove.append(bl)

        return to_remove


class RemoveBlacklisted(Rule):
    """Remove blacklisted properties from final result."""

    priority = POST_PROCESS - 9000
    consequence = RemoveMatch

    def when(self, matches, context):
        """Remove blacklisted properties.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        return matches.named('blacklist')
