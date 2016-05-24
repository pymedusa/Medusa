# coding=utf-8
# Author: Gonçalo M. (aka duramato/supergonkas) <supergonkas@gmail.com>
#
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

import datetime
import traceback

from dateutil import parser
from requests.compat import urljoin
import validators

from sickbeard import logger, tvcache
from sickbeard.common import USER_AGENT

from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class TorrentProjectProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, "TorrentProject")

        # Credentials
        self.public = True

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # URLs
        self.url = 'https://torrentproject.se/'

        self.custom_url = None
        self.headers.update({'User-Agent': USER_AGENT})

        # Proper Strings

        # Cache
        self.cache = tvcache.TVCache(self, search_params={'RSS': ['0day']})

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        """
        Searches indexer using the params in search_strings, either for latest releases, or a string/id search
        :param search_strings: Search to perform
        :param age: Not used for this provider
        :param ep_obj: Not used for this provider

        :return: A list of items found
        """

        results = []

        search_params = {
            'out': 'json',
            'filter': 2101,
            'showmagnets': 'on',
            'num': 150
        }

        for mode in search_strings:  # Mode = RSS, Season, Episode
            items = []
            logger.log(u"Search Mode: {}".format(mode), logger.DEBUG)

            if mode == 'RSS':
                last_pubdate = self.cache.get_last_pubdate()
                logger.log("Provider last RSS pubdate: {}".format(last_pubdate), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log(u"Search string: {}".format(search_string.decode("utf-8")),
                               logger.DEBUG)

                search_params['s'] = search_string

                if self.custom_url:
                    if not validators.url(self.custom_url):
                        logger.log("Invalid custom url set, please check your settings", logger.WARNING)
                        return results
                    search_url = self.custom_url
                else:
                    search_url = self.url

                torrents = self.get_url(search_url, params=search_params, returns='json')
                if not (torrents and int(torrents.pop('total_found', 0)) > 0):
                    logger.log(u"Data returned from provider does not contain any torrents", logger.DEBUG)
                    continue

                for i in torrents:
                    title = torrents[i].get("title")
                    seeders = try_int(torrents[i].get("seeds"), 1)
                    leechers = try_int(torrents[i].get("leechs"), 0)
                    #pubdate_raw = torrents[i].get("pubdate")
                    #pubdate = parser.parse(pubdate_raw, fuzzy=True)
    
                    # Here we discard item if is not a new item
                    #if mode == "RSS" and pubdate and last_pubdate and pubdate < last_pubdate:
                    #    logger.log("Discarded {0} because it was already processed. Pubdate: {1}".format(title, pubdate))
                    #    continue

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            logger.log(u"Discarding torrent because it doesn't meet the minimum seeders: {0}. Seeders: {1})".format(title, seeders), logger.DEBUG)
                        continue

                    t_hash = torrents[i].get("torrent_hash")
                    torrent_size = torrents[i].get("torrent_size")
                    size = convert_size(torrent_size) or -1
                    download_url = torrents[i].get('magnet') + self._custom_trackers

                    if not all([title, download_url]):
                        continue

                    item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'pubdate': None, 'hash': t_hash}

                    if mode != 'RSS':
                        logger.log(u"Found result: {0} with {1} seeders and {2} leechers".format
                                   (title, seeders, leechers), logger.DEBUG)

                    items.append(item)

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items

            # Set last pubdate for provider
            #if mode == 'RSS' and results:
            #    last_pubdate = max([result['pubdate'] for result in results])
            #    if isinstance(last_pubdate, datetime.datetime):
            #        logger.log("Setting provider last RSS pubdate to: {}".format(last_pubdate), logger.DEBUG)
            #        self.cache.set_last_pubdate(last_pubdate)

        return results


provider = TorrentProjectProvider()
