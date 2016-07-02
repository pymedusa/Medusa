#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Properties: This section contains additional properties to be guessed by guessit
"""
import re
from string import upper

import babelfish
from guessit.rules.common import dash, alt_dash
from guessit.rules.common.validators import seps, seps_surround
from rebulk.rebulk import Rebulk
from rebulk.rules import Rule, RemoveMatch


def blacklist():
    """
    :return:
    :rtype: Rebulk
    """
    rebulk = Rebulk().regex_defaults(flags=re.IGNORECASE, abbreviations=[dash])
    rebulk.defaults(name='other', private=True)
    rebulk.regex('DownRev', 'small-size')

    return rebulk


def format_():
    """
    :return:
    :rtype: Rebulk
    """
    rebulk = Rebulk().regex_defaults(flags=re.IGNORECASE, abbreviations=[dash])
    rebulk.defaults(name='format')

    # https://github.com/guessit-io/guessit/issues/307
    rebulk.regex('HDTV-?Mux', value='HDTV')
    rebulk.regex('B[RD]-?Mux', 'Blu-?ray-?Mux', value='BluRay')
    rebulk.regex('DVD-?Mux', value='DVD')
    rebulk.regex('WEB-?Mux', 'DL-?WEB-?Mux', 'WEB-?DL-?Mux', 'DL-?Mux', value='WEB-DL')

    # https://github.com/guessit-io/guessit/issues/315
    rebulk.regex('WEB-?DL-?Rip', value='WEBRip')
    rebulk.regex('WEB-?Cap', value='WEBCap')
    rebulk.regex('DSR', 'DS-?Rip', 'SAT-?Rip', 'DTH-?Rip', value='DSRip')
    rebulk.regex('LDTV', value='TV')
    rebulk.regex('DVD\d', value='DVD')

    return rebulk


def screen_size():
    """
    :return:
    :rtype: Rebulk
    """

    # https://github.com/guessit-io/guessit/issues/319
    rebulk = Rebulk().regex_defaults(flags=re.IGNORECASE)
    rebulk.defaults(name='screen_size', validator=seps_surround)
    rebulk.regex(r'(?:\d{3,}(?:x|\*))?720phd', value='720p')
    rebulk.regex(r'(?:\d{3,}(?:x|\*))?1080phd', value='1080p')

    rebulk.regex('NetflixUHD', value='4k')

    return rebulk


def audio_codec():
    """
    :return:
    :rtype: Rebulk
    """
    rebulk = Rebulk().regex_defaults(flags=re.IGNORECASE, abbreviations=[dash]).string_defaults(ignore_case=True)
    rebulk.defaults(name='audio_codec')

    #rebulk.regex('Dolby', value='DolbyDigital')

    return rebulk


def other():
    """
    https://github.com/guessit-io/guessit/issues/300
    :return:
    :rtype: Rebulk
    """
    rebulk = Rebulk().regex_defaults(flags=re.IGNORECASE, abbreviations=[dash])
    rebulk.defaults(name='other', validator=seps_surround)
    rebulk.regex(r'Re-?Enc(?:oded)?', value='Re-Encoded')
    rebulk.regex('DIRFIX', value='DirFix')
    rebulk.regex('INTERNAL', value='Internal')
    rebulk.regex(r'(?:HD)?iTunes(?:HD)?', value='iTunes')
    rebulk.regex('HC', value='Hardcoded subtitles')

    rebulk.rules(ValidateHardcodedSubs)

    return rebulk


def size():
    """
    https://github.com/guessit-io/guessit/issues/299
    :return:
    :rtype: Rebulk
    """
    rebulk = Rebulk().regex_defaults(flags=re.IGNORECASE, abbreviations=[dash])
    rebulk.defaults(name='size', validator=seps_surround)
    rebulk.regex(r'(?:\d+\.)?\d+[mgt]b', formatter=upper)

    return rebulk


def language():
    """
    :return:
    :rtype: Rebulk
    """
    rebulk = Rebulk().regex_defaults(flags=re.IGNORECASE, abbreviations=[dash])
    rebulk.defaults(name='language', validator=seps_surround)
    rebulk.regex('SPANISH-?AUDIO', r'(?:Espa[.]ol-)?castellano', value=babelfish.Language('spa'))
    rebulk.regex('german-dubbed', 'dubbed-german', value=babelfish.Language('deu'))
    rebulk.regex('dublado', value='und', formatter=babelfish.Language)

    return rebulk


def subtitle_language():
    """
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
                 value='und', formatter=babelfish.Language)

    return rebulk


class ValidateHardcodedSubs(Rule):
    priority = 32
    consequence = RemoveMatch

    def when(self, matches, context):
        """
        Removes other: Hardcoded subtitles if there's no neighbour subtitle_language matches

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

            to_remove.append(other)

        return to_remove
