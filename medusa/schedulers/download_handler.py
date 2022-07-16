# coding=utf-8
# Author: fernandog
#
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
"""Download handler module."""
from __future__ import unicode_literals

import datetime
import logging
from builtins import object
from enum import Enum
from uuid import uuid4

from medusa import app, db, ws
from medusa.clients import torrent
from medusa.clients.nzb import nzbget, sab
from medusa.clients.torrent.generic import GenericClient
from medusa.helper.common import ConstsBitwize
from medusa.helper.exceptions import DownloadClientConnectionException
from medusa.logger.adapters.style import BraceAdapter
from medusa.process_tv import PostProcessQueueItem
from medusa.show.show import Show

from requests import RequestException

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class ClientStatusEnum(Enum):
    """Enum to keep track of all the client statusses."""

    SNATCHED = 0  # 0
    PAUSED = 1  # 1
    DOWNLOADING = 1 << 1  # 2
    DOWNLOADED = 1 << 2  # 4
    SEEDED = 1 << 3  # 8
    # Can trigger a new snatch if configured.
    FAILED = 1 << 4  # 16
    # Failed, but won't trigger a new snatch.
    # Can be manually aborted, or Failed by client because it's a Dupe (see nzbget)
    ABORTED = 1 << 5  # 32
    EXTRACTING = 1 << 6  # 64
    COMPLETED = 1 << 7  # 128
    POSTPROCESSED = 1 << 8  # 256
    SEEDACTION = 1 << 9  # 512
    REMOVED = 1 << 10  # 1024


status_strings = {
    ClientStatusEnum.SNATCHED: 'Snatched',
    ClientStatusEnum.PAUSED: 'Paused',
    ClientStatusEnum.DOWNLOADING: 'Downloading',
    ClientStatusEnum.DOWNLOADED: 'Downloaded',
    ClientStatusEnum.SEEDED: 'Seeded',
    ClientStatusEnum.FAILED: 'Failed',
    ClientStatusEnum.ABORTED: 'Aborted',
    ClientStatusEnum.EXTRACTING: 'Extracting',
    ClientStatusEnum.COMPLETED: 'Completed',
    # Reserved for the Medusa postprocessing (not that of the client!).
    ClientStatusEnum.POSTPROCESSED: 'Postprocessed',
    ClientStatusEnum.SEEDACTION: 'SeededAction',
    ClientStatusEnum.REMOVED: 'Removed'
}


class ClientStatus(ConstsBitwize):
    """ClientStatus Class."""

    CONSTANTS = ClientStatusEnum
    STRINGS = status_strings

    def __init__(self, status=0, status_string=None):
        """Initialize ClientStatus object."""
        super(ClientStatus, self).__init__(status)
        self.ratio = 0.0
        self.progress = 0
        self.destination = ''
        self.resource = ''

        # Overwrite the default set status using a string.
        if status_string:
            self.set_status_string(status_string)


