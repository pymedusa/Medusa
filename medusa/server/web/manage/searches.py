# coding=utf-8

from __future__ import unicode_literals

from tornroutes import route
from .handler import Manage
from ..core import PageTemplate
from .... import app, logger, ui


@route('/manage/manageSearches(/?.*)')
class ManageSearches(Manage):
    def __init__(self, *args, **kwargs):
        super(ManageSearches, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename='manage_manageSearches.mako')
        # t.backlogPI = api.backlog_search_scheduler.action.get_progress_indicator()

        return t.render(backlogPaused=app.search_queue_scheduler.action.is_backlog_paused(),
                        backlogRunning=app.search_queue_scheduler.action.is_backlog_in_progress(),
                        dailySearchStatus=app.daily_search_scheduler.action.amActive,
                        findPropersStatus=app.proper_finder_scheduler.action.amActive,
                        searchQueueLength=app.search_queue_scheduler.action.queue_length(),
                        forcedSearchQueueLength=app.forced_search_queue_scheduler.action.queue_length(),
                        subtitlesFinderStatus=app.subtitles_finder_scheduler.action.amActive,
                        title='Manage Searches', header='Manage Searches', topmenu='manage',
                        controller='manage', action='manageSearches')

    def forceBacklog(self):
        # force it to run the next time it looks
        result = app.backlog_search_scheduler.forceRun()
        if result:
            logger.log('Backlog search forced')
            ui.notifications.message('Backlog search started')

        return self.redirect('/manage/manageSearches/')

    def forceSearch(self):

        # force it to run the next time it looks
        result = app.daily_search_scheduler.forceRun()
        if result:
            logger.log('Daily search forced')
            ui.notifications.message('Daily search started')

        return self.redirect('/manage/manageSearches/')

    def forceFindPropers(self):
        # force it to run the next time it looks
        result = app.proper_finder_scheduler.forceRun()
        if result:
            logger.log('Find propers search forced')
            ui.notifications.message('Find propers search started')

        return self.redirect('/manage/manageSearches/')

    def forceSubtitlesFinder(self):
        # force it to run the next time it looks
        result = app.subtitles_finder_scheduler.forceRun()
        if result:
            logger.log('Subtitle search forced')
            ui.notifications.message('Subtitle search started')

        return self.redirect('/manage/manageSearches/')

    def pauseBacklog(self, paused=None):
        if paused == '1':
            app.search_queue_scheduler.action.pause_backlog()
        else:
            app.search_queue_scheduler.action.unpause_backlog()

        return self.redirect('/manage/manageSearches/')
