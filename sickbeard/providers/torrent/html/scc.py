# coding=utf-8
# Author: Idan Gutman
# Modified by jkaberg, https://github.com/jkaberg for SceneAccess
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

from requests.compat import urljoin, quote
from requests.utils import dict_from_cookiejar

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import convert_size
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class SCCProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'SceneAccess')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://sceneaccess.eu'
        self.urls = {
            'base_url': self.url,
            'login': urljoin(self.url, 'login'),
            'detail': urljoin(self.url, 'details?id=%s'),
            'search': urljoin(self.url, 'all?search=%s&method=1&%s'),
            'download': urljoin(self.url, '%s')
        }

        # Proper Strings

        # Miscellaneous Options
        self.categories = {
            'Season': 'c26=26&c44=44&c45=45',  # Archive, non-scene HD, non-scene SD; need to include non-scene because WEB-DL packs get added to those categories
            'Episode': 'c17=17&c27=27&c33=33&c34=34&c44=44&c45=45',  # TV HD, TV SD, non-scene HD, non-scene SD, foreign XviD, foreign x264
            'RSS': 'c17=17&c26=26&c27=27&c33=33&c34=34&c44=44&c45=45'  # Season + Episode
        }

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tvcache.TVCache(self)  # only poll SCC every 20 minutes max

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        """
        Search a provider and parse the results

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        if not self.login():
            return results

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                search_url = self.urls['search'] % (quote(search_string), self.categories[mode])
                response = self.get_url(search_url, returns='response')
                if not response.text:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                results += self.parse(response.text, mode)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """

        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find('table', attrs={'id': 'torrents-table'})
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                return items

            for row in torrent_rows[1:]:
                try:
                    link = row.find('td', attrs={'class': 'ttr_name'}).find('a')
                    url = row.find('td', attrs={'class': 'td_dl'}).find('a')

                    title = link.string
                    if re.search(r'\.\.\.', title):
                        response = self.get_url(urljoin(self.url, link['href']), returns='response')
                        if response.text:
                            with BS4Parser(response.text) as details_html:
                                title = re.search("(?<=').+(?<!')", details_html.title.string).group(0)
                    download_url = self.urls['download'] % url['href']
                    if not all([title, download_url]):
                        continue

                    seeders = int(row.find('td', attrs={'class': 'ttr_seeders'}).string)
                    leechers = int(row.find('td', attrs={'class': 'ttr_leechers'}).string)

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            logger.log("Discarding torrent because it doesn't meet the "
                                       "minimum seeders: {0}. Seeders: {1}".format
                                       (title, seeders), logger.DEBUG)
                        continue

                    torrent_size = row.find('td', attrs={'class': 'ttr_size'}).contents[0]
                    size = convert_size(torrent_size) or -1

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': None,
                        'hash': None,
                    }
                    if mode != 'RSS':
                        logger.log('Found result: {0} with {1} seeders and {2} leechers'.format
                                   (title, seeders, leechers), logger.DEBUG)

                    items.append(item)
                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    logger.log('Failed parsing provider. Traceback: {0!r}'.format
                               (traceback.format_exc()), logger.ERROR)

        return items

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'submit': 'come on in',
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='response')
        if not response.text:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        if any([re.search(r'Username or password incorrect', response.text),
                re.search(r'<title>SceneAccess \| Login</title>', response.text), ]):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            return False

        return True

    @staticmethod
    def _is_section(section, text):
        title = r'<title>.+? \| %s</title>' % section
        return re.search(title, text, re.IGNORECASE)


provider = SCCProvider()
