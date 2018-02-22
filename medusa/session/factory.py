"""Session class factory methods."""
from __future__ import unicode_literals

import logging

from cachecontrol import CacheControlAdapter
from cachecontrol.cache import DictCache

from medusa import app

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


def add_proxies():
    # request session proxies
    if app.PROXY_SETTING:
        log.debug('Using global proxy: ' + app.PROXY_SETTING)
        proxy = urlparse(app.PROXY_SETTING)
        address = app.PROXY_SETTING if proxy.scheme else 'http://' + app.PROXY_SETTING
        return {
            'http': address,
            'https': address,
        }
    else:
        return None
