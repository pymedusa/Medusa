#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Properties: This section contains additional properties to be guessed by guessit."""
import re

import babelfish
from guessit.reutils import build_or_pattern
from guessit.rules.common import alt_dash, dash
from guessit.rules.common.validators import seps, seps_surround
from rebulk.processors import POST_PROCESS
from rebulk.rebulk import Rebulk
from rebulk.rules import RemoveMatch, Rule


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


def format_():
    """Format property.

    :return:
    :rtype: Rebulk
    """
    rebulk = Rebulk().regex_defaults(flags=re.IGNORECASE, abbreviations=[dash])
    rebulk.defaults(name='format')

    # More accurate formats
    rebulk.regex('AHDTV', value='AHDTV')
    rebulk.regex('BD(?!\d)', 'BD-?Rip', 'BD-?Mux', 'BD-?Rip-?Mux',
                 value='BDRip', validator=seps_surround,
                 conflict_solver=lambda match, other: other if other.name == 'format' else '__default__')
    rebulk.regex('BR-?Rip', 'BR-?Mux', 'BR-?Rip-?Mux',
                 value='BRRip',
                 conflict_solver=lambda match, other: other if other.name == 'format' else '__default__')
    rebulk.regex('DVD-?Rip', value='DVDRip',
                 conflict_solver=lambda match, other: other if other.name == 'format' else '__default__')

    # https://github.com/guessit-io/guessit/issues/307
    rebulk.regex('HDTV-?Mux', value='HDTV')
    rebulk.regex('Blu-?ray-?Mux', value='BluRay')
    rebulk.regex('DVD-?Mux', value='DVD')
    rebulk.regex('WEB-?Mux', 'DL-?WEB-?Mux', 'WEB-?DL-?Mux', 'DL-?Mux', value='WEB-DL')

    # https://github.com/guessit-io/guessit/issues/315
    rebulk.regex('WEB-?DL-?Rip', 'WEB-?Cap', value='WEBRip')
    rebulk.regex('DSR', 'DS-?Rip', 'SAT-?Rip', 'DTH-?Rip', value='SATRip')
    rebulk.regex('LDTV', value='TV')
    rebulk.regex('DVD\d', value='DVD')

    return rebulk


def screen_size():
    """Screen size property.

    :return:
    :rtype: Rebulk
    """
    rebulk = Rebulk().regex_defaults(flags=re.IGNORECASE)
    rebulk.defaults(name='screen_size', validator=seps_surround)

    rebulk.regex('NetflixUHD', value='2160p')
    rebulk.regex(r'(?:\d{3,}(?:x|\*))?4320(?:p?x?)', value='4320p')

    return rebulk


def other():
    """Other property.

    :return:
    :rtype: Rebulk
    """
    rebulk = Rebulk().regex_defaults(flags=re.IGNORECASE, abbreviations=[dash])
    rebulk.defaults(name='other', validator=seps_surround)

    # https://github.com/guessit-io/guessit/issues/300
    rebulk.regex(r'Re-?Enc(?:oded)?', value='Re-Encoded')

    rebulk.regex('DIRFIX', value='DirFix')
    rebulk.regex('INTERNAL', value='Internal')
    rebulk.regex(r'(?:HD)?iTunes(?:HD)?', value='iTunes')
    rebulk.regex(r'UNCENSORED', value='Uncensored')
    rebulk.regex('HC', value='Hardcoded subtitles')

    # Discarded:
    rebulk.regex('DownRev', 'small-size', private=True)

    rebulk.rules(ValidateHardcodedSubs)

    return rebulk


