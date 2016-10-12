# coding=utf-8
"""General encoding tests."""

from __future__ import print_function

import locale
import os.path
import unittest

import medusa as app
from medusa import ex
from medusa.helper.common import sanitize_filename
from six import text_type


class EncodingTests(unittest.TestCase):
    """Test encodings."""

    def test_encoding(self):
        root_dir = 'C:\\Temp\\TV'
        strings = [u'Les Enfants De La T\xe9l\xe9', u'RT� One']

        app.SYS_ENCODING = None

        try:
            locale.setlocale(locale.LC_ALL, "")
            app.SYS_ENCODING = locale.getpreferredencoding()
        except (locale.Error, IOError):
            pass

        # For OSes that are poorly configured I'll just randomly force UTF-8
        if not app.SYS_ENCODING or app.SYS_ENCODING in ('ANSI_X3.4-1968', 'US-ASCII', 'ASCII'):
            app.SYS_ENCODING = 'UTF-8'

        for test in strings:
            try:
                show_dir = os.path.join(root_dir, sanitize_filename(test))
                self.assertTrue(isinstance(show_dir, text_type))
            except Exception as error:  # pylint: disable=broad-except
                ex(error)
