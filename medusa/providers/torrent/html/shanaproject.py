# coding=utf-8

"""Provider code for ShanaProject."""

from __future__ import unicode_literals

import logging
import re

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import convert_size
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class ShanaProjectProvider(TorrentProvider):
    """ShanaProject Torrent provider."""

    size_regex = re.compile(r'([\d.]+)(.*)')

    def __init__(self):
        """Initialize the class."""
        super(ShanaProjectProvider, self).__init__('ShanaProject')

        # Credentials
        self.public = True

        # URLs
        self.url = 'https://www.shanaproject.com/'
        self.urls = {
            'search': urljoin(self.url, '/search/{page}/'),
        }

        # Miscellaneous Options
        self.max_pages = 3  # Max return 150 results for 3 pages.
        self.supports_absolute_numbering = True
        self.anime_only = True

        # Cache
        self.cache = tv.Cache(self, min_time=20)

    def search(self, search_strings, age=0, ep_obj=None, **kwargs):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []

        search_params = {}

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                    search_params = {
                        'sort': 'date',
                        'dir': 'Descending',
                        'title': '{0}'.format(search_string)
                    }

                page = 1
                while page and page <= self.max_pages:
                    response = self.session.get(
                        self.urls['search'].format(page=page), params=search_params
                    )
                    if not response or not response.text:
                        log.debug('No data returned from provider')
                        page = None
                        continue

                    page = page + 1 if 'list_next >>' in response.text else None

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

            torrent_rows = html('div', class_='release_block')
            if len(torrent_rows) < 2:
                return items

            for row in torrent_rows[1:]:

                try:
                    first_cell = row.find('div', class_='release_row_first')
                    cells = row('div', class_='release_row')

                    title = cells[1].find('div', class_='release_text_contents').get_text().strip()
                    download_url = first_cell('a')[-1].get('href')

                    if not all([title, download_url]):
                        continue

                    download_url = urljoin(self.url, download_url)

                    # Provider does not support seeders or leechers.
                    seeders = 1
                    leechers = 0

                    torrent_size = first_cell.find('div', class_='release_size').get_text()
                    match_size = ShanaProjectProvider.size_regex.match(torrent_size)
                    try:
                        size = convert_size(match_size.group(1) + ' ' + match_size.group(2)) or -1
                    except AttributeError:
                        size = -1

                    pubdate_raw = cells[0].find('div', class_='release_last').get_text()
                    pubdate = self.parse_pubdate(pubdate_raw)

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': pubdate,
                    }
                    if mode != 'RSS':
                        log.debug('Found result: {0} with {1} seeders and {2} leechers',
                                  title, seeders, leechers)

                    items.append(item)
                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    log.exception('Failed parsing provider.')

        return items

    def _get_episode_search_strings(self, episode, add_string=''):
        """Get episode search strings."""
        if not episode:
            return []

        search_string = {
            'Episode': []
        }

        for show_name in episode.series.get_all_possible_names(season=episode.scene_season):
            search_string['Episode'].append(show_name.strip())

        return [search_string]

    def _get_season_search_strings(self, episode):
        """Get search search strings."""
        log.info('ShanaProject does not support season searches. Better to run a regular episode search')
        search_string = {
            'Season': []
        }

        for show_name in episode.series.get_all_possible_names(season=episode.season):
            search_string['Season'].append(show_name.strip())

        return [search_string]


provider = ShanaProjectProvider()
