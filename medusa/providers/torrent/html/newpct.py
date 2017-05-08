# coding=utf-8

"""Provider code for Newpct."""

from __future__ import unicode_literals

import logging
import re
import traceback

from medusa import (
    helpers,
    tv,
)
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import convert_size
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class NewpctProvider(TorrentProvider):
    """Newpct Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('Newpct')

        # Credentials

        # URLs
        self.url = 'http://www.newpct.com'
        self.urls = {
            'search': urljoin(self.url, 'index.php'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.onlyspasearch = None

        # Torrent Stats

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

        # Only search if user conditions are true
        lang_info = '' if not ep_obj or not ep_obj.show else ep_obj.show.lang

        # http://www.newpct.com/index.php?l=doSearch&q=fringe&category_=All&idioma_=1&bus_de_=All
        # Search Params
        search_params = {
            'l': 'doSearch',
            'q': '',  # Show name
            'category_': 'All',  # Category 'Shows' (767)
            'idioma_': 1,  # Language Spanish (1)
            'bus_de_': 'All'  # Date from (All, hoy)
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            # Only search if user conditions are true
            if self.onlyspasearch and lang_info != 'es' and mode != 'RSS':
                log.debug('Show info is not spanish, skipping provider search')
                continue

            search_params['bus_de_'] = 'All' if mode != 'RSS' else 'hoy'

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                search_params['q'] = search_string
                response = self.get_url(self.urls['search'], params=search_params, returns='response')
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
            torrent_table = html.find('table', id='categoryTable')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 3:  # Headers + 1 Torrent + Pagination
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # 'Fecha', 'Título', 'Tamaño', ''
            # Date,    Title,     Size
            labels = [label.get_text(strip=True) for label in torrent_rows[0]('th')]

            # Skip column headers
            for row in torrent_rows[1:-1]:
                cells = row('td')

                try:
                    torrent_anchor = row.find('a')
                    title = self._process_title(torrent_anchor.get_text())
                    download_url = torrent_anchor.get('href', '')
                    if not all([title, download_url]):
                        continue

                    seeders = 1  # Provider does not provide seeders
                    leechers = 0  # Provider does not provide leechers
                    torrent_size = cells[labels.index('Tamaño')].get_text(strip=True)
                    size = convert_size(torrent_size) or -1

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
                    log.error('Failed parsing provider. Traceback: {0!r}',
                              traceback.format_exc())

        return items

    @staticmethod
    def _process_title(title):
        # Add encoder and group to title
        title = title.strip() + ' x264-NEWPCT'

        # Quality - Use re module to avoid case sensitive problems with replace
        title = re.sub(r'\[ALTA DEFINICION[^\[]*]', '720p HDTV', title, flags=re.IGNORECASE)
        title = re.sub(r'\[(BluRay MicroHD|MicroHD 1080p)[^\[]*]', '1080p BluRay', title, flags=re.IGNORECASE)
        title = re.sub(r'\[(B[RD]rip|BLuRay)[^\[]*]', '720p BluRay', title, flags=re.IGNORECASE)

        # Language
        title = re.sub(r'\[(Spanish|Castellano|Español)[^\[]*]', 'SPANISH AUDIO', title, flags=re.IGNORECASE)
        title = re.sub(r'\[AC3 5\.1 Español[^\[]*]', 'SPANISH AUDIO AC3 5.1', title, flags=re.IGNORECASE)

        return title

    def get_url(self, url, post_data=None, params=None, timeout=30, **kwargs):
        """
        Parse URL to get the torrent file.

        :return: 'content' when trying access to torrent info (For calling torrent client).
        """
        trickery = kwargs.pop('returns', '')
        if trickery == 'content':
            kwargs['returns'] = 'text'
            data = super(NewpctProvider, self).get_url(url, post_data=post_data, params=params, timeout=timeout,
                                                       **kwargs)
            url = re.search(r'http://tumejorserie.com/descargar/.+\.torrent', data, re.DOTALL).group()

        kwargs['returns'] = trickery
        return super(NewpctProvider, self).get_url(url, post_data=post_data, params=params,
                                                   timeout=timeout, **kwargs)

    def download_result(self, result):
        """Save the result to disk."""
        # check for auth
        if not self.login():
            return False

        urls, filename = self._make_url(result)

        for url in urls:
            # Search results don't return torrent files directly,
            # it returns show sheets so we must parse showSheet to access torrent.
            response = self.get_url(url, returns='response')
            url_torrent = re.search(r'http://tumejorserie.com/descargar/.+\.torrent', response.text, re.DOTALL).group()

            if url_torrent.startswith('http'):
                self.headers.update({'Referer': '/'.join(url_torrent.split('/')[:3]) + '/'})

            log.info('Downloading a result from {0}', url)

            if helpers.download_file(url_torrent, filename, session=self.session, headers=self.headers):
                if self._verify_download(filename):
                    log.info('Saved result to {0}', filename)
                    return True
                else:
                    log.warning('Could not download {0}', url)
                    helpers.remove_file_failed(filename)

        if urls:
            log.warning('Failed to download any results')

        return False


provider = NewpctProvider()
