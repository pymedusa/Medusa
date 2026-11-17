#!/usr/bin/env python
"""
Extracts as much information as possible from a video file.
"""

from . import monkeypatch as _monkeypatch
from .__version__ import __version__
from .api import GuessItApi, guessit
from .options import ConfigurationException
from .rules.common.quantity import Size
from .schema import GUESSIT_SCHEMA

__all__ = ["GUESSIT_SCHEMA", "ConfigurationException", "GuessItApi", "Size", "__version__", "guessit"]

_monkeypatch.monkeypatch_rebulk()
