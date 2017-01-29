# coding=utf-8

from __future__ import unicode_literals

import certifi
import logging
import requests

from cachecontrol import CacheControlAdapter
from cachecontrol.cache import DictCache

from . import hooks
from .. import app
import medusa.common

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


try:
    from urllib.parse import splittype
except ImportError:
    from urllib2 import splittype


class Session(requests.Session):
    """
    A Medusa Session.
    """
    default_headers = {
        'User-Agent': medusa.common.USER_AGENT,
        'Accept-Encoding': 'gzip,deflate',
    }

    # request session proxies
    if app.PROXY_SETTING:
        log.debug(u"Using global proxy: " + app.PROXY_SETTING)
        scheme, address = splittype(app.PROXY_SETTING)
        address = app.PROXY_SETTING if scheme else 'http://' + app.PROXY_SETTING
        proxies = {
            "http": address,
            "https": address,
        }
    else:
        proxies = None

    def __init__(self, cache_etags=True, serializer=None, heuristic=None, verify=True, **kwargs):
        self.my_hooks = kwargs.pop('hooks', [])
        super(Session, self).__init__(**kwargs)
        adapter = CacheControlAdapter(
            DictCache(),
            cache_etags=cache_etags,
            serializer=serializer,
            heuristic=heuristic,
        )
        self.mount('http://', adapter)
        self.mount('https://', adapter)
        self.cache_controller = adapter.controller

        # Configure global session hooks
        self.hooks['response'].append(hooks.log_url)

        # Extend the hooks with kwargs provided session hooks
        self.hooks['response'].extend(self.my_hooks)

        # Set default headers.
        for header, value in self.default_headers.items():
            # Use `setdefault` to avoid clobbering existing headers
            self.headers.setdefault(header, value)

        # Set default ssl verify
        self.verify = certifi.old_where() if all([app.SSL_VERIFY, verify]) else False
class ThrottledSession(Session):
    """
    A Throttled Session that rate limits requests.
    """
    def __init__(self, throttle, **kwargs):
        super(ThrottledSession, self).__init__(**kwargs)
        self.throttle = throttle
        if self.throttle:
            self.request = self.throttle(super(ThrottledSession, self).request)
