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

from . import clients

logger = logging.getLogger(__name__)


class TorrentChecker(object):
    """Torrent checker class."""

    def __init__(self):
        """Initialize the class."""
        self.amActive = False

    def run(self, force=False):
        """Start the Torrent Checker Thread."""
        if not (app.USE_TORRENTS and app.REMOVE_FROM_CLIENT):
            return

        self.amActive = True
        client = clients.get_client_class(app.TORRENT_METHOD)()
        client.get_torrents_status()

        self.amActive = False
