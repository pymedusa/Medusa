# coding=utf-8
# This file is part of Medusa.
#
# Git: https://github.com/PyMedusa/SickRage.git
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


from feedparser.util import FeedParserDict
from hachoir_parser import createParser
import medusa as sickbeard
from ..GenericProvider import GenericProvider
from ... import logger
from ...classes import TorrentSearchResult
from ...helper.common import try_int
from ...helper.exceptions import ex


class TorrentProvider(GenericProvider):
    def __init__(self, name):
        GenericProvider.__init__(self, name)
        self.ratio = None
        self.provider_type = GenericProvider.TORRENT

    def is_active(self):
        return bool(sickbeard.USE_TORRENTS) and self.is_enabled()

    @property
    def _custom_trackers(self):
        if not (sickbeard.TRACKERS_LIST and self.public):
            return ''

        return '&tr=' + '&tr='.join({x.strip() for x in sickbeard.TRACKERS_LIST.split(',') if x.strip()})

    def _get_result(self, episodes):
        return TorrentSearchResult(episodes)

    def _get_size(self, item):
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
        return sickbeard.TORRENT_DIR

    def _get_result_info(self, item):
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

        if title.endswith('DIAMOND'):
            logger.log(u'Skipping DIAMOND release for mass fake releases.')
            download_url = title = u'FAKERELEASE'

        if download_url:
            download_url = download_url.replace('&amp;', '&')

        if title:
            title = title.replace(' ', '.')

        return title, download_url

    def _verify_download(self, file_name=None):
        try:
            parser = createParser(file_name)

            if parser:
                # pylint: disable=protected-access
                # Access to a protected member of a client class
                mime_type = parser._getMimeType()

                try:
                    parser.stream._input.close()
                except Exception:
                    pass

                if mime_type == 'application/x-bittorrent':
                    return True
        except Exception as e:
            logger.log(u'Failed to validate torrent file: %s' % ex(e), logger.DEBUG)

        logger.log(u'Result is not a valid torrent file', logger.DEBUG)
        return False

    def seed_ratio(self):
        return self.ratio

    def _get_pubdate(self, item):
        """
        Return publish date of the item. If provider doesnt
        have _get_pubdate function this will be used
        """
        if isinstance(item, dict):
            pubdate = item.get('pubdate')
        elif isinstance(item, (list, tuple)) and len(item) > 2:
            pubdate = item[5]
        else:
            pubdate = None

        return pubdate

    def _get_hash(self, item):
        """
        Return hash of the item. If provider doesnt
        have _get_hash function this will be used
        """
        if isinstance(item, dict):
            hash = item.get('hash')
        elif isinstance(item, (list, tuple)) and len(item) > 2:
            hash = item[6]
        else:
            hash = None

        return hash
