# coding=utf-8

"""Provider code for Generic Torrent Provider."""

from __future__ import unicode_literals

import logging
import os
import re
from base64 import b16encode, b32decode
from contextlib import suppress
from os.path import join
from random import shuffle

from bencodepy import BencodeDecodeError, DEFAULT as BENCODE

from feedparser.util import FeedParserDict

from medusa import app
from medusa.classes import TorrentSearchResult
from medusa.helper.common import sanitize_filename, try_int
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

        self.bt_cache_urls = [
            'https://asnet.pw/download/{info_hash}/',
            'https://p2pdl.com/download/{info_hash}',
            'https://itorrents.org/torrent/{info_hash}.torrent',
            'https://watercache.nanobytes.org/get/{info_hash}',
            'https://medusa.win/dl?magnet=magnet:?xt=urn:btih:{info_hash}&direct=true',
        ]
        self.ratio = None
        self.provider_type = GenericProvider.TORRENT
        self.minseed = 0
        self.minleech = 0

        # Ratio used for client actions when seed ratio reached.
        # For example: Remove torrent when upload/download ratio (4.0) reached.
        self.client_ratio = None

    def is_active(self):
        """Check if provider is enabled."""
        return bool(app.USE_TORRENTS) and self.is_enabled()

    def get_result(self, series, item=None, cache=None):
        """Get result."""
        search_result = TorrentSearchResult(provider=self, series=series,
                                            item=item, cache=cache)

        return search_result

    @property
    def _custom_trackers(self):
        """Check if provider has custom trackers."""
        if not self.public or not app.TRACKERS_LIST:
            return ''

        return '&tr=' + '&tr='.join(x.strip() for x in app.TRACKERS_LIST if x.strip())

    def _get_size(self, item):
        """Get result size."""
        if isinstance(item, dict):
            size = item.get('size', -1)
        elif isinstance(item, (list, tuple)) and len(item) > 2:
            size = item[2]
        else:
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

    def _verify_download(self, file_path):
        """Validate torrent file."""
        if not file_path or not os.path.isfile(file_path):
            return False

        try:
            with open(file_path, 'rb') as f:
                # `bencodepy` is monkeypatched in `medusa.init`
                meta_info = BENCODE.decode(f.read(), allow_extra_data=True)
            return 'info' in meta_info and meta_info['info']
        except BencodeDecodeError as error:
            log.debug('Failed to validate torrent file: {name}. Error: {error}',
                      {'name': file_path, 'error': error})

        remove_file_failed(file_path)
        log.debug('{result} is not a valid torrent file',
                  {'result': file_path})

        return False

    def _verify_magnet(self, file_path):
        """
        Validate Magnet file.

        Check if the Magnet file exists and has a valid info_hash.
        :param file_path: Absolute path to the Magnet file.
        :returns: True or False
        """
        if not file_path or not os.path.isfile(file_path):
            return False

        magnet_uri = None
        with open(file_path, 'r', encoding='utf-8') as fp:
            magnet_uri = fp.read()

        if self._get_info_from_magnet(magnet_uri):
            return True
        return False

    @staticmethod
    def _get_torrent_name_from_magnet(magnet_uri):
        """Try to extract a torrent name from a Magnet URI."""
        torrent_name = 'NO_DOWNLOAD_NAME'
        with suppress(Exception):
            torrent_name = re.findall('dn=([^&]+)', magnet_uri)[0]

        return torrent_name

    @staticmethod
    def _get_info_from_magnet(magnet_uri):
        """Try to extract an info_hash from a Magnet URI."""
        info_hash = re.findall(r'urn:btih:([\w]{32,40})', magnet_uri)
        if not info_hash:
            return False

        info_hash = info_hash[0]
        if len(info_hash) == 32:
            info_hash = b16encode(b32decode(info_hash))

        return info_hash.upper()

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

    def get_redirect_url(self, url):
        """Get the final address that the provided URL redirects to."""
        log.debug('Retrieving redirect URL for {url}', {'url': url})

        response = self.session.get(url, stream=True)
        if response:
            response.close()
            return response.url

        # Jackett redirects to a magnet causing InvalidSchema.
        # Use an alternative method to get the redirect URL.
        log.debug('Using alternative method to retrieve redirect URL')
        response = self.session.get(url, allow_redirects=False)
        if response and response.headers.get('Location'):
            return response.headers['Location']

        log.debug('Unable to retrieve redirect URL for {url}', {'url': url})
        return url

    def _make_url(self, result):
        """Return url if result is a Magnet URI."""
        urls = []
        filename = ''

        if not result or not result.url:
            return urls, filename

        if result.url.startswith('magnet:'):
            try:
                torrent_name = self._get_torrent_name_from_magnet(result.url)
                info_hash = self._get_info_from_magnet(result.url)

                if not info_hash:
                    log.error('Unable to extract torrent hash from magnet: {0}', result.url)
                    return urls, filename

                urls = [
                    cache_url.format(info_hash=info_hash,
                                     torrent_name=torrent_name)
                    for cache_url in self.bt_cache_urls
                ]
                shuffle(urls)
            except Exception:
                log.error('Unable to extract torrent hash or name from magnet: {0}', result.url)
                return urls, filename
        else:
            # Required for Jackett providers that use magnet redirects
            # See: https://github.com/pymedusa/Medusa/issues/3435
            if self.kind() == 'TorznabProvider':
                redirect_url = self.get_redirect_url(result.url)
                if redirect_url != result.url:
                    result.url = redirect_url
                    return self._make_url(result)

            urls = [result.url]

        result_name = sanitize_filename(result.name)
        filename = join(self._get_storage_dir(), result_name)

        return urls, filename

    @staticmethod
    def _get_identifier(item):
        """
        If the url has a magnet link, use the info hash as identifier.

        By default this is the url.
        """
        if item.url.startswith('magnet:'):
            hash = re.findall(r'urn:btih:([\w]{32,40})', item.url)
            if hash:
                return hash[0]
        return item.url
