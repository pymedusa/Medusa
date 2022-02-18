# coding=utf-8

"""Search module for all Medusa searches."""
from __future__ import unicode_literals

from enum import Enum

BACKLOG_SEARCH = 10
DAILY_SEARCH = 20
FAILED_SEARCH = 30
FORCED_SEARCH = 40
MANUAL_SEARCH = 50
PROPER_SEARCH = 60
SNATCH_RESULT = 70


class SearchType(Enum):
    """Enum with search types."""

    BACKLOG_SEARCH = 10
    DAILY_SEARCH = 20
    FAILED_SEARCH = 30
    FORCED_SEARCH = 40
    MANUAL_SEARCH = 50
    PROPER_SEARCH = 60