class DownloadHandler(object):
    """Download handler checker class."""

    def __init__(self):
        """Initialize the class."""
        self.name = 'DOWNLOADHANDLER'
        self.amActive = False
        self.main_db_con = db.DBConnection()
        self.forced = False
        self.queueTime = str(datetime.datetime.utcnow())
        self.identifier = str(uuid4())

    @property
    def _to_json(self):
        return {
            'isActive': self.amActive,
            'identifier': self.identifier,
            'name': self.name,
            'queueTime': self.queueTime,
            'force': self.forced
        }

    def _get_history_results_from_db(self, provider_type, exclude_status=None, include_status=None):
        params = [provider_type]

        query = 'SELECT * FROM history WHERE info_hash is not null AND provider_type = ?'

        format_param = {}
        if exclude_status:
            params += exclude_status
            query += ' AND client_status not in ({exclude})'
            format_param['exclude'] = ','.join(['?'] * (len(exclude_status)))

        if include_status:
            params += include_status
            query += ' AND client_status in ({include})'
            format_param['include'] = ','.join(['?'] * (len(include_status)))

        # We don't want any results for client_status removed. This is a bit-set status.
        # So we check for > 1024.
        query += ' AND client_status < 1024'

        history_results = self.main_db_con.select(query.format(**format_param), params)

        # If a history item is part of a batch, only return the first occurrence.

        batch_results = {}
        for result in history_results:
            if result['part_of_batch']:
                if result['info_hash'] not in batch_results:
                    batch_results[result['info_hash']] = result
            else:
                yield result

        for result in batch_results.values():
            yield result

    def save_status_to_history(self, history_row, status):
        """Update history record with a new status."""
        log.info('Updating status to [{status}] for {resource} with info_hash {info_hash}',
                 {'status': status, 'resource': history_row['resource'], 'info_hash': history_row['info_hash']})
        self.main_db_con.action('UPDATE history set client_status = ? WHERE info_hash = ? AND resource = ?',
                                [status.status, history_row['info_hash'], history_row['resource']])

    def _update_status(self, client):
        """Update status (in db) with current state on client."""
        excluded = [
            ClientStatusEnum.COMPLETED.value | ClientStatusEnum.POSTPROCESSED.value,
            ClientStatusEnum.FAILED.value | ClientStatusEnum.POSTPROCESSED.value,
            ClientStatusEnum.SEEDED.value | ClientStatusEnum.POSTPROCESSED.value,
            ClientStatusEnum.ABORTED.value,
            ClientStatusEnum.SEEDACTION.value
        ]

        client_type = 'torrent' if isinstance(client, GenericClient) else 'nzb'
        for history_result in self._get_history_results_from_db(client_type, exclude_status=excluded):
            try:
                status = client.get_status(history_result['info_hash'])
            except DownloadClientConnectionException as error:
                log.warning('The client cannot be reached or authentication is failing.'
                            '\nError: {error}', {'error': error})
                continue

            if not status:
                continue

            log.debug(
                'Found {client_type} on {client} with info_hash {info_hash}',
                {
                    'client_type': client_type,
                    'client': app.TORRENT_METHOD if client_type == 'torrent' else app.NZB_METHOD,
                    'info_hash': history_result['info_hash']
                }
            )
            if history_result['client_status'] != status.status:
                self.save_status_to_history(history_result, status)

    def _check_postprocess(self, client):
        """Check the history table for ready available downlaods, that need to be post-processed."""
        client_type = 'torrent' if isinstance(client, GenericClient) else 'nzb'

        for history_result in self._get_history_results_from_db(
            client_type,
            include_status=[
                ClientStatusEnum.COMPLETED.value,
                ClientStatusEnum.FAILED.value,
                ClientStatusEnum.SEEDED.value,
                ClientStatusEnum.COMPLETED.value | ClientStatusEnum.SEEDED.value,
                ClientStatusEnum.COMPLETED.value | ClientStatusEnum.PAUSED.value,
                ClientStatusEnum.COMPLETED.value | ClientStatusEnum.SEEDED.value | ClientStatusEnum.PAUSED.value,
            ],
        ):
            try:
                status = client.get_status(history_result['info_hash'])
            except DownloadClientConnectionException as error:
                log.warning('The client cannot be reached or authentication is failing.'
                            '\nAbandon check postprocess. error: {error}', {'error': error})
                continue

            if not status:
                continue

            log.debug(
                'Sending postprocess job for {client_type} with info_hash: {info_hash}'
                '\nstatus: {status}\nclient: {client}'
                '\ndestination: {destination}\nresource: {resource}',
                {
                    'client_type': client_type,
                    'info_hash': history_result['info_hash'],
                    'status': status,
                    'client': app.TORRENT_METHOD if client_type == 'torrent' else app.NZB_METHOD,
                    'destination': status.destination,
                    'resource': status.resource or history_result['resource']
                }
            )

            if not status.destination and not status.resource and history_result['resource']:
                # We didn't get a destination, because probably it failed to start a download.
                # For example when it already failed to get the nzb. But we have a resource name from the snatch.
                # We'll use this, so that we can finish the postprocessing and possible failed download handling.
                status.resource = history_result['resource']

            if not status.destination and not status.resource:
                log.warning('Not starting postprocessing for info_hash {info_hash}, need a destination path.',
                            {'info_hash': history_result['info_hash']})
                continue

            self._postprocess(
                status.destination, history_result['info_hash'], status.resource,
                failed=str(status) == 'Failed', client_type=client_type
            )

    def _check_torrent_ratio(self, client):
        """Perform configured action after seed ratio reached (or by configuration)."""
        if app.TORRENT_SEED_ACTION == '':
            log.debug(
                'No global ratio or provider ratio configured for {client}, skipping actions.',
                {'client': client.name}
            )
            return

        # The base ClienStatus to include in the query.
        include = [
            ClientStatusEnum.COMPLETED.value | ClientStatusEnum.POSTPROCESSED.value
        ]

        from medusa.providers import get_provider_class
        from medusa.providers.generic_provider import GenericProvider

        for history_result in self._get_history_results_from_db(
            'torrent', include_status=include,
        ):
            provider_id = GenericProvider.make_id(history_result['provider'])
            provider = get_provider_class(provider_id)
            if not provider:
                log.debug('Skip provider {provider} with id: {provider_id}',
                          {'provider': history_result['provider'], 'provider_id': provider_id})
                continue

            provider_ratio = -1 if provider.ratio == '' else provider.ratio
            try:
                desired_ratio = provider_ratio if provider_ratio > -1 else app.TORRENT_SEED_RATIO
            except TypeError:
                log.warning('could not get provider ratio {ratio} for provider {provider}', {
                    'ratio': provider_ratio, 'provider': provider_id
                })
                desired_ratio = app.TORRENT_SEED_RATIO

            if desired_ratio == -1:
                # Not sure if this option is of use.
                continue

            try:
                status = client.get_status(history_result['info_hash'])
            except DownloadClientConnectionException as error:
                log.warning('The client cannot be reached or authentication is failing.'
                            '\nAbandon check torrent ratio. error: {error}', {'error': error})
                continue

            if not status:
                continue

            action_after_seeding = desired_ratio * 1.0 > 0.0
            if status.ratio < desired_ratio * action_after_seeding:
                continue

            if not action_after_seeding:
                log.debug('Action after seeding disabled')

            log.debug(
                'Ratio of ({ratio}) reached for torrent {info_hash}, starting action: {action}.',
                {
                    'ratio': status.ratio,
                    'info_hash': history_result['info_hash'],
                    'action': app.TORRENT_SEED_ACTION
                }
            )
            hash = history_result['info_hash']
            # Perform configured action.
            if app.TORRENT_SEED_ACTION == 'remove':
                # Remove torrent from client
                client.remove_torrent(hash)
            elif app.TORRENT_SEED_ACTION == 'pause':
                # Pause torrent on client
                client.pause_torrent(hash)
            elif app.TORRENT_SEED_ACTION == 'remove_with_data':
                # Remove torrent and all files from disk (not implemented for each client!)
                client.remove_torrent_data(hash)
            else:
                log.debug('Invalid action {action}', {'action': app.TORRENT_SEED_ACTION})
                continue

            self.save_status_to_history(history_result, ClientStatus(status_string='SeededAction'))

    def _postprocess(self, path, info_hash, resource_name, failed=False, client_type=None):
        """Queue a postprocess action.

        :param path: Path to process
        :type path: str
        :param info_hash: info hash
        :type info_hash: str
        :param resource_name: Resource name
        :type resource_name: str
        :param failed: Flag to determin if this was a failed download
        :type failed: bool
        :param client_type: Client type ('nzb', 'torrent')
        :type client_type: str
        """
        # Use the info hash get a segment of episodes.
        history_items = self.main_db_con.select(
            'SELECT * FROM history WHERE info_hash = ?',
            [info_hash]
        )

        episodes = []
        for history_item in history_items:
            # Search for show in library
            show = Show.find_by_id(app.showList, history_item['indexer_id'], history_item['showid'])
            if not show:
                # Show is "no longer" available in library.
                continue
            episodes.append(show.get_episode(history_item['season'], history_item['episode']))

        queue_item = PostProcessQueueItem(
            path, info_hash, resource_name=resource_name,
            failed=failed, episodes=episodes, client_type=client_type,
            process_single_resource=True
        )
        app.post_processor_queue_scheduler.action.add_item(queue_item)

    def _clean(self, client):
        """Update status in the history table for torrents/nzb's that can't be located anymore."""
        client_type = 'torrent' if isinstance(client, GenericClient) else 'nzb'

        for history_result in self._get_history_results_from_db(client_type):
            try:
                if not client.get_status(history_result['info_hash']):
                    log.debug(
                        'Cannot find {client_type} on {client} with info_hash {info_hash}'
                        'Adding status Removed, to prevent from future processing.',
                        {
                            'client_type': client_type,
                            'client': app.TORRENT_METHOD if client_type == 'torrent' else app.NZB_METHOD,
                            'info_hash': history_result['info_hash']
                        }
                    )
                    new_status = ClientStatus(int(history_result['client_status']))
                    new_status.add_status_string('Removed')
                    self.save_status_to_history(history_result, new_status)
            except DownloadClientConnectionException as error:
                log.warning('The client cannot be reached or authentication is failing.'
                            '\nAbandon cleanup. error: {error}', {'error': error})

    def run(self, force=False):
        """Start the Download Handler Thread."""
        if self.amActive:
            log.debug('Download handler is still running, not starting it again')
            return

        self.amActive = True
        # Push an update to any open Web UIs through the WebSocket
        ws.Message('QueueItemUpdate', self._to_json).push()

        try:
            if app.USE_TORRENTS and app.TORRENT_METHOD != 'blackhole':
                torrent_client = torrent.get_client_class(app.TORRENT_METHOD)()
                self._update_status(torrent_client)
                self._check_postprocess(torrent_client)
                self._check_torrent_ratio(torrent_client)
                self._clean(torrent_client)
        except NotImplementedError:
            log.warning('Feature not currently implemented for this torrent client({torrent_client})',
                        torrent_client=app.TORRENT_METHOD)
        except (RequestException, DownloadClientConnectionException) as error:
            log.warning('Unable to connect to {torrent_client}. Error: {error}',
                        torrent_client=app.TORRENT_METHOD, error=error)
        except Exception as error:
            log.exception('Exception while checking torrent status. with error: {error}', {'error': error})

        try:
            if app.USE_NZBS and app.NZB_METHOD != 'blackhole':
                nzb_client = sab if app.NZB_METHOD == 'sabnzbd' else nzbget
                self._update_status(nzb_client)
                self._check_postprocess(nzb_client)
                self._clean(nzb_client)
        except NotImplementedError:
            log.warning('Feature not currently implemented for this torrent client({torrent_client})',
                        torrent_client=app.TORRENT_METHOD)
        except (RequestException, DownloadClientConnectionException) as error:
            log.warning('Unable to connect to {torrent_client}. Error: {error}',
                        torrent_client=app.TORRENT_METHOD, error=error)
        except Exception as error:
            log.exception('Exception while checking torrent status. with error: {error}', {'error': error})

        self.amActive = False
        # Push an update to any open Web UIs through the WebSocket
        ws.Message('QueueItemUpdate', self._to_json).push()
