# coding=utf-8

"""Provider code for Newpct."""

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


class NewpctProvider(TorrentProvider):
    """Newpct Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(NewpctProvider, self).__init__('Newpct')

        # Credentials
        self.public = True

        # URLs
        self.url = 'http://www.tvsinpagar.com'
        self.urls = {'search':  [urljoin(self.url, '/series'),
                                 urljoin(self.url, '/series-hd')],
                     # 'searchvo': urljoin(self.url, '/series-vo'),
                     'daily':    urljoin(self.url, '/ultimas-descargas/pg/{0}'),
                     'letter':  [urljoin(self.url, '/series/letter/{0}'),
                                 urljoin(self.url, '/series-hd/letter/{0}')],
                     # 'lettervo': urljoin(self.url, '/series-vo/letter/{0}'),
                     'downloadregex': r'[^\"]*/descargar-torrent/\d+_[^\"]*'}

        # Proper Strings

        # Miscellaneous Options
        self.supports_absolute_numbering = True
        self.onlyspasearch = None

        self.recent_url = ''
        self.max_daily_pages = 10

        # Torrent Stats

        # Cache
        self.cache = tv.Cache(self, min_time=20)

    def _get_episode_search_strings(self, episode, add_string=''):
        """Get episode search strings."""
        if not episode:
            return []

        search_string = {'Episode': []}

        for show_name in episode.series.get_all_possible_names(season=episode.scene_season):
            search_string['Episode'].append(show_name.strip())

        return [search_string]

    def _get_season_search_strings(self, episode):
        """Get search search strings."""
        search_string = {'Season': []}

        for show_name in episode.series.get_all_possible_names(season=episode.season):
            search_string['Season'].append(show_name.strip())

        return [search_string]

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

        if self.series and (self.series.air_by_date or self.series.is_sports):
            log.debug("Provider doesn't support air by date or sports search")
            return results

        # collect modes, series names, series first letters
        rss_requested = False
        manual_search_requested = False
        series_names = []
        letters = []
        for mode in search_strings:
            if mode == 'RSS':
                rss_requested = True
            else:
                manual_search_requested = True
                for search_string in search_strings[mode]:
                    name = search_string.strip().lower()
                    if name not in series_names:
                        series_names.append(name)
                    letter = name[0] if not name[0].isdigit() else '0-9'
                    if letter not in letters:
                        letters.append(letter)

        if rss_requested:
            log.debug('Search mode: RSS')

            recent_url = self.recent_url
            pg = 1
            while pg <= self.max_daily_pages:
                response = self.session.get(self.urls['daily'].format(pg))
                if not response or not response.text:
                    log.debug('No data returned from provider')
                    break

                items = self._parse_daily_content(response.text)
                if not items:
                    break
                results += items

                # check if we need to go for the next daily page
                if pg == 1:
                    self.recent_url = items[0]['link']
                item_found = any(item['link'] == recent_url for item in items)
                if item_found:
                    break

                pg += 1

        if manual_search_requested:
            log.debug('Episode search')

            # Only search if user conditions are true
            if self.onlyspasearch and lang_info != 'es':
                log.debug('Show info is not Spanish, skipping provider search')
                return results

            for letter in letters:
                for letter_url in self.urls['letter']:
                    response = self.session.get(letter_url.format(letter))
                    if not response or not response.text:
                        continue

                    # get links to series episodes list
                    series_parsed = self._parse_series_list_content(series_names, response.text)
                    if not series_parsed or not len(series_parsed):
                        continue

                    for series_parsed_item in series_parsed:
                        pg = 1
                        while pg < 100:
                            response = self.session.get(series_parsed_item['url'] + '/pg/' + str(pg))
                            if not response or not response.text:
                                break

                            items = self._parse_episodes_list_content(response.text)
                            if not items:
                                break
                            results += items

                            pg += 1

        return results

    def _parse_daily_content(self, data):
        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find('div', class_='content')

            torrent_rows = []
            if torrent_table:
                torrent_rows = torrent_table('div', class_='info')

            # Continue only if at least one release is found
            if not torrent_rows:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            for row in torrent_rows:
                try:
                    row_spans = row.find_all('span')
                    # check if it's an episode
                    if len(row_spans) < 3 or 'capitulo' not in row_spans[2].get_text().lower():
                        continue

                    anchor_item = row.find('a')
                    title = anchor_item.get_text().replace('\t', '').strip()
                    details_url = anchor_item.get('href', '')

                    quality_text = row_spans[0].contents[0].strip()
                    size_text = row_spans[0].contents[1].text.replace(u'Tama\u00f1o', '').strip()

                    row_strongs = row.find_all('strong')
                    language_text = row_strongs[1].get_text().strip()

                    seeders = 1  # Provider does not provide seeders
                    leechers = 0  # Provider does not provide leechers
                    size = convert_size(size_text) or -1

                    composed_title = 'Serie {0} - {1} Calidad [{2}]'.format(title, language_text, quality_text)

                    title = self._parse_composed_title(composed_title, details_url)

                    item = {
                        'title': title,
                        'link': details_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                    }

                    items.append(item)

                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    log.exception('Failed parsing provider daily content.')

        return items

    def _parse_series_list_content(self, series_names, data):
        results = []

        with BS4Parser(data) as html:
            series_table = html.find('ul', class_='pelilist')

            series_rows = []
            if series_table:
                series_rows = series_table('li') if series_table else []

            # Continue only if at least one series is found
            if not series_rows:
                log.debug('Data returned from provider does not contain any series')
                return results

            for row in series_rows:
                try:
                    series_anchor = row.find_all('a')[0]
                    title = series_anchor.get('title', '').strip().lower()
                    url = series_anchor.get('href', '')
                    if title and title in series_names:
                        item = {
                            'title': title,
                            'url': url,
                        }
                        results.append(item)

                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    log.exception('Failed parsing series list content.')

        return results

    def _parse_episodes_list_content(self, data):

        items = []

        with BS4Parser(data) as html:
            torrent_table = html.find('ul', class_='buscar-list')

            torrent_rows = []
            if torrent_table:
                torrent_rows = torrent_table('div', class_='info')

            # Continue only if at least one release is found
            if not torrent_rows:
                log.debug('Data returned from provider does not contain any episodes')
                return items

            for row in torrent_rows:
                try:
                    anchor_item = row.find('a')
                    title = anchor_item.get_text().replace('\t', '').strip()
                    details_url = anchor_item.get('href', '')

                    row_spans = row.find_all('span')
                    size = convert_size(row_spans[3].get_text().strip()) if row_spans and len(row_spans) >= 4 else -1
                    pubdate_text = row_spans[2].get_text().strip() if row_spans and len(row_spans) >= 3 else ''

                    seeders = 1  # Provider does not provide seeders
                    leechers = 0  # Provider does not provide leechers

                    title = self._parse_composed_title(title, details_url)

                    item = {
                        'title': title,
                        'link': details_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': pubdate_text,
                    }

                    items.append(item)

                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    log.exception('Failed parsing episode list content.')

        return items

    def _parse_composed_title(self, composed_title, url):
        # Serie Juego De Tronos  Temporada 7 Capitulo 5 - Español Castellano Calidad [ HDTV ]
        # Serie Juego De Tronos  Temporada [7] Capitulo [5] - Español Castellano Calidad [ HDTV ]
        # Serie El Estrangulador De Rillington Place Capitulos 1 al 3 - Español Castellano Calidad [ HDTV 720p AC3 5.1 ]
        # Serie Van Helsing - Temporada 2 Capitulos 9 al 13 - Español Castellano Calidad [ HDTV 720p AC3 5.1 ]
        # The Big Bang Theory - Temporada 1 [HDTV][Cap.101][Spanish]

        result = composed_title

        regex = r'Serie(.+?)(Temporada ?\[?(\d+)\]?.*)?Capitulos? ?\[?(\d+)\]? ?(al ?\[?(\d+)\]?)?.*- ?(.*) ?Calidad ?(.+)'

        match = re.search(regex, composed_title, flags=re.I)
        if match:
            name = match.group(1).strip(' -')
            season = match.group(3).strip() if match.group(3) else 1
            episode = match.group(4).strip().zfill(2)
            audio_quality = match.group(7).strip(' []')
            video_quality = match.group(8).strip(' []')

            if not match.group(5):
                result = "{0} - Temporada {1} [{2}][Cap.{3}{4}][{5}]".format(name, season, video_quality, season,
                                                                             episode, audio_quality)
            else:
                episode_to = match.group(6).strip().zfill(2)
                result = "{0} - Temporada {1} [{2}][Cap.{3}{4}_{5}{6}][{7}]".format(name, season, video_quality,
                                                                                    season, episode, season, episode_to,
                                                                                    audio_quality)

        # add "NEWPCT" to allow results be filtered by the "required words" tvshow filter
        result = result + '[NEWPCT]'

        # help quality parser
        result = result.replace('HDTV', 'x264 HDTV')

        return result

    def _get_torrent_url(self, details_page_url):
        if not details_page_url:
            log.debug('Torrent url empty')
            return None

        response = self.session.get(details_page_url)
        if not response or not response.text:
            log.debug('No data returned while downloading details page')
            return

        with BS4Parser(response.text, 'html5lib') as html:
            match = re.search(r'' + self.urls['downloadregex'], html.text, re.I)
            if not match:
                log.debug('No torrent url found in details page')
                return None
            return match.group()

    def get_content(self, url, params=None, timeout=30, **kwargs):
        torrent_url = self._get_torrent_url(url)
        if not torrent_url:
            torrent_url = url

        return super(NewpctProvider, self).get_content(torrent_url, params=params, timeout=timeout, **kwargs)

    def download_result(self, result):
        torrent_url = self._get_torrent_url(result.url)
        if torrent_url:
            result.url = torrent_url

        return super(NewpctProvider, self).download_result(result)


provider = NewpctProvider()
