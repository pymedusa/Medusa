# coding=utf-8

"""Provider code for Newpct."""

from __future__ import unicode_literals

import logging
import re
from collections import OrderedDict

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import convert_size, try_int
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class NewpctProvider(TorrentProvider):
    """Newpct Torrent provider."""

    search_regex = re.compile(r'(.*) S0?(\d+)E0?(\d+)')
    anime_search_regex = re.compile(r'(.*) (\d+)')
    torrent_id = re.compile(r'\/(\d{6,7})_')

    def __init__(self):
        """Initialize the class."""
        super(NewpctProvider, self).__init__('Newpct')

        # Credentials
        self.public = True

        # URLs
        self.url = 'http://www.tvsinpagar.com'
        self.urls = OrderedDict([
            ('daily', urljoin(self.url, 'ultimas-descargas')),
            ('torrent_url', urljoin(self.url, 'descargar-torrent/{0}_{1}.html')),
            ('download_series', urljoin(self.url, 'descargar-serie/{0}/capitulo-{1}/hdtv/')),
            ('download_series_hd', urljoin(self.url, 'descargar-seriehd/{0}/capitulo-{1}/hdtv-720p-ac3-5-1/')),
            ('download_series_vo', urljoin(self.url, 'descargar-serievo/{0}/capitulo-{1}/')),
        ])

        # Proper Strings

        # Miscellaneous Options
        self.supports_absolute_numbering = True
        self.onlyspasearch = None
        self.torrent_id_counter = None

        # Torrent Stats

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

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            if self.series and (self.series.air_by_date or self.series.is_sports):
                log.debug("Provider doesn't support air by date or sports search")
                continue

            # Only search if user conditions are true
            if self.onlyspasearch and lang_info != 'es' and mode != 'RSS':
                log.debug('Show info is not Spanish, skipping provider search')
                continue

            for search_string in search_strings[mode]:

                search_urls = [self.urls['daily']]

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                    name, chapter = self._parse_title(search_string)
                    search_urls = [self.urls[url].format(name, chapter) for url in self.urls
                                   if url.startswith('download')]

                for url in search_urls:
                    response = self.session.get(url)
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
        self.torrent_id_counter = 0

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find('div', class_='content')

            torrent_rows = []
            if torrent_table:
                torrent_rows = torrent_table('div', class_='info') if mode == 'RSS' else [torrent_table]

            # Continue only if at least one release is found
            if not torrent_rows or not torrent_rows[0]:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            for row in torrent_rows:
                try:
                    if mode == 'RSS':
                        quality = row.find('span', id='deco')
                        if not quality.get_text(strip=True).startswith('HDTV'):
                            if self.torrent_id_counter:
                                self.torrent_id_counter -= 1
                            continue

                        anchor = row.find('a')
                        if not self.torrent_id_counter:
                            torrent_content = self._get_content(anchor.get('href'), mode)
                            if not torrent_content:
                                continue
                            title, torrent_id, torrent_size, pubdate_raw = torrent_content
                        else:
                            self.torrent_id_counter -= 1
                            h2 = anchor.h2.get_text(strip=True).replace('  ', ' ')
                            title = '{0} {1}'.format(h2, quality.contents[0].strip())
                            torrent_id = self.torrent_id_counter
                            torrent_size = quality.contents[1].text.replace('Tamaño', '').strip()
                    else:
                        torrent_info = self._parse_download(row, mode)
                        if not torrent_info:
                            continue
                        title, torrent_id, torrent_size, pubdate_raw = torrent_info

                    if not all([title, torrent_id]):
                        continue

                    download_url = self.urls['torrent_url'].format(torrent_id, title)

                    seeders = 1  # Provider does not provide seeders
                    leechers = 0  # Provider does not provide leechers

                    size = convert_size(torrent_size) or -1

                    pubdate = self.parse_pubdate(pubdate_raw, dayfirst=True)

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

    def _parse_title(self, search_string):
        if self.series and self.series.is_anime:
            search_matches = NewpctProvider.anime_search_regex.match(search_string)
            name = search_matches.group(1)
            chapter = '1{0}'.format(search_matches.group(2))
        else:
            search_matches = NewpctProvider.search_regex.match(search_string)
            name = search_matches.group(1)
            chapter = '{0}{1}'.format(search_matches.group(2), search_matches.group(3))

        norm_name = re.sub(r'\W', '-', name)
        title = norm_name.replace('--', '-').strip('-').lower()

        return title, chapter

    def _get_content(self, torrent_url, mode):
        response = self.session.get(torrent_url)
        if not response or not response.text:
            log.debug('No data returned for first item')
            return

        with BS4Parser(response.text, 'html5lib') as html:
            torrent_content = html.find('div', class_='content')
            if not torrent_content:
                log.debug('Wrong data returned for first item')
                return

            return self._parse_download(torrent_content, mode)

    def _parse_download(self, torrent_content, mode):
        torrent_dl = torrent_content.find('div', id='tabs_content_container')
        if not torrent_dl:
            log.debug('No data returned for searched item')
            return

        torrent_h1 = torrent_content.find('h1')
        title = torrent_h1.get_text(' ', strip=True).split('/')[-1].strip()

        torrent_info = torrent_content.find('div', class_='entry-left')
        spans = torrent_info('span', class_='imp')
        size = spans[0].contents[1].strip()
        pubdate_raw = spans[1].contents[1].strip()

        dl_script = torrent_dl.find('script', type='text/javascript').get_text(strip=True)
        item_id = try_int(NewpctProvider.torrent_id.search(dl_script).group(1))

        if mode == 'RSS' and not self.torrent_id_counter:
            self.torrent_id_counter = item_id

        return title, item_id, size, pubdate_raw


provider = NewpctProvider()
