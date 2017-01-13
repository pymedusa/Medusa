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
"""Provider code for Anizb provider."""
from __future__ import unicode_literals

import traceback

from requests.compat import urljoin

from .nzb_provider import NZBProvider
from ... import logger, tv_cache
from ...bs4_parser import BS4Parser
from ...helper.common import try_int

from ...scene_exceptions import get_scene_exceptions
from ...show_name_helpers import allPossibleShowNames


class Anizb(NZBProvider):
    """Nzb Provider using the open api of anizb.org for daily (rss) and backlog/forced searches."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('Anizb')

        # Credentials
        self.public = True

        # URLs
        self.url = 'https://anizb.org/'
        self.urls = {
            'rss': self.url,
            'api': urljoin(self.url, 'api/?q=')
        }

        # Proper Strings

        # Miscellaneous Options
        self.supports_absolute_numbering = True
        self.anime_only = True

        # Torrent Stats

        # Cache
        self.cache = tv_cache.TVCache(self)

    def search(self, search_strings, age=0, ep_obj=None):
        """Start searching for anime using the provided search_strings. Used for backlog and daily."""
        results = []
        if self.show and not self.show.is_anime:
            return results

        for mode in search_strings:
            items = []
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                    search_url = (self.urls['rss'], self.urls['api'] + search_string)[mode != 'RSS']
                    response = self.get_url(search_url, returns='response')
                    if not response or not response.text:
                        logger.log('No data returned from provider', logger.DEBUG)
                        continue

                    if not response.text.startswith('<?xml'):
                        logger.log('Expected xml but got something else, is your mirror failing?', logger.INFO)
                        continue

                    with BS4Parser(response.text, 'html5lib') as html:
                        entries = html('item')
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

                                item = {
                                    'title': title,
                                    'link': download_url,
                                    'size': size,
                                }

                                items.append(item)
                            except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                                logger.log('Failed parsing provider. Traceback: {0!r}'.format
                                           (traceback.format_exc()), logger.ERROR)
                                continue

                results += items

            return results

    def _get_size(self, item):
        """Override the default _get_size to prevent it from extracting using the default tags."""
        return try_int(item.get('size'))

    def _get_episode_search_strings(self, episode):
        """Get episode search strings."""
        if not episode:
            return []

        search_string = {
            'Episode': []
        }

        for show_name in allPossibleShowNames(episode.show, season=episode.scene_season):
            episode_string = show_name + '*'

            # If the showname is a season scene exception, we want to use the indexer episode number.
            if show_name in get_scene_exceptions(episode.show.indexerid, season=episode.scene_season,
                                                 indexer=episode.show.indexer):
                # This is apparently a season exception, let's use the scene_episode instead of absolute
                ep = episode.scene_episode
            else:
                ep = episode.scene_absolute_number
            episode_string += str(ep)

            search_string['Episode'].append(episode_string.strip())

        return [search_string]


provider = Anizb()
