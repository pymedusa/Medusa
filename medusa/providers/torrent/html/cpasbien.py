# coding=utf-8

"""Provider code for Cpasbien."""

from __future__ import unicode_literals

import logging
import re
import traceback

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import (
    convert_size,
    try_int,
)
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class CpasbienProvider(TorrentProvider):
    """Cpasbien Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('Cpasbien')

        # Credentials
        self.public = True

        # URLs
        self.url = 'http://www.cpasbien.cm'

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK']

        # Miscellaneous Options

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv.Cache(self)

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
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})
                    search_url = self.url + '/recherche/' + \
                        search_string.replace('.', '-').replace(' ', '-') + '.html,trie-seeds-d'
                else:
                    search_url = self.url + '/view_cat.php?categorie=series&trie=date-d'

                response = self.get_url(search_url, returns='response')
                if not response or not response.text:
                    log.debug('No data returned from provider')
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
        # Units
        units = ['o', 'Ko', 'Mo', 'Go', 'To', 'Po']

        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_rows = html(class_=re.compile('ligne[01]'))
            for row in torrent_rows:
                try:
                    title = row.find(class_='titre').get_text(strip=True).replace('HDTV', 'HDTV x264-CPasBien')
                    title = re.sub(r' Saison', ' Season', title, flags=re.IGNORECASE)
                    tmp = row.find('a')['href'].split('/')[-1].replace('.html', '.torrent').strip()
                    download_url = (self.url + '/telechargement/%s' % tmp)
                    if not all([title, download_url]):
                        continue

                    seeders = try_int(row.find(class_='up').get_text(strip=True))
                    leechers = try_int(row.find(class_='down').get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      " minimum seeders: {0}. Seeders: {1}",
                                      title, seeders)
                        continue

                    torrent_size = row.find(class_='poid').get_text(strip=True)
                    size = convert_size(torrent_size, units=units) or -1

                    pubdate_raw = row.find('a')['title'].split("-")[1]
                    pubdate = self._parse_pubdate(pubdate_raw)

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
                    log.error('Failed parsing provider. Traceback: {0!r}',
                              traceback.format_exc())

        return items


provider = CpasbienProvider()
