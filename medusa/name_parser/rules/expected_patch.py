# coding=utf-8
"""Medusa patch for GuessIt expected_title / expected_group values."""
from __future__ import unicode_literals

from rebulk import Rebulk
from rebulk.remodule import re
from rebulk.utils import find_all

from guessit.rules.common import dash, seps


def build_expected_function(context_key):
    """Match loosely but keep the original expected string as Match.value.

    GuessIt 4.1.0 otherwise uses the separator-normalized substring as the value
    (``11.22.63`` -> ``11 22 63``). Medusa needs GuessIt 3.x semantics: punctuation
    from the expected search string is preserved (Rebulk skips formatters when
    value is set).

    Applied from :mod:`medusa.name_parser.rules` before ``default_api.configure``
    so a future vendoring of ``lib/guessit`` does not silently drop the fix.
    Consider proposing this behavior upstream.
    """

    def expected(input_string, context):
        ret = []
        for search in context.get(context_key) or ():
            if search.startswith('re:'):
                search = search[3:]
                search = search.replace(' ', '-')
                matches = (
                    Rebulk()
                    .regex(search, abbreviations=[dash], flags=re.IGNORECASE)
                    .matches(input_string, context)
                )
                for match in matches:
                    ret.append(match.span)
            else:
                value = search
                normalized_input = input_string
                normalized_search = search
                for sep in seps:
                    normalized_input = normalized_input.replace(sep, ' ')
                    normalized_search = normalized_search.replace(sep, ' ')
                for start in find_all(normalized_input, normalized_search, ignore_case=True):
                    ret.append({
                        'start': start,
                        'end': start + len(normalized_search),
                        'value': value,
                    })
        return ret

    return expected


def apply_expected_value_patch():
    """Patch GuessIt modules that bind ``build_expected_function`` at import time."""
    import guessit.rules.common.expected as expected_mod
    import guessit.rules.properties.release_group as release_group_mod
    import guessit.rules.properties.title as title_mod

    expected_mod.build_expected_function = build_expected_function
    title_mod.build_expected_function = build_expected_function
    release_group_mod.build_expected_function = build_expected_function
