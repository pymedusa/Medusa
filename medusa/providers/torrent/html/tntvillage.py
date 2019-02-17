# coding=utf-8

"""Provider code for TNTVillage."""

from __future__ import unicode_literals

import logging

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class TNTVillageProvider(TorrentProvider):
    """TNTVillage Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(TNTVillageProvider, self).__init__('TNTVillage')

        # Credentials
        self.public = True

        # URLs
        self.url = 'http://tntvillage.scambioetico.org'
        self.urls = {
            'search': urljoin(self.url, 'src/releaselist.php'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK']

        # Miscellaneous Options
        self.engrelease = None  # Currently unused
        self.subtitle = None

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
        if not self.login():
            return results

        # Search Params
        search_params = {
            'cat': 29,
            'page': 1,
            'srcrel': '',
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                    search_params['cat'] = 0
                    search_params['srcrel'] = search_string

                response = self.session.post(self.urls['search'], data=search_params)
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
            torrent_table = html.find('div', class_='showrelease_tb')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # T	 M  Cat	 L	S  C  Titolo
            labels = [label.get_text() for label in torrent_rows[0]('td')]

            # Skip column headers
            for row in torrent_rows[1:]:
                cells = row('td')

                try:
                    title_cell = cells[labels.index('Titolo')]
                    title = title_cell.get_text()
                    download_url = cells[labels.index('T')].a.get('href')
                    if not all([title, download_url]):
                        continue

                    seeders = int(cells[labels.index('S')].get_text())
                    leechers = int(cells[labels.index('L')].get_text())

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    if self._has_only_subs(title) and not self.subtitle:
                        log.debug('Torrent is only subtitled, skipping: {0}',
                                  title)
                        continue

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': -1,  # Provider doesn't have size information
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': None,  # Provider doesn't have pubdate information
                    }
                    if mode != 'RSS':
                        log.debug('Found result: {0} with {1} seeders and {2} leechers',
                                  title, seeders, leechers)

                    items.append(item)
                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    log.exception('Failed parsing provider.')

        return items

    @staticmethod
    def _process_title(title, info, mode):  # Currently unused

        result_title = title.find('a').get_text()
        result_info = info.find('span')

        if not result_info:
            return None

        bad_words = ['[cura]', 'hot', 'season', 'stagione', 'series', 'premiere', 'finale', 'fine',
                     'full', 'Completa', 'supereroi', 'commedia', 'drammatico', 'poliziesco', 'azione',
                     'giallo', 'politico', 'sitcom', 'fantasy', 'funzionante']

        formatted_info = ''
        for info_part in result_info:
            if mode == 'RSS':
                try:
                    info_part = info_part.get('src')
                    info_part = info_part.replace('style_images/mkportal-636/', '')
                    info_part = info_part.replace('.gif', '').replace('.png', '')
                    if info_part == 'dolby':
                        info_part = 'Ac3'
                    elif info_part == 'fullHd':
                        info_part = '1080p'
                except AttributeError:
                    info_part = info_part.replace('·', '').replace(',', '')
                    info_part = info_part.replace('by', '-').strip()
                formatted_info += ' ' + info_part
            else:
                formatted_info = info_part

        allowed_words = [word for word in formatted_info.split() if word.lower() not in bad_words]
        final_title = '{0} '.format(result_title) + ' '.join(allowed_words).strip('-').strip()

        return final_title

    @staticmethod
    def _has_only_subs(title):

        title = title.lower()

        if 'sub' in title:
            title = title.split()
            counter = 0
            for word in title:
                if 'ita' in word:
                    counter += 1
            if counter < 2:
                return True


provider = TNTVillageProvider()
