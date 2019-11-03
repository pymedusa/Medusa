# coding=utf-8

"""Provider code for Binsearch provider."""

from __future__ import unicode_literals

import logging
import re
from builtins import zip
from os.path import join

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import convert_size, sanitize_filename
from medusa.helpers import download_file
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.nzb.nzb_provider import NZBProvider

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class BinSearchProvider(NZBProvider):
    """BinSearch Newznab provider."""

    size_regex = re.compile(r'size: (\d+\.\d+\xa0\w{2}), parts', re.I)
    title_regex = re.compile(r'\"([^\"]+)"', re.I)
    title_reqex_clean = re.compile(r'^[ \d_]+ (.+)')
    title_regex_rss = re.compile(r'- \"([^\"]+)"', re.I)
    nzb_check_segment = re.compile(r'<segment bytes="[\d]+"')

    def __init__(self):
        """Initialize the class."""
        super(BinSearchProvider, self).__init__('BinSearch')

        # Credentials
        self.public = True

        # URLs
        self.url = 'https://www.binsearch.info'
        self.urls = {
            'search': urljoin(self.url, 'index.php'),
            'rss': urljoin(self.url, 'browse.php'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL', 'RERIP']

        # Miscellaneous Options

        # Cache
        self.cache = tv.Cache(self)

    def search(self, search_strings, **kwargs):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :returns: A list of search results (structure)
        """
        results = []
        search_params = {
            'adv_age': '',
            'xminsize': 20,
            'max': 250,
        }
        groups = [1, 2]

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)
            # https://www.binsearch.info/browse.php?bg=alt.binaries.teevee&server=2
            for search_string in search_strings[mode]:
                search_params['q'] = search_string
                for group in groups:
                    # Try both 'search in the most popular groups' & 'search in the other groups' modes
                    search_params['server'] = group
                    if mode != 'RSS':
                        log.debug('Search string: {search}', {'search': search_string})
                        search_url = self.urls['search']
                    else:
                        search_params = {
                            'bg': 'alt.binaries.teevee',
                            'server': 2,
                            'max': 50,
                        }
                        search_url = self.urls['rss']

                    response = self.session.get(search_url, params=search_params)
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
        def process_column_header(td):
            return td.get_text(strip=True).lower()

        items = []

        with BS4Parser(data, 'html5lib') as html:

            # We need to store the post url, to be used with every result later on.
            post_url = html.find('form', {'method': 'post'})['action']

            table = html.find('table', class_='xMenuT')
            rows = table('tr') if table else []
            row_offset = 1
            if not rows or not len(rows) - row_offset:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            headers = rows[0]('th')
            # 0, 1, subject, poster, group, age
            labels = [process_column_header(header) or idx
                      for idx, header in enumerate(headers)]

            # Skip column headers
            rows = rows[row_offset:]
            for row in rows:
                try:
                    col = dict(list(zip(labels, row('td'))))
                    nzb_id_input = col[0 if mode == 'RSS' else 1].find('input')
                    if not nzb_id_input:
                        continue
                    nzb_id = nzb_id_input['name']
                    # Try and get the the article subject from the weird binsearch format
                    title = self.clean_title(col['subject'].text, mode)

                except AttributeError:
                    log.debug('Parsing rows, that may not always have useful info. Skipping to next.')
                    continue
                if not all([title, nzb_id]):
                    continue

                # Obtain the size from the 'description'
                size_field = BinSearchProvider.size_regex.search(col['subject'].text)
                if size_field:
                    size_field = size_field.group(1)
                size = convert_size(size_field, sep='\xa0') or -1
                size = int(size)

                download_url = urljoin(self.url, '{post_url}|nzb_id={nzb_id}'.format(post_url=post_url, nzb_id=nzb_id))

                # For future use
                # detail_url = 'https://www.binsearch.info/?q={0}'.format(title)
                human_time = True
                date = col['age' if mode != 'RSS' else 'date'].get_text(strip=True).replace('-', ' ')
                if mode == 'RSS':
                    human_time = False
                pubdate_raw = date
                pubdate = self.parse_pubdate(pubdate_raw, human_time=human_time)

                item = {
                    'title': title,
                    'link': download_url,
                    'size': size,
                    'pubdate': pubdate,
                }
                if mode != 'RSS':
                    log.debug('Found result: {0}', title)

                items.append(item)

        return items

    @staticmethod
    def clean_title(title, mode):
        """
        Clean title field, using a series of regex.

        RSS search requires different cleaning then the other searches.
        When adding to this function, make sure you update the tests.
        """
        try:
            if mode == 'RSS':
                title = BinSearchProvider.title_regex_rss.search(title).group(1)
            else:
                title = BinSearchProvider.title_regex.search(title).group(1)
                if BinSearchProvider.title_reqex_clean.search(title):
                    title = BinSearchProvider.title_reqex_clean.search(title).group(1)
            for extension in ('.nfo', '.par2', '.rar', '.zip', '.nzb', '.part'):
                # Strip extensions that aren't part of the file name
                if title.endswith(extension):
                    title = title[:len(title) - len(extension)]
            return title
        except AttributeError:
            return None

    def download_result(self, result):
        """
        Download result from provider.

        This is used when a blackhole is used for sending the nzb file to the nzb client.
        For now the url and the post data is stored as one string in the db, using a pipe (|) to separate them.

        :param result: A SearchResult object.
        :return: The result of the nzb download (True/False).
        """
        if not self.login():
            return False

        result_name = sanitize_filename(result.name)
        filename = join(self._get_storage_dir(), result_name + '.' + self.provider_type)

        if result.url.startswith('http'):
            self.session.headers.update({
                'Referer': '/'.join(result.url.split('/')[:3]) + '/'
            })

        log.info('Downloading {result} from {provider} at {url}',
                 {'result': result.name, 'provider': self.name, 'url': result.url})

        verify = False if self.public else None

        url, data = result.url.split('|')

        data = {
            data.split('=')[1]: 'on',
            'action': 'nzb',
        }

        if download_file(url, filename, method='POST', data=data, session=self.session,
                         headers=self.headers, verify=verify):

            if self._verify_download(filename):
                log.info('Saved {result} to {location}',
                         {'result': result.name, 'location': filename})
                return True

        return False

    def download_nzb_for_post(self, result):
        """
        Download the nzb content, prior to sending it to the nzb download client.

        :param result: Nzb SearchResult object.
        :return: The content of the nzb file if successful else None.
        """
        if not self.login():
            return False

        # For now to separate the url and the post data, where splitting it with a pipe.
        url, data = result.url.split('|')

        data = {
            data.split('=')[1]: 'on',
            'action': 'nzb',
        }

        log.info('Downloading {result} from {provider} at {url} and data {data}',
                 {'result': result.name, 'provider': self.name, 'url': result.url, 'data': data})

        verify = False if self.public else None

        response = self.session.post(url, data=data, headers=self.session.headers,
                                     verify=verify, hooks={}, allow_redirects=True)
        if not response or not response.content:
            log.warning('Failed to download the NZB from BinSearch')
            return None

        # Validate that the result has the content of a valid nzb.
        if not BinSearchProvider.nzb_check_segment.search(response.text):
            log.warning('Result returned from BinSearch was not a valid NZB')
            return None

        return response.content

    def _get_size(self, item):
        """
        Get result size.

        Overwrite this, as the default _get_size() from nzb_provider isn't working for us.
        :param item:
        :return: size in bytes or -1
        """
        return item.get('size', -1)

    @staticmethod
    def _get_identifier(item):
        """
        Return the identifier for the item.

        By default this is the url. Providers can overwrite this, when needed.
        """
        return '{name}_{size}'.format(name=item.name, size=item.size)


provider = BinSearchProvider()