def network():
    """Network property.

    :return:
    :rtype: Rebulk
    """
    rebulk = Rebulk().regex_defaults(flags=re.IGNORECASE, abbreviations=[dash])
    rebulk.defaults(name='network', validator=seps_surround)

    # https://github.com/guessit-io/guessit/issues/344
    rebulk.regex(r'AE', value='A&E')
    rebulk.regex(r'AMBC', value='ABC')
    rebulk.regex(r'AMZN', value='Amazon Prime')
    rebulk.regex(r'AS', value='Adult Swim')
    rebulk.regex(r'iP', value='BBC iPlayer')
    rebulk.regex(r'CBS', value='CBS')
    rebulk.regex(r'CC', value='Comedy Central',
                 conflict_solver=lambda match, other: other if other.name == 'other' else '__default__')
    rebulk.regex(r'CR', value='Crunchy Roll')
    rebulk.regex(r'CW', value='The CW')
    rebulk.regex(r'DISC', value='Discovery')
    rebulk.regex(r'DSNY', value='Disney')
    rebulk.regex(r'EPIX', value='ePix')
    rebulk.regex(r'HBO', value='HBO Go')
    rebulk.regex(r'HIST', value='History')
    rebulk.regex(r'IFC', value='IFC')
    rebulk.regex(r'PBS', value='PBS')
    rebulk.regex(r'NATG', value='National Geographic')
    rebulk.regex(r'NBA', value='NBA TV')
    rebulk.regex(r'NBC', value='NBC')
    rebulk.regex(r'NFL', value='NFL')
    rebulk.regex(r'NICK', value='Nickelodeon')
    rebulk.regex(r'NF', value='Netflix',
                 conflict_solver=lambda match, other: other if other.name == 'other' else '__default__')
    rebulk.regex(r'SESO', value='SeeSo')
    rebulk.regex(r'SPKE', value='Spike TV')
    rebulk.regex(r'SYFY', value='Syfy')
    rebulk.regex(r'TFOU', value='TFou')
    rebulk.regex(r'TVL', value='TV Land')
    rebulk.regex(r'UFC', value='UFC')

    rebulk.rules(ValidateNetwork)

    return rebulk


def size():
    """Size property.

    Remove when https://github.com/guessit-io/guessit/issues/299 is fixed.
    :return:
    :rtype: Rebulk
    """
    def format_size(value):
        return re.sub(r'(?<=\d)[\.](?=[^\d])', '', value.upper())

    rebulk = Rebulk().regex_defaults(flags=re.IGNORECASE, abbreviations=[dash])
    rebulk.defaults(name='size', validator=seps_surround)
    rebulk.regex(r'\d+\.?[mgt]b', r'\d+\.\d+[mgt]b', formatter=format_size, tags=['release-group-prefix'])

    return rebulk


def language():
    """Language property.

    :return:
    :rtype: Rebulk
    """
    rebulk = Rebulk().regex_defaults(flags=re.IGNORECASE, abbreviations=[dash])
    rebulk.defaults(name='language', validator=seps_surround)
    rebulk.regex('SPANISH-?AUDIO', r'(?:Espa[.]ol-)?castellano', value=babelfish.Language('spa'))
    rebulk.regex('german-dubbed', 'dubbed-german', value=babelfish.Language('deu'))
    rebulk.regex('english-dubbed', value=babelfish.Language('eng'))
    rebulk.regex('dublado', value='und', formatter=babelfish.Language)

    return rebulk


def subtitle_language():
    """Subtitle language property.

    :return:
    :rtype: Rebulk
    """
    rebulk = Rebulk().regex_defaults(flags=re.IGNORECASE | re.UNICODE, abbreviations=[alt_dash])
    rebulk.defaults(name='subtitle_language', validator=seps_surround)

    # special handling
    rebulk.regex(r'Legenda(?:s|do)?@PT-?BR', value=babelfish.Language('por', 'BR'))
    rebulk.regex(r'Legenda(?:s|do)?@PT(?!-?BR)', value=babelfish.Language('por'))
    rebulk.regex('Subtitulado@ESP(?:a[nñ]ol)?@Spanish', 'Subtitulado@ESP(?:a[nñ]ol)?', value=babelfish.Language('spa'),
                 conflict_solver=lambda match, other: other if other.name == 'language' else '__default__')

    # undefined language
    rebulk.regex('Subtitles', 'Legenda(?:s|do)', 'Subbed', 'Sub(?:title)?s?@Latino',
                 value='und', formatter=babelfish.Language, tags='subtitle.undefined')

    rebulk.rules(RemoveSubtitleUndefined)

    return rebulk


