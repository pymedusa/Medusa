# -*- coding: utf-8 -*-
"""A wrapper for the Trakt.tv REST API"""
try:
    from trakt.core import *  # NOQA
except ImportError:
    pass

from .__version__ import __version__

__author__ = 'Jon Nappi, Elan Ruusamäe'
