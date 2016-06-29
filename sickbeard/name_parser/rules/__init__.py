#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Guessit customization
"""
from guessit.api import default_api
from sickbeard.name_parser.rules.properties import (audio_codec, blacklist, format_, language, other, size, screen_size,
                                                    subtitle_language)
from sickbeard.name_parser.rules.rules import rules


default_api.rebulk.rebulk(blacklist())
default_api.rebulk.rebulk(format_())
default_api.rebulk.rebulk(screen_size())
default_api.rebulk.rebulk(audio_codec())
default_api.rebulk.rebulk(other())
default_api.rebulk.rebulk(size())
default_api.rebulk.rebulk(language())
default_api.rebulk.rebulk(subtitle_language())
default_api.rebulk.rebulk(rules())
