# coding=utf-8

"""Provider code for BJ-Share."""

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


class BJShareProvider(TorrentProvider):
    """BJ-Share Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(BJShareProvider, self).__init__('BJ-Share')

        # URLs
        self.url = 'https://bj-share.me'
        self.urls = {
            'detail': urljoin(self.url, "torrents.php?id=%s"),
            'search': urljoin(self.url, "torrents.php"),
            'download': urljoin(self.url, "%s"),
        }

        # Credentials
        self.enable_cookies = True
        self.cookies = ''
        self.required_cookies = ['session']

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Miscellaneous Options
        self.supports_absolute_numbering = True
        self.max_back_pages = 2
        self.units = ["B", "KB", "MB", "GB", "TB", "PB"]

        # Proper Strings
        self.proper_strings = ["PROPER", "REPACK", "REAL", "RERIP"]

        # Cache
        self.cache = tv.Cache(self, min_time=30)

        self.quality = OrderedDict([
            ('Full HD ', '1080p'),
            ('HD ', '720p'),
            ('4K', '2160p')])

        self.absolute_numbering = [
            'One Piece'
        ]

    def search(self, search_strings, age=0, ep_obj=None, **kwargs):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Informations about the episode being searched (when not RSS)

        :returns: A list of search results (structure)
        """
        results = []
        if not self.login():
            return results

        manual_search = "manual_search" in kwargs and kwargs['manual_search']
        if manual_search:
            self.max_back_pages = 20

        anime = False
        if ep_obj and ep_obj.series:
            anime = ep_obj.series.anime == 1

        search_params = {
            "order_by": "time",
            "order_way": "desc",
            "group_results": 0,
            "action": "basic",
            "searchsubmit": 1
        }

        if 'RSS' in search_strings.keys():
            search_params["filter_cat[14]"] = 1  # anime
            search_params["filter_cat[2]"] = 1  # tv shows
        elif anime:
            search_params["filter_cat[14]"] = 1
        else:
            search_params["filter_cat[2]"] = 1

        for mode in search_strings:
            items = []
            log.debug(u"Search Mode: {0}".format(mode))

            # if looking for season, look for more pages
            if mode == 'Season' and not manual_search:
                self.max_back_pages = 10

            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    log.debug(u"Search string: {0}".format(search_string.decode("utf-8")))

                # Remove season / episode from search (not supported by tracker)
                search_str = re.sub(r'\d+$' if anime else r'[S|E]\d\d', '', search_string).strip()
                # Remove year from search (not supported by tracker)
                search_str = re.sub(r"\((\d{4})\)$", '', search_str).strip()

                search_params['searchstr'] = search_str

                next_page = 1
                has_next_page = True
                while has_next_page and next_page <= self.max_back_pages:

                    search_params["page"] = next_page
                    log.debug(u"Page Search: {0}".format(next_page))
                    next_page += 1

                    response = self.session.get(self.urls['search'], params=search_params)
                    if not response:
                        log.debug("No data returned from provider")
                        continue

                    result = self._parse(response.content, mode, search_string)
                    has_next_page = result['has_next_page']
                    items += result['items']

                # For each search mode sort all the items by seeders if available
                items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)

                results += items

        return results

    def _parse(self, data, mode, search_string):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS
        :param search_string: Original search string

        :return: A KV with a list of items found and if there's an next page to search
        """
        items = []
        has_next_page = False
        with BS4Parser(data, "html5lib") as html:
            torrent_table = html.find("table", id="torrent_table")
            torrent_rows = torrent_table("tr") if torrent_table else []

            # year_re = re.search(r"\((\d{4})\)|(\d{4})", search_string, re.I)

            # ignore next page in RSS mode
            has_next_page = mode != 'RSS' and html.find("a", attrs={"class", "pager_next"}) is not None
            log.debug(u"More Pages? {0}".format(has_next_page))

            # Continue only if at least one Release is found
            if len(torrent_rows) < 2:
                log.debug("Data returned from provider does not contain any torrents")
                return {'has_next_page': has_next_page, 'items': []}

            # "", "", "Name /Year", "Files", "Time", "Size", "Snatches", "Seeders", "Leechers"
            labels = [self._process_column_header(label) for label in torrent_rows[0]("td")]

            # Skip column headers
            for result in torrent_rows[1:]:
                cells = result("td")
                if len(cells) < len(labels):
                    continue
                try:
                    title = cells[labels.index("Nome/Ano")].find("a", dir="ltr").get_text(strip=True)
                    # get international title if available
                    title = re.sub(".* \[(.*?)\](.*)", r"\1\2", title)

                    for serie in self.absolute_numbering:
                        if serie in title:
                            # remove season from title when its in absolute format
                            title = re.sub("S\d{2}(E\d{2,4})", r"\1", title)
                            break

                    download_url = urljoin(self.url, cells[labels.index("Nome/Ano")].find("a", title="Baixar")["href"])
                    if not all([title, download_url]):
                        continue

                    seeders = try_int(cells[labels.index("Seeders")].get_text(strip=True))
                    leechers = try_int(cells[labels.index("Leechers")].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < self.minseed or leechers < self.minleech:
                        if mode != "RSS":
                            log.debug("Discarding torrent because it doesn't meet the"
                                      " minimum seeders or leechers: {0} (S:{1} L:{2})".format
                                      (title, seeders, leechers))
                        continue

                    torrent_details = cells[labels.index("Nome/Ano")].find("div", attrs={
                        "class": "torrent_info"}).get_text(strip=True).replace('[', ' ').replace(']', ' ')\
                        .replace('/', ' ')

                    for key, value in self.quality.iteritems():
                        torrent_details = torrent_details.replace(key, value)

                    torrent_size = cells[labels.index("Tamanho")].get_text(strip=True)
                    size = convert_size(torrent_size, units=self.units) or -1

                    torrent_name = "{0} {1}".format(title, torrent_details.strip()).strip()
                    torrent_name = re.sub('\s+', ' ', torrent_name)

                    items.append({
                        'title': torrent_name,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'hash': ''
                    })

                    if mode != "RSS":
                        log.debug("Found result: {0} with {1} seeders and {2} leechers".format
                                  (torrent_name, seeders, leechers))

                except StandardError:
                    continue
        return {'has_next_page': has_next_page, 'items': items}

    @staticmethod
    def _process_column_header(td):
        ret = u""
        if td.a and td.a.img:
            ret = td.a.img.get("title", td.a.get_text(strip=True))
        if not ret:
            ret = td.get_text(strip=True)
        return ret

    def login(self):
        """Login method used for logging in before doing a search and torrent downloads."""
        return self.cookie_login('Login', check_url=self.urls['search'])


provider = BJShareProvider()
