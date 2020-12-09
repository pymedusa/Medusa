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

from medusa import app, db
from medusa.clients import torrent
from medusa.clients.nzb import nzbget, sab
from medusa.logger.adapters.style import BraceAdapter

from requests import RequestException

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class DownloadHandler(object):
    """Download handler checker class."""

    def __init__(self):
        """Initialize the class."""
        self.amActive = False
        self.main_db_con = db.DBConnection()

    def _check_torrents(self):
        """
        Check torrent client for completed torrents.

        Start postprocessing if app.DOWNLOAD_HANDLING is enabled.
        """
        torrenet_client = torrent.get_client_class(app.TORRENT_METHOD)()

    def _check_nzbs(self):
        """
        Check torrent client for completed nzbs.

        Start postprocessing if app.DOWNLOAD_HANDLING is enabled.
        """
        if app.NZB_METHOD == 'sabnzbd':
            client = sab
        if app.NZB_METHOD == 'nzbget':
            client = nzbget

        history_results = self.main_db_con.select('SELECT * FROM history WHERE info_hash is not null')
        # client._get_nzb_history()
        for history_result in history_results:
            nzb_on_client = client.get_nzb_by_id(history_result['info_hash'])
            if nzb_on_client:
                log.debug(
                    u'Found nzb (status {status}) on {client} with info_hash {info_hash}',
                    {
                        'status': nzb_on_client['status'],
                        'client': app.NZB_METHOD,
                        'info_hash': history_result['info_hash']
                    }
                )

    def run(self, force=False):
        """Start the Download Handler Thread."""
        if self.amActive:
            log.debug(u'Download handler is still running, not starting it again')
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
