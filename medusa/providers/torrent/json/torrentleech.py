# coding=utf-8

"""Provider code for TorrentLeech."""

from __future__ import division, unicode_literals

import logging
import math

from medusa import tv
from medusa.helper.common import convert_size
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from six.moves import range

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class TorrentLeechProvider(TorrentProvider):
    """TorrentLeech Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(TorrentLeechProvider, self).__init__('TorrentLeech')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://www.torrentleech.org'
        self.urls = {
            'login': urljoin(self.url, 'user/account/login'),
            'search': urljoin(self.url, 'torrents/browse/list/'),
            'download': urljoin(self.url, 'download/{id}/{file}'),
            'details': urljoin(self.url, 'torrent/{id}'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL', 'RERIP']

        # Miscellaneous Options
        self.max_torrents = 100

        # Cache
        self.cache = tv.Cache(self)

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

        # Categories:
        #   TV
        #     26: Episodes
        #     27: BoxSets
        #     32: Episodes HD
        #   Animation
        #     34: Anime
        #     35: Cartoons
        #   Foreign
        #     44: Foreign

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            # Configured for: mode == 'RSS'
            search_params = {
                'categories': ['26', '27', '32', '34', '35', '44'],
                'query': '',
                'orderby': 'added',
                'order': 'desc',
            }

            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                    search_params['categories'] = ['35']
                    search_params['categories'] += ['26', '32', '44'] if mode == 'Episode' else ['27']
                    if self.series and self.series.is_anime:
                        search_params['categories'] += ['34']

                    search_params['query'] = search_string
                    search_params['orderby'] = 'seeders'

                fragments = 'categories/{categories}/'
                if search_params['query']:
                    fragments += 'query/{query}/'
                fragments += 'orderby/{orderby}/order/{order}/'

                path_params = fragments.format(
                    categories=','.join(search_params['categories']),
                    query=search_params['query'],
                    orderby=search_params['orderby'],
                    order=search_params['order']
                )
                search_url = urljoin(self.urls['search'], path_params)

                data = self.session.get_json(search_url)
                if not data:
                    log.debug('No data returned from provider')
                    continue

                results += self.parse(data, mode)

                # Handle pagination
                results += self._pagination(data, mode, search_url)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """
        items = []

        torrents = data['torrentList']
        user_timezone = data.get('userTimeZone', 'UTC')

        # Continue only if at least one release is found
        if not torrents:
            log.debug('Data returned from provider does not contain any torrents')
            return items

        for torrent in torrents:
            try:
                title = torrent['name']
                download_url = self.urls['download'].format(id=torrent['fid'], file=torrent['filename'])

                seeders = int(torrent['seeders'])
                leechers = int(torrent['leechers'])

                # Filter unseeded torrent
                if seeders < self.minseed:
                    if mode != 'RSS':
                        log.debug("Discarding torrent because it doesn't meet the"
                                  ' minimum seeders: {0}. Seeders: {1}',
                                  title, seeders)
                    continue

                size = convert_size(torrent['size']) or -1

                pubdate_raw = torrent['addedTimestamp']
                pubdate = self.parse_pubdate(pubdate_raw, timezone=user_timezone)

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

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""
        cookies = dict_from_cookiejar(self.session.cookies)
        if any(cookies.values()) and cookies.get('member_id'):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'login': 'submit',
            'remember_me': 'on',
        }

        response = self.session.post(self.urls['login'], data=login_params)
        if not response or not response.text:
            log.warning('Unable to connect to provider')
            return False

        if '<title>Login :: TorrentLeech.org</title>' in response.text:
            log.warning('Invalid username or password. Check your settings')
            return False

        return True

    def _pagination(self, data, mode, search_url):
        """If needed, query the next page(s) of results, parse them and return."""
        results = []
        num_found = data.get('numFound', 0)
        per_page = data.get('perPage', 35)

        if per_page < 100 and num_found > per_page:
            log.warning('It is recommended to change "Default Results Per Page" to 100'
                        ' in your profile options on {name}.', {'name': self.name})

        try:
            pages = int(math.ceil(self.max_torrents / per_page))
        except ZeroDivisionError:
            pages = 1

        if num_found and num_found > per_page and pages > 1:
            log.debug('Total results found: {total}, getting {pages} more page{s} of results', {
                'total': num_found,
                'pages': pages - 1,
                's': ('', 's')[pages - 1 > 1]
            })

            for page in range(2, pages + 1):
                page_url = urljoin(search_url, 'page/{page}/'.format(page=page))
                data = self.session.get_json(page_url)

                if not data:
                    log.debug('Page {0} returned no data from provider,'
                              ' not getting more pages.', page)
                    break

                log.debug('Parsing page {0} of results', page)
                results += self.parse(data, mode)

        return results


provider = TorrentLeechProvider()
