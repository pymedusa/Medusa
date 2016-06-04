# coding=utf-8

from __future__ import unicode_literals

from tornado.routes import route
import sickbeard
from sickbeard import ui
from sickrage.helper.common import try_int
from sickrage.show.History import History as HistoryTool
from sickbeard.server.web.core.base import WebRoot, PageTemplate


@route('/history(/?.*)')
class History(WebRoot):
    def __init__(self, *args, **kwargs):
        super(History, self).__init__(*args, **kwargs)

        self.history = HistoryTool()

    def index(self, limit=None):

        if limit is None:
            if sickbeard.HISTORY_LIMIT:
                limit = int(sickbeard.HISTORY_LIMIT)
            else:
                limit = 100
        else:
            limit = try_int(limit, 100)

        sickbeard.HISTORY_LIMIT = limit

        sickbeard.save_config()

        history = self.history.get(limit)

        t = PageTemplate(rh=self, filename='history.mako')
        submenu = [
            {'title': 'Clear History', 'path': 'history/clearHistory', 'icon': 'ui-icon ui-icon-trash', 'class': 'clearhistory', 'confirm': True},
            {'title': 'Trim History', 'path': 'history/trimHistory', 'icon': 'menu-icon-cut', 'class': 'trimhistory', 'confirm': True},
        ]

        return t.render(historyResults=history.detailed, compactResults=history.compact, limit=limit,
                        submenu=submenu, title='History', header='History',
                        topmenu='history', controller='history', action='index')

    def clearHistory(self):
        self.history.clear()

        ui.notifications.message('History cleared')

        return self.redirect('/history/')

    def trimHistory(self):
        self.history.trim()

        ui.notifications.message('Removed history entries older than 30 days')

        return self.redirect('/history/')
