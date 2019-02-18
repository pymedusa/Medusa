# coding=utf-8

"""Provider code for Anizb provider."""

from __future__ import unicode_literals

import logging

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import convert_size, try_int
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.nzb.nzb_provider import NZBProvider

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Anizb(NZBProvider):
    """Nzb Provider using the open api of anizb.org for daily (rss) and backlog/forced searches."""

    def __init__(self):
        """Initialize the class."""
        super(Anizb, self).__init__('Anizb')

        # Credentials
        self.public = True

        # URLs
        self.url = 'https://anizb.org/'
        self.urls = {
            'search': urljoin(self.url, 'api'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.supports_absolute_numbering = True
        self.anime_only = True
        self.search_separator = '*'

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

        # Search Params
        search_params = {
            'q': '',
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})
                    search_params['q'] = search_string

                response = self.session.get(self.urls['search'], params=search_params)
                if not response or not response.text:
                    log.debug('No data returned from provider')
                    continue
                elif not response.text.startswith('<?xml'):
                    log.info('Expected xml but got something else, is your mirror failing?')
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
            entries = html('item')

            for item in entries:
                try:
                    title = item.title.get_text(strip=True)
                    download_url = item.enclosure.get('url').strip()
                    if not (title and download_url):
                        continue

                    # description = item.find('description')
                    size = convert_size(item.enclosure.get('length'), default=-1)

                    pubdate_raw = item.pubdate.get_text(strip=True)
                    pubdate = self.parse_pubdate(pubdate_raw)

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'pubdate': pubdate,
                    }

                    items.append(item)
                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    log.exception('Failed parsing provider.')

        return items

    def _get_size(self, item):
        """Override the default _get_size to prevent it from extracting using the default tags."""
        return try_int(item.get('size'))


provider = Anizb()
