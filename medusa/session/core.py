# coding=utf-8

from __future__ import unicode_literals

import requests
import logging

from . import hooks
import medusa.common

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class Session(requests.Session):
    """
    A Medusa Session.
    """
    default_headers = {
        'User-Agent': medusa.common.USER_AGENT,
        'Accept-Encoding': 'gzip,deflate',
    }

    def __init__(self, **kwargs):
        super(Session, self).__init__()

        self.hooks['response'].add(hooks.log_url)

        # Set default headers.
        for header, value in self.default_headers:
            # Use `setdefault` to avoid clobbering existing headers
            self.headers.setdefault(header, value)
