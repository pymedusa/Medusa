# coding=utf-8

"""Provider code for EliteTorrent."""

from __future__ import unicode_literals

import logging
import re

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import try_int
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class EliteTorrentProvider(TorrentProvider):
    """EliteTorrent Torrent provider."""

    id_regex = re.compile(r'/torrent/(\d+)')

    def __init__(self):
        """Initialize the class."""
        super(EliteTorrentProvider, self).__init__('EliteTorrent')

        # Credentials
        self.public = True

        # URLs
        self.url = 'https://elitetorrent.eu'
        self.urls = {
            'base_url': self.url,
            'search': urljoin(self.url, 'torrents.php'),
            'download': urljoin(self.url, 'get-torrent/{0}'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.onlyspasearch = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None

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
        lang_info = '' if not ep_obj or not ep_obj.series else ep_obj.series.lang

        # Search query:
        # http://www.elitetorrent.net/torrents.php?cat=4&modo=listado&orden=fecha&pag=1&buscar=fringe
        # Search Params
        search_params = {
            'cat': 4,  # Shows
            'modo': 'listado',  # display results mode
            'orden': 'fecha',  # date order
            'pag': 1,  # page number
            'buscar': '',  # Search show
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            # Only search if user conditions are true
            if self.onlyspasearch and lang_info != 'es' and mode != 'RSS':
                log.debug('Show info is not Spanish, skipping provider search')
                continue

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    search_string = re.sub(r'S0?(\d+)E(\d+)', r'\1x\2', search_string)
                    search_params['buscar'] = search_string

                    log.debug('Search string: {search}',
                              {'search': search_string})

                response = self.session.get(self.urls['search'], params=search_params)
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
        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find('table', class_='fichas-listado')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # Skip column headers
            for row in torrent_rows[1:]:
                try:
                    title = self._process_title(row.find('a', class_='nombre')['title'])
                    torrent_id = EliteTorrentProvider.id_regex.match(row.find('a')['href'])
                    if not all([title, torrent_id]):
                        continue

                    download_url = self.urls['download'].format(torrent_id.group(1))

                    seeders = try_int(row.find('td', class_='semillas').get_text(strip=True))
                    leechers = try_int(row.find('td', class_='clientes').get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      " minimum seeders: {0}. Seeders: {1}",
                                      title, seeders)
                        continue

                    size = -1  # Provider does not provide size

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': None,
                    }
                    if mode != 'RSS':
                        log.debug('Found result: {0} with {1} seeders and {2} leechers',
                                  title, seeders, leechers)

                    items.append(item)
                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    log.exception('Failed parsing provider.')

        return items

    @staticmethod
    def _process_title(title):
        if title:
            # Quality, if no literal is defined it's HDTV
            if 'calidad' not in title:
                title += ' HDTV x264'
            else:
                title = title.replace('(calidad baja)', 'HDTV x264')
                title = title.replace('(Buena calidad)', '720p HDTV x264')
                title = title.replace('(Alta calidad)', '720p HDTV x264')
                title = title.replace('(calidad regular)', 'DVDrip x264')
                title = title.replace('(calidad media)', 'DVDrip x264')

            # Language, all results from this provider have spanish audio,
            # We append it to title (to avoid downloading undesired torrents)
            title += ' SPANISH AUDIO-ELITETORRENT'

        return title


provider = EliteTorrentProvider()
