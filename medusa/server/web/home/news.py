# coding=utf-8

from __future__ import unicode_literals

from medusa.server.web.core import PageTemplate
from medusa.server.web.home.handler import Home

from tornroutes import route


@route('/news(/?.*)')
class HomeNews(Home):
    def __init__(self, *args, **kwargs):
        super(HomeNews, self).__init__(*args, **kwargs)

    def index(self):
        """
        Render the IRC page.

        [Converted to VueRouter]
        """
        t = PageTemplate(rh=self, filename='index.mako')
        return t.render()
