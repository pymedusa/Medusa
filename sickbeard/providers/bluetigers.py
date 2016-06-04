# coding=utf-8
# Author: raver2046 <raver2046@gmail.com>
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

from __future__ import unicode_literals

import re
import traceback

from requests.utils import dict_from_cookiejar

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class BlueTigersProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        TorrentProvider.__init__(self, 'BLUETIGERS')

        self.username = None
        self.password = None
        self.token = None

        self.cache = tvcache.TVCache(self, min_time=10)  # Only poll BLUETIGERS every 10 minutes max

        self.urls = {
            'base_url': 'https://www.bluetigers.ca/',
            'search': 'https://www.bluetigers.ca/torrents-search.php',
            'login': 'https://www.bluetigers.ca/account-login.php',
            'download': 'https://www.bluetigers.ca/torrents-details.php?id=%s&hit=1',
        }

        self.search_params = {
            'c16': 1, 'c10': 1, 'c130': 1, 'c131': 1, 'c17': 1, 'c18': 1, 'c19': 1, 'c9': 1
        }

        self.url = self.urls['base_url']

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'take_login': '1'
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='text')

        if not response:
            check_login = self.get_url(self.urls['base_url'], returns='text')
            if re.search('account-logout.php', check_login):
                return True
            else:
                logger.log('Unable to connect to provider', logger.WARNING)
                return False

        if re.search('account-login.php', response):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            return False

        return True

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals
        results = []

        if not self.login():
            return results

        for mode in search_strings:
            items = []
            logger.log('Search Mode: {0}'.format(mode), logger.DEBUG)
            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {0}'.format(search_string.decode('utf-8')),
                               logger.DEBUG)

                self.search_params['search'] = search_string

                data = self.get_url(self.urls['search'], params=self.search_params, returns='text')
                if not data:
                    continue

                try:
                    with BS4Parser(data, 'html5lib') as html:
                        result_linkz = html('a', href=re.compile('torrents-details'))

                        if not result_linkz:
                            logger.log('Data returned from provider do not contains any torrent', logger.DEBUG)
                            continue

                        if result_linkz:
                            for link in result_linkz:
                                title = link.text
                                download_url = self.urls['base_url'] + link['href']
                                download_url = download_url.replace('torrents-details', 'download')
                                # FIXME
                                size = -1
                                seeders = 1
                                leechers = 0

                                if not title or not download_url:
                                    continue

                                # Filter unseeded torrent
                                # if seeders < min(self.minseed, 1):
                                #    if mode != 'RSS':
                                #        logger.log('Discarding torrent because it doesn't meet the minimum seeders: {0}. Seeders: {1})'.format
                                #                   (title, seeders), logger.DEBUG)
                                #    continue

                                item = {
                                    'title': title,
                                    'link': download_url,
                                    'size': size,
                                    'seeders': seeders,
                                    'leechers': leechers,
                                    'pubdate': None,
                                    'hash': None
                                }
                                if mode != 'RSS':
                                    logger.log('Found result: {0} with {1} seeders and {2} leechers'.format
                                               (title, seeders, leechers), logger.DEBUG)

                                items.append(item)

                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    logger.log('Failed parsing provider. Traceback: {0!r}'.format
                               (traceback.format_exc()), logger.ERROR)
                    continue

            results += items

        return results


provider = BlueTigersProvider()
