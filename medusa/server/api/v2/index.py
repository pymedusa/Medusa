# coding=utf-8
"""Request handler for index."""

from .base import BaseRequestHandler
from .... import app, logger


class IndexHandler(BaseRequestHandler):
    """Index request handler."""

    def get(self):
        self.api_finish(data='Welcome to the Medusa API, documentation can be found at http://docs.medusaapi.apiary.io/')
