# coding=utf-8

from __future__ import print_function

# Test encoding

# pylint: disable=line-too-long

import locale
import os.path
import sys
import unittest

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '../lib')))
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from six import text_type
import medusa as app
from medusa import ek, ex
from medusa.helper.common import sanitize_filename


class EncodingTests(unittest.TestCase):
    """
    Test encodings
    """
    def test_encoding(self):
        """
        Test encoding
        """
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
                show_dir = ek(os.path.join, root_dir, sanitize_filename(test))
                self.assertTrue(isinstance(show_dir, text_type))
            except Exception as error:  # pylint: disable=broad-except
                ex(error)

if __name__ == "__main__":
    print("""
    ==================
    STARTING - ENCODING TESTS
    ==================
    ######################################################################
    """)

    SUITE = unittest.TestLoader().loadTestsFromTestCase(EncodingTests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
