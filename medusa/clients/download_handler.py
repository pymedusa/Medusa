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

import logging
from builtins import object
from enum import Enum

from medusa import app, db
from medusa.clients import torrent
from medusa.clients.nzb import nzbget, sab
from medusa.helper.common import ConstsBitwize
from medusa.logger.adapters.style import BraceAdapter

from requests import RequestException

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class ClientStatusEnum(Enum):
    """Enum to keep track of all the client statusses."""

    NA = 0  # 0
    PAUSED = 1  # 1
    DOWNLOADING = 1 << 1  # 2
    DOWNLOADED = 1 << 2  # 4
    SEEDED = 1 << 3  # 8
    FAILED = 1 << 4  # 16
    EXTRACTING = 1 << 5  # 32
    COMPLETED = 1 << 6  # 64
    POSTPROCESSED = 1 << 7  # 128


status_strings = {
    ClientStatusEnum.NA: 'N/A',
    ClientStatusEnum.PAUSED: 'Paused',
    ClientStatusEnum.DOWNLOADING: 'Downloading',
    ClientStatusEnum.DOWNLOADED: 'Downloaded',
    ClientStatusEnum.SEEDED: 'Seeded',
    ClientStatusEnum.FAILED: 'Failed',
    ClientStatusEnum.EXTRACTING: 'Extracting',
    ClientStatusEnum.COMPLETED: 'Completed',
    ClientStatusEnum.POSTPROCESSED: 'Postprocessed',
}


class ClientStatus(ConstsBitwize):
    """ClientStatus Class."""

    CONSTANTS = ClientStatusEnum
    STRINGS = status_strings


class DownloadHandler(object):
    """Download handler checker class."""

    def __init__(self):
        """Initialize the class."""
        self.amActive = False
        self.main_db_con = db.DBConnection()

    def _get_history_results_from_db(self):
        return self.main_db_con.select('SELECT * FROM history WHERE info_hash is not null AND client_status is not ?',
                                       [ClientStatusEnum.COMPLETED.value])

    def _check_torrents(self):
        """
        Check torrent client for completed torrents.

        Start postprocessing if app.DOWNLOAD_HANDLING is enabled.
        """
        torrent_client = torrent.get_client_class(app.TORRENT_METHOD)()

        for history_result in self._get_history_results_from_db():
            if torrent_client.torrent_completed(history_result['info_hash']):
                log.debug(
                    'Found torrent on {client} with info_hash {info_hash}',
                    {
                        'client': app.TORRENT_METHOD,
                        'info_hash': history_result['info_hash']
                    }
                )

    def _check_nzbs(self):
        """
        Check torrent client for completed nzbs.

        Start postprocessing if app.DOWNLOAD_HANDLING is enabled.
        """
        if app.NZB_METHOD == 'sabnzbd':
            client = sab
        if app.NZB_METHOD == 'nzbget':
            client = nzbget

        for history_result in self._get_history_results_from_db():
            nzb_on_client = client.get_nzb_by_id(history_result['info_hash'])
            if nzb_on_client:
                status = client.nzb_status(history_result['info_hash'])
                log.debug(
                    'Found nzb (status {status}) on {client} with info_hash {info_hash}',
                    {
                        'status': status,
                        'client': app.NZB_METHOD,
                        'info_hash': history_result['info_hash']
                    }
                )
                if history_result['client_status'] != status.status:
                    self.save_status_to_history(history_result, status)

    def save_status_to_history(self, history_row, status):
        """Update history record with a new status."""
        log.info('Saving new status {status} for {resource} with info_hash {info_hash}',
                 {'status': status, 'resource': history_row['resource'], 'info_hash': history_row['info_hash']})
        self.main_db_con.action('UPDATE history set client_status = ? where info_hash = ?',
                                [status.status, history_row['info_hash']])

    def run(self, force=False):
        """Start the Download Handler Thread."""
        if self.amActive:
            log.debug('Download handler is still running, not starting it again')
            return

        self.amActive = True

        try:
            if app.USE_TORRENTS:
                self._check_torrents()

            if app.USE_NZBS:
                self._check_nzbs()
            # client.remove_ratio_reached()
        except NotImplementedError:
            log.warning('Feature not currently implemented for this torrent client({torrent_client})',
                        torrent_client=app.TORRENT_METHOD)
        except RequestException as error:
            log.warning('Unable to connect to {torrent_client}. Error: {error}',
                        torrent_client=app.TORRENT_METHOD, error=error)
        except Exception as error:
            log.exception('Exception while checking torrent status. with error: {error}', {'error': error})
        finally:
            self.amActive = False