def container():
    """Builder for rebulk object.

    :return: Created Rebulk object
    :rtype: Rebulk
    """
    rebulk = Rebulk().regex_defaults(flags=re.IGNORECASE).string_defaults(ignore_case=True)
    rebulk.defaults(name='container',
                    formatter=lambda value: value[1:],
                    tags=['extension'],
                    conflict_solver=lambda match, other: other
                    if other.name in ['format', 'video_codec'] or
                    other.name == 'container' and 'extension' not in other.tags
                    else '__default__')

    nzb = ['nzb']

    rebulk.regex(r'\.' + build_or_pattern(nzb) + '$', exts=nzb, tags=['extension', 'torrent'])

    rebulk.defaults(name='container',
                    validator=seps_surround,
                    formatter=lambda s: s.upper(),
                    conflict_solver=lambda match, other: match
                    if other.name in ['format',
                                      'video_codec'] or other.name == 'container' and 'extension' in other.tags
                    else '__default__')

    rebulk.string(*nzb, tags=['nzb'])

    return rebulk


class ValidateHardcodedSubs(Rule):
    """Validate HC matches."""

    priority = 32
    consequence = RemoveMatch

    def when(self, matches, context):
        """Remove `other: Hardcoded subtitles` if there's no subtitle_language matches as a neighbour.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        to_remove = []
        for hc in matches.named('other', predicate=lambda match: match.value == 'Hardcoded subtitles'):
            next_match = matches.next(hc, predicate=lambda match: match.name == 'subtitle_language', index=0)
            if next_match and not matches.holes(hc.end, next_match.start,
                                                predicate=lambda match: match.value.strip(seps)):
                continue

            previous_match = matches.previous(hc, predicate=lambda match: match.name == 'subtitle_language', index=0)
            if previous_match and not matches.holes(previous_match.end, hc.start,
                                                    predicate=lambda match: match.value.strip(seps)):
                continue

            to_remove.append(hc)

        return to_remove


class ValidateNetwork(Rule):
    """Validate network matches."""

    priority = 32
    consequence = RemoveMatch

    def when(self, matches, context):
        """Network is always after screen_size and before format.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        to_remove = []
        for nw in matches.named('network'):
            next_match = matches.next(nw, predicate=lambda match: match.name == 'format', index=0)
            if next_match and not matches.holes(nw.end, next_match.start,
                                                predicate=lambda match: match.value.strip(seps)):
                continue

            previous_match = matches.previous(nw, predicate=lambda match: match.name == 'screen_size', index=0)
            if previous_match and not matches.holes(previous_match.end, nw.start,
                                                    predicate=lambda match: match.value.strip(seps)):
                continue

            to_remove.append(nw)

        return to_remove


class RemoveSubtitleUndefined(Rule):
    """Remove subtitle undefined when there's an actual subtitle language."""

    priority = POST_PROCESS - 1000
    consequence = RemoveMatch

    def when(self, matches, context):
        """Remove subtitle undefined if there's a subtitle language as a neighbor.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        to_remove = []
        for und in matches.tagged('subtitle.undefined'):
            next_match = matches.next(und, predicate=lambda match: match.name == 'subtitle_language', index=0)
            if not next_match or matches.holes(und.end, next_match.start,
                                               predicate=lambda match: match.value.strip(seps)):
                previous_match = matches.previous(und,
                                                  predicate=lambda match: match.name == 'subtitle_language', index=0)
                if not previous_match or matches.holes(previous_match.end, und.start,
                                                       predicate=lambda match: match.value.strip(seps)):
                    continue

            to_remove.append(und)

        return to_remove


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
