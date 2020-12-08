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

from medusa import app
from medusa.clients import torrent
from medusa.clients.nzb import nzbget, sab

from requests import RequestException

logger = logging.getLogger(__name__)


class DownloadHandler(object):
    """Download handler checker class."""

    def __init__(self):
        """Initialize the class."""
        self.amActive = False

    @staticmethod
    def _check_torrents():
        """
        Check torrent client for completed torrents.

        Start postprocessing if app.DOWNLOAD_HANDLING is enabled.
        """
        torrenet_client = torrent.get_client_class(app.TORRENT_METHOD)()

    @staticmethod
    def _check_nzbs():
        """
        Check torrent client for completed nzbs.

        Start postprocessing if app.DOWNLOAD_HANDLING is enabled.
        """
        if app.NZB_METHOD == 'sabnzbd':
            client = sab
        if app.NZB_METHOD == 'nzbget':
            client = nzbget

        client._get_nzb_history()
        pass


    def run(self, force=False):
        """Start the Download Handler Thread."""
        if self.amActive:
            logger.debug(u'Download handler is still running, not starting it again')
            return

        self.amActive = True

        try:
            if app.USE_TORRENTS:
                self._check_torrents()

            if app.USE_NZBS:
                self._check_nzbs()
            # client.remove_ratio_reached()
        except NotImplementedError:
            logger.warning('Feature not currently implemented for this torrent client({torrent_client})',
                           torrent_client=app.TORRENT_METHOD)
        except RequestException as error:
            logger.warning('Unable to connect to {torrent_client}. Error: {error}',
                           torrent_client=app.TORRENT_METHOD, error=error)
        except Exception as error:
            logger.exception('Exception while checking torrent status. with error: {error}', {'error': error})
        finally:
            self.amActive = False
