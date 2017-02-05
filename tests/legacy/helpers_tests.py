#!/usr/bin/env python2.7
# coding=utf-8
# Author: Dustyn Gibson <miigotu@gmail.com>
#
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

"""Test helpers."""

from __future__ import print_function

import unittest

from medusa import helpers
from medusa.helper.common import media_extensions, subtitle_extensions

TEST_RESULT = 'Show.Name.S01E01.HDTV.x264-RLSGROUP'
# TODO: py.test parameters
TEST_CASES = {
    'removewords': [
        TEST_RESULT,
        'Show.Name.S01E01.HDTV.x264-RLSGROUP[cttv]',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP.RiPSaLoT',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP[GloDLS]',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP[EtHD]',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP-20-40',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP[NO-RAR] - [ www.torrentday.com ]',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP[rarbg]',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP[Seedbox]',
        '{ www.SceneTime.com } - Show.Name.S01E01.HDTV.x264-RLSGROUP',
        '].[www.tensiontorrent.com] - Show.Name.S01E01.HDTV.x264-RLSGROUP',
        '[ www.TorrentDay.com ] - Show.Name.S01E01.HDTV.x264-RLSGROUP',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP[silv4]',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP[AndroidTwoU]',
        '[www.newpct1.com]Show.Name.S01E01.HDTV.x264-RLSGROUP',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP-NZBGEEK',
        '.www.Cpasbien.pwShow.Name.S01E01.HDTV.x264-RLSGROUP',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP [1044]',
        '[ www.Cpasbien.pw ] Show.Name.S01E01.HDTV.x264-RLSGROUP',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP.[BT]',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP[vtv]',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP.[www.usabit.com]',
        '[www.Cpasbien.com] Show.Name.S01E01.HDTV.x264-RLSGROUP',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP[ettv]',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP[rartv]',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP-Siklopentan',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP-RP',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP[PublicHD]',
        '[www.Cpasbien.pe] Show.Name.S01E01.HDTV.x264-RLSGROUP',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP[eztv]',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP-[SpastikusTV]',
        '].[ www.tensiontorrent.com ] - Show.Name.S01E01.HDTV.x264-RLSGROUP',
        '[ www.Cpasbien.com ] Show.Name.S01E01.HDTV.x264-RLSGROUP',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP- { www.SceneTime.com }',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP- [ www.torrentday.com ]',
        'Show.Name.S01E01.HDTV.x264-RLSGROUP.Renc'
    ]
}


class HelpersTests(unittest.TestCase):
    """Test using test generator."""

    def __init__(self, *args, **kwargs):
        """Initialize test."""
        super(HelpersTests, self).__init__(*args, **kwargs)


def generator(test_strings):
    """Generate tests from test strings.

    :param test_strings: to generate tests from
    :return: test
    """
    def _test(self):
        """Generate tests.

        :param self:
        :return: test to run
        """
        for test_string in test_strings:
            self.assertEqual(test_string, TEST_RESULT)
    return _test


class HelpersFileTests(unittest.TestCase):
    """Test file helpers."""

    def test_is_media_file(self):
        # TODO: Add unicode tests
        # TODO: Add MAC OS resource fork tests
        # TODO: Add RARBG release tests
        # RARBG release intros should be ignored
        # MAC OS's "resource fork" files should be ignored
        # Extras should be ignored
        # and the file extension should be in the list of media extensions

        # Test all valid media extensions
        temp_name = 'Show.Name.S01E01.HDTV.x264-RLSGROUP'
        extension_tests = {'.'.join((temp_name, ext)): True for ext in media_extensions}

        # ...and some invalid ones
        other_extensions = ['txt', 'sfv', 'srr', 'rar', 'nfo', 'zip']
        extension_tests.update({'.'.join((temp_name, ext)): False for ext in other_extensions + subtitle_extensions})

        # Samples should be ignored
        sample_tests = {  # Samples should be ignored, valid samples will return False
            'Show.Name.S01E01.HDTV.sample.mkv': False,  # default case
            'Show.Name.S01E01.HDTV.sAmPle.mkv': False,  # Ignore case
            'Show.Name.S01E01.HDTV.samples.mkv': True,  # sample should not be plural
            'Show.Name.S01E01.HDTVsample.mkv': True,  # no separation, can't identify as sample
            'Sample.Show.Name.S01E01.HDTV.mkv': False,  # location doesn't matter
            'Show.Name.Sample.S01E01.HDTV.sample.mkv': False,  # location doesn't matter
            'Show.Name.S01E01.HDTV.sample1.mkv': False,  # numbered samples are ok
            'Show.Name.S01E01.HDTV.sample12.mkv': False,  # numbered samples are ok
            'Show.Name.S01E01.HDTV.sampleA.mkv': True,  # samples should not be indexed alphabetically
        }

        edge_cases = {
            None: False,
            '': False,
            0: False,
            1: False,
            42: False,
            123189274981274: False,
            12.23: False,
            ('this', 'is', 'a tuple'): False,
        }

        for cur_test in extension_tests, sample_tests, edge_cases:
            for cur_name, expected_result in cur_test.items():
                self.assertEqual(helpers.is_media_file(cur_name), expected_result, cur_name)
