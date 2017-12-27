# coding=utf-8

"""Transmission Client."""

from __future__ import unicode_literals

import json
import logging
import os
import re
from base64 import b64encode
from datetime import datetime, timedelta

from medusa import app
from medusa.clients.torrent.generic import GenericClient
from medusa.helpers import (
    get_extension,
    is_already_processed_media,
    is_info_hash_in_history,
    is_info_hash_processed,
    is_media_file,
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

    def check_response(self):
        """Check if response is a valid json and its a success one."""
        try:
            return self.response.json()['result'] == 'success'
        except ValueError:
            return False

    def _get_auth(self):

        post_data = json.dumps({
            'method': 'session-get',
        })

        self.response = self.session.post(self.url, data=post_data.encode('utf-8'), timeout=120,
                                          verify=app.TORRENT_VERIFY_CERT)
        self.auth = re.search(r'X-Transmission-Session-Id:\s*(\w+)', self.response.text).group(1)

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

        return self.check_response()

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

        return self.check_response()

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

        return self.check_response()

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

            return self.check_response()
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

        return self.check_response()

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

        return self.check_response()

    def move_torrent(self, info_hash):
        """Set new torrent location given info_hash.

        :param info_hash:
        :type info_hash: string
        :return
        :rtype: bool
        """
        if not app.TORRENT_SEED_LOCATION or not info_hash:
            return

        arguments = {
            'ids': [info_hash],
            'location': app.TORRENT_SEED_LOCATION,
            'move': 'true'
        }

        post_data = json.dumps({
            'arguments': arguments,
            'method': 'torrent-set-location',
        })

        self._request(method='post', data=post_data)

        return self.check_response()

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

        isFinished = whether seeding finished (based on seed ratio)
        IsStalled =  Based on Tranmission setting "Transfer is stalled when inactive for"
        """
        log.info('Checking Transmission torrent status.')

        return_params = {
            'fields': ['name', 'hashString', 'percentDone', 'status',
                       'isStalled', 'errorString', 'seedRatioLimit',
                       'isFinished', 'uploadRatio', 'seedIdleLimit', 'files', 'activityDate']
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
                # Need to check only the media file or the .rar file to avoid checking all .r0* files in history
                if not (is_media_file(i['name']) or get_extension(i['name']) == 'rar'):
                    continue
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
            error_string = torrent.get('errorString')
            if torrent.get('isStalled') and not torrent['percentDone'] == 1:
                status = 'stalled'
            elif error_string and 'unregistered torrent' in error_string.lower():
                status = 'unregistered'
            elif torrent['status'] == 0:
                status = 'stopped'
                if torrent['percentDone'] == 1:
                    # Check if torrent is stopped because of idle timeout
                    seed_timed_out = False
                    if torrent['activityDate'] > 0 and torrent['seedIdleLimit'] > 0:
                        last_activity_date = datetime.fromtimestamp(torrent['activityDate'])
                        seed_timed_out = (datetime.now() - timedelta(
                            minutes=torrent['seedIdleLimit'])) > last_activity_date

                    if torrent.get('isFinished') or seed_timed_out:
                        status = 'completed'
            elif torrent['status'] == 6:
                status = 'seeding'

            if status == 'completed':
                log.info(
                    'Torrent completed and reached minimum'
                    ' ratio: [{ratio:.3f}/{ratio_limit:.3f}] or'
                    ' seed idle limit: [{seed_limit} min].'
                    ' Removing it: [{name}]',
                    ratio=torrent['uploadRatio'],
                    ratio_limit=torrent['seedRatioLimit'],
                    seed_limit=torrent['seedIdleLimit'],
                    name=torrent['name']
                )
                self.remove_torrent(torrent['hashString'])
            elif status == 'stalled':
                log.warning('Torrent is stalled. Check it: [{name}]',
                            name=torrent['name'])
            elif status == 'unregistered':
                log.warning('Torrent was unregistered from tracker.'
                            ' Check it: [{name}]', name=torrent['name'])
            elif status == 'seeding':
                if float(torrent['uploadRatio']) < float(torrent['seedRatioLimit']):
                    log.info(
                        'Torrent did not reach minimum'
                        ' ratio: [{ratio:.3f}/{ratio_limit:.3f}].'
                        ' Keeping it: [{name}]',
                        ratio=torrent['uploadRatio'],
                        ratio_limit=torrent['seedRatioLimit'],
                        name=torrent['name']
                    )
                else:
                    log.info(
                        'Torrent completed and reached minimum ratio but it'
                        ' was force started again. Current'
                        ' ratio: [{ratio:.3f}/{ratio_limit:.3f}].'
                        ' Keeping it: [{name}]',
                        ratio=torrent['uploadRatio'],
                        ratio_limit=torrent['seedRatioLimit'],
                        name=torrent['name']
                    )
            elif status in ('stopped', 'busy'):
                log.info('Torrent is {status}. Keeping it: [{name}]',
                         status=status, name=torrent['name'])
            else:
                log.warning(
                    'Torrent has an unmapped status. Keeping it: [{name}].'
                    ' Report torrent info: {info}',
                    name=torrent['name'],
                    info=torrent
                )
        if not found_torrents:
            log.info('No torrents found that were snatched by Medusa')


api = TransmissionAPI
