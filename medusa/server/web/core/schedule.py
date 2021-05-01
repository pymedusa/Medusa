# coding=utf-8

from __future__ import unicode_literals

from medusa import app
from medusa.server.web.core.base import PageTemplate, WebRoot

from tornroutes import route


@route('/schedule(/?.*)')
class Schedule(WebRoot):
    def __init__(self, *args, **kwargs):
        super(Schedule, self).__init__(*args, **kwargs)

    def index(self):
        """
        Render the schedule page.

        [Converted to VueRouter]
        """
        return PageTemplate(rh=self, filename='index.mako').render()

    def toggleScheduleDisplayPaused(self):
        app.COMING_EPS_DISPLAY_PAUSED = not app.COMING_EPS_DISPLAY_PAUSED

        return self.redirect('/schedule/')

    def setScheduleSort(self, sort):
        if sort not in ('date', 'network', 'show') or app.COMING_EPS_LAYOUT == 'calendar':
            sort = 'date'

        app.COMING_EPS_SORT = sort

        return self.redirect('/schedule/')
