# coding=utf-8
"""Route to error logs web page."""

from __future__ import unicode_literals

from datetime import datetime, timedelta

from mako.filters import html_escape
from six import text_type
from tornado.routes import route
from .base import PageTemplate, WebRoot
from .... import logger, ui
from ....classes import ErrorViewer, WarningViewer
from ....issuesubmitter import IssueSubmitter
from ....logger import filter_logline, read_loglines
from ....versionChecker import CheckVersion


# log name filters
log_name_filters = {
    None: html_escape('<No Filter>'),
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

log_periods = {
    'all': None,
    'one_day': timedelta(days=1),
    'three_days': timedelta(days=3),
    'one_week': timedelta(days=7),
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

    def viewlog(self, min_level=logger.INFO, log_filter=None, log_search=None, max_lines=1000, log_period='one_day', **kwargs):
        """View the log given the specified filters."""
        min_level = int(min_level)
        log_filter = log_filter if log_filter in log_name_filters else None

        t = PageTemplate(rh=self, filename='viewlogs.mako')

        period = log_periods.get(log_period)
        modification_time = datetime.now() - period if period else None
        data = [line for line in read_loglines(modification_time=modification_time, formatter=text_type, max_lines=max_lines,
                                               predicate=lambda l: filter_logline(l, min_level=min_level, thread_name=log_filter, search_query=log_search))]

        return t.render(header='Log File', title='Logs', topmenu='system', log_lines='\n'.join([html_escape(line) for line in data]),
                        min_level=min_level, log_name_filters=log_name_filters, log_filter=log_filter, log_search=log_search, log_period=log_period,
                        controller='errorlogs', action='viewlogs')

    def submit_errors(self):
        """Create an issue in medusa issue tracker."""
        results = self.issue_submitter.submit_github_issue(CheckVersion())
        for submitter_result, issue_id in results:
            submitter_notification = ui.notifications.error if issue_id is None else ui.notifications.message
            submitter_notification(submitter_result)

        return self.redirect('/errorlogs/')
