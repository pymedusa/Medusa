# coding=utf-8
"""Series name comparison helpers for GuessIt integration."""
from __future__ import unicode_literals

import unicodedata

from medusa.helpers import full_sanitize_scene_name


def normalize_series_name_for_comparison(name):
    """Normalize a series title for equality checks only.

    GuessIt 4 may return more accurate punctuation than GuessIt 3
    (``11.22.63``, ``R-15``, ``9-1-1``). Keep those raw values in parser
    output; use this helper when matching against the library or aliases.

    Applies Unicode NFKD (strip combining marks) then
    :func:`medusa.helpers.full_sanitize_scene_name`, which folds case, dots,
    hyphens and ordinary separators for scene matching.
    """
    if not name:
        return ''

    decomposed = unicodedata.normalize('NFKD', name)
    without_marks = ''.join(
        char for char in decomposed
        if not unicodedata.combining(char)
    )
    return full_sanitize_scene_name(without_marks)
