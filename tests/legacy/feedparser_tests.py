# coding=utf-8
"""Test Feed parser."""

from __future__ import print_function

import unittest

from medusa.providers.nzb.womble import provider as womble


class FeedParserTests(unittest.TestCase):
    """Test feed parser."""

    def test_womble(self):
        result = womble.cache.get_rss_feed(womble.urls['rss'], params={'sec': 'tv-sd', 'fr': 'false'})
        self.assertTrue('entries' in result)
        for item in result['entries'] or []:
            title, url = womble._get_title_and_url(item)     # pylint: disable=protected-access
            self.assertTrue(title and url)
