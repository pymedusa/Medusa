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


def _prefer_over_polluted(match, other):
    """Keep broadcast/duration tags over mistaken release_group or alternative_title."""
    if other.name in ('release_group', 'alternative_title'):
        return match
    return '__default__'


def duration():
    """Parse broadcast-style runtimes such as ``42m35s`` or ``1h05m``.

    GuessIt has no duration property; these tokens often become release_group.
    """
    rebulk = Rebulk().regex_defaults(flags=re.IGNORECASE)
    rebulk.defaults(
        name='duration',
        validator=seps_surround,
        conflict_solver=_prefer_over_polluted,
    )
    rebulk.regex(
        r'(?P<value>\d{1,2}h\d{1,2}m|\d{1,3}m\d{1,2}s)',
        formatter=lambda value: value.lower(),
    )
    return rebulk


def broadcast_channel():
    """Parse common FR/EU broadcast channel tokens from rip filenames.

    Matched as ``broadcast_channel`` so GuessIt's ``ValidateStreamingService``
    does not strip standalone names like ``ARTE``. A POST_PROCESS rule renames
    them to ``streaming_service`` for Medusa consumers.
    """
    rebulk = Rebulk().string_defaults(ignore_case=True).regex_defaults(
        flags=re.IGNORECASE, abbreviations=[dash]
    )
    rebulk.defaults(
        name='broadcast_channel',
        validator=seps_surround,
        conflict_solver=_prefer_over_polluted,
        tags=['medusa-broadcast-channel'],
    )

    rebulk.string('ARTE', value='ARTE')
    rebulk.string('TF1', value='TF1')
    rebulk.string('M6', value='M6')
    rebulk.string('C8', value='C8')
    rebulk.string('TMC', value='TMC')
    rebulk.string('W9', value='W9')
    rebulk.string('Gulli', value='Gulli')
    rebulk.string('FranceTV', 'France TV', value='FranceTV')
    rebulk.string('France 2', 'France2', 'France-2', value='France 2')
    rebulk.string('France 3', 'France3', 'France-3', value='France 3')
    rebulk.string('France 4', 'France4', 'France-4', value='France 4')
    rebulk.string('France 5', 'France5', 'France-5', 'Fr5', 'Fr 5', value='France 5')
    rebulk.string('Canal+', 'CanalPlus', 'Canal Plus', value='Canal+')

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
