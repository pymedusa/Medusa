# coding=utf-8
"""Route to error logs web page."""

from __future__ import unicode_literals

from mako.filters import html_escape
from sickbeard import logger, ui
from sickbeard.classes import ErrorViewer, WarningViewer
from sickbeard.issuesubmitter import IssueSubmitter
from sickbeard.logger import read_loglines
from sickbeard.server.web.core.base import PageTemplate, WebRoot
from sickbeard.versionChecker import CheckVersion
from tornado.routes import route


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

    # GitHub Issue submitter
    issue_submitter = IssueSubmitter()

    def __init__(self, *args, **kwargs):
        """Default constructor."""
        super(ErrorLogs, self).__init__(*args, **kwargs)

    def _create_menu(self, level):
        return [
            {  # Clear Errors
                'title': 'Clear Errors',
                'path': 'errorlogs/clearerrors/',
                'requires': self._has_errors() and level == logger.ERROR,
                'icon': 'ui-icon ui-icon-trash'
            },
            {  # Clear Warnings
                'title': 'Clear Warnings',
                'path': 'errorlogs/clearerrors/?level={level}'.format(level=logger.WARNING),
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
        return bool(ErrorViewer.errors)

    @staticmethod
    def _has_warnings():
        return bool(WarningViewer.errors)

    def clearerrors(self, level=logger.ERROR):
        """Clear the errors or warnings."""
        if int(level) == logger.WARNING:
            WarningViewer.clear()
        else:
            ErrorViewer.clear()

        return self.redirect('/errorlogs/viewlog/')

    @staticmethod
    def match_filter(logline, min_level=None, thread_name=None, search_query=None):
        """Return if logline matches the defined filter.

        :param logline:
        :type logline: sickbeard.logger.LogLine
        :param min_level:
        :type min_level: int
        :param thread_name:
        :type thread_name: str
        :param search_query:
        :type search_query: str
        :return:
        :rtype: bool
        """
        if not logline.is_loglevel_valid(min_level=min_level):
            return False

        if search_query:
            search_query = search_query.lower()
            if (not logline.message or search_query not in logline.message) and (not logline.extra or search_query not in logline.extra):
                return False

        return not thread_name or thread_name in ('<NONE>', logline.thread_name)

    def viewlog(self, minLevel=logger.INFO, logFilter=None, logSearch=None, maxLines=1000, **kwargs):
        """View the log given the specified filters."""
        min_level = int(minLevel)
        log_filter = logFilter if logFilter in log_name_filters else '<NONE>'
        log_search = logSearch
        max_lines = maxLines

        t = PageTemplate(rh=self, filename='viewlogs.mako')

        data = []
        for logline in read_loglines():
            if ErrorLogs.match_filter(logline, min_level=min_level, thread_name=log_filter, search_query=log_search):
                data.append(str(logline))

            if len(data) >= max_lines:
                break

        return t.render(header='Log File', title='Logs', topmenu='system', logLines='\n'.join([html_escape(line) for line in data]),
                        minLevel=min_level, logNameFilters=log_name_filters, logFilter=log_filter, logSearch=log_search,
                        controller='errorlogs', action='viewlogs')

    def submit_errors(self):
        """Create an issue in medusa issue tracker."""
        results = self.issue_submitter.submit_github_issue(CheckVersion())
        for submitter_result, issue_id in results:
            submitter_notification = ui.notifications.error if issue_id is None else ui.notifications.message
            submitter_notification(submitter_result)

        return self.redirect('/errorlogs/')
