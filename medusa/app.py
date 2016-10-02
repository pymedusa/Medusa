# coding=utf-8
"""First module to initialize."""
import guessit

from .name_parser.guessit_parser import guessit as pre_configured_guessit

# Replace standard modules/functions by our custom ones

# Replace guessit function with a pre-configured one, so guessit.guessit() could be called directly in any place.
guessit.guessit = pre_configured_guessit
