# coding=utf-8
"""Api v2 tests."""
from __future__ import unicode_literals

import os
import sys

import six

# Start event loop in python3
if six.PY3:
    import asyncio

    # We need to set the WindowsSelectorEventLoop event loop on python 3 (3.8 and higher) running on windows
    if sys.platform == 'win32':
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError:  # Only available since Python 3.7.0
            pass

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../lib')))
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ext')))
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
