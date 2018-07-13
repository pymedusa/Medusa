# coding=utf-8

from __future__ import unicode_literals

from medusa.server.web.core import PageTemplate
from medusa.server.web.home.handler import Home

from tornroutes import route


@route('/IRC(/?.*)')
class HomeIRC(Home):
    def __init__(self, *args, **kwargs):
        super(HomeIRC, self).__init__(*args, **kwargs)

    def index(self):

        t = PageTemplate(rh=self, filename='IRC.mako')
        return t.render(header='IRC', title='IRC', controller='IRC', action='index')
