# coding=utf-8

from __future__ import unicode_literals

import datetime

from medusa import app, network_timezones
from medusa.server.web.core.base import PageTemplate, WebRoot
from medusa.show.coming_episodes import ComingEpisodes

from tornroutes import route


@route('/schedule(/?.*)')
class Schedule(WebRoot):
    def __init__(self, *args, **kwargs):
        super(Schedule, self).__init__(*args, **kwargs)

    def index(self):
        next_week = datetime.date.today() + datetime.timedelta(days=7)
        next_week1 = datetime.datetime.combine(next_week, datetime.time(tzinfo=network_timezones.app_timezone))
        results = ComingEpisodes.get_coming_episodes(ComingEpisodes.categories, app.COMING_EPS_SORT, False)
        today = datetime.datetime.now().replace(tzinfo=network_timezones.app_timezone)

        t = PageTemplate(rh=self, filename='schedule.mako')
        return t.render(next_week=next_week1, today=today, results=results,
                        layout=app.COMING_EPS_LAYOUT, controller='schedule', action='index')

    def toggleScheduleDisplayPaused(self):
        app.COMING_EPS_DISPLAY_PAUSED = not app.COMING_EPS_DISPLAY_PAUSED

        return self.redirect('/schedule/')

    def setScheduleSort(self, sort):
        if sort not in ('date', 'network', 'show') or app.COMING_EPS_LAYOUT == 'calendar':
            sort = 'date'

        app.COMING_EPS_SORT = sort

        return self.redirect('/schedule/')
