# coding=utf-8
"""Replace guessit functions."""

import guessit
from ..name_parser.guessit_parser import guessit as pre_configured_guessit


def initialize():
    """Replace guessit function with a pre-configured one, so guessit.guessit() could be called directly in any place."""
    guessit.guessit = pre_configured_guessit
