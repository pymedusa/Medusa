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


class IssueSubmitter(object):
    """GitHub issue submitter."""

    INVALID_CONFIG = 'Please set your GitHub username and password in the config and enable debug. Unable to submit issue ticket to GitHub.'
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
        """Create a private gist with log data for the specified logline.

        :param github:
        :type github: Github
        :param logline:
        :type logline: medusa.logger.LogLine
        :return:
        :rtype: github.Gist.Gist
        """
        context_loglines = logline.get_context_loglines()
        if context_loglines:
            content = '\n'.join([str(ll) for ll in context_loglines])
            return github.get_user().create_gist(False, {'application.log': InputFileContent(content)})

    @staticmethod
    def create_issue_data(logline, log_url):
        """Create the issue data expected by github api to be submitted.

        :param logline:
        :type logline: medusa.logger.LogLine
        :param log_url:
        :type log_url: str
        :return:
        :rtype: str
        """
        try:
            locale_name = locale.getdefaultlocale()[1]
        except ValueError:
            locale_name = 'unknown'

        # Get current DB version
        main_db_con = db.DBConnection()
        cur_branch_major_db_version, cur_branch_minor_db_version = main_db_con.checkDBVersion()

        commit = app.CUR_COMMIT_HASH
        base_url = '../blob/{commit}'.format(commit=commit) if commit else None
        return '\n'.join([
            '### INFO',
            '**Python Version**: `{python_version}`'.format(python_version=sys.version[:120].replace('\n', '')),
            '**Operating System**: `{os}`'.format(os=platform.platform()),
            '**Locale**: `{locale}`'.format(locale=locale_name),
            '**Branch**: [{branch}](../tree/{branch})'.format(branch=app.BRANCH),
            '**Database**: `{0}.{1}`'.format(cur_branch_major_db_version, cur_branch_minor_db_version),
            '**Commit**: {org}/{repo}@{commit}'.format(org=app.GIT_ORG, repo=app.GIT_REPO, commit=commit),
            '**Link to Log**: {log_url}'.format(log_url=log_url) if log_url else '**No Log available**',
            '### ERROR',
            logline.format_to_html(base_url=base_url),
            '---',
            '_STAFF NOTIFIED_: @{org}/support @{org}/moderators'.format(org=app.GIT_ORG),
        ])

    @staticmethod
    def find_similar_issues(github_repo, loglines, max_age=timedelta(days=180)):
        """Find similar issues in GitHub repo.

        :param github_repo:
        :type github_repo: github.Repository.Repository
        :param loglines:
        :type loglines: list of medusa.logger.LogLine
        :param max_age:
        :type max_age: timedelta
        :return:
        :rtype: dict(str, github.Issue.Issue)
        """
        results = dict()
        issues = github_repo.get_issues(state='all', since=datetime.now() - max_age)
        for issue in issues:
            if hasattr(issue, 'pull_request') and issue.pull_request:
                continue
            issue_title = issue.title
            if issue_title.startswith(IssueSubmitter.TITLE_PREFIX):
                issue_title = issue_title[len(IssueSubmitter.TITLE_PREFIX):]

            for logline in loglines:
                log_title = logline.issue_title
                if IssueSubmitter.similar(log_title, issue_title):
                    results[logline.key] = issue

            if len(results) >= len(loglines):
                break

        return results

    @staticmethod
    def similar(title1, title2, ratio=0.9):
        """Return wheter the title1 is similar to title2.

        :param title1:
        :type title1: str
        :param title2:
        :type title2: str
        :param ratio:
        :type ratio: float
        :return:
        :rtype: bool
        """
        return difflib.SequenceMatcher(None, title1, title2).ratio() >= ratio

    def submit_github_issue(self, version_checker, max_issues=500):
        """Submit errors to github.

        :param version_checker:
        :type version_checker: CheckVersion
        :param max_issues:
        :type max_issues: int
        :return: user message and issue number
        :rtype: list of tuple(str, str)
        """
        if app.GIT_AUTH_TYPE == 0:
            if not app.DEBUG or not app.GIT_USERNAME or not app.GIT_PASSWORD:
                log.warning(IssueSubmitter.INVALID_CONFIG)
                return [(IssueSubmitter.INVALID_CONFIG, None)]
        else:
            if not app.DEBUG or not app.GIT_TOKEN:
                log.warning(IssueSubmitter.INVALID_CONFIG)
                return [(IssueSubmitter.INVALID_CONFIG, None)]
        if not ErrorViewer.errors:
            log.info(IssueSubmitter.NO_ISSUES)
            return [(IssueSubmitter.NO_ISSUES, None)]

        if not app.DEVELOPER and version_checker.need_update():
            log.warning(IssueSubmitter.UNSUPPORTED_VERSION)
            return [(IssueSubmitter.UNSUPPORTED_VERSION, None)]

        if self.running:
            log.warning(IssueSubmitter.ALREADY_RUNNING)
            return [(IssueSubmitter.ALREADY_RUNNING, None)]

        self.running = True
        try:
            if app.GIT_AUTH_TYPE == 0:
                github = authenticate(app.GIT_USERNAME, app.GIT_PASSWORD)
            else:
                github = token_authenticate(app.GIT_TOKEN)
            if not github:
                return [(IssueSubmitter.BAD_CREDENTIALS, None)]

            github_repo = get_github_repo(app.GIT_ORG, app.GIT_REPO, gh=github)
            loglines = ErrorViewer.errors[:max_issues]
            similar_issues = IssueSubmitter.find_similar_issues(github_repo, loglines)

            return IssueSubmitter.submit_issues(github, github_repo, loglines, similar_issues)
        except RateLimitExceededException:
            log.warning(IssueSubmitter.RATE_LIMIT)
            return [(IssueSubmitter.RATE_LIMIT, None)]
        except (GithubException, IOError):
            log.warning(IssueSubmitter.GITHUB_EXCEPTION)
            return [(IssueSubmitter.GITHUB_EXCEPTION, None)]
        finally:
            self.running = False

    @staticmethod
    def submit_issues(github, github_repo, loglines, similar_issues):
        """Submit issues to github.

        :param github:
        :type github: Github
        :param github_repo:
        :type github_repo: github.Repository.Repository
        :param loglines:
        :type loglines: list of medusa.logger.LogLine
        :param similar_issues:
        :type similar_issues: dict(str, github.Issue.Issue)
        :return:
        :rtype: list of tuple(str, str)
        """
        results = []
        for logline in loglines:
            gist = IssueSubmitter.create_gist(github, logline)
            message = IssueSubmitter.create_issue_data(logline, log_url=gist.html_url if gist else None)
            similar_issue = similar_issues.get(logline.key)
            issue_id = None
            if similar_issue:
                if similar_issue.raw_data['locked']:
                    submitter_result = IssueSubmitter.EXISTING_ISSUE_LOCKED.format(number=similar_issue.number)
                    log.warning(submitter_result)
                else:
                    similar_issue.create_comment(message)
                    issue_id = similar_issue.number
                    submitter_result = IssueSubmitter.COMMENTED_EXISTING_ISSUE.format(number=issue_id)
                    log.info(submitter_result)
                    ErrorViewer.remove(logline)
            else:
                issue = github_repo.create_issue('{prefix}{title}'.format(prefix=IssueSubmitter.TITLE_PREFIX, title=logline.issue_title), message)
                issue_id = issue.number
                submitter_result = IssueSubmitter.ISSUE_CREATED.format(number=issue_id)
                log.info(submitter_result)
                ErrorViewer.remove(logline)
            results.append((submitter_result, issue_id))

        return results
