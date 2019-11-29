# coding=utf-8
# Author: Kevin Ould email: ouldsmobile1@gmail.com
"""Adds Join Notifications."""
from __future__ import unicode_literals

import logging
from builtins import object

from medusa import app, common
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import MedusaSession

import requests

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    """Notifier class for Join."""

    def __init__(self):
        """Init method."""
        self.session = MedusaSession()
        self.url = 'https://joinjoaomgcd.appspot.com/_ah/api/messaging/v1/sendPush?'

    def test_notify(self, join_api, join_device):
        """Sends test notification from config screen."""
        log.debug('Sending a test Join notification.')
        return self._sendjoin(
            title='Test',
            message='Testing Join settings from Medusa',
            join_api=join_api,
            join_device=join_device,
            force=True
        )

    def notify_snatch(self, title, message):
        """Send Join notification when nzb snatched if selected in config."""
        if app.JOIN_NOTIFY_ONSNATCH:
            self._sendjoin(
                title=title,
                message=message
            )

    def notify_download(self, ep_obj):
        """Send Join notification when nzb download completed if selected in config."""
        if app.JOIN_NOTIFY_ONDOWNLOAD:
            self._sendjoin(
                title=common.notifyStrings[common.NOTIFY_DOWNLOAD],
                message=ep_obj.pretty_name_with_quality()
            )

    def notify_subtitle_download(self, ep_obj, lang):
        """Send Join notification when subtitles downloaded if selected in config."""
        if app.JOIN_NOTIFY_ONSUBTITLEDOWNLOAD:
            self._sendjoin(
                title=common.notifyStrings[common.NOTIFY_SUBTITLE_DOWNLOAD],
                message=ep_obj.pretty_name() + ': ' + lang
            )

    def notify_git_update(self, new_version='??'):
        """Send Join notification when new version available from git."""
        self._sendjoin(
            title=common.notifyStrings[common.NOTIFY_GIT_UPDATE],
            message=common.notifyStrings[common.NOTIFY_GIT_UPDATE_TEXT] + new_version,
        )

    def notify_login(self, ipaddress=''):
        """Send Join notification when login detected."""
        self._sendjoin(
            title=common.notifyStrings[common.NOTIFY_LOGIN],
            message=common.notifyStrings[common.NOTIFY_LOGIN_TEXT].format(ipaddress)
        )

    def _sendjoin(self, title, message, join_api=None, join_device=None, force=False):
        """Compose and send Join notification."""
        push_result = {'success': False, 'error': ''}

        if not (app.USE_JOIN or force):
            return False

        join_api = join_api or app.JOIN_API
        join_device = join_device or app.JOIN_DEVICE
        icon_url = 'https://cdn.pymedusa.com/images/ico/favicon-310.png'

        params = {'title': title, 'text': message, 'deviceId': join_device, 'apikey': join_api, 'icon': icon_url}

        r = requests.get(self.url, params=params)
        try:
            response = r.json()
        except ValueError:
            log.warning('Join notification failed. Could not parse join response.')
            push_result['error'] = 'Join notification failed. Could not parse join response.'
            return push_result

        failed = response.pop('errorMessage', {})
        if failed:
            log.warning('Join notification failed: {0}', failed)
            push_result['error'] = 'Join notification failed: {0}'.format(failed)
        else:
            log.debug('Join notification sent.')
            push_result['success'] = True

        return push_result
