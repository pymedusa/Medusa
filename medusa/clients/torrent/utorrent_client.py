# coding=utf-8

"""uTorrent Client."""

from __future__ import unicode_literals

import logging
import re
from collections import OrderedDict

from medusa import app
from medusa.clients.torrent.generic import GenericClient
from medusa.logger.adapters.style import BraceAdapter

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class UTorrentAPI(GenericClient):
    """uTorrent API class."""

    def __init__(self, host=None, username=None, password=None):
        """Constructor.

        :param host:
        :type host: string
        :param username:
        :type username: string
        :param password:
        :type password: string
        """
        super(UTorrentAPI, self).__init__('uTorrent', host, username, password)
        self.url = urljoin(self.host, 'gui/')

    def _request(self, method='get', params=None, data=None, files=None, cookies=None):
        if cookies:
            log.debug('{name}: Received unused argument: cookies={value!r}',
                      {'name': self.name, 'value': cookies})

        # "token" must be the first parameter: https://goo.gl/qTxf9x
        ordered_params = OrderedDict({
            'token': self.auth,
        })
        ordered_params.update(params)

        return super(UTorrentAPI, self)._request(method=method, params=ordered_params, data=data, files=files)

    def _get_auth(self):
        self.response = self.session.get(urljoin(self.url, 'token.html'), verify=False)
        if not self.response.status_code == 404:
            self.auth = re.findall('<div.*?>(.*?)</', self.response.text)[0]
            return self.auth

    def _add_torrent_uri(self, result):
        return self._request(params={
            'action': 'add-url',
            # limit the param length to 1024 chars (uTorrent bug)
            's': result.url[:1024],
        })

    def _add_torrent_file(self, result):
        return self._request(
            method='post',
            params={
                'action': 'add-file',
            },
            files={
                'torrent_file': (
                    '{name}.torrent'.format(name=result.name),
                    result.content,
                ),
            }
        )

    def _set_torrent_label(self, result):
        if result.series.is_anime and app.TORRENT_LABEL_ANIME:
            label = app.TORRENT_LABEL_ANIME
        else:
            label = app.TORRENT_LABEL

        return self._request(params={
            'action': 'setprops',
            'hash': result.hash,
            's': 'label',
            'v': label,
        })

    def _set_torrent_ratio(self, result):
        ratio = result.ratio or None

        if ratio:
            if self._request(params={
                'action': 'setprops',
                'hash': result.hash,
                's': 'seed_override',
                'v': '1',
            }):
                return self._request(params={
                    'action': 'setprops',
                    'hash': result.hash,
                    's': 'seed_ratio',
                    'v': float(ratio) * 10,
                })
            else:
                return False

        return True

    def _set_torrent_seed_time(self, result):
        if app.TORRENT_SEED_TIME:
            if self._request(params={
                'action': 'setprops',
                'hash': result.hash,
                's': 'seed_override',
                'v': '1',
            }):
                return self._request(params={
                    'action': 'setprops',
                    'hash': result.hash,
                    's': 'seed_time',
                    'v': 3600 * float(app.TORRENT_SEED_TIME),
                })
            else:
                return False
        else:
            return True

    def _set_torrent_priority(self, result):
        return True if result.priority != 1 else self._request(params={
            'action': 'queuetop',
            'hash': result.hash,
        })

    def _set_torrent_pause(self, result):
        return self._request(params={
            'action': 'pause' if app.TORRENT_PAUSED else 'start',
            'hash': result.hash,
        })

    def remove_torrent(self, info_hash):
        """Remove torrent from client using given info_hash.

        :param info_hash:
        :type info_hash: string
        :return
        :rtype: bool
        """
        return self._request(params={
            'action': 'removedatatorrent',
            'hash': info_hash,
        })


api = UTorrentAPI
