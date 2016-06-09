# coding=utf-8
# Author: seedboy
#

#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import re
import traceback

from requests.utils import dict_from_cookiejar

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.exceptions import AuthException
from sickrage.helper.common import convert_size
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class IPTorrentsProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        TorrentProvider.__init__(self, 'IPTorrents')

        self.username = None
        self.password = None
        self.freeleech = False
        self.minseed = None
        self.minleech = None

        self.cache = tvcache.TVCache(self, min_time=10)  # Only poll IPTorrents every 10 minutes max

        self.urls = {'base_url': 'https://iptorrents.eu',
                     'login': 'https://iptorrents.eu/torrents/',
                     'search': 'https://iptorrents.eu/t?%s%s&q=%s&qf=#torrents'}

        self.url = self.urls['base_url']

        self.categories = '73=&60='

    def _check_auth(self):

        if not self.username or not self.password:
            raise AuthException('Your authentication credentials for {0} are missing, check your config.'.format(self.name))

        return True

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {'username': self.username,
                        'password': self.password,
                        'login': 'submit'}

        self.get_url(self.urls['login'], returns='text')
        response = self.get_url(self.urls['login'], post_data=login_params, returns='text')
        if not response:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        # Invalid username and password combination
        if re.search('Invalid username and password combination', response):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            return False

        # You tried too often, please try again after 2 hours!
        if re.search('You tried too often', response):
            logger.log('You tried too often, please try again after 2 hours! Disable IPTorrents for at least 2 hours', logger.WARNING)
            return False

        return True

    def search(self, search_params, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        results = []
        if not self.login():
            return results

        freeleech = '&free=on' if self.freeleech else ''

        for mode in search_params:
            items = []
            logger.log('Search Mode: {0}'.format(mode), logger.DEBUG)
            for search_string in search_params[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {0}'.format(search_string),
                               logger.DEBUG)

                # URL with 50 tv-show results, or max 150 if adjusted in IPTorrents profile
                search_url = self.urls['search'] % (self.categories, freeleech, search_string)
                search_url += ';o=seeders' if mode != 'RSS' else ''

                data = self.get_url(search_url, returns='text')
                if not data:
                    continue

                try:
                    data = re.sub(r'(?im)<button.+?<[\/]button>', '', data, 0)
                    with BS4Parser(data, 'html5lib') as html:
                        if not html:
                            logger.log('No data returned from provider', logger.DEBUG)
                            continue

                        if html.find(text='No Torrents Found!'):
                            logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                            continue

                        torrent_table = html.find('table', attrs={'class': 'torrents'})
                        torrents = torrent_table('tr') if torrent_table else []

                        # Continue only if one Release is found
                        if len(torrents) < 2:
                            logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                            continue

                        for result in torrents[1:]:
                            try:
                                title = result('td')[1].find('a').text
                                download_url = self.urls['base_url'] + result('td')[3].find('a')['href']
                                seeders = int(result.find('td', attrs={'class': 'ac t_seeders'}).text)
                                leechers = int(result.find('td', attrs={'class': 'ac t_leechers'}).text)
                                torrent_size = result('td')[5].text
                                size = convert_size(torrent_size) or -1

                                if not all([title, download_url]):
                                    continue

                                # Filter unseeded torrent
                                if seeders < min(self.minseed, 1):
                                    if mode != 'RSS':
                                        logger.log("Discarding torrent because it doesn't meet the minimum seeders: {0}. Seeders: {1})".format
                                                   (title, seeders), logger.DEBUG)
                                    continue

                                item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders,
                                        'leechers': leechers, 'pubdate': None, 'hash': None}
                                if mode != 'RSS':
                                    logger.log('Found result: {0} with {1} seeders and {2} leechers'.format(title, seeders, leechers), logger.DEBUG)

                                items.append(item)
                            except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                                logger.log('Failed parsing provider. Traceback: {0!r}'.format
                                           (traceback.format_exc()), logger.ERROR)
                                continue

                except Exception:
                    logger.log('Failed parsing provider. Traceback: {0!r}'.format
                               (traceback.format_exc()), logger.ERROR)
            results += items

        return results


provider = IPTorrentsProvider()
