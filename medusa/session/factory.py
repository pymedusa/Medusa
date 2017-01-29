"""Session class factory methods."""

import logging
from cachecontrol import CacheControlAdapter
from cachecontrol.cache import DictCache

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def add_cache_control(session, cache_control_config):
    if not all(['cache_etags' in cache_control_config,
                'serializer' in cache_control_config,
                'heuristic' in cache_control_config]):
        logging.warning('Insufficient paramaters provided for the add_cache_control factory.')
        return

    adapter = CacheControlAdapter(
        DictCache(),
        cache_etags=cache_control_config.get('cache_etags'),
        serializer=cache_control_config.get('serializer'),
        heuristic=cache_control_config.get('heuristic'),
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.cache_controller = adapter.controller
