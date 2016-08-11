# coding=utf-8

from __future__ import unicode_literals
from sickbeard.server.web.core import PageTemplate
from sickbeard.server.web.home.handler import Home
from tornado.routes import route


@route('/addRecommended(/?.*)')
class HomeAddRecommended(Home):
    def __init__(self, *args, **kwargs):
        super(HomeAddRecommended, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename="addRecommended.mako")
        return t.render(title='Add Recommended Shows', header='Add Recommended Shows',
                        topmenu='home', controller="addShows", action="index")
