"""Slack notifier."""
# coding=utf-8

from __future__ import unicode_literals

import json
import logging
from builtins import object

from medusa import app, common
from medusa.logger.adapters.style import BraceAdapter

import requests

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    """Slack notifier class."""

    def notify_snatch(self, title, message):
        """
        Send a notification to a Slack channel when an episode is snatched.

        :param ep_name: The name of the episode snatched
        :param is_proper: Boolean. If snatch is proper or not
        """
        if app.SLACK_NOTIFY_SNATCH:
            self._notify_slack('{title}: {message}'.format(title=title,
                                                           message=message))

    def notify_download(self, ep_obj):
        """
        Send a notification to a slack channel when an episode is downloaded.

        :param ep_name: The name of the episode downloaded
        """
        if app.SLACK_NOTIFY_DOWNLOAD:
            message = common.notifyStrings[common.NOTIFY_DOWNLOAD]
            self._notify_slack('{message}: {ep_name}'.format(message=message,
                                                             ep_name=ep_obj.pretty_name_with_quality()))

    def notify_subtitle_download(self, ep_obj, lang):
        """
        Send a notification to a Slack channel when subtitles for an episode are downloaded.

        :param ep_name: The name of the episode subtitles were downloaded for
        :param lang: The language of the downloaded subtitles
        """
        if app.SLACK_NOTIFY_SUBTITLEDOWNLOAD:
            message = common.notifyStrings[common.NOTIFY_SUBTITLE_DOWNLOAD]
            self._notify_slack('{message} {ep_name}: {lang}'.format(message=message, ep_name=ep_obj.pretty_name(),
                                                                    lang=lang))

    def notify_git_update(self, new_version='??'):
        """
        Send a notification to a Slack channel for git updates.

        :param new_version: The new version available from git
        """
        if app.USE_SLACK:
            message = common.notifyStrings[common.NOTIFY_GIT_UPDATE_TEXT]
            title = common.notifyStrings[common.NOTIFY_GIT_UPDATE]
            self._notify_slack('{title} - {message} {version}'.format(title=title, message=message,
                                                                      version=new_version))

    def notify_login(self, ipaddress=''):
        """
        Send a notification to a Slack channel on login.

        :param ipaddress: The ip address the login is originating from
        """
        if app.USE_SLACK:
            message = common.notifyStrings[common.NOTIFY_LOGIN_TEXT]
            title = common.notifyStrings[common.NOTIFY_LOGIN]
            self._notify_slack(title + '{title} - {message}'.format(title=title, message=message.format(ipaddress)))

    def test_notify(self, slack_webhook):
        """
        Send a test notification.

        :param slack_webhook: The slack webhook to send the message to
        :returns: the notification
        """
        return self._notify_slack('This is a test notification from Medusa', force=True, webhook=slack_webhook)

    def _send_slack(self, message=None, webhook=None):
        """Send the http request using the Slack webhook."""
        webhook = webhook or app.SLACK_WEBHOOK

        log.info('Sending slack message: {message}', {'message': message})
        log.info('Sending slack message  to url: {url}', {'url': webhook})

        headers = {'Content-Type': 'application/json'}
        data = {
            'text': message,
            'username': 'MedusaBot',
            'icon_url': 'https://cdn.pymedusa.com/images/ico/favicon-310.png'
        }

        try:
            r = requests.post(webhook, data=json.dumps(data), headers=headers)
            r.raise_for_status()
        except Exception:
            log.exception('Error Sending Slack message')
            return False

        return True

    def _notify_slack(self, message='', force=False, webhook=None):
        """Send the Slack notification."""
        if not app.USE_SLACK and not force:
            return False

        return self._send_slack(message, webhook)
