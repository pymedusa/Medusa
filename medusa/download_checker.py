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
"""Torrent checker module."""

import logging

import app
from medusa.clients import torrent
from medusa.failed_history import find_expired_releases

logger = logging.getLogger(__name__)


class DownloadChecker(object):
    """Thread for periodically managing the search providers."""

    def __init__(self):
        """Initialize the class."""
        self.amActive = False

    def run(self, force=False):
        """Start the Torrent Checker Thread."""

        self.amActive = True

        if app.USE_TORRENTS and app.REMOVE_FROM_CLIENT:
            # Torrent checker. Check torrents on seed ratio. Remove torrent from client.
            try:
                client = torrent.get_client_class(app.TORRENT_METHOD)()
                client.remove_ratio_reached()
            except Exception as e:
                logger.debug('Failed to check torrent status. Error: {error}', error=e)

        if app.TORRENT_DOWNLOAD_EXPIRE_HOURS or app.NZB_DOWNLOAD_EXPIRE_HOURS:

            # Download timeout. Check the failed.db history table for expired downloads.
            # Revert episode to previous status if possible.
            episodes = find_expired_releases()
            pass

        self.amActive = False
