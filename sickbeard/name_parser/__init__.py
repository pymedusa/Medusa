# coding=utf-8
"""Name Parser module.

Replace guessit function with a pre-configured one, so guessit.guessit() could be called directly in any place.
"""
import guessit

from guessit_parser import guessit as pre_configured_guessit

guessit.guessit = pre_configured_guessit
