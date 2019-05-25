# coding=utf-8
"""Route to error logs web page."""

from __future__ import unicode_literals

import logging
from datetime import datetime, timedelta

from mako.filters import html_escape

from medusa import ui
from medusa.classes import ErrorViewer, WarningViewer
from medusa.issue_submitter import IssueSubmitter
from medusa.logger import filter_logline, read_loglines
from medusa.server.web.core.base import PageTemplate, WebRoot
from medusa.updater.version_checker import CheckVersion

from six import text_type

from tornroutes import route

log = logging.getLogger(__name__)

log_name_filters = {
    '': html_escape('<No Filter>'),
    'DAILYSEARCHER': 'Daily Searcher',
    'BACKLOG': 'Backlog',
    'SHOWUPDATER': 'Show Updater',
    'CHECKVERSION': 'Check Version',
    'SHOWQUEUE': 'Show Queue (All)',
    'SEARCHQUEUE': 'Search Queue (All)',
    'SEARCHQUEUE-DAILY-SEARCH': 'Search Queue (Daily Searcher)',
    'SEARCHQUEUE-BACKLOG': 'Search Queue (Backlog)',
    'SEARCHQUEUE-MANUAL': 'Search Queue (Manual)',
    'SEARCHQUEUE-FORCED': 'Search Queue (Forced)',
    'SEARCHQUEUE-RETRY': 'Search Queue (Retry/Failed)',
    'SEARCHQUEUE-RSS': 'Search Queue (RSS)',
    'SHOWQUEUE-UPDATE': 'Show Queue (Update)',
    'SHOWQUEUE-SEASON-UPDATE': 'Show Season Queue (Update)',
    'SHOWQUEUE-REFRESH': 'Show Queue (Refresh)',
    'FINDPROPERS': 'Find Propers',
    'POSTPROCESSOR': 'PostProcessor',
    'FINDSUBTITLES': 'Find Subtitles',
    'TRAKTCHECKER': 'Trakt Checker',
    'TORRENTCHECKER': 'Torrent Checker',
    'EVENT': 'Event',
    'ERROR': 'Error',
    'TORNADO': 'Tornado',
    'Thread': 'Thread',
    'MAIN': 'Main',
}

thread_names = {
    'SHOWQUEUE': {name for name in log_name_filters if name and name.startswith('SHOWQUEUE-')},
    'SEARCHQUEUE': {name for name in log_name_filters if name and name.startswith('SEARCHQUEUE-')}
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

    # @TODO: Move this route to /log(/?)

    # GitHub Issue submitter
    issue_submitter = IssueSubmitter()

    def __init__(self, *args, **kwargs):
        """Initialize class with default constructor."""
        super(ErrorLogs, self).__init__(*args, **kwargs)

    def index(self, level=logging.ERROR, **kwargs):
        """Render default index page."""
        try:
            level = int(level)
        except (TypeError, ValueError):
            level = logging.ERROR

        t = PageTemplate(rh=self, filename='errorlogs.mako')
        return t.render(logLevel=level, controller='errorlogs', action='index')

    def clearerrors(self, level=logging.ERROR):
        """Clear the errors or warnings."""
        # @TODO: Replace this with DELETE /api/v2/log/{logLevel} or /api/v2/log/
        if int(level) == logging.WARNING:
            WarningViewer.clear()
        else:
            ErrorViewer.clear()

        return self.redirect('/errorlogs/viewlog/')

    def viewlog(self, min_level=logging.INFO, log_filter=None, log_search=None, max_lines=1000, log_period='one_day',
                text_view=None, **kwargs):
        """View the log given the specified filters."""
        # @TODO: Replace index with this or merge it so ?search=true or ?query={queryString} enables this "view"
        min_level = int(min_level)
        log_filter = log_filter if log_filter in log_name_filters else None

        t = PageTemplate(rh=self, filename='viewlogs.mako')

        period = log_periods.get(log_period)
        modification_time = datetime.now() - period if period else None
        data = (html_escape(line) for line in read_loglines(modification_time=modification_time, formatter=text_type, max_lines=max_lines,
                                                            predicate=lambda l: filter_logline(l, min_level=min_level,
                                                                                               thread_name=thread_names.get(log_filter, log_filter),
                                                                                               search_query=log_search)))

        if not text_view:
            return t.render(log_lines='\n'.join(data),
                            min_level=min_level, log_name_filters=log_name_filters, log_filter=log_filter, log_search=log_search, log_period=log_period,
                            controller='errorlogs', action='viewlogs')
        else:
            return '<br/>'.join(data)

    def submit_errors(self):
        """Create an issue in medusa issue tracker."""
        results = self.issue_submitter.submit_github_issue(CheckVersion())
        for submitter_result, issue_id in results:
            submitter_notification = ui.notifications.error if issue_id is None else ui.notifications.message
            submitter_notification(submitter_result)

        return self.redirect('/errorlogs/')
