# coding=utf-8
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
"""Provider code for Generic Torrent Provider."""
import os

import bencode
from bencode.BTL import BTFailure

from feedparser.util import FeedParserDict

from ..generic_provider import GenericProvider
from ... import app, logger
from ...classes import TorrentSearchResult
from ...helper.common import try_int
from ...helpers import remove_file_failed


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
        if not (app.TRACKERS_LIST and self.public):
            return ''

        return '&tr=' + '&tr='.join({x.strip() for x in app.TRACKERS_LIST.split(',') if x.strip()})

    def _get_result(self, episodes):
        """Return provider result."""
        return TorrentSearchResult(episodes)

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
            logger.log(u'Failed to validate torrent file: {name}. Error: {error}'.format
                       (name=file_name, error=e), logger.DEBUG)

        remove_file_failed(file_name)
        logger.log(u'{result} is not a valid torrent file'.format(result=file_name), logger.WARNING)

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

    def _get_torrent_hash(self, item):
        """
        Return torrent_hash of the item.

        If provider doesnt have _get_torrent_hash function this will be used
        """
        if isinstance(item, dict):
            torrent_hash = item.get('torrent_hash')
        elif isinstance(item, (list, tuple)) and len(item) > 2:
            torrent_hash = item[6]
        else:
            torrent_hash = None

        return torrent_hash
