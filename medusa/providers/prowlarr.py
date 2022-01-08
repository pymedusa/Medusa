"""Utility class for prowlarr."""
from urllib.parse import urljoin

from medusa.session.core import ProviderSession


class ProwlarrManager(object):
    """Utility class for prowlarr."""

    def __init__(self, url, apikey):
        self.url = url
        self.apikey = apikey
        self.session = ProviderSession()
        self.session.headers.update({'x-api-key': self.apikey})

    def test_connectivity(self):
        """Verify connectivity to Prowlarrs internal api."""
        response = self.session.get(urljoin(self.url, 'api/v1/health'))
        if response and response.ok:
            return True
        return False

    def get_indexers(self):
        """Get a list of providers (newznab/torznab indexers)."""
        response = self.session.get(urljoin(self.url, 'api/v1/indexer'))
        if not response:
            return False

        return response.json()
