# coding=utf-8

"""Provider code for BJ-Share."""

from __future__ import unicode_literals

import logging
import re

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
            'today': urljoin(self.url, "torrents.php?action=today"),
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

        self.quality = {
            'Full HD': '1080p',
            'HD': '720p'
        }

        self.animes_with_broken_seasons_numbering = [
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

        manual_search = kwargs.get('manual_search')
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

        if anime:
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

                    url = self.urls['today'] if mode == "RSS" else self.urls['search']
                    search_params = None if mode == "RSS" else search_params
                    response = self.session.get(url, params=search_params)
                    if not response:
                        log.debug("No data returned from provider")
                        continue

                    if mode == "RSS":
                        result = self._parse_rss(response.content)
                    else:
                        result = self._parse(response.content, search_string)
                    has_next_page = result['has_next_page']
                    items += result['items']

                # For each search mode sort all the items by seeders if available
                items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)

                results += items

        return results

    def _parse(self, data, search_string):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param search_string: Original search string

        :return: A KV with a list of items found and if there's an next page to search
        """
        items = []
        has_next_page = False
        with BS4Parser(data, "html5lib") as html:
            torrent_table = html.find("table", id="torrent_table")
            torrent_rows = torrent_table("tr") if torrent_table else []

            year_re = re.search(r"\((\d{4})\)|(\d{4})", search_string, re.I)
            searching_year = '' if year_re is None else year_re.group(1)

            has_next_page = html.find("a", attrs={"class", "pager_next"}) is not None
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
                torrent = {}
                try:
                    anime = "filter_cat[14]=14" in result.find("td", attrs={"class": "cats_col"}).find("a")[
                        "href"]
                    title = cells[labels.index("Nome/Ano")].find("a", dir="ltr").get_text(strip=True)
                    dual_title_re = re.search(r"(.*) \[(.*?)\]", title)
                    if dual_title_re:
                        torrent['national_title'] = dual_title_re.group(1)
                        torrent['international_name'] = dual_title_re.group(2)
                    else:
                        torrent['national_title'] = None
                        torrent['international_name'] = title

                    year = cells[labels.index("Nome/Ano")].find("a", dir="ltr").next_sibling.strip().replace(
                        '[', '').replace(']', '')
                    torrent['year'] = year
                    download_url = urljoin(self.url,
                                           cells[labels.index("Nome/Ano")].find("a", title="Baixar")["href"])
                    if not all([title, download_url]):
                        continue

                    seeders = try_int(cells[labels.index("Seeders")].get_text(strip=True))
                    leechers = try_int(cells[labels.index("Leechers")].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < self.minseed or leechers < self.minleech:
                        log.debug("Discarding torrent because it doesn't meet the"
                                  " minimum seeders or leechers: {0} (S:{1} L:{2})".format
                                  (title, seeders, leechers))
                        continue

                    torrent_details = cells[labels.index("Nome/Ano")].find("div", attrs={
                        "class": "torrent_info"}).get_text(strip=True).replace('[', '').replace(']', '')

                    torrent_details_slitted = torrent_details.split('/')
                    details = []
                    for torrent_detail in torrent_details_slitted:
                        detail = torrent_detail.strip()
                        details.append(detail)

                    if len(details) >= 7 and details[6] != 'Free':
                        resolution = self.quality.get(details[6])
                        resolution = details[6] if resolution is None else resolution
                    else:
                        resolution = '480p'

                    source = details[3]
                    codec = details[2]
                    audio = details[4]
                    ext = details[0]

                    torrent_size = cells[labels.index("Tamanho")].get_text(strip=True)
                    size = convert_size(torrent_size, units=self.units) or -1
                    try:
                        season = re.findall(r"(?:s|season)(\d{2})", title, re.I)[0]
                    except IndexError:
                        season = ''

                    try:
                        episode = re.findall(r"(?:e|x|episode|ep|\n)(\d{2,4})", title, re.I)[0]
                    except IndexError:
                        episode = ''

                    title = torrent['international_name']
                    if not torrent['national_title'] and season.isdigit() and episode.isdigit():
                        title = title[:title.rfind('-')].strip()

                    # Include year in result only if the search have it
                    search_year_fmt = ''
                    if searching_year != '':
                        search_year_fmt = " ({0})".format(torrent['year'])

                    if anime and title in self.animes_with_broken_seasons_numbering:
                        # Some animes season is broken, so ignore it and include only the episode
                        # In this case, the episode is in absolute format
                        torrent_name = u"{0}{1} E{2} {3} {4} {5} {6}" \
                            .format(title, search_year_fmt, episode, resolution, source, codec, audio)
                    elif season.isdigit() and not episode.isdigit():
                        # Season Pack
                        torrent_name = u"{0}{1} S{2} {3} {4} {5} {6}" \
                            .format(title, search_year_fmt, season, resolution, source, codec, audio)
                    elif season.isdigit() and episode.isdigit():
                        # Season with episode included
                        torrent_name = u"{0}{1} S{2}E{3} {4} {5} {6} {7}" \
                            .format(title, search_year_fmt, season, episode, resolution, source, codec, audio)
                    else:
                        # Probably movie or something else that does not have season or episode
                        torrent_name = u"{0}{1} {2} {3} {4} {5}" \
                            .format(title, search_year_fmt, resolution, source, codec, audio)

                    if searching_year != '' and torrent['year'] != searching_year:
                        # If the year is included in the search term, skip releases with different year
                        log.debug("Discarding result, different year than being searched: {0}".format(
                            torrent_name))
                        continue

                    # Removing accents due to an bug that i noticed that the torrent is not being sent to
                    # qBittorrent when accents are present, there was no error in log.
                    torrent_name = re.sub('\s+', ' ', self._remove_accents(torrent_name)).strip()
                    if ext:
                        torrent_name = u"{0}.{1}".format(torrent_name, ext)

                    items.append({
                        'title': torrent_name,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'hash': ''
                    })

                    log.debug("Found result: {0} with {1} seeders and {2} leechers".format
                              (torrent_name, seeders, leechers))

                except StandardError:
                    continue
        return {'has_next_page': has_next_page, 'items': items}

    def _parse_rss(self, data):
        """
        Parse rss results for items.

        :param data: The raw response from a search
        :param search_string: Original search string

        :return: A KV with a list of items found and if there's an next page to search
        """
        items = []
        has_next_page = False
        with BS4Parser(data, "html5lib") as html:

            torrent_table = html.find("table", attrs={"class", "torrent_table"})
            torrent_rows = torrent_table("tr") if torrent_table else []

            # Continue only if at least one Release is found
            if len(torrent_rows) < 2:
                log.debug("Data returned from provider does not contain any torrents")
                return {'has_next_page': has_next_page, 'items': []}

            # "", "", "Name /Year", "Files", "Time", "Size", "Snatches", "Seeders", "Leechers"
            labels = [self._process_column_header(label) for label in torrent_rows[0]("th")]

            # Skip column headers
            for result in torrent_rows[1:]:
                cells = result("td")
                if len(cells) < len(labels):
                    continue
                torrent = {}
                try:
                    anime = "filter_cat[14]=14" in result.find("td").find("a")["href"]
                    title = cells[labels.index("Nome")].find("a").find("font").get_text(strip=True)
                    dual_title_re = re.search(r"(.*) \[(.*?)\]", title)
                    if dual_title_re:
                        torrent['national_title'] = dual_title_re.group(1)
                        torrent['international_name'] = dual_title_re.group(2)
                    else:
                        torrent['national_title'] = None
                        torrent['international_name'] = title

                    details = self._remove_accents(str(cells[labels.index("Nome")].find("a").find("span")))

                    audio_re = re.search(r"(?s)(?<=Audio: ).*?(?=<br/>)", details)
                    # pubdate_re = re.search(r"(?s)(?<=Lancado em: ).*?(?=<br/>)", details)
                    size_re = re.search(r"(?s)(?<=Tamanho: ).*?(?=<br/>)", details)
                    year_re = re.search(r"(?s)(?<=Ano: ).*?(?=<br/>)", details)
                    # resolution_re = re.search(r"(?s)(?<=Resolucao: ).*?(?=<br/>)", details)
                    quality_re = re.search(r"(?s)(?<=Qualidade: ).*?(?=<br/>)", details)
                    format_re = re.search(r"(?s)(?<=Formato: ).*?(?=<br/>)", details)

                    torrent['year'] = None if not year_re else year_re.group(0)
                    download_url = urljoin(self.url, cells[labels.index("Baixar")].find("a")["href"])
                    if not all([title, download_url]):
                        continue

                    seeders = try_int(cells[labels.index("Seeders")].get_text(strip=True))
                    leechers = try_int(cells[labels.index("Leechers")].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < self.minseed or leechers < self.minleech:
                        continue

                    details = cells[labels.index("Nome")].find_all("font")
                    if len(details) >= 3:
                        resolution = self.quality[details[2].get_text()]
                        resolution = details[6] if resolution is None else resolution
                    else:
                        resolution = '480p'

                    source = '' if not quality_re else quality_re.group(0)
                    codec = ''
                    audio = '' if not audio_re else audio_re.group(0)
                    ext = '' if not format_re else format_re.group(0)

                    torrent_size = size_re.group(0)
                    size = convert_size(torrent_size, units=self.units) or -1
                    try:
                        season = re.findall(r"(?:s|season)(\d{2})", title, re.I)[0]
                    except IndexError:
                        season = ''

                    try:
                        episode = re.findall(r"(?:e|x|episode|ep|\n)(\d{2,4})", title, re.I)[0]
                    except IndexError:
                        episode = ''

                    title = torrent['international_name']
                    if not torrent['national_title'] and season.isdigit() and episode.isdigit():
                        title = title[:title.rfind('-')].strip()

                    if anime and title in self.animes_with_broken_seasons_numbering:
                        # Some animes season is broken, so ignore it and include only the episode
                        # In this case, the episode is in absolute format
                        torrent_name = u"{0} E{1} {2} {3} {4} {5}" \
                            .format(title, episode, resolution, source, codec, audio)
                    elif season.isdigit() and not episode.isdigit():
                        # Season Pack
                        torrent_name = u"{0} S{1} {2} {3} {4} {5}" \
                            .format(title, season, resolution, source, codec, audio)
                    elif season.isdigit() and episode.isdigit():
                        # Season with episode included
                        torrent_name = u"{0} S{1}E{2} {3} {4} {5} {6}" \
                            .format(title, season, episode, resolution, source, codec, audio)
                    else:
                        # Probably movie or something else that does not have season or episode
                        torrent_name = u"{0} {1} {2} {3} {4}" \
                            .format(title, resolution, source, codec, audio)
                    # Removing accents due to an bug that i noticed that the torrent is not being sent to
                    # qBittorrent when accents are present, there was no error in log.
                    torrent_name = re.sub('\s+', ' ', self._remove_accents(torrent_name)).strip()
                    if ext:
                        torrent_name = u"{0}.{1}".format(torrent_name, ext)

                    items.append({
                        'title': torrent_name,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'hash': ''
                    })

                except StandardError:
                    continue
        return {'has_next_page': False, 'items': items}

    @staticmethod
    def _process_column_header(td):
        ret = u""
        if td.img and 'seeders' in td.img.attrs.get('src'):
            return u"Seeders"
        if td.img and 'leechers' in td.img.attrs.get('src'):
            return u"Leechers"
        if td.a and td.a.img:
            ret = td.a.img.get("title", td.a.get_text(strip=True))
        if not ret:
            ret = td.get_text(strip=True)
        return ret

    def login(self):
        """Login method used for logging in before doing a search and torrent downloads."""
        return self.cookie_login('Login', check_url=self.urls['search'])

    @staticmethod
    def _remove_accents(string):
        """Remove all accents from string."""
        if type(string) is not unicode:
            string = unicode(string, encoding='utf-8')

        string = re.sub(u"[àáâãäå]", 'a', string)
        string = re.sub(u"[èéêë]", 'e', string)
        string = re.sub(u"[ìíîï]", 'i', string)
        string = re.sub(u"[òóôõö]", 'o', string)
        string = re.sub(u"[ùúûü]", 'u', string)
        string = re.sub(u"[ýÿ]", 'y', string)
        string = re.sub(u"[ç]", 'ç', string)
        string = re.sub(u"[Ç]", 'Ç', string)
        string = re.sub(u"[ÀÁÂÃÄÅ]", 'A', string)
        string = re.sub(u"[ÈÉÊË]", 'E', string)
        string = re.sub(u"[ÌÍÎÏ]", 'I', string)
        string = re.sub(u"[ÒÓÔÕÖ]", 'O', string)
        string = re.sub(u"[ÙÚÛÜ]", 'U', string)
        string = re.sub(u"[ÝŸ]", 'Y', string)

        return string


provider = BJShareProvider()
