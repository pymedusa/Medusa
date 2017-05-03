# coding=utf-8

from __future__ import unicode_literals

import logging
import re

from medusa import app, common
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import MedusaSession

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):

    def __init__(self):
        self.session = MedusaSession()
        self.url = 'https://api.pushbullet.com/v2/'

    def test_notify(self, pushbullet_api):
        log.debug('Sending a test Pushbullet notification.')
        return self._sendPushbullet(
            pushbullet_api,
            event='Test',
            message='Testing Pushbullet settings from Medusa',
            force=True
        )

    def get_devices(self, pushbullet_api):
        log.debug('Testing Pushbullet authentication and retrieving the device list.')
        headers = {'Access-Token': pushbullet_api,
                   'Content-Type': 'application/json'}
        try:
            r = self.session.get(urljoin(self.url, 'devices'), headers=headers)
            return r.text
        except ValueError:
            return {}

    def notify_snatch(self, ep_name, is_proper):
        if app.PUSHBULLET_NOTIFY_ONSNATCH:
            self._sendPushbullet(
                pushbullet_api=None,
                event=common.notifyStrings[(common.NOTIFY_SNATCH, common.NOTIFY_SNATCH_PROPER)[is_proper]] + ' : ' + ep_name,
                message=ep_name
            )

    def notify_download(self, ep_name):
        if app.PUSHBULLET_NOTIFY_ONDOWNLOAD:
            self._sendPushbullet(
                pushbullet_api=None,
                event=common.notifyStrings[common.NOTIFY_DOWNLOAD] + ' : ' + ep_name,
                message=ep_name
            )

    def notify_subtitle_download(self, ep_name, lang):
        if app.PUSHBULLET_NOTIFY_ONSUBTITLEDOWNLOAD:
            self._sendPushbullet(
                pushbullet_api=None,
                event=common.notifyStrings[common.NOTIFY_SUBTITLE_DOWNLOAD] + ' : ' + ep_name + ' : ' + lang,
                message=ep_name + ': ' + lang
            )

    def notify_git_update(self, new_version='??'):
        link = re.match(r'.*href="(.*?)" .*', app.NEWEST_VERSION_STRING)
        if link:
            link = link.group(1)

        self._sendPushbullet(
            pushbullet_api=None,
            event=common.notifyStrings[common.NOTIFY_GIT_UPDATE],
            message=common.notifyStrings[common.NOTIFY_GIT_UPDATE_TEXT] + new_version,
            link=link
        )

    def notify_login(self, ipaddress=''):
        self._sendPushbullet(
            pushbullet_api=None,
            event=common.notifyStrings[common.NOTIFY_LOGIN],
            message=common.notifyStrings[common.NOTIFY_LOGIN_TEXT].format(ipaddress)
        )

    def _sendPushbullet(  # pylint: disable=too-many-arguments
            self, pushbullet_api=None, pushbullet_device=None, event=None, message=None, link=None, force=False):
        push_result = {'success': False, 'error': ''}

        if not (app.USE_PUSHBULLET or force):
            return False

        pushbullet_api = pushbullet_api or app.PUSHBULLET_API
        pushbullet_device = pushbullet_device or app.PUSHBULLET_DEVICE

        log.debug('Pushbullet event: {0!r}', event)
        log.debug('Pushbullet message: {0!r}', message)
        log.debug('Pushbullet api: {0!r}', pushbullet_api)
        log.debug('Pushbullet devices: {0!r}', pushbullet_device)

        post_data = {
            'title': event,
            'body': message,
            'device_iden': pushbullet_device,
            'type': 'link' if link else 'note'
        }
        if link:
            post_data['url'] = link

        headers = {'Access-Token': pushbullet_api,
                   'Content-Type': 'application/json'}

        r = self.session.post(urljoin(self.url, 'pushes'), json=post_data, headers=headers)

        try:
            response = r.json()
        except ValueError:
            log.warning('Pushbullet notification failed. Could not parse pushbullet response.')
            push_result['error'] = 'Pushbullet notification failed. Could not parse pushbullet response.'
            return push_result

        failed = response.pop('error', {})
        if failed:
            log.warning('Pushbullet notification failed: {0}', failed.get('message'))
            push_result['error'] = 'Pushbullet notification failed: {0}'.format(failed.get('message'))
        else:
            log.debug('Pushbullet notification sent.')
            push_result['success'] = True

        return push_result
