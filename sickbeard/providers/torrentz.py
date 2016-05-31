# coding=utf-8
# Author: Dustyn Gibson <miigotu@gmail.com>
#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage. If not, see <http://www.gnu.org/licenses/>.

import re
import traceback
import datetime

from dateutil import parser

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser
from sickbeard.common import USER_AGENT

from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class TorrentzProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """
    Provider class
    """

    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, "Torrentz")

        # Credentials
        self.public = True
        self.confirmed = True

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # URLs
        self.url = 'https://torrentz.eu/'
        self.urls = {
            'verified': 'https://torrentz.eu/feed_verified',
            'feed': 'https://torrentz.eu/feed',
            'base': self.url,
        }
        self.headers.update({'User-Agent': USER_AGENT})

        # Proper Strings

        # Cache
        self.cache = tvcache.TVCache(self, min_time=10)  # only poll Torrentz every 15 minutes max

    @staticmethod
    def _split_description(description):
        """
        Converts a html text into: torrent_size, seeders, leechers
        """
        match = re.findall(r'[0-9]+', description)
        return int(match[0]) * 1024 ** 2, int(match[1]), int(match[2])

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals
        """
        Searches indexer using the params in search_strings, either for latest releases, or a string/id search
        :param search_strings: Search to perform
        :param age: Not used for this provider
        :param ep_obj: Not used for this provider

        :return: A list of items found
        """

        _ = ep_obj
        _ = age

        results = []

        for mode in search_strings:
            items = []
            logger.log(u"Search Mode: {}".format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:
                search_url = self.urls['verified'] if self.confirmed else self.urls['feed']
                if mode != 'RSS':
                    logger.log(u"Search string: {}".format
                               (search_string.decode("utf-8")), logger.DEBUG)

                data = self.get_url(search_url, params={'q': search_string}, returns='text')
                if not data:
                    logger.log(u"No data returned from provider", logger.DEBUG)
                    continue

                if not data.startswith("<?xml"):
                    logger.log(u"Expected xml but got something else, is your mirror failing?", logger.INFO)
                    continue

                try:
                    with BS4Parser(data, 'html5lib') as html:
                        for item in html('item'):
                            if item.category and 'tv' not in item.category.get_text(strip=True):
                                continue

                            title_raw = item.title.text
                            # Add "-" after codec and add missing "."
                            title = re.sub(r'([xh][ .]?264|xvid)( )', r'\1-', title_raw).replace(' ','.') if title_raw else ''
                            t_hash = item.guid.text.rsplit('/', 1)[-1]

                            if not all([title, t_hash]):
                                continue

                            download_url = "magnet:?xt=urn:btih:" + t_hash + "&dn=" + title + self._custom_trackers
                            torrent_size, seeders, leechers = self._split_description(item.find('description').text)
                            size = convert_size(torrent_size) or -1
                            pubdate_raw = item.pubdate.text
                            pubdate = parser.parse(pubdate_raw) if pubdate_raw else None

                            # Filter unseeded torrent
                            if seeders < min(self.minseed, 1):
                                if mode != 'RSS':
                                    logger.log(u"Discarding torrent because it doesn't meet the minimum seeders: {0}. Seeders: {1})".format
                                               (title, seeders), logger.DEBUG)
                                continue

                            result = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'pubdate': pubdate, 'hash': t_hash}
                            items.append(result)
                except StandardError:
                    logger.log(u"Failed parsing provider. Traceback: {0!r}".format(traceback.format_exc()), logger.ERROR)
                    continue

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items

        return results


provider = TorrentzProvider()
