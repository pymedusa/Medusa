# coding=utf-8

from __future__ import unicode_literals

from tornado.routes import route

from sickbeard.server.web.core import PageTemplate
from sickbeard.server.web.home.handler import Home


@route('/addRecommended(/?.*)')
class HomeAddRecommended(Home):
    def __init__(self, *args, **kwargs):
        super(HomeAddRecommended, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename="addRecommended.mako")
        return t.render(title='Add From Recommended', header='Add From Recommended',
                        topmenu='home', controller="addShows", action="index")
