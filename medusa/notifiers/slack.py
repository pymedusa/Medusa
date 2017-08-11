# coding=utf-8

from __future__ import unicode_literals

import logging
import json

import requests
import six

from medusa import app, common
from medusa.logger.adapters.style import BraceAdapter

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):

    SLACK_WEBHOOK_URL = 'https://hooks.slack.com/services/'

    def notify_snatch(self, ep_name):
        if app.SLACK_NOTIFY_SNATCH:
            self._notify_slack(common.notifyStrings[common.NOTIFY_SNATCH] + ': ' + ep_name)

    def notify_download(self, ep_name):
        if app.SLACK_NOTIFY_DOWNLOAD:
            self._notify_slack(common.notifyStrings[common.NOTIFY_DOWNLOAD] + ': ' + ep_name)

    def notify_subtitle_download(self, ep_name, lang):
        if app.SLACK_NOTIFY_SUBTITLEDOWNLOAD:
            self._notify_slack(common.notifyStrings[common.NOTIFY_SUBTITLE_DOWNLOAD] + ' ' + ep_name + ': ' + lang)

    def notify_git_update(self, new_version='??'):
        if app.USE_SLACK:
            update_text = common.notifyStrings[common.NOTIFY_GIT_UPDATE_TEXT]
            title = common.notifyStrings[common.NOTIFY_GIT_UPDATE]
            self._notify_slack(title + ' - ' + update_text + new_version)

    def notify_login(self, ipaddress=''):
        if app.USE_SLACK:
            update_text = common.notifyStrings[common.NOTIFY_LOGIN_TEXT]
            title = common.notifyStrings[common.NOTIFY_LOGIN]
            self._notify_slack(title + ' - ' + update_text.format(ipaddress))

    def test_notify(self, slack_webhook):
        return self._notify_slack('This is a test notification from Medusa', force=True, webhook=slack_webhook)

    def _send_slack(self, message=None, webhook=None):
        app.SLACK_WEBHOOK = webhook or app.SLACK_WEBHOOK
        slack_webhook = self.SLACK_WEBHOOK_URL + app.SLACK_WEBHOOK.replace(self.SLACK_WEBHOOK_URL, '')

        log.info('Sending slack message: {message}', {'message': message})
        log.info('Sending slack message  to url: {url}', {'url': slack_webhook})

        if isinstance(message, six.text_type):
            message = message.encode('utf-8')

        headers = {b'Content-Type': b'application/json'}
        try:
            r = requests.post(slack_webhook, data=json.dumps(dict(text=message, username='MedusaBot')), headers=headers)
            r.raise_for_status()
        except Exception as e:
            log.exception('Error Sending Slack message')
            return False

        return True

    def _notify_slack(self, message='', force=False, webhook=None):
        if not app.USE_SLACK and not force:
            return False

        return self._send_slack(message, webhook)
