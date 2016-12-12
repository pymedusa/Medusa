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
        # t.backlogPI = api.backlogSearchScheduler.action.get_progress_indicator()

        return t.render(backlogPaused=app.searchQueueScheduler.action.is_backlog_paused(),
                        backlogRunning=app.searchQueueScheduler.action.is_backlog_in_progress(),
                        dailySearchStatus=app.dailySearchScheduler.action.amActive,
                        findPropersStatus=app.properFinderScheduler.action.amActive,
                        searchQueueLength=app.searchQueueScheduler.action.queue_length(),
                        forcedSearchQueueLength=app.forcedSearchQueueScheduler.action.queue_length(),
                        subtitlesFinderStatus=app.subtitlesFinderScheduler.action.amActive,
                        title='Manage Searches', header='Manage Searches', topmenu='manage',
                        controller='manage', action='manageSearches')

    def forceBacklog(self):
        # force it to run the next time it looks
        result = app.backlogSearchScheduler.forceRun()
        if result:
            logger.log('Backlog search forced')
            ui.notifications.message('Backlog search started')

        return self.redirect('/manage/manageSearches/')

    def forceSearch(self):

        # force it to run the next time it looks
        result = app.dailySearchScheduler.forceRun()
        if result:
            logger.log('Daily search forced')
            ui.notifications.message('Daily search started')

        return self.redirect('/manage/manageSearches/')

    def forceFindPropers(self):
        # force it to run the next time it looks
        result = app.properFinderScheduler.forceRun()
        if result:
            logger.log('Find propers search forced')
            ui.notifications.message('Find propers search started')

        return self.redirect('/manage/manageSearches/')

    def forceSubtitlesFinder(self):
        # force it to run the next time it looks
        result = app.subtitlesFinderScheduler.forceRun()
        if result:
            logger.log('Subtitle search forced')
            ui.notifications.message('Subtitle search started')

        return self.redirect('/manage/manageSearches/')

    def pauseBacklog(self, paused=None):
        if paused == '1':
            app.searchQueueScheduler.action.pause_backlog()
        else:
            app.searchQueueScheduler.action.unpause_backlog()

        return self.redirect('/manage/manageSearches/')
