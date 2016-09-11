# coding=utf-8
# Author: Jordon Smith <smith@jordon.me.uk>
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

import sickbeard
from sickrage.helper.common import convert_size, try_int
from sickrage.providers.nzb.NZBProvider import NZBProvider
from ... import logger, tvcache


class OmgwtfnzbsProvider(NZBProvider):

    def __init__(self):

        # Provider Init
        NZBProvider.__init__(self, 'OMGWTFNZBs')

        # Credentials
        self.username = None
        self.api_key = None

        # URLs
        self.url = 'https://omgwtfnzbs.org/'
        self.urls = {
            'rss': 'https://rss.omgwtfnzbs.org/rss-download.php',
            'api': 'https://api.omgwtfnzbs.org/json/',
        }

        # Proper Strings
        self.proper_strings = ['.PROPER.', '.REPACK.']

        # Miscellaneous Options

        # Cache
        self.cache = OmgwtfnzbsCache(self)

    def search(self, search_strings, age=0, ep_obj=None):
        results = []
        if not self._check_auth():
            return results

        search_params = {
            'user': self.username,
            'api': self.api_key,
            'eng': 1,
            'catid': '19,20',  # SD,HD
            'retention': sickbeard.USENET_RETENTION,
        }

        for mode in search_strings:
            items = []
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:
                search_params['search'] = search_string
                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                response = self.get_url(self.urls['api'], params=search_params, returns='json')
                if not response:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                if not self._check_auth_from_data(response, is_XML=False):
                    return items

                for item in response:
                    try:
                        if not self._get_title_and_url(item):
                            continue

                        logger.log('Found result: {0}'.format(item.get('title')), logger.DEBUG)
                        items.append(item)
                    except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                            logger.log('Failed parsing provider. Traceback: {0!r}'.format
                                       (traceback.format_exc()), logger.ERROR)
                            continue

            results += items

        return results

    def _check_auth(self):

        if not self.username or not self.api_key:
            logger.log('Invalid api key. Check your settings', logger.WARNING)
            return False

        return True

    def _check_auth_from_data(self, parsed_data, is_XML=True):

        if not parsed_data:
            return self._check_auth()

        if is_XML:
            # provider doesn't return xml on error
            return True

        if 'notice' in parsed_data:
            description_text = parsed_data.get('notice')
            if 'information is incorrect' in description_text:
                logger.log('Invalid api key. Check your settings', logger.WARNING)
            elif '0 results matched your terms' not in description_text:
                logger.log('Unknown error: {0}'.format(description_text), logger.DEBUG)
            return False

        return True

    def _get_title_and_url(self, item):
        return item['release'], item['getnzb']

    def _get_size(self, item):
        size = item.get('sizebytes', -1)

        # Try to get the size from the summary tag
        if size == -1:
            # Units
            units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
            summary = item.get('summary')
            if summary:
                size_match = re.search(r'Size[^\d]*([0-9.]*.[A-Z]*)', summary)
                size = convert_size(size_match.group(1), units=units) or -1 if size_match else -1

        return try_int(size)


class OmgwtfnzbsCache(tvcache.TVCache):
    def _get_title_and_url(self, item):
        title = item.get('title')
        if title:
            title = title.replace(' ', '.')

        url = item.get('link')
        if url:
            url = url.replace('&amp;', '&')

        return title, url

    def _getRSSData(self):
        search_params = {
            'user': provider.username,
            'api': provider.api_key,
            'eng': 1,
            'catid': '19,20'  # SD,HD
        }
        return self.getRSSFeed(self.provider.urls['rss'], params=search_params)


provider = OmgwtfnzbsProvider()
