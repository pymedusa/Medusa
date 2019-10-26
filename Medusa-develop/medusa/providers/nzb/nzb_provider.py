# coding=utf-8

"""Provider code for Generic NZB Provider."""
from __future__ import unicode_literals

from medusa import app
from medusa.classes import NZBSearchResult
from medusa.helper.common import try_int
from medusa.providers.generic_provider import GenericProvider


class NZBProvider(GenericProvider):
    """Generic NZB provider."""

    def __init__(self, name):
        """Initialize the class."""
        super(NZBProvider, self).__init__(name)

        self.provider_type = GenericProvider.NZB

    def is_active(self):
        """Check if provider is active."""
        return bool(app.USE_NZBS) and self.is_enabled()

    def _get_result(self, episodes):
        """Return provider result."""
        return NZBSearchResult(episodes, provider=self)

    def _get_size(self, item):
        """Get result size."""
        try:
            size = item.get('links')[1].get('length', -1)
        except (AttributeError, IndexError, TypeError):
            size = -1
        return try_int(size, -1)

    def _get_result_info(self, item):
        # Get seeders/leechers for Torznab
        seeders = item.get('seeders', -1)
        leechers = item.get('leechers', -1)
        return try_int(seeders, -1), try_int(leechers, -1)

    def _get_storage_dir(self):
        """Get nzb storage dir."""
        return app.NZB_DIR

    def _get_pubdate(self, item):
        """Return publish date of the item."""
        return item.get('pubdate')
