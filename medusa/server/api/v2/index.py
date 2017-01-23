# coding=utf-8
"""Request handler for index."""

from .base import BaseRequestHandler


class IndexHandler(BaseRequestHandler):
    """Index request handler."""

    def get(self):
        """Return info about API v2."""
        self.api_finish(data='Welcome to the Medusa API, documentation can be found at http://docs.medusaapi.apiary.io/')
