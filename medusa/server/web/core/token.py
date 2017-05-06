# coding=utf-8

from __future__ import unicode_literals

from tornado.web import authenticated

from ..core.base import WebHandler, BaseHandler
from medusa import app


class TokenHandler(BaseHandler):
    def __init__(self, *args, **kwargs):
        super(TokenHandler, self).__init__(*args, **kwargs)

    @authenticated
    def get(self, *args, **kwargs):
        self.finish({'token': app.API_KEY})
