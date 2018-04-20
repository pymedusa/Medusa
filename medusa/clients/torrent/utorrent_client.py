# coding=utf-8

"""uTorrent Client."""

from __future__ import unicode_literals

import logging
import re
import os

from collections import OrderedDict

from medusa import app
from medusa.clients.torrent.generic import GenericClient
from medusa.logger.adapters.style import BraceAdapter

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

def get_torrent_subfolder(result):
            # Get the sub-folder name the user has assigned to that series
            root_dirs = app.ROOT_DIRS
            root_location = root_dirs[int(root_dirs[0]) + 1]
            torrent_path = result.series._location
            torrent_subfolder = None

            if not root_location == torrent_path:
                torrent_subfolder = os.path.basename(torrent_path)
            # Use the series name if there is no subfolder defined
            else:
                torrent_subfolder = series_name

            log.info('Show {name}: torrent snatched, download destination folder is: {path} (sub-folder: {sub})',
                    {'name': result.series.name, 'path': torrent_path, 'sub': torrent_subfolder})

            return(torrent_subfolder)


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

        # Set proper subfolder as download destination for uTorrent torrent 
        torrent_subfolder = get_torrent_subfolder(result)

        return self._request(params={
            'action': 'add-url',
            # limit the param length to 1024 chars (uTorrent bug)
            's': result.url[:1024],
            # add torrent path to request
            'path': torrent_subfolder,
        })

    def _add_torrent_file(self, result):

        # Set proper subfolder as download destination for uTorrent torrent 
        torrent_subfolder = get_torrent_subfolder(result)

        return self._request(
            method='post',
            params={
                'action': 'add-file',
                # add torrent path to request
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
        torrent_new_label = result.series.name

        if result.series.is_anime and app.TORRENT_LABEL_ANIME:
            label = app.TORRENT_LABEL_ANIME
        else:
            label = app.TORRENT_LABEL

        log.info('torrent label was {path}',
                    {'path': label})

        label = label.replace('%N',torrent_new_label)

        log.info('torrent label is now set to {path}', {'path': label})

        #  Always use show name as label? TBD.
        # if not label:
        #    label = torrent_new_label

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
