# coding=utf-8
"""GitHub issue submitter."""
from __future__ import unicode_literals

import locale
import logging
import platform
import sys
from datetime import datetime, timedelta

from github import InputFileContent
from github.GithubException import BadCredentialsException, RateLimitExceededException
from github.MainClass import Github
import sickbeard
from sickbeard.classes import ErrorViewer

logger = logging.getLogger(__name__)


class IssueSubmitter(object):
    """GitHub issue submitter."""

    INVALID_CONFIG = 'Please set your GitHub username and password in the config and enable debug. Unable to submit issue ticket to GitHub.'
    NO_ISSUES = 'No issue to be submitted to GitHub.'
    UNSUPPORTED_VERSION = 'Please update Medusa, unable to submit issue ticket to GitHub with an outdated version.'
    ALREADY_RUNNING = 'An issue is already being submitted, please wait for it to complete.'
    BAD_CREDENTIALS = 'Please check your Github credentials in Medusa settings. Bad Credentials error'
    RATE_LIMIT = 'Please wait before submit new issues. Github Rate Limit Exceeded error'
    UNABLE_CREATE_ISSUE = 'Failed to create a new issue!'

    def __init__(self):
        """Default constructor."""
        self.running = False

    @staticmethod
    def create_gist(git, logline):
        """Create a private gist with log data for the specified logline.

        :param git:
        :type git: Github
        :param logline:
        :type logline: sickbeard.logger.LogLine
        :return:
        :rtype: github.Gist.Gist
        """
        context_loglines = logline.get_context_loglines()
        if context_loglines:
            content = '\n'.join([str(ll) for ll in context_loglines])
            return git.get_user().create_gist(False, {'sickrage.log': InputFileContent(content)})

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

        return '\n'.join([
            '### INFO',
            '**Python Version**: `{python_version}`'.format(python_version=sys.version[:120].replace('\n', '')),
            '**Operating System**: `{os}`'.format(os=platform.platform()),
            '**Locale**: `{locale}`'.format(locale=locale_name),
            '**Branch**: `{branch}`'.format(branch=sickbeard.BRANCH),
            '**Commit**: PyMedusa/SickRage@{commit}'.format(commit=sickbeard.CUR_COMMIT_HASH),
            '**Link to Log**: {log_url}'.format(log_url=log_url) if log_url else '**No Log available**',
            '### ERROR',
            '```',
            str(logline),
            '```',
            '---',
            '_STAFF NOTIFIED_: @pymedusa/support @pymedusa/moderators',
        ])

    @staticmethod
    def find_similar_issues(git_repo, loglines):
        """Find similar issues in GitHub repo.

        :param git_repo:
        :type git_repo: github.Repository.Repository
        :param loglines:
        :type loglines: list of sickbeard.logger.LogLine
        :return:
        :rtype: dict(str, github.Issue.Issue)
        """
        results = dict()
        reports = git_repo.get_issues(state='all', since=datetime.now() - timedelta(days=180))
        for report in reports:
            for logline in loglines:
                if logline.is_title_similar_to(report.title):
                    results[logline.key] = report

            if len(results) >= len(loglines):
                break

        return results

    def submit_github_issue(self, version_checker):
        """Submit errors to github.

        :param version_checker:
        :type version_checker: CheckVersion
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
            git = Github(login_or_token=sickbeard.GIT_USERNAME, password=sickbeard.GIT_PASSWORD, user_agent='Medusa')
            git_repo = git.get_organization(sickbeard.GIT_ORG).get_repo(sickbeard.GIT_REPO)

            results = []
            loglines = ErrorViewer.errors[:500]
            similar_issues = IssueSubmitter.find_similar_issues(git_repo, loglines)
            # parse and submit errors to issue tracker
            for logline in loglines:
                gist = IssueSubmitter.create_gist(git, logline)
                message = IssueSubmitter.create_issue_data(logline, log_url=gist.html_url if gist else None)
                similar_issue = similar_issues[logline.key]
                issue_id = None
                if similar_issue:
                    if similar_issue.raw_data['locked']:
                        submitter_result = 'Issue #{number} is locked, check GitHub to find info about the error.'.format(number=similar_issue.number)
                        logger.warning(submitter_result)
                    elif similar_issue.create_comment(message):
                        issue_id = similar_issue.number
                        submitter_result = 'Commented on existing issue #{number} successfully!'.format(number=issue_id)
                        logger.info(submitter_result)
                        ErrorViewer.remove(logline)
                    else:
                        submitter_result = 'Failed to comment on found issue #{number}!'.format(number=similar_issue.number)
                        logger.warning(submitter_result)
                else:
                    issue = git_repo.create_issue(logline.issue_title, message)
                    if issue:
                        issue_id = issue.number
                        submitter_result = 'Your issue ticket #{number} was submitted successfully!'.format(number=issue_id)
                        logger.info(submitter_result)
                        ErrorViewer.remove(logline)
                    else:
                        submitter_result = IssueSubmitter.UNABLE_CREATE_ISSUE
                        logger.warning(submitter_result)
                results.append((submitter_result, issue_id))

            return results
        except BadCredentialsException:
            logger.warning(IssueSubmitter.BAD_CREDENTIALS)
            return [(IssueSubmitter.BAD_CREDENTIALS, None)]
        except RateLimitExceededException:
            logger.warning(IssueSubmitter.RATE_LIMIT)
            return [(IssueSubmitter.RATE_LIMIT, None)]
        finally:
            self.running = False
