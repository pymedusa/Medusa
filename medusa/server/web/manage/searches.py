# coding=utf-8

from __future__ import unicode_literals

import logging

from tornroutes import route

from medusa import app, ui
from medusa.server.web.core import PageTemplate
from medusa.server.web.manage.handler import Manage

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


@route('/manage/manageSearches(/?.*)')
class ManageSearches(Manage):
    def __init__(self, *args, **kwargs):
        super(ManageSearches, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename='manage_manageSearches.mako')

        return t.render(backlogPaused=app.search_queue_scheduler.action.is_backlog_paused(),
                        backlogRunning=app.search_queue_scheduler.action.is_backlog_in_progress(),
                        dailySearchStatus=app.daily_search_scheduler.action.am_active,
                        findPropersStatus=app.proper_finder_scheduler.action.am_active,
                        searchQueueLength=app.search_queue_scheduler.action.queue_length(),
                        forcedSearchQueueLength=app.forced_search_queue_scheduler.action.queue_length(),
                        subtitlesFinderStatus=app.subtitles_finder_scheduler.action.am_active,
                        title='Manage Searches', header='Manage Searches', topmenu='manage',
                        controller='manage', action='manageSearches')

    def forceBacklog(self):
        # force it to run the next time it looks
        result = app.backlog_search_scheduler.force_run()
        if result:
            log.info('Backlog search forced')
            ui.notifications.message('Backlog search started')

        return self.redirect('/manage/manageSearches/')

    def forceSearch(self):

        # force it to run the next time it looks
        result = app.daily_search_scheduler.force_run()
        if result:
            log.info('Daily search forced')
            ui.notifications.message('Daily search started')

        return self.redirect('/manage/manageSearches/')

    def forceFindPropers(self):
        # force it to run the next time it looks
        result = app.proper_finder_scheduler.force_run()
        if result:
            log.info('Find propers search forced')
            ui.notifications.message('Find propers search started')

        return self.redirect('/manage/manageSearches/')

    def forceSubtitlesFinder(self):
        # force it to run the next time it looks
        result = app.subtitles_finder_scheduler.force_run()
        if result:
            log.info('Subtitle search forced')
            ui.notifications.message('Subtitle search started')

        return self.redirect('/manage/manageSearches/')

    def pauseBacklog(self, paused=None):
        if paused == '1':
            app.search_queue_scheduler.action.pause_backlog()
        else:
            app.search_queue_scheduler.action.unpause_backlog()

        return self.redirect('/manage/manageSearches/')
