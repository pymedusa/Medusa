# coding=utf-8

"""Provider code for Anizb provider."""

from __future__ import unicode_literals

import logging

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import try_int
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
            'rss': self.url,
            'api': urljoin(self.url, 'api/?q=')
        }

        # Proper Strings

        # Miscellaneous Options
        self.supports_absolute_numbering = True
        self.anime_only = True
        self.search_separator = '*'

        # Cache
        self.cache = tv.Cache(self)

    def search(self, search_strings, age=0, ep_obj=None, **kwargs):
        """Start searching for anime using the provided search_strings. Used for backlog and daily."""
        results = []

        for mode in search_strings:
            items = []
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                    search_url = (self.urls['rss'], self.urls['api'] + search_string)[mode != 'RSS']
                    response = self.session.get(search_url)
                    if not response or not response.text:
                        log.debug('No data returned from provider')
                        continue

                    if not response.text.startswith('<?xml'):
                        log.info('Expected xml but got something else, is your mirror failing?')
                        continue

                    with BS4Parser(response.text, 'html5lib') as html:
                        entries = html('item')
                        if not entries:
                            log.info('Returned xml contained no results')
                            continue

                        for item in entries:
                            try:
                                title = item.title.get_text(strip=True)
                                download_url = item.enclosure.get('url').strip()
                                if not (title and download_url):
                                    continue

                                # description = item.find('description')
                                size = try_int(item.enclosure.get('length', -1))

                                item = {
                                    'title': title,
                                    'link': download_url,
                                    'size': size,
                                }

                                items.append(item)
                            except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                                log.exception('Failed parsing provider.')
                                continue

                results += items

            return results

    def _get_size(self, item):
        """Override the default _get_size to prevent it from extracting using the default tags."""
        return try_int(item.get('size'))


provider = Anizb()
