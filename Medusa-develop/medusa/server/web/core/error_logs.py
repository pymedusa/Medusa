# coding=utf-8
"""Route to error logs web page."""

from __future__ import unicode_literals

import logging

from medusa import ui
from medusa.classes import ErrorViewer, WarningViewer
from medusa.issue_submitter import IssueSubmitter
from medusa.server.web.core.base import PageTemplate, WebRoot
from medusa.updater.version_checker import CheckVersion

from tornroutes import route

log = logging.getLogger(__name__)


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

    def viewlog(self, **kwargs):
        """
        Render the log viewer page.

        [Converted to VueRouter]
        """
        return PageTemplate(rh=self, filename='index.mako').render()

    def submit_errors(self):
        """Create an issue in medusa issue tracker."""
        results = self.issue_submitter.submit_github_issue(CheckVersion())
        for submitter_result, issue_id in results:
            submitter_notification = ui.notifications.error if issue_id is None else ui.notifications.message
            submitter_notification(submitter_result)

        return self.redirect('/errorlogs/')
