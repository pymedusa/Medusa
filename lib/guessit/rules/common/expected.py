#!/usr/bin/env python
"""
Expected property factory
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rebulk import Rebulk
from rebulk.remodule import re
from rebulk.utils import find_all

from . import dash, seps

if TYPE_CHECKING:
    from collections.abc import Callable


def build_expected_function(context_key: str) -> Callable[[str, dict[str, Any]], list[Any]]:
    """
    Creates a expected property function
    :param context_key:
    :type context_key:
    :param cleanup:
    :type cleanup:
    :return:
    :rtype:
    """

    def expected(input_string: str, context: dict[str, Any]) -> list[Any]:
        """
        Expected property functional pattern.
        :param input_string:
        :type input_string:
        :param context:
        :type context:
        :return:
        :rtype:
        """
        ret: list[Any] = []
        for search in context.get(context_key) or ():
            if search.startswith("re:"):
                search = search[3:]
                search = search.replace(" ", "-")
                matches = (
                    Rebulk().regex(search, abbreviations=[dash], flags=re.IGNORECASE).matches(input_string, context)
                )
                for match in matches:
                    ret.append(match.span)
            else:
                # Preserve the original expected value (e.g. "11.22.63", "R-15",
                # "20-40"). GuessIt 4.x used the separator-normalized substring as
                # value, which replaced punctuation with spaces and broke Medusa's
                # expected_title / expected_group matching. Restore the GuessIt 3.x
                # behavior: match on a normalized copy, keep the original search
                # string as Match.value (Rebulk skips formatters when value is set).
                value = search
                for sep in seps:
                    input_string = input_string.replace(sep, " ")
                    search = search.replace(sep, " ")
                for start in find_all(input_string, search, ignore_case=True):
                    ret.append({"start": start, "end": start + len(search), "value": value})
        return ret

    return expected
