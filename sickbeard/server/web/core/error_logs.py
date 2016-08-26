# coding=utf-8
"""Route to error logs web page."""

from __future__ import unicode_literals

import io
import os
import re

from mako.filters import html_escape
import sickbeard
from sickbeard import (
    classes, logger, ui,
)
from sickbeard.server.web.core.base import PageTemplate, WebRoot
from sickrage.helper.encoding import ek
from tornado.routes import route


# log regular expression: 2016-08-06 15:58:34 ERROR    DAILYSEARCHER :: [d4ea5af] Exception generated in thread DAILYSEARCHER
log_re = re.compile(r'^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})\s+'
                    r'(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})\s+'
                    r'(?P<log_level>[A-Z]+)\s+(?P<log_name>.+?)\s+::\s+(?P<log_message>.*)$')

# log name filters
log_name_filters = {
    '<NONE>': html_escape('<No Filter>'),
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
    'SHOWQUEUE-FORCE-UPDATE': 'Show Queue (Forced Update)',
    'SHOWQUEUE-UPDATE': 'Show Queue (Update)',
    'SHOWQUEUE-REFRESH': 'Show Queue (Refresh)',
    'SHOWQUEUE-FORCE-REFRESH': 'Show Queue (Forced Refresh)',
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


@route('/errorlogs(/?.*)')
class ErrorLogs(WebRoot):
    """Route to errorlogs web page."""

    def __init__(self, *args, **kwargs):
        """Default constructor."""
        super(ErrorLogs, self).__init__(*args, **kwargs)

    def _create_menu(self, level):
        return [
            {  # Clear Errors
                'title': 'Clear Errors',
                'path': '/api/v2/log/',
                'requires': self._has_errors() and level == logger.ERROR,
                'icon': 'ui-icon ui-icon-trash'
            },
            {  # Clear Warnings
                'title': 'Clear Warnings',
                'path': '/api/v2/log/{level}'.format(level=logger.WARNING),
                'requires': self._has_warnings() and level == logger.WARNING,
                'icon': 'ui-icon ui-icon-trash'
            },
            {  # Submit Errors
                'title': 'Submit Errors',
                'path': 'errorlogs/submit_errors/',
                'requires': self._has_errors() and level == logger.ERROR,
                'class': 'submiterrors',
                'confirm': True,
                'icon': 'ui-icon ui-icon-arrowreturnthick-1-n'
            },
        ]

    def index(self, level=logger.ERROR, **kwargs):
        """Default index page."""
        try:
            level = int(level)
        except (TypeError, ValueError):
            level = logger.ERROR

        t = PageTemplate(rh=self, filename='errorlogs.mako')
        return t.render(header='Logs &amp; Errors', title='Logs &amp; Errors', topmenu='system',
                        submenu=self._create_menu(level), logLevel=level, controller='errorlogs', action='index')

    @staticmethod
    def _has_errors():
        return bool(classes.ErrorViewer.errors)

    @staticmethod
    def _has_warnings():
        return bool(classes.WarningViewer.errors)

    def clearerrors(self, level=logger.ERROR):
        """Clear the errors or warnings."""
        if int(level) == logger.WARNING:
            classes.WarningViewer.clear()
        else:
            classes.ErrorViewer.clear()

        return self.redirect('/errorlogs/viewlog/')

    @staticmethod
    def _get_data(lines, min_level, log_filter, log_search, num_lines, max_lines):
        last_line = False
        num_to_show = min(max_lines, num_lines + len(lines))

        final_data = []
        for line in reversed(lines):
            match = log_re.match(line)
            if match:
                level = match.group('log_level')
                log_name = match.group('log_name')
                if level not in logger.LOGGING_LEVELS:
                    last_line = False
                    continue

                if log_search and log_search.lower() in line.lower():
                    last_line = True
                    final_data.append(line)
                    num_lines += 1

                elif not log_search and logger.LOGGING_LEVELS[level] >= min_level and (log_filter == '<NONE>' or log_name.startswith(log_filter)):
                    last_line = True
                    final_data.append(line)
                    num_lines += 1
                else:
                    last_line = False
                    continue

            elif last_line:
                final_data.append('AA' + line)
                num_lines += 1

            if num_lines >= num_to_show:
                return final_data

        return final_data

    def viewlog(self, minLevel=logger.INFO, logFilter='<NONE>', logSearch=None, maxLines=1000, **kwargs):
        """View the log given the specified filters."""
        min_level = int(minLevel)
        log_filter = logFilter if logFilter in log_name_filters else '<NONE>'
        log_search = logSearch
        max_lines = maxLines

        t = PageTemplate(rh=self, filename='viewlogs.mako')

        data = []
        log_files = [logger.log_file] + ['{file}.{number}'.format(file=logger.log_file, number=i) for i in range(1, int(sickbeard.LOG_NR))]
        for log_file in log_files:
            if len(data) <= max_lines and ek(os.path.isfile, log_file):
                with io.open(log_file, 'r', encoding='utf-8') as f:
                    data += ErrorLogs._get_data(f.readlines(), min_level, log_filter, log_search, len(data), max_lines)

        return t.render(header='Log File', title='Logs', topmenu='system', logLines=''.join([html_escape(line) for line in data]),
                        minLevel=min_level, logNameFilters=log_name_filters, logFilter=log_filter, logSearch=log_search,
                        controller='errorlogs', action='viewlogs')

    def submit_errors(self):
        """Create an issue in medusa issue tracker."""
        submitter_result, issue_id = logger.submit_errors()
        logger.log(submitter_result, (logger.INFO, logger.WARNING)[issue_id is None])
        submitter_notification = ui.notifications.error if issue_id is None else ui.notifications.message
        submitter_notification(submitter_result)

        return self.redirect('/errorlogs/')
