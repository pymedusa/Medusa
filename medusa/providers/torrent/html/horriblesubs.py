# coding=utf-8

"""Provider code for HorribleSubs."""

from __future__ import unicode_literals

import traceback

from dateutil import parser

from medusa import (
    logger,
    tv,
)
from medusa.bs4_parser import BS4Parser
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin


class HorribleSubsProvider(TorrentProvider):
    """HorribleSubs Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('HorribleSubs')

        # Credentials
        self.public = True

        # URLs
        self.url = 'http://horriblesubs.info'
        self.urls = {
            'daily': urljoin(self.url, '/lib/latest.php'),
            'search': urljoin(self.url, '/lib/search.php'),
        }

        # Miscellaneous Options

        # Cache
        self.cache = tv.Cache(self, min_time=20)

    def search(self, search_strings, age=0, ep_obj=None):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            search_params = {}
            search_url = self.urls['daily']

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)
                    search_params = {'value': '{0}'.format(search_string)}
                    search_url = self.urls['search']

                response = self.get_url(search_url, params=search_params, returns='response')
                if not response or not response.text:
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
            torrent_rows = html.find_all(class_=['release-info', 'release-links'])

            # Continue only if at least one release is found
            if not torrent_rows:
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                return items

            for row in torrent_rows:
                try:
                    if row['class'] == ['release-info']:
                        pubdate = None
                        # pubdate is only supported for non-daily searches
                        if mode != 'RSS':
                            # keep the date and strip the rest
                            date = row.find('td', class_='rls-label').get_text()[1:9]
                            pubdate = parser.parse(date)
                        continue

                    title = row.find('td', class_='dl-label').get_text()
                    download_url = row.find('td', class_='dl-type hs-magnet-link').a.get('href')
                    if not all([title, download_url]):
                        continue

                    # Add HorribleSubs group to the title
                    title = '{group} {title}'.format(group='[HorribleSubs]', title=title)

                    # HorribleSubs doesn't provide this information
                    seeders = 1
                    leechers = 0
                    size = -1

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': pubdate,
                    }
                    if mode != 'RSS':
                        logger.log('Found result: {0} with {1} seeders and {2} leechers'.format
                                   (title, seeders, leechers), logger.DEBUG)

                    items.append(item)
                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    logger.log('Failed parsing provider. Traceback: {0!r}'.format
                               (traceback.format_exc()), logger.ERROR)

        return items


provider = HorribleSubsProvider()
