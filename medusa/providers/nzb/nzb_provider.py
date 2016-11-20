# coding=utf-8
# This file is part of Medusa.
#
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
"""Provider code for Generic NZB Provider."""

from ..generic_provider import GenericProvider
from ... import app
from ...classes import NZBSearchResult
from ...helper.common import try_int


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
        return NZBSearchResult(episodes)

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
