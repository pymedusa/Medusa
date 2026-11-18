# coding=utf-8
"""Series name comparison helpers for GuessIt integration."""
from __future__ import unicode_literals

import re
import unicodedata

from medusa.helpers import full_sanitize_scene_name

# Optional plural marker in titles (e.g. ``Show Name(s)``). GuessIt often drops
# "(s)" as a release_group token; strip it before sanitize so library names still
# match the parsed title (``Name(s)`` must not become ``names``).
_OPTIONAL_PLURAL = re.compile(r'\([sS]\)')


def strip_optional_plural_marker(text):
    """Remove only the optional ``(s)`` / ``(S)`` marker; leave ordinary plurals intact."""
    if not text:
        return text
    return _OPTIONAL_PLURAL.sub('', text)


def normalize_series_name_for_comparison(name):
    """Normalize a series title for equality checks only.

    GuessIt 4 may return more accurate punctuation than GuessIt 3
    (``11.22.63``, ``R-15``, ``9-1-1``). Keep those raw values in parser
    output; use this helper when matching against the library or aliases.

    Applies Unicode NFKD (strip combining marks), removes optional ``(s)``
    plural markers, then :func:`medusa.helpers.full_sanitize_scene_name`, which
    folds case, dots, hyphens and ordinary separators for scene matching.
    """
    if not name:
        return ''

    decomposed = unicodedata.normalize('NFKD', name)
    without_marks = ''.join(
        char for char in decomposed
        if not unicodedata.combining(char)
    )
    without_optional_plural = strip_optional_plural_marker(without_marks)
    return full_sanitize_scene_name(without_optional_plural)
