# coding=utf-8

"""Provider code for RSS Torrents."""

from __future__ import unicode_literals

import io
import logging
import os
import re

from bencodepy import DEFAULT as BENCODE

from medusa import (
    app,
    helpers,
    tv,
)
from medusa.helper.exceptions import ex
from medusa.providers.torrent.torrent_provider import TorrentProvider

log = logging.getLogger(__name__)
log.logger.addHandler(logging.NullHandler())


class TorrentRssProvider(TorrentProvider):
    """Torrent RSS provider."""

    def __init__(self, name, url='', cookies='', title_tag=None, search_mode='eponly', search_fallback=False,
                 enable_daily=False, enable_backlog=False, enable_manualsearch=False):
        """Initialize the class."""
        super(TorrentRssProvider, self).__init__(name)

        # Credentials

        # URLs
        self.url = url.rstrip('/')

        # Proper Strings

        # Miscellaneous Options
        self.supports_backlog = False
        self.search_mode = search_mode
        self.search_fallback = search_fallback
        self.enable_daily = enable_daily
        self.enable_manualsearch = enable_manualsearch
        self.enable_backlog = enable_backlog
        self.enable_cookies = True
        self.cookies = cookies
        self.required_cookies = ('uid', 'pass')
        self.title_tag = title_tag or 'title'

        # Torrent Stats

        # Cache
        self.cache = TorrentRssCache(self, min_time=15)

    def _get_title_and_url(self, item):
        """Get title and url from result."""
        title = item.get(self.title_tag, '').replace(' ', '.')

        attempt_list = [
            lambda: item.get('torrent_magneturi'),
            lambda: item.enclosures[0].href,
            lambda: item.get('link')
        ]

        url = None
        for cur_attempt in attempt_list:
            try:
                url = cur_attempt()
            except Exception:
                continue

            if title and url:
                break

        return title, url

    def config_string(self):
        """Return default RSS torrent provider config setting."""
        return '{}|{}|{}|{}|{}|{}|{}|{}|{}|{}'.format(
            self.name or '',
            self.url or '',
            self.cookies or '',
            self.title_tag or '',
            int(self.enabled),
            self.search_mode or '',
            int(self.search_fallback),
            int(self.enable_daily),
            int(self.enable_manualsearch),
            int(self.enable_backlog)
        )

    @staticmethod
    def get_providers_list(providers):
        """Return custom rss torrent providers."""
        return [TorrentRssProvider(custom_provider) for custom_provider in providers]

    def image_name(self):
        """Return RSS torrent image."""
        if os.path.isfile(os.path.join(app.THEME_DATA_ROOT, 'assets/img/providers/', self.get_id() + '.png')):
            return self.get_id() + '.png'
        return 'torrentrss.png'

    def validate_rss(self):
        """Validate if RSS."""
        try:
            add_cookie = self.add_cookies_from_ui()
            if not add_cookie.get('result'):
                return add_cookie

            data = self.cache._get_rss_data()['entries']
            if not data:
                return {'result': False,
                        'message': 'No items found in the RSS feed {0}'.format(self.url)}

            title, url = self._get_title_and_url(data[0])

            if not title:
                return {'result': False,
                        'message': 'Unable to get title from first item'}

            if not url:
                return {'result': False,
                        'message': 'Unable to get torrent url from first item'}

            if url.startswith('magnet:') and re.search(r'urn:btih:([\w]{32,40})', url):
                return {'result': True,
                        'message': 'RSS feed Parsed correctly'}
            else:
                torrent_file = self.session.get_content(url)
                try:
                    # `bencodepy` is monkeypatched in `medusa.init`
                    BENCODE.decode(torrent_file, allow_extra_data=True)
                except Exception as error:
                    self.dump_html(torrent_file)
                    return {'result': False,
                            'message': 'Torrent link is not a valid torrent file: {0}'.format(ex(error))}

            return {'result': True, 'message': 'RSS feed Parsed correctly'}

        except Exception as error:
            return {'result': False, 'message': 'Error when trying to load RSS: {0}'.format(ex(error))}

    @staticmethod
    def dump_html(data):
        """Dump html data."""
        dump_name = os.path.join(app.CACHE_DIR, 'custom_torrent.html')

        try:
            file_out = io.open(dump_name, 'wb')
            file_out.write(data)
            file_out.close()
            helpers.chmod_as_parent(dump_name)
        except IOError as error:
            log.error('Unable to save the file: {0}', error)
            return False

        log.info('Saved custom_torrent html dump {0} ', dump_name)
        return True


class TorrentRssCache(tv.Cache):
    """RSS torrent cache class."""

    def _get_rss_data(self):
        """Get RSS data."""
        return self.get_rss_feed(self.provider.url)
