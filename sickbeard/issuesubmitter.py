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
from github.GithubException import RateLimitExceededException

import sickbeard

from .classes import ErrorViewer
from .github_client import authenticate, get_github_repo

logger = logging.getLogger(__name__)


class IssueSubmitter(object):
    """GitHub issue submitter."""

    INVALID_CONFIG = 'Please set your GitHub username and password in the config and enable debug. Unable to submit issue ticket to GitHub.'
    NO_ISSUES = 'No issue to be submitted to GitHub.'
    UNSUPPORTED_VERSION = 'Please update Medusa, unable to submit issue ticket to GitHub with an outdated version.'
    ALREADY_RUNNING = 'An issue is already being submitted, please wait for it to complete.'
    BAD_CREDENTIALS = 'Please check your Github credentials in Medusa settings. Bad Credentials error'
    RATE_LIMIT = 'Please wait before submit new issues. Github Rate Limit Exceeded error'
    EXISTING_ISSUE_LOCKED = 'Issue #{number} is locked, check GitHub to find info about the error.'
    COMMENTED_EXISTING_ISSUE = 'Commented on existing issue #{number} successfully!'
    ISSUE_CREATED = 'Your issue ticket #{number} was submitted successfully!'

    TITLE_PREFIX = '[APP SUBMITTED]: '

    def __init__(self):
        """Default constructor."""
        self.running = False

    @staticmethod
    def create_gist(github, logline):
        """Create a private gist with log data for the specified logline.

        :param github:
        :type github: Github
        :param logline:
        :type logline: sickbeard.logger.LogLine
        :return:
        :rtype: github.Gist.Gist
        """
        context_loglines = logline.get_context_loglines()
        if context_loglines:
            content = '\n'.join([str(ll) for ll in context_loglines])
            return github.get_user().create_gist(False, {'sickrage.log': InputFileContent(content)})

    @staticmethod
    def create_issue_data(logline, log_url):
        """Create the issue data expected by github api to be submitted.

        :param logline:
        :type logline: sickbeard.logger.LogLine
        :param log_url:
        :type log_url: str
        :return:
        :rtype: str
        """
        try:
            locale_name = locale.getdefaultlocale()[1]
        except ValueError:
            locale_name = 'unknown'

        commit = sickbeard.CUR_COMMIT_HASH
        base_url = '../blob/{commit}'.format(commit=commit) if commit else None
        return '\n'.join([
            '### INFO',
            '**Python Version**: `{python_version}`'.format(python_version=sys.version[:120].replace('\n', '')),
            '**Operating System**: `{os}`'.format(os=platform.platform()),
            '**Locale**: `{locale}`'.format(locale=locale_name),
            '**Branch**: [{branch}](../tree/{branch})'.format(branch=sickbeard.BRANCH),
            '**Commit**: PyMedusa/SickRage@{commit}'.format(commit=commit),
            '**Link to Log**: {log_url}'.format(log_url=log_url) if log_url else '**No Log available**',
            '### ERROR',
            logline.format_to_html(base_url=base_url),
            '---',
            '_STAFF NOTIFIED_: @pymedusa/support @pymedusa/moderators',
        ])

    @staticmethod
    def find_similar_issues(github_repo, loglines, max_age=timedelta(days=180)):
        """Find similar issues in GitHub repo.

        :param github_repo:
        :type github_repo: github.Repository.Repository
        :param loglines:
        :type loglines: list of sickbeard.logger.LogLine
        :param max_age:
        :type max_age: timedelta
        :return:
        :rtype: dict(str, github.Issue.Issue)
        """
        results = dict()
        issues = github_repo.get_issues(state='all', since=datetime.now() - max_age)
        for issue in issues:
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
        if not sickbeard.DEBUG or not sickbeard.GIT_USERNAME or not sickbeard.GIT_PASSWORD:
            logger.warning(IssueSubmitter.INVALID_CONFIG)
            return [(IssueSubmitter.INVALID_CONFIG, None)]

        if not ErrorViewer.errors:
            logger.info(IssueSubmitter.NO_ISSUES)
            return [(IssueSubmitter.NO_ISSUES, None)]

        if not sickbeard.DEVELOPER and version_checker.need_update():
            logger.warning(IssueSubmitter.UNSUPPORTED_VERSION)
            return [(IssueSubmitter.UNSUPPORTED_VERSION, None)]

        if self.running:
            logger.warning(IssueSubmitter.ALREADY_RUNNING)
            return [(IssueSubmitter.ALREADY_RUNNING, None)]

        self.running = True
        try:
            github = authenticate(sickbeard.GIT_USERNAME, sickbeard.GIT_PASSWORD, quiet=True)
            if not github:
                logger.warning(IssueSubmitter.BAD_CREDENTIALS)
                return [(IssueSubmitter.BAD_CREDENTIALS, None)]

            github_repo = get_github_repo(sickbeard.GIT_ORG, sickbeard.GIT_REPO, gh=github)
            loglines = ErrorViewer.errors[:max_issues]
            similar_issues = IssueSubmitter.find_similar_issues(github_repo, loglines)

            return IssueSubmitter.submit_issues(github, github_repo, loglines, similar_issues)
        except RateLimitExceededException:
            logger.warning(IssueSubmitter.RATE_LIMIT)
            return [(IssueSubmitter.RATE_LIMIT, None)]
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
        :type loglines: list of sickbeard.logger.LogLine
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
                    logger.warning(submitter_result)
                else:
                    similar_issue.create_comment(message)
                    issue_id = similar_issue.number
                    submitter_result = IssueSubmitter.COMMENTED_EXISTING_ISSUE.format(number=issue_id)
                    logger.info(submitter_result)
                    ErrorViewer.remove(logline)
            else:
                issue = github_repo.create_issue('{prefix}{title}'.format(prefix=IssueSubmitter.TITLE_PREFIX, title=logline.issue_title), message)
                issue_id = issue.number
                submitter_result = IssueSubmitter.ISSUE_CREATED.format(number=issue_id)
                logger.info(submitter_result)
                ErrorViewer.remove(logline)
            results.append((submitter_result, issue_id))

        return results
