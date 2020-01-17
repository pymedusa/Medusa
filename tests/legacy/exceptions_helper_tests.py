# -*- coding: utf-8 -*-

"""Test exceptions helpers."""
from __future__ import unicode_literals

import unittest

from medusa.helper.exceptions import ex


class ExceptionsHelperTestCase(unittest.TestCase):
    """Test exceptions helper."""

    def test_none_returns_empty(self):
        self.assertEqual(ex(None), u'')

    def test_empty_args_returns_empty(self):
        self.assertEqual(ex(Exception()), u'')

    def test_args_of_none_returns_empty(self):
        self.assertEqual(ex(Exception(None, None)), u'')

    def test_ex_ret_args_string(self):
        self.assertEqual(ex(Exception('hi')), 'hi')

    # TODO why doesn't this work?@
    @unittest.skip('Errors with unicode conversion')
    def test_ex_ret_args_ustring(self):
        self.assertEqual(ex(Exception('\xc3\xa4h')), u'äh')

    def test_ex_ret_concat_args_strings(self):
        self.assertEqual(ex(Exception('lots', 'of', 'strings')), 'lots : of : strings')

    def test_ex_ret_stringed_args(self):
        self.assertEqual(ex(Exception(303)), 'error 303')
