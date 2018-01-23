# coding=utf-8
"""GitHub issue submitter."""
from __future__ import unicode_literals

import difflib
import locale
import logging
import platform
import sys
from datetime import datetime, timedelta
from github import InputFileContent
from github.GithubException import GithubException, RateLimitExceededException
from medusa import app, db
from medusa.classes import ErrorViewer
from medusa.github_client import authenticate, get_github_repo, token_authenticate
from medusa.logger.adapters.style import BraceAdapter

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

ISSUE_REPORT = """
### INFO
**Python Version**: `{python_version}`
**Operating System**: `{os}`
**Locale**: `{locale}`
**Branch**: [{branch}](../tree/{branch})
**Database**: `{db_major_version}.{db_minor_version}`
**Commit**: {org}/{repo}@{commit}
**Link to Log**: {log_url}
### ERROR
{log_line}
---
_STAFF NOTIFIED_: @{org}/support @{org}/moderators
"""


class IssueSubmitter(object):
    """GitHub issue submitter."""

    MISSING_CREDENTIALS = 'Please set your GitHub Username and Password in the config.  Unable to submit issue ticket to GitHub.'
    DEBUG_NOT_ENABLED = 'Please enable Debug mode in the config.  Unable to submit issue ticket to GitHub.'
    NO_ISSUES = 'No issue to be submitted to GitHub.'
    UNSUPPORTED_VERSION = 'Please update Medusa, unable to submit issue ticket to GitHub with an outdated version.'
    ALREADY_RUNNING = 'An issue is already being submitted, please wait for it to complete.'
    BAD_CREDENTIALS = 'Please check your Github credentials in Medusa settings. Bad Credentials error'
    RATE_LIMIT = 'Please wait before submit new issues. Github Rate Limit Exceeded error'
    GITHUB_EXCEPTION = 'Error trying to contact Github. Please try again'
    EXISTING_ISSUE_LOCKED = 'Issue #{number} is locked, check GitHub to find info about the error.'
    COMMENTED_EXISTING_ISSUE = 'Commented on existing issue #{number} successfully!'
    ISSUE_CREATED = 'Your issue ticket #{number} was submitted successfully!'

    TITLE_PREFIX = '[APP SUBMITTED]: '

    def __init__(self):
        """Initialize class with the default constructor."""
        self.running = False

    @staticmethod
    def create_gist(github, logline):
        """Create a private gist with log data for the specified log line."""
        context_loglines = logline.get_context_loglines()
        if context_loglines:
            content = '\n'.join([str(ll) for ll in context_loglines])
            return github.get_user().create_gist(False, {'application.log': InputFileContent(content)})

    @staticmethod
    def create_issue_data(logline, log_url):
        """Create the issue data expected by github api to be submitted."""
        try:
            locale_name = locale.getdefaultlocale()[1]
        except ValueError:
            locale_name = 'unknown'

        # Get current DB version
        main_db_con = db.DBConnection()
        cur_branch_major_db_version, cur_branch_minor_db_version = main_db_con.checkDBVersion()

        commit = app.CUR_COMMIT_HASH
        base_url = '../blob/{commit}'.format(commit=commit) if commit else None
        return ISSUE_REPORT.format(
            python_version=sys.version[:120].replace('\n', ''),
            os=platform.platform(),
            locale=locale_name,
            branch=app.BRANCH,
            org=app.GIT_ORG,
            repo=app.GIT_REPO,
            commit=commit,
            db_major_version=cur_branch_major_db_version,
            db_minor_version=cur_branch_minor_db_version,
            log_url=log_url or '**No Log available**',
            log_line=logline.format_to_html(base_url=base_url),
        )

    @classmethod
    def find_similar_issues(cls, github_repo, loglines, max_age=timedelta(days=180)):
        """Find similar issues in the GitHub repository."""
        results = dict()
        issues = github_repo.get_issues(state='all', since=datetime.now() - max_age)
        for issue in issues:
            if hasattr(issue, 'pull_request') and issue.pull_request:
                continue
            issue_title = issue.title
            if issue_title.startswith(cls.TITLE_PREFIX):
                issue_title = issue_title[len(cls.TITLE_PREFIX):]

            for logline in loglines:
                log_title = logline.issue_title
                if cls.similar(log_title, issue_title):
                    results[logline.key] = issue

            if len(results) >= len(loglines):
                break

        return results

    @staticmethod
    def similar(title1, title2, ratio=0.9):
        """Compare title similarity."""
        return difflib.SequenceMatcher(None, title1, title2).ratio() >= ratio

    def submit_github_issue(self, version_checker, max_issues=500):
        """Submit errors to github."""
        def result(message, level=logging.WARNING):
            log.log(level, message)
            return [(message, None)]

        if not app.DEBUG:
            return result(self.DEBUG_NOT_ENABLED)

        if not (app.GIT_USERNAME and app.GIT_PASSWORD) or app.GIT_TOKEN:
            return result(self.MISSING_CREDENTIALS)

        if not ErrorViewer.errors:
            return result(self.NO_ISSUES, logging.INFO)

        if not app.DEVELOPER and version_checker.need_update():
            return result(self.UNSUPPORTED_VERSION)

        if self.running:
            return result(self.ALREADY_RUNNING)

        self.running = True
        try:
            if app.GIT_AUTH_TYPE:
                github = token_authenticate(app.GIT_TOKEN)
            else:
                github = authenticate(app.GIT_USERNAME, app.GIT_PASSWORD)
            if not github:
                return result(self.BAD_CREDENTIALS)

            github_repo = get_github_repo(app.GIT_ORG, app.GIT_REPO, gh=github)
            loglines = ErrorViewer.errors[:max_issues]
            similar_issues = self.find_similar_issues(github_repo, loglines)

            return self.submit_issues(github, github_repo, loglines, similar_issues)
        except RateLimitExceededException:
            return result(self.RATE_LIMIT)
        except (GithubException, IOError):
            return result(self.GITHUB_EXCEPTION)
        finally:
            self.running = False

    @classmethod
    def submit_issues(cls, github, github_repo, loglines, similar_issues):
        """Submit issues to github."""
        results = []
        for line in loglines:
            gist = cls.create_gist(github, line)
            message = cls.create_issue_data(line, log_url=gist.html_url if gist else None)
            similar_issue = similar_issues.get(line.key)
            issue_id = None
            if similar_issue:
                if similar_issue.raw_data['locked']:
                    submitter_result = cls.EXISTING_ISSUE_LOCKED.format(number=similar_issue.number)
                    log.warning(submitter_result)
                else:
                    similar_issue.create_comment(message)
                    issue_id = similar_issue.number
                    submitter_result = cls.COMMENTED_EXISTING_ISSUE.format(number=issue_id)
                    log.info(submitter_result)
                    ErrorViewer.remove(line)
            else:
                issue = github_repo.create_issue('{prefix}{title}'.format(prefix=cls.TITLE_PREFIX, title=line.issue_title), message)
                issue_id = issue.number
                submitter_result = cls.ISSUE_CREATED.format(number=issue_id)
                log.info(submitter_result)
                ErrorViewer.remove(line)
            results.append((submitter_result, issue_id))

        return results
