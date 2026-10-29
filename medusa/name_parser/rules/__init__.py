#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Guessit customization."""
from __future__ import unicode_literals

from guessit.api import default_api

from medusa.name_parser.rules.expected_patch import apply_expected_value_patch
from medusa.name_parser.rules.properties import (
    blacklist,
    container,
    other,
    screen_size,
    source
)
from medusa.name_parser.rules.rules import rules

# Must run before configure() rebuilds title/release_group expected matchers.
apply_expected_value_patch()

default_api.configure({}, force=True)
default_api.rebulk.rebulk(blacklist())
default_api.rebulk.rebulk(source())
default_api.rebulk.rebulk(screen_size())
default_api.rebulk.rebulk(other())
default_api.rebulk.rebulk(container())
default_api.rebulk.rebulk(rules())
