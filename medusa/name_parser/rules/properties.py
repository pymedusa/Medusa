#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Properties: This section contains additional properties to be guessed by guessit."""
import re

import babelfish
from guessit.reutils import build_or_pattern
from guessit.rules.common import alt_dash, dash
from guessit.rules.common.validators import seps, seps_surround
from guessit.rules.properties.audio_codec import Ac3Rule, AudioValidatorRule, HqConflictRule
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

    rebulk.regex('DVD\d', value='DVD')

    return rebulk


def audio_codec():
    """Audio codec property.

    :return:
    :rtype: Rebulk
    """
    rebulk = Rebulk().regex_defaults(name='audio_codec', flags=re.IGNORECASE)
    rebulk.regex(r'DDP', value='AC3')
    rebulk.rules(Ac3Rule, AudioValidatorRule, HqConflictRule)

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
    rebulk.regex(r'MULTi', value='Multi Language')
    rebulk.regex('HC', value='Hardcoded subtitles')

    # Discarded:
    rebulk.regex('DownRev', 'small-size', private=True)

    rebulk.rules(ValidateHardcodedSubs)

    return rebulk


def streaming_service():
    """Streaming service property.

    :return:
    :rtype: Rebulk
    """
    rebulk = Rebulk().string_defaults(ignore_case=True)
    rebulk.defaults(name='streaming_service', validator=seps_surround)

    rebulk.string('AE', value='A&E')
    rebulk.string('AMBC', value='ABC')
    rebulk.string('AMZN', value='Amazon Prime')
    rebulk.string('AS', value='Adult Swim')
    rebulk.string('iP', value='BBC iPlayer')
    rebulk.string('CBS', value='CBS')
    rebulk.string('CC', value='Comedy Central',
                  conflict_solver=lambda match, other: other if other.name == 'other' else '__default__')
    rebulk.string('CR', value='Crunchy Roll')
    rebulk.string('CW', value='The CW')
    rebulk.string('DISC', value='Discovery')
    rebulk.string('DSNY', value='Disney')
    rebulk.string('EPIX', value='ePix')
    rebulk.string('HBO', value='HBO Go')
    rebulk.string('HIST', value='History')
    rebulk.string('IFC', value='IFC')
    rebulk.string('PBS', value='PBS')
    rebulk.string('NATG', value='National Geographic')
    rebulk.string('NBA', value='NBA TV')
    rebulk.string('NBC', value='NBC')
    rebulk.string('NFL', value='NFL')
    rebulk.string('NICK', value='Nickelodeon')
    rebulk.string('NF', value='Netflix',
                  conflict_solver=lambda match, other: other if other.name == 'other' else '__default__')
    rebulk.string('SESO', value='SeeSo')
    rebulk.string('SPKE', value='Spike TV')
    rebulk.string('SYFY', value='Syfy')
    rebulk.string('TFOU', value='TFou')
    rebulk.string('TVL', value='TV Land')
    rebulk.string('UFC', value='UFC')

    rebulk.rules(ValidateStreamingService)

    return rebulk


def size():
    """Size property.

    Remove when https://github.com/guessit-io/guessit/issues/299 is fixed.
    :return:
    :rtype: Rebulk
    """
    def format_size(value):
        return re.sub(r'(?<=\d)[.](?=[^\d])', '', value.upper())

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


class ValidateStreamingService(Rule):
    """Validate streaming service matches."""

    priority = 32
    consequence = RemoveMatch

    def when(self, matches, context):
        """Streaming service is always after screen_size and before format.

        :param matches:
        :type matches: rebulk.match.Matches
        :param context:
        :type context: dict
        :return:
        """
        to_remove = []
        for ss in matches.named('streaming_service'):
            next_match = matches.next(ss, predicate=lambda match: match.name == 'format', index=0)
            if next_match and not matches.holes(ss.end, next_match.start,
                                                predicate=lambda match: match.value.strip(seps)):
                continue

            previous_match = matches.previous(ss, predicate=lambda match: match.name == 'screen_size', index=0)
            if previous_match and not matches.holes(previous_match.end, ss.start,
                                                    predicate=lambda match: match.value.strip(seps)):
                continue

            to_remove.append(ss)

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
