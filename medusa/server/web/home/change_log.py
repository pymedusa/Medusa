# coding=utf-8

from __future__ import unicode_literals

import markdown2

from medusa import app, logger
from medusa.server.web.core import PageTemplate
from medusa.server.web.home.handler import Home
from medusa.session.core import MedusaSafeSession

from tornroutes import route


@route('/changes(/?.*)')
class HomeChangeLog(Home):
    session = MedusaSafeSession()

    def __init__(self, *args, **kwargs):
        super(HomeChangeLog, self).__init__(*args, **kwargs)

    def index(self):
        """
        Render the IRC page.

        [Converted to VueRouter]
        """
        t = PageTemplate(rh=self, filename='index.mako')
        return t.render()
