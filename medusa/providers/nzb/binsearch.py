# coding=utf-8
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
"""Provider code for Binsearch provider."""
from __future__ import unicode_literals

import datetime
import re
from time import time

from medusa.helper.common import (
    convert_size,
)

from medusa import (
    logger,
    tv,
)
from medusa.bs4_parser import BS4Parser
from medusa.providers.nzb.nzb_provider import NZBProvider

from requests.compat import urljoin
from pytimeparse import parse

size_regex = re.compile(r'size: (.*)(?:\\xa0)(.*), parts', re.I) 
title_regex = re.compile(r'\[? ?(.*?) ?\]? ?-? ?(?:-? ?\[.*] ?-)? ?\"(.*?)\" ?(?:yEnc)? ?\(*.*\)', re.I)

class BinSearchProvider(NZBProvider):
    """BinSearch Newznab provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('BinSearch')

        # Credentials
        self.public = True

        # URLs
        self.url = 'https://www.binsearch.info'
        self.urls = {
            'search': urljoin(self.url, 'index.php'),
            'rss': urljoin(self.url, 'rss.php')
        }

        # Proper Strings

        # Miscellaneous Options

        # Cache
        self.cache = BinSearchCache(self, min_time=30)  # only poll Binsearch every 30 minutes max

    def search(self, search_strings, age=0, ep_obj=None):
        results = []
        if not self._check_auth():
            return results
        search_params = {
            'adv_age': "",
            'xminsize': 20,
            'max': 250,
        }

        for mode in search_strings:
            items = []
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:
                search_params['q'] = search_string
                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                response = self.get_url(self.urls['search'], params=search_params)
                if not response:
                    logger.log('No data returned from provider', logger.DEBUG)
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
            torrent_table = html.find('table', class_='xMenuT')
            torrent_rows = torrent_table.find("tbody").find("tr") if torrent_table else []
            
            if len(torrent_rows) < 1:
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                return items

            # Skip column headers
            for row in torrent_table:
                cells = row('tr')[2:]
                for cell in cells:
                    attributes = cell.find_all("td")
                    nzb_id = attributes[1].find("input")["name"]
                    title = attributes[2].find("span").get_text()
                    title_re = title_regex.search(title)
                    if title_re:
                        title = title_re.group(1) or title_re.group(2) or attributes[2].find("span").get_text()
                    if not all([title, nzb_id]):
                        continue
                    torrent_size = size_regex.search(str(attributes).encode("utf-8"))
                    if torrent_size:
                        torrent_size = "{0} {1}".format(torrent_size.group(1), torrent_size.group(2))
                        size = convert_size(torrent_size) or -1
                    download_url = "https://www.binsearch.info/?action=nzb&amp;{}=1".format(nzb_id)
                    date = attributes[5].get_text()
                    detail_url = "https://www.binsearch.info/?q={0}".format(title)
                    pubdate_raw = parse(date)
                    pubdate = '{0}'.format(datetime.datetime.now() - datetime.timedelta(seconds=pubdate_raw))
                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'pubdate': pubdate,
                    }
                    if mode != 'RSS':
                        logger.log('Found result: {0}'.format
                                   (title), logger.DEBUG)

                    items.append(item)

        return items



class BinSearchCache(tv.Cache):
    """BinSearch NZB provider."""

    def __init__(self, provider_obj, **kwargs):
        """Initialize the class."""
        kwargs.pop('search_params', None)  # does not use _get_rss_data so strip param from kwargs...
        search_params = None  # ...and pass None instead
        tv.Cache.__init__(self, provider_obj, search_params=search_params, **kwargs)

        # compile and save our regular expressions

        # this pulls the title from the URL in the description
        self.descTitleStart = re.compile(r'^.*https?://www\.binsearch\.info/.b=')
        self.descTitleEnd = re.compile('&amp;.*$')

        # these clean up the horrible mess of a title if the above fail
        self.titleCleaners = [
            re.compile(r'.?yEnc.?\(\d+/\d+\)$'),
            re.compile(r' \[\d+/\d+\] '),
        ]

    def _get_title_and_url(self, item):
        """
        Retrieve the title and URL data from the item XML node.

        item: An elementtree.ElementTree element representing the <item> tag of the RSS feed

        Returns: A tuple containing two strings representing title and URL respectively
        """
        title = item.get('description')
        if title:
            if self.descTitleStart.match(title):
                title = self.descTitleStart.sub('', title)
                title = self.descTitleEnd.sub('', title)
                title = title.replace('+', '.')
            else:
                # just use the entire title, looks hard/impossible to parse
                title = item.get('title')
                if title:
                    for titleCleaner in self.titleCleaners:
                        title = titleCleaner.sub('', title)

        url = item.get('link')
        if url:
            url = url.replace('&amp;', '&')

        return title, url

    def update_cache(self):
        """Updade provider cache."""
        # check if we should update
        if not self.should_update():
            return

        # clear cache
        self._clear_cache()

        # set updated
        self.updated = time()

        cl = []
        for group in ['alt.binaries.hdtv', 'alt.binaries.hdtv.x264', 'alt.binaries.tv', 'alt.binaries.tvseries']:
            search_params = {'max': 50, 'g': group}
            data = self.get_rss_feed(self.provider.urls['rss'], search_params)['entries']
            if not data:
                logger.log('No data returned from provider', logger.DEBUG)
                continue

            for item in data:
                ci = self._parse_item(item)
                if ci:
                    cl.append(ci)

        if cl:
            cache_db_con = self._get_db()
            cache_db_con.mass_action(cl)

    def _check_auth(self, data):
        return data if data['feed'] and data['feed']['title'] != 'Invalid Link' else None


provider = BinSearchProvider()
