# coding=utf-8

from __future__ import unicode_literals

from tornado.web import authenticated

from ..core.base import BaseHandler
from medusa import app


class TokenHandler(BaseHandler):
    """
    Handle the request for /token, and return the app.API_KEY if authenticated.
    """
    def __init__(self, *args, **kwargs):
        super(TokenHandler, self).__init__(*args, **kwargs)

    @authenticated
    def get(self, *args, **kwargs):
        self.finish({'token': app.API_KEY})
