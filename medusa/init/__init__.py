# coding=utf-8
"""First modules to initialize."""
from . import filesystem, misc


def initialize():
    """Initialize all required modules."""
    filesystem.initialize()
    misc.initialize()
