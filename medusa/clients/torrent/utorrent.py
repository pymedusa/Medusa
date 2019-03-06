# coding=utf-8

"""uTorrent Client."""

from __future__ import unicode_literals

import logging
import os
import re
from collections import OrderedDict

from medusa import app
from medusa.clients.torrent.generic import GenericClient
from medusa.logger.adapters.style import BraceAdapter

from requests.compat import urljoin
from requests.exceptions import RequestException

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


def get_torrent_subfolder(result):
    """Retrieve the series destination-subfolder required for uTorrent WebUI 'start' action."""
    # Get the subfolder name the user has assigned to that series
    root_dirs = app.ROOT_DIRS
    if root_dirs:
        root_location = root_dirs[int(root_dirs[0]) + 1]
    torrent_path = result.series.location

    if root_dirs and root_location != torrent_path:
        # Subfolder is under root, but possibly not directly under
        if torrent_path.startswith(root_location):
            torrent_subfolder = torrent_path.replace(root_location, '')
        # Subfolder is NOT under root, use it too (WebUI limitation)
        else:
            torrent_subfolder = os.path.basename(torrent_path)
    # Use the series name if there is no subfolder defined
    else:
        torrent_subfolder = result.series.name

    log.debug('Show {name}: torrent download destination folder is: {path} (sub-folder: {sub})',
              {'name': result.series.name, 'path': torrent_path, 'sub': torrent_subfolder})

    return torrent_subfolder


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
        try:
            self.response = self.session.get(urljoin(self.url, 'token.html'), verify=False)
        except RequestException as error:
            log.warning('Unable to authenticate with uTorrent client: {0!r}', error)
            return None

        if not self.response.status_code == 404:
            self.auth = re.findall('<div.*?>(.*?)</', self.response.text)[0]
            return self.auth

        return None

    def _add_torrent_uri(self, result):
        """Send an 'add-url' download request to uTorrent when search provider is using a magnet link."""
        # Set proper subfolder as download destination for uTorrent torrent
        torrent_subfolder = get_torrent_subfolder(result)

        return self._request(params={
            'action': 'add-url',
            # limit the param length to 1024 chars (uTorrent bug)
            's': result.url[:1024],
            'path': torrent_subfolder,
        })

    def _add_torrent_file(self, result):
        """Send an 'add-file' download request to uTorrent when the search provider is using a .torrent file."""
        # Set proper subfolder as download destination for uTorrent torrent
        torrent_subfolder = get_torrent_subfolder(result)

        return self._request(
            method='post',
            params={
                'action': 'add-file',
                'path': torrent_subfolder,
            },
            files={
                'torrent_file': (
                    '{name}.torrent'.format(name=result.name),
                    result.content,
                ),
            }
        )

    def _set_torrent_label(self, result):
        """Send a 'setprop' request to uTorrent to set a label for the torrent, optionally - the show name."""
        torrent_new_label = result.series.name

        if result.series.is_anime and app.TORRENT_LABEL_ANIME:
            label = app.TORRENT_LABEL_ANIME
        else:
            label = app.TORRENT_LABEL

        label = label.replace('%N', torrent_new_label)

        log.debug('Torrent label is now set to {path}', {'path': label})

        return self._request(
            params={
                'action': 'setprops',
                'hash': result.hash,
                's': 'label',
                'v': label,
            }
        )

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
        #  Allow 0 - as unlimitted, and "-1" - that is used to disable
        if float(app.TORRENT_SEED_TIME) >= 0:
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
            #  "stop" torrent, can always be resumed!
            'action': 'stop' if app.TORRENT_PAUSED else 'start',
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
