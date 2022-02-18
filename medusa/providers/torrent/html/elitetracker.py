# coding=utf-8

"""Provider code for EliteTracker."""

from __future__ import unicode_literals

import logging
import re

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import (
    convert_size,
    try_int,
)
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class EliteTrackerProvider(TorrentProvider):
    """EliteTracker Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(EliteTrackerProvider, self).__init__('EliteTracker')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://elite-tracker.net'
        self.urls = {
            'login': urljoin(self.url, '/takelogin.php'),
            'search': urljoin(self.url, '/browse.php')
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL', 'RERIP']

        # Miscellaneous Options
        self.translation = {
            'heures': 'hours',
            'jour': 'day',
            'jours': 'days',
            'mois': 'month',
            'an': 'year',
            'années': 'years'
        }

        # Cache
        self.cache = tv.Cache(self, min_time=30)

        # Freeleech
        self.freeleech = False

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
            'do': 'search',
            'search_type': 't_name',
            'category': 30,
            'include_dead_torrents': 'no',
            'submit': 'search'
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                search_params['keywords'] = search_string
                search_params['category'] = 30
                response = self.session.get(self.urls['search'], params=search_params)
                if not response or not response.text:
                    log.debug('No data returned from provider')
                    continue

                results += self.parse(response.text, mode, keywords=search_string)

        return results

    def parse(self, data, mode, **kwargs):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS.

        :return: A list of items found
        """
        items = []

        keywords = kwargs.pop('keywords', None)

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find(id='sortabletable')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if torrent_rows[1].get_text(strip=True) == 'Aucun résultat':
                log.debug('Data returned from provider does not contain any torrents')
                return items

            labels = [label.img['title'] if label.img else label.get_text(strip=True) for label in
                      torrent_rows[0]('td')]
            for torrent in torrent_rows[1:]:
                try:
                    if self.freeleech and not torrent.find('img', alt=re.compile('TORRENT GRATUIT : Seulement '
                                                                                 "l'upload sera compter.")):
                        continue

                    title = torrent.find(class_='tooltip-content').div.get_text(strip=True)
                    download_url = torrent.find(title='Télécharger le torrent!').parent['href']
                    if not all([title, download_url]):
                        continue

                    # Chop off tracker/channel prefix or we cannot parse the result!
                    if mode != 'RSS' and keywords:
                        show_name_first_word = re.search(r'^[^ .]+', keywords).group()
                        if not title.startswith(show_name_first_word):
                            title = re.sub(r'.*(' + show_name_first_word + '.*)', r'\1', title)

                    seeders = try_int(torrent.find(title='Seeders').get_text(strip=True))
                    leechers = try_int(torrent.find(title='Leechers').get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    torrent_size = torrent('td')[labels.index('Taille')].get_text(strip=True)
                    size = convert_size(torrent_size) or -1

                    # Get Pubdate if it is available. Sometimes only PRE is displayed.
                    pubdate_raw = torrent('td')[labels.index('Nom')].find_all('div')[-1].get_text(strip=True)
                    pubdate = None
                    if 'PRE' not in pubdate_raw:
                        pubdate = self.parse_pubdate(pubdate_raw, dayfirst=True)

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': pubdate
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
        if len(self.session.cookies) > 3:
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'logout': 'no',
            'submit': 'LOGIN',
            'returnto': '/browse.php'
        }

        response = self.session.post(self.urls['login'], data=login_params)
        if not response:
            log.warning('Unable to connect to provider')
            return False

        if "Une erreur s'est produite!" in response.text:
            log.warning('Invalid username or password. Check your settings')
            return False

        return True


provider = EliteTrackerProvider()
