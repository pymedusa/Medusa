"""Torrent checker module."""

import logging

from medusa import app
from medusa.clients import torrent
from medusa.logger.adapters.style import BraceAdapter

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log = BraceAdapter(log)


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

        try:
            client = torrent.get_client_class(app.TORRENT_METHOD)()
            client.remove_ratio_reached()
        except Exception as error:
            log.debug('Failed to check torrent status. Error: {0}', error)

        self.amActive = False
