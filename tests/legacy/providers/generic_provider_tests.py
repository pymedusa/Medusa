# coding=utf-8
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.

"""Test GenericProvider."""
from __future__ import unicode_literals

import unittest

from medusa.providers.generic_provider import GenericProvider
from mock import MagicMock, patch
from six import iteritems


class GenericProviderTests(unittest.TestCase):
    """Test GenericProvider."""

    def test_get_id(self):
        test_cases = {
            None: '',
            123: '123',
            12.3: '12_3',
            0: '',
            -123: '_123',
            -12.3: '_12_3',
            '': '',
            ' ': '',
            '123': '123',
            ' 123 ': '123',
            '12.3': '12_3',
            ' 12.3 ': '12_3',
            '0': '0',
            ' 0 ': '0',
            '-123': '_123',
            ' -123 ': '_123',
            '-12.3': '_12_3',
            ' -12.3 ': '_12_3',
            'abc': 'abc',
            ' abc ': 'abc',
            'ABC': 'abc',
            ' ABC ': 'abc',
            '.def': '_def',
            'g,hi': 'g_hi',
            'jk!l': 'jk_l',
            'mno?': 'mno_',
            '_pqr$': '_pqr_',
        }

        unicode_test_cases = {
            u'': '',
            u' ': '',
            u'123': '123',
            u' 123 ': '123',
            u'12.3': '12_3',
            u' 12.3 ': '12_3',
            u'0': '0',
            u' 0 ': '0',
            u'-123': '_123',
            u' -123 ': '_123',
            u'-12.3': '_12_3',
            u' -12.3 ': '_12_3',
            u'abc': 'abc',
            u' abc ': 'abc',
            u'ABC': 'abc',
            u' ABC ': 'abc',
            u'.def': '_def',
            u'g,hi': 'g_hi',
            u'jk!l': 'jk_l',
            u'mno?': 'mno_',
            u'_pqr$': '_pqr_',
        }

        for test in test_cases, unicode_test_cases:
            for (name, result) in iteritems(test):
                self.assertEqual(GenericProvider(name).get_id(), result)

    def test_image_name(self):
        test_cases = {
            None: '.png',
            123: '123.png',
            12.3: '12_3.png',
            0: '.png',
            -123: '_123.png',
            -12.3: '_12_3.png',
            '': '.png',
            ' ': '.png',
            '123': '123.png',
            ' 123 ': '123.png',
            '12.3': '12_3.png',
            ' 12.3 ': '12_3.png',
            '0': '0.png',
            ' 0 ': '0.png',
            '-123': '_123.png',
            ' -123 ': '_123.png',
            '-12.3': '_12_3.png',
            ' -12.3 ': '_12_3.png',
            'abc': 'abc.png',
            ' abc ': 'abc.png',
            'ABC': 'abc.png',
            ' ABC ': 'abc.png',
            '.def': '_def.png',
            'g,hi': 'g_hi.png',
            'jk!l': 'jk_l.png',
            'mno?': 'mno_.png',
            '_pqr$': '_pqr_.png',
        }

        unicode_test_cases = {
            u'': '.png',
            u' ': '.png',
            u'123': '123.png',
            u' 123 ': '123.png',
            u'12.3': '12_3.png',
            u' 12.3 ': '12_3.png',
            u'0': '0.png',
            u' 0 ': '0.png',
            u'-123': '_123.png',
            u' -123 ': '_123.png',
            u'-12.3': '_12_3.png',
            u' -12.3 ': '_12_3.png',
            u'abc': 'abc.png',
            u' abc ': 'abc.png',
            u'ABC': 'abc.png',
            u' ABC ': 'abc.png',
            u'.def': '_def.png',
            u'g,hi': 'g_hi.png',
            u'jk!l': 'jk_l.png',
            u'mno?': 'mno_.png',
            u'_pqr$': '_pqr_.png',
        }

        for test in test_cases, unicode_test_cases:
            for (name, result) in iteritems(test):
                self.assertEqual(GenericProvider(name).image_name(), result)

    def test_is_active(self):
        """Test is active."""
        self.assertFalse(GenericProvider('Test Provider').is_active())

    def test_is_enabled(self):
        """Test is enabled."""
        self.assertFalse(GenericProvider('Test Provider').is_enabled())

    def test_make_id(self):
        test_cases = {
            None: '',
            123: '123',
            12.3: '12_3',
            0: '',
            -123: '_123',
            -12.3: '_12_3',
            '': '',
            ' ': '',
            '123': '123',
            ' 123 ': '123',
            '12.3': '12_3',
            ' 12.3 ': '12_3',
            '0': '0',
            ' 0 ': '0',
            '-123': '_123',
            ' -123 ': '_123',
            '-12.3': '_12_3',
            ' -12.3 ': '_12_3',
            'abc': 'abc',
            ' abc ': 'abc',
            'ABC': 'abc',
            ' ABC ': 'abc',
            '.def': '_def',
            'g,hi': 'g_hi',
            'jk!l': 'jk_l',
            'mno?': 'mno_',
            '_pqr$': '_pqr_',
        }

        unicode_test_cases = {
            u'': '',
            u' ': '',
            u'123': '123',
            u' 123 ': '123',
            u'12.3': '12_3',
            u' 12.3 ': '12_3',
            u'0': '0',
            u' 0 ': '0',
            u'-123': '_123',
            u' -123 ': '_123',
            u'-12.3': '_12_3',
            u' -12.3 ': '_12_3',
            u'abc': 'abc',
            u' abc ': 'abc',
            u'ABC': 'abc',
            u' ABC ': 'abc',
            u'.def': '_def',
            u'g,hi': 'g_hi',
            u'jk!l': 'jk_l',
            u'mno?': 'mno_',
            u'_pqr$': '_pqr_',
        }

        for test in test_cases, unicode_test_cases:
            for (name, result) in iteritems(test):
                self.assertEqual(GenericProvider.make_id(name), result)

    def test_seed_ratio(self):
        self.assertEqual(GenericProvider('Test Provider').seed_ratio(), '')

    def test__check_auth(self):
        self.assertTrue(GenericProvider('Test Provider')._check_auth())

    def test_login(self):
        self.assertTrue(GenericProvider('Test Provider').login())

    def test_search(self):
        test_cases = {
            None: [],
            123: [],
            12.3: [],
            -123: [],
            -12.3: [],
            '': [],
            '123': [],
            '12.3': [],
            '-123': [],
            '-12.3': [],
        }

        unicode_test_cases = {
            u'': [],
            u'123': [],
            u'12.3': [],
            u'-123': [],
            u'-12.3': [],
        }

        for test in test_cases, unicode_test_cases:
            for (search_params, result) in iteritems(test):
                self.assertEqual(GenericProvider('Test Provider').search(search_params), result)

    def test__get_size(self):
        self.assertEqual(GenericProvider('Test Provider')._get_size(None), -1)

    def test__get_storage_dir(self):
        self.assertEqual(GenericProvider('Test Provider')._get_storage_dir(), '')

    def test__get_title_and_url(self):
        """Test _get_title_and_url."""
        items_list = [
            None, {}, {'link': None, 'title': None}, {'link': '', 'title': ''},
            {'link': 'http://www.google.com/&amp;foo=bar%26tr%3Dtest', 'title': 'Some Title'}
        ]
        results_list = [
            ('', ''), ('', ''), ('', ''), ('', ''), ('Some.Title', 'http://www.google.com/&foo=bar&tr=test')
        ]

        unicode_items_list = [
            {'link': u'', 'title': u''},
            {'link': u'http://www.google.com/&amp;foo=bar%26tr%3Dtest', 'title': u'Some Title'}
        ]
        unicode_results_list = [
            ('', ''), ('Some.Title', 'http://www.google.com/&foo=bar&tr=test')
        ]

        self.assertEqual(
            len(items_list), len(results_list),
            'Number of parameters (%d) and results (%d) does not match' % (len(items_list), len(results_list))
        )

        self.assertEqual(
            len(unicode_items_list), len(unicode_results_list),
            'Number of parameters (%d) and results (%d) does not match' % (
                len(unicode_items_list), len(unicode_results_list))
        )

        for (index, item) in enumerate(items_list):
            self.assertEqual(GenericProvider('Test Provider')._get_title_and_url(item), results_list[index])

        for (index, item) in enumerate(unicode_items_list):
            self.assertEqual(GenericProvider('Test Provider')._get_title_and_url(item), unicode_results_list[index])

    def test__verify_download(self):
        """Test _verify_download."""
        self.assertTrue(GenericProvider('Test Provider')._verify_download())

    @patch('medusa.providers.generic_provider.download_file')
    def test_download_file(self, df_mock):
        domain = 'domain'
        filename = 'TestFilename.nzb'
        urls = [
            'http://{0}/{1}.torrentNO_DOWNLOAD_NAME'.format(domain, filename),
            'http://{0}/{1}.torrent'.format(domain, filename),
        ]

        # Test the login() check
        gp1 = GenericProvider('Test Provider 1')
        login_mock = MagicMock()
        login_mock.name = 'result 1'
        login_mock.return_value = False
        with patch.object(gp1, 'login', login_mock):
            self.assertFalse(gp1.download_result(login_mock))
            self.assertTrue(login_mock.called)

        # Test the _make_url call
        gp2 = GenericProvider('Test Provider 2')
        make_url_mock = MagicMock()
        make_url_mock.name = 'result 2'
        make_url_mock.return_value = (urls, filename)
        df_mock.return_value = True
        with patch.object(gp2, '_make_url', make_url_mock):
            resp = gp2.download_result(make_url_mock)
            self.assertTrue(resp)
            self.assertTrue('Referer' in gp2.headers)
            self.assertTrue(domain in gp2.headers['Referer'])
            self.assertTrue(df_mock.called)

        # Test the remove_file_failed path
        gp3 = GenericProvider('Test Provider 3')
        make_url_mock = MagicMock()
        make_url_mock.name = 'result 3'
        make_url_mock.return_value = (urls, filename)
        verify_download_mock = MagicMock()
        verify_download_mock.return_value = False
        df_mock.return_value = True
        with patch.object(gp3, '_make_url', make_url_mock):
            with patch.object(gp3, '_verify_download', verify_download_mock):
                resp = gp3.download_result(make_url_mock)
                self.assertFalse(resp)
