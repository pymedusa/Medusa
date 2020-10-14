"""Session class factory methods."""
from __future__ import unicode_literals

import logging

from cachecontrol import CacheControlAdapter
from cachecontrol.cache import DictCache

from medusa.app import app

from six.moves.urllib.parse import urlparse

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def add_cache_control(session, cache_control_config):
    """Add cache_control adapter to session object."""
    adapter = CacheControlAdapter(
        DictCache(),
        cache_etags=cache_control_config.get('cache_etags', True),
        serializer=cache_control_config.get('serializer', None),
        heuristic=cache_control_config.get('heuristic', None),
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.cache_controller = adapter.controller
