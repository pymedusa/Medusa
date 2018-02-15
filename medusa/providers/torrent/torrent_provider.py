# coding=utf-8

"""Provider code for Generic Torrent Provider."""

from __future__ import unicode_literals

import logging
import os

import bencode
from bencode.BTL import BTFailure
from feedparser.util import FeedParserDict

from medusa import app
from medusa.classes import TorrentSearchResult
from medusa.helper.common import try_int
from medusa.helpers import remove_file_failed
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.generic_provider import GenericProvider

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class TorrentProvider(GenericProvider):
    """Generic Torrent provider."""

    def __init__(self, name):
        """Initialize the class."""
        super(TorrentProvider, self).__init__(name)

        self.ratio = None
        self.provider_type = GenericProvider.TORRENT

    def is_active(self):
        """Check if provider is enabled."""
        return bool(app.USE_TORRENTS) and self.is_enabled()

    @property
    def _custom_trackers(self):
        """Check if provider has custom trackers."""
        if not self.public or not app.TRACKERS_LIST:
            return ''

        return '&tr=' + '&tr='.join(x.strip() for x in app.TRACKERS_LIST if x.strip())

    def _get_result(self, episodes):
        """Return a provider result object."""
        return TorrentSearchResult(episodes, provider=self)

    def _get_size(self, item):
        """Get result size."""
        if isinstance(item, dict):
            size = item.get('size', -1)
        elif isinstance(item, (list, tuple)) and len(item) > 2:
            size = item[2]
        else:
            size = -1

        # Make sure we didn't select seeds/leechers by accident
        if not size or size < 1024 * 1024:
            size = -1

        return try_int(size, -1)

    def _get_storage_dir(self):
        """Get torrent storage dir."""
        return app.TORRENT_DIR

    def _get_result_info(self, item):
        """Return seeders and leechers from result."""
        if isinstance(item, (dict, FeedParserDict)):
            seeders = item.get('seeders', '-1')
            leechers = item.get('leechers', '-1')

        elif isinstance(item, (list, tuple)) and len(item) > 1:
            seeders = item[3]
            leechers = item[4]
        else:
            seeders = -1
            leechers = -1

        return seeders, leechers

    def _get_title_and_url(self, item):
        """Get title and url from result."""
        if isinstance(item, (dict, FeedParserDict)):
            download_url = item.get('url', '')
            title = item.get('title', '')

            if not download_url:
                download_url = item.get('link', '')
        elif isinstance(item, (list, tuple)) and len(item) > 1:
            download_url = item[1]
            title = item[0]
        else:
            download_url = ''
            title = ''

        if download_url:
            download_url = download_url.replace('&amp;', '&')

        if title:
            title = title.replace(' ', '.')

        return title, download_url

    def _verify_download(self, file_name=None):
        """Validate torrent file."""
        if not file_name or not os.path.isfile(file_name):
            return False

        try:
            with open(file_name, 'rb') as f:
                meta_info = bencode.bdecode(f.read())
            return 'info' in meta_info and meta_info['info']
        except BTFailure as e:
            log.debug('Failed to validate torrent file: {name}. Error: {error}',
                      {'name': file_name, 'error': e})

        remove_file_failed(file_name)
        log.debug('{result} is not a valid torrent file',
                  {'result': file_name})

        return False

    def seed_ratio(self):
        """Return seed ratio of provider."""
        return self.ratio

    def _get_pubdate(self, item):
        """Return publish date of the item.

        If provider doesnt have _get_pubdate function this will be used
        """
        if isinstance(item, dict):
            pubdate = item.get('pubdate')
        elif isinstance(item, (list, tuple)) and len(item) > 2:
            pubdate = item[5]
        else:
            pubdate = None

        return pubdate
