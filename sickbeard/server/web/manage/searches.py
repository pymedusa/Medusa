# coding=utf-8

from __future__ import unicode_literals

from tornado.routes import route
import sickbeard
from sickbeard import (
    logger, ui,
)
from sickbeard.server.web.core import PageTemplate
from sickbeard.server.web.manage.handler import Manage


@route('/manage/manageSearches(/?.*)')
class ManageSearches(Manage):
    def __init__(self, *args, **kwargs):
        super(ManageSearches, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename='manage_manageSearches.mako')
        # t.backlogPI = sickbeard.backlogSearchScheduler.action.getProgressIndicator()

        return t.render(backlogPaused=sickbeard.searchQueueScheduler.action.is_backlog_paused(),
                        backlogRunning=sickbeard.searchQueueScheduler.action.is_backlog_in_progress(),
                        dailySearchStatus=sickbeard.dailySearchScheduler.action.amActive,
                        findPropersStatus=sickbeard.properFinderScheduler.action.amActive,
                        searchQueueLength=sickbeard.searchQueueScheduler.action.queue_length(),
                        forcedSearchQueueLength=sickbeard.forcedSearchQueueScheduler.action.queue_length(),
                        subtitlesFinderStatus=sickbeard.subtitlesFinderScheduler.action.amActive,
                        title='Manage Searches', header='Manage Searches', topmenu='manage',
                        controller='manage', action='manageSearches')

    def forceBacklog(self):
        # force it to run the next time it looks
        result = sickbeard.backlogSearchScheduler.forceRun()
        if result:
            logger.log('Backlog search forced')
            ui.notifications.message('Backlog search started')

        return self.redirect('/manage/manageSearches/')

    def forceSearch(self):

        # force it to run the next time it looks
        result = sickbeard.dailySearchScheduler.forceRun()
        if result:
            logger.log('Daily search forced')
            ui.notifications.message('Daily search started')

        return self.redirect('/manage/manageSearches/')

    def forceFindPropers(self):
        # force it to run the next time it looks
        result = sickbeard.properFinderScheduler.forceRun()
        if result:
            logger.log('Find propers search forced')
            ui.notifications.message('Find propers search started')

        return self.redirect('/manage/manageSearches/')

    def forceSubtitlesFinder(self):
        # force it to run the next time it looks
        result = sickbeard.subtitlesFinderScheduler.forceRun()
        if result:
            logger.log('Subtitle search forced')
            ui.notifications.message('Subtitle search started')

        return self.redirect('/manage/manageSearches/')

    def pauseBacklog(self, paused=None):
        if paused == '1':
            sickbeard.searchQueueScheduler.action.pause_backlog()
        else:
            sickbeard.searchQueueScheduler.action.unpause_backlog()

        return self.redirect('/manage/manageSearches/')
