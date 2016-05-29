# coding=utf-8

from __future__ import unicode_literals

import io
import os
import re
from tornado.routes import route
import sickbeard
from sickbeard import (
    classes, logger, ui,
)
from sickrage.helper.encoding import ek
from sickbeard.server.web.core.base import WebRoot, PageTemplate


@route('/errorlogs(/?.*)')
class ErrorLogs(WebRoot):
    def __init__(self, *args, **kwargs):
        super(ErrorLogs, self).__init__(*args, **kwargs)

    def ErrorLogsMenu(self, level):
        menu = [
            {'title': 'Clear Errors',
             'path': 'errorlogs/clearerrors/',
             'requires': self.haveErrors() and level == logger.ERROR,
             'icon': 'ui-icon ui-icon-trash'},
            {'title': 'Clear Warnings',
             'path': 'errorlogs/clearerrors/?level={level}'.format(level=logger.WARNING),
             'requires': self.haveWarnings() and level == logger.WARNING,
             'icon': 'ui-icon ui-icon-trash'},
            {'title': 'Submit Errors',
             'path': 'errorlogs/submit_errors/',
             'requires': self.haveErrors() and level == logger.ERROR,
             'class': 'submiterrors',
             'confirm': True,
             'icon': 'ui-icon ui-icon-arrowreturnthick-1-n'},
        ]
        return menu

    def index(self, level=logger.ERROR):
        try:
            level = int(level)
        except Exception:
            level = logger.ERROR

        t = PageTemplate(rh=self, filename='errorlogs.mako')
        return t.render(header='Logs &amp; Errors', title='Logs &amp; Errors',
                        topmenu='system', submenu=self.ErrorLogsMenu(level),
                        logLevel=level, controller='errorlogs', action='index')

    @staticmethod
    def haveErrors():
        if classes.ErrorViewer.errors:
            return True

    @staticmethod
    def haveWarnings():
        if classes.WarningViewer.errors:
            return True

    def clearerrors(self, level=logger.ERROR):
        if int(level) == logger.WARNING:
            classes.WarningViewer.clear()
        else:
            classes.ErrorViewer.clear()

        return self.redirect('/errorlogs/viewlog/')

    def viewlog(self, minLevel=logger.INFO, logFilter='<NONE>', logSearch=None, maxLines=1000):
        min_level = minLevel
        log_filter = logFilter

        def Get_Data(Levelmin, data_in, lines_in, regex, Filter, Search, mlines):

            last_line = False
            num_lines = lines_in
            num_to_show = min(maxLines, num_lines + len(data_in))

            final_data = []

            for x in reversed(data_in):
                match = re.match(regex, x)

                if match:
                    level = match.group(7)
                    log_name = match.group(8)
                    if level not in logger.LOGGING_LEVELS:
                        last_line = False
                        continue

                    if logSearch and logSearch.lower() in x.lower():
                        last_line = True
                        final_data.append(x)
                        num_lines += 1
                    elif not logSearch and logger.LOGGING_LEVELS[level] >= min_level and (log_filter == '<NONE>' or log_name.startswith(log_filter)):
                        last_line = True
                        final_data.append(x)
                        num_lines += 1
                    else:
                        last_line = False
                        continue

                elif last_line:
                    final_data.append('AA' + x)
                    num_lines += 1

                if num_lines >= num_to_show:
                    return final_data

            return final_data

        t = PageTemplate(rh=self, filename='viewlogs.mako')

        min_level = int(min_level)

        log_name_filters = {
            '<NONE>': '&lt;No Filter&gt;',
            'DAILYSEARCHER': 'Daily Searcher',
            'BACKLOG': 'Backlog',
            'SHOWUPDATER': 'Show Updater',
            'CHECKVERSION': 'Check Version',
            'SHOWQUEUE': 'Show Queue',
            'SEARCHQUEUE': 'Search Queue (All)',
            'SEARCHQUEUE-DAILY-SEARCH': 'Search Queue (Daily Searcher)',
            'SEARCHQUEUE-BACKLOG': 'Search Queue (Backlog)',
            'SEARCHQUEUE-MANUAL': 'Search Queue (Manual)',
            'SEARCHQUEUE-FORCED': 'Search Queue (Forced)',
            'SEARCHQUEUE-RETRY': 'Search Queue (Retry/Failed)',
            'SEARCHQUEUE-RSS': 'Search Queue (RSS)',
            'SHOWQUEUE-FORCE-UPDATE': 'Search Queue (Forced Update)',
            'SHOWQUEUE-UPDATE': 'Search Queue (Update)',
            'SHOWQUEUE-REFRESH': 'Search Queue (Refresh)',
            'SHOWQUEUE-FORCE-REFRESH': 'Search Queue (Forced Refresh)',
            'FINDPROPERS': 'Find Propers',
            'POSTPROCESSOR': 'PostProcessor',
            'FINDSUBTITLES': 'Find Subtitles',
            'TRAKTCHECKER': 'Trakt Checker',
            'EVENT': 'Event',
            'ERROR': 'Error',
            'TORNADO': 'Tornado',
            'Thread': 'Thread',
            'MAIN': 'Main',
        }

        if log_filter not in log_name_filters:
            log_filter = '<NONE>'

        regex = r'^(\d\d\d\d)\-(\d\d)\-(\d\d)\s*(\d\d)\:(\d\d):(\d\d)\s*([A-Z]+)\s*(.+?)\s*\:\:\s*(.*)$'

        data = []

        if ek(os.path.isfile, logger.log_file):
            with io.open(logger.log_file, 'r', encoding='utf-8') as f:
                data = Get_Data(min_level, f.readlines(), 0, regex, log_filter, logSearch, maxLines)

        for i in range(1, int(sickbeard.LOG_NR)):
            log_file = '{file}.{number}'.format(file=logger.log_file, number=i)
            if ek(os.path.isfile, log_file) and (len(data) <= maxLines):
                with io.open(log_file, 'r', encoding='utf-8') as f:
                    data += Get_Data(min_level, f.readlines(), len(data), regex, log_filter, logSearch, maxLines)

        return t.render(
            header='Log File', title='Logs', topmenu='system',
            logLines=''.join(data), minLevel=min_level, logNameFilters=log_name_filters,
            logFilter=log_filter, logSearch=logSearch,
            controller='errorlogs', action='viewlogs')

    def submit_errors(self):
        submitter_result, issue_id = logger.submit_errors()
        logger.log(submitter_result, (logger.INFO, logger.WARNING)[issue_id is None])
        submitter_notification = ui.notifications.error if issue_id is None else ui.notifications.message
        submitter_notification(submitter_result)

        return self.redirect('/errorlogs/')
