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
from __future__ import unicode_literals

import logging
from builtins import object

from medusa import app
from medusa.clients import torrent

from requests import RequestException

logger = logging.getLogger(__name__)


class TorrentChecker(object):
    """Torrent checker class."""

    def __init__(self):
        """Initialize the class."""
        self.amActive = False

    def run(self, force=False):
        """Start the Torrent Checker Thread."""
        self.amActive = True

        try:
            client = torrent.get_client_class(app.TORRENT_METHOD)()
            client.remove_ratio_reached()
        except NotImplementedError:
            logger.warning('Feature not currently implemented for this torrent client({torrent_client})',
                           torrent_client=app.TORRENT_METHOD)
        except RequestException as e:
            logger.warning('Unable to connect to {torrent_client}. Error: {error}',
                           torrent_client=app.TORRENT_METHOD, error=e)
        except Exception:
            logger.exception('Exception while checking torrent status.')
        finally:
            self.amActive = False
