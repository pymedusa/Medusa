# coding=utf-8

"""Transmission Client."""

from __future__ import unicode_literals

import json
import logging
import os
import re
from base64 import b64encode

from medusa import app
from medusa.clients.torrent.generic import GenericClient
from medusa.helpers import (
    is_already_processed_media,
    is_info_hash_in_history,
    is_info_hash_processed,
)
from medusa.logger.adapters.style import BraceAdapter

from requests.compat import urljoin


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class TransmissionAPI(GenericClient):
    """Transmission API class."""

    def __init__(self, host=None, username=None, password=None):
        """Constructor.

        :param host:
        :type host: string
        :param username:
        :type username: string
        :param password:
        :type password: string
        """
        super(TransmissionAPI, self).__init__('Transmission', host, username, password)

        self.rpcurl = self.rpcurl.strip('/')
        self.url = urljoin(self.host, self.rpcurl + '/rpc')

    def _get_auth(self):

        post_data = json.dumps({
            'method': 'session-get',
        })

        try:
            self.response = self.session.post(self.url, data=post_data.encode('utf-8'), timeout=120,
                                              verify=app.TORRENT_VERIFY_CERT)
            self.auth = re.search(r'X-Transmission-Session-Id:\s*(\w+)', self.response.text).group(1)
        except Exception:
            return None

        self.session.headers.update({'x-transmission-session-id': self.auth})

        # Validating Transmission authorization
        post_data = json.dumps({
            'arguments': {},
            'method': 'session-get',
        })

        self._request(method='post', data=post_data)

        return self.auth

    def _add_torrent_uri(self, result):

        arguments = {
            'filename': result.url,
            'paused': 1 if app.TORRENT_PAUSED else 0
        }
        if os.path.isabs(app.TORRENT_PATH):
            arguments['download-dir'] = app.TORRENT_PATH

        post_data = json.dumps({
            'arguments': arguments,
            'method': 'torrent-add',
        })

        self._request(method='post', data=post_data)

        return self.response.json()['result'] == 'success'

    def _add_torrent_file(self, result):

        arguments = {
            'metainfo': b64encode(result.content),
            'paused': 1 if app.TORRENT_PAUSED else 0
        }

        if os.path.isabs(app.TORRENT_PATH):
            arguments['download-dir'] = app.TORRENT_PATH

        post_data = json.dumps({
            'arguments': arguments,
            'method': 'torrent-add',
        })

        self._request(method='post', data=post_data)

        return self.response.json()['result'] == 'success'

    def _set_torrent_ratio(self, result):

        ratio = None
        if result.ratio:
            ratio = result.ratio

        mode = 0
        if ratio:
            if float(ratio) == -1:
                ratio = 0
                mode = 2
            elif float(ratio) >= 0:
                ratio = float(ratio)
                mode = 1  # Stop seeding at seedRatioLimit

        arguments = {
            'ids': [result.hash],
            'seedRatioLimit': ratio,
            'seedRatioMode': mode,
        }

        post_data = json.dumps({
            'arguments': arguments,
            'method': 'torrent-set',
        })

        self._request(method='post', data=post_data)

        return self.response.json()['result'] == 'success'

    def _set_torrent_seed_time(self, result):

        if app.TORRENT_SEED_TIME and app.TORRENT_SEED_TIME != -1:
            time = int(60 * float(app.TORRENT_SEED_TIME))
            arguments = {
                'ids': [result.hash],
                'seedIdleLimit': time,
                'seedIdleMode': 1,
            }

            post_data = json.dumps({
                'arguments': arguments,
                'method': 'torrent-set',
            })

            self._request(method='post', data=post_data)

            return self.response.json()['result'] == 'success'
        else:
            return True

    def _set_torrent_priority(self, result):

        arguments = {'ids': [result.hash]}

        if result.priority == -1:
            arguments['priority-low'] = []
        elif result.priority == 1:
            # set high priority for all files in torrent
            arguments['priority-high'] = []
            # move torrent to the top if the queue
            arguments['queuePosition'] = 0
            if app.TORRENT_HIGH_BANDWIDTH:
                arguments['bandwidthPriority'] = 1
        else:
            arguments['priority-normal'] = []

        post_data = json.dumps({
            'arguments': arguments,
            'method': 'torrent-set',
        })

        self._request(method='post', data=post_data)

        return self.response.json()['result'] == 'success'

    def remove_torrent(self, info_hash):
        """Remove torrent from client using given info_hash.

        :param info_hash:
        :type info_hash: string
        :return
        :rtype: bool
        """
        arguments = {
            'ids': [info_hash],
            'delete-local-data': 1,
        }

        post_data = json.dumps({
            'arguments': arguments,
            'method': 'torrent-remove',
        })

        self._request(method='post', data=post_data)

        return self.response.json()['result'] == 'success'

    def remove_ratio_reached(self):
        """Remove all Medusa torrents that ratio was reached.

        It loops in all hashes returned from client and check if it is in the snatch history
        if its then it checks if we already processed media from the torrent (episode status `Downloaded`)
        If is a RARed torrent then we don't have a media file so we check if that hash is from an
        episode that has a `Downloaded` status

        0 = Torrent is stopped
        1 = Queued to check files
        2 = Checking files
        3 = Queued to download
        4 = Downloading
        5 = Queued to seed
        6 = Seeding
        """
        log.info('Checking Transmission torrent status.')

        return_params = {
            'fields': ['id', 'name', 'hashString', 'percentDone', 'status', 'eta', 'isStalled',
                       'isFinished', 'downloadDir', 'uploadRatio', 'secondsSeeding', 'seedIdleLimit', 'files']
        }

        post_data = json.dumps({'arguments': return_params, 'method': 'torrent-get'})

        if not self._request(method='post', data=post_data):
            log.debug('Could not connect to Transmission. Check logs')
            return

        try:
            returned_data = json.loads(self.response.content)
        except ValueError:
            log.warning('Unexpected data received from Transmission: {resp}',
                        {'resp': self.response.content})
            return

        if not returned_data['result'] == 'success':
            log.debug('Nothing in queue or error')
            return

        found_torrents = False
        for torrent in returned_data['arguments']['torrents']:

            # Check if that hash was sent by Medusa
            if not is_info_hash_in_history(str(torrent['hashString'])):
                continue
            found_torrents = True

            to_remove = False
            for i in torrent['files']:
                # Check if media was processed
                # OR check hash in case of RARed torrents
                if is_already_processed_media(i['name']) or is_info_hash_processed(str(torrent['hashString'])):
                    to_remove = True

            # Don't need to check status if we are not going to remove it.
            if not to_remove:
                log.info('Torrent not yet post-processed. Skipping: {torrent}',
                         {'torrent': torrent['name']})
                continue

            status = 'busy'
            if torrent.get('isStalled') and not torrent['percentDone'] == 1:
                status = 'failed'
            elif torrent['status'] == 0:
                if torrent['percentDone'] == 1 and torrent.get('isFinished'):
                    status = 'completed'
                else:
                    status = 'stopped'

            if status == 'completed':
                log.info(
                    'Torrent minimum ratio ({ratio:.3f})'
                    ' or seed idle limit ({seed_limit} min) reached.'
                    ' Removing: {name}', {
                        'ratio': torrent['uploadRatio'],
                        'seed_limit': torrent['seedIdleLimit'],
                        'name': torrent['name']
                    }
                )
                #  self.remove_torrent(torrent['hashString'])
            else:
                log.info(
                    'Torrent minimum ratio ({ratio:.3f}) not reached.'
                    ' Keeping it: {name}', {
                        'ratio': torrent['uploadRatio'],
                        'name': torrent['name']
                    }
                )

        if not found_torrents:
            log.info('No torrents found that were snatched by Medusa')


api = TransmissionAPI
