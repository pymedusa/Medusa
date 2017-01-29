# coding=utf-8

from __future__ import unicode_literals

import certifi
import logging
import requests

from . import hooks
from .. import app
import medusa.common
import factory

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

    def __init__(self, verify=True, **kwargs):
        # Add
        self.my_hooks = kwargs.pop('hooks', [])

        # Pop the cache_control config
        cache_control = kwargs.pop('cache_control', [])

        # Initialize request.session
        super(Session, self).__init__(**kwargs)

        # Add cache control of provided as a dict. Needs to be attached after super init.
        if cache_control:
            factory.add_cache_control(self, cache_control)

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
