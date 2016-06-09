# coding=utf-8
# Author: p0psicles
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

import traceback

from sickbeard import logger, tvcache

from sickrage.providers.nzb.NZBProvider import NZBProvider
from sickrage.helper.common import try_int

from requests.compat import urljoin

from bs4 import BeautifulSoup


class Anizb(NZBProvider):  # pylint: disable=too-many-instance-attributes
    """Nzb Provider using the open api of anizb.org for daily (rss) and backlog/forced searches"""
    def __init__(self):

        # Provider Init
        NZBProvider.__init__(self, 'Anizb')

        self.public = True
        self.supports_absolute_numbering = True
        self.anime_only = True

        self.url = 'https://anizb.org/'
        self.urls = {
            'rss': self.url,
            'api': urljoin(self.url, 'api/?q=')
        }
        # Proper Strings

        # Cache
        self.cache = tvcache.TVCache(self)

    def _get_size(self, item):
        """Override the default _get_size to prevent it from extracting using it the default tags"""
        return try_int(item.get('size'))

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals
        """Start searching for anime using the provided search_strings. Used for backlog and daily"""
        results = []

        if self.show and not self.show.is_anime:
            return results

        for mode in search_strings:
            logger.log('Search Mode: {0}'.format(mode), logger.DEBUG)
            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {0}'.format(search_string), logger.DEBUG)

                try:
                    search_url = (self.urls['rss'], self.urls['api'] + search_string)[mode != 'RSS']

                    data = self.get_url(search_url, returns='text')
                    if not data:
                        logger.log('No data returned from provider', logger.DEBUG)
                        continue

                    if not data.startswith('<?xml'):
                        logger.log('Expected xml but got something else, is your mirror failing?', logger.INFO)
                        continue

                    data = BeautifulSoup(data, 'html5lib')
                    entries = data('item')
                    if not entries:
                        logger.log('Returned xml contained no results', logger.INFO)
                        continue

                    for item in entries:
                        try:
                            title = item.title.get_text(strip=True)
                            download_url = item.enclosure.get('url').strip()

                            if not (title and download_url):
                                continue
                            # description = item.find('description')
                            size = try_int(item.enclosure.get('length', -1))

                        except (AttributeError, TypeError, KeyError, ValueError):
                            continue

                        result = {'title': title, 'link': download_url, 'size': size}
                        results.append(result)

                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    logger.log('Failed parsing provider. Traceback: {0!r}'.format
                               (traceback.format_exc()), logger.ERROR)

        return results

provider = Anizb()
