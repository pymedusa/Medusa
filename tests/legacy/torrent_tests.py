# coding=UTF-8
# Author: Dennis Lutter <lad1337@gmail.com>
#
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.
"""Torrent tests."""

from __future__ import print_function

from bs4 import BeautifulSoup
from medusa.helpers import get_url, make_session
from medusa.providers.torrent.json.bitcannon import BitCannonProvider
from medusa.tv import Episode, Series
from six.moves.urllib_parse import urljoin
from . import test_lib as test


class TorrentBasicTests(test.AppTestDBCase):
    """Test torrents."""

    @classmethod
    def setUpClass(cls):
        cls.shows = []

        show = Series(1, 121361)
        show.name = "Italian Works"
        show.episodes = []
        episode = Episode(show, 5, 10)
        episode.name = "Pines of Rome"
        episode.scene_season = 5
        episode.scene_episode = 10
        show.episodes.append(episode)
        cls.shows.append(show)

    def test_bitcannon(self):
        bitcannon = BitCannonProvider()
        bitcannon.custom_url = ""        # true testing requires a valid URL here (e.g., "http://localhost:3000/")
        bitcannon.api_key = ""

        if bitcannon.custom_url:
            # pylint: disable=protected-access
            search_strings_list = bitcannon._get_episode_search_strings(self.shows[0].episodes[0])  # [{'Episode': ['Italian Works S05E10']}]
            for search_strings in search_strings_list:
                bitcannon.search(search_strings)   # {'Episode': ['Italian Works S05E10']} # pylint: disable=protected-access

        return True

    @staticmethod
    def test_search():  # pylint: disable=too-many-locals
        url = 'http://kickass.to/'
        search_url = 'http://kickass.to/usearch/American%20Dad%21%20S08%20-S08E%20category%3Atv/?field=seeders&sorder=desc'

        html = get_url(search_url, session=make_session(), returns='text')
        if not html:
            return

        soup = BeautifulSoup(html, 'html5lib')

        torrent_table = soup.find('table', attrs={'class': 'data'})
        torrent_rows = torrent_table.find_all('tr') if torrent_table else []

        # cleanup memory
        soup.clear(True)

        # Continue only if one Release is found
        if len(torrent_rows) < 2:
            print("The data returned does not contain any torrents")
            return

        for row in torrent_rows[1:]:
            try:
                link = urljoin(url, (row.find('div', {'class': 'torrentname'}).find_all('a')[1])['href'])
                _id = row.get('id')[-7:]
                title = (row.find('div', {'class': 'torrentname'}).find_all('a')[1]).text \
                    or (row.find('div', {'class': 'torrentname'}).find_all('a')[2]).text
                url = row.find('a', 'imagnet')['href']
                verified = True if row.find('a', 'iverify') else False
                trusted = True if row.find('img', {'alt': 'verified'}) else False
                seeders = int(row.find_all('td')[-2].text)
                leechers = int(row.find_all('td')[-1].text)
                print((link, _id, verified, trusted, seeders, leechers))
            except (AttributeError, TypeError):
                continue

            print(title)
