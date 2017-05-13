# coding=utf-8

"""Provider code for Binsearch provider."""

from __future__ import unicode_literals

import logging
import re
from time import time

from medusa import tv
from medusa.providers.nzb.nzb_provider import NZBProvider

from requests.compat import urljoin

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class BinSearchProvider(NZBProvider):
    """BinSearch Newznab provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('BinSearch')

        # Credentials
        self.public = True
        self.supports_backlog = False

        # URLs
        self.url = 'https://www.binsearch.info'
        self.urls = {
            'rss': urljoin(self.url, 'rss.php')
        }

        # Proper Strings

        # Miscellaneous Options

        # Cache
        self.cache = BinSearchCache(self, min_time=30)  # only poll Binsearch every 30 minutes max


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

        :item: An elementtree.ElementTree element representing the <item> tag of the RSS feed
        :return: A tuple containing two strings representing title and URL respectively
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
                log.debug('No data returned from provider')
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
