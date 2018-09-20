# coding=utf-8

from __future__ import unicode_literals

import logging
import re
from builtins import object

from medusa import app, common
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import MedusaSession

import requests
import urllib

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):

    def __init__(self):
        self.session = MedusaSession()
        self.url = 'https://joinjoaomgcd.appspot.com/_ah/api/messaging/v1/sendPush?'

    def test_notify(self, join_api, join_device):
        log.debug('Sending a test Join notification.')
        return self._sendJoin(
            join_api=join_api,
	    join_device=join_device,
            event='Test',
            message='Testing Join settings from Medusa',
            force=True
        )

    def notify_snatch(self, ep_name, is_proper):
        if app.JOIN_NOTIFY_ONSNATCH:
            self._sendJoin(
                join_api=None,
                event=common.notifyStrings[(common.NOTIFY_SNATCH, common.NOTIFY_SNATCH_PROPER)[is_proper]] + ' : ' + ep_name,
                message=ep_name
            )

    def notify_download(self, ep_name):
        if app.JOIN_NOTIFY_ONDOWNLOAD:
            self._sendJoin(
                join_api=None,
                event=common.notifyStrings[common.NOTIFY_DOWNLOAD] + ' : ' + ep_name,
                message=ep_name
            )

    def notify_subtitle_download(self, ep_name, lang):
        if app.PUSHBULLET_NOTIFY_ONSUBTITLEDOWNLOAD:
            self._sendJoin(
                join_api=None,
                event=common.notifyStrings[common.NOTIFY_SUBTITLE_DOWNLOAD] + ' : ' + ep_name + ' : ' + lang,
                message=ep_name + ': ' + lang
            )

    def notify_git_update(self, new_version='??'):
        link = re.match(r'.*href="(.*?)" .*', app.NEWEST_VERSION_STRING)
        if link:
            link = link.group(1)

        self._sendJoin(
            join_api=None,
            event=common.notifyStrings[common.NOTIFY_GIT_UPDATE],
            message=common.notifyStrings[common.NOTIFY_GIT_UPDATE_TEXT] + new_version,
            link=link
        )

    def notify_login(self, ipaddress=''):
        self._sendJoin(
            join_api=None,
            event=common.notifyStrings[common.NOTIFY_LOGIN],
            message=common.notifyStrings[common.NOTIFY_LOGIN_TEXT].format(ipaddress)
        )

    def _sendJoin(self, join_api=None, join_device=None, event=None, message=None, force=False):
        push_result = {'success': False, 'error': ''}

        if not (app.USE_JOIN or force):
            return False

        join_api = join_api or app.JOIN_API
        join_device = join_device or app.JOIN_DEVICE
	icon_url = 'https://cdn.pymedusa.com/images/ico/favicon-310.png'

        log.debug('Join title: {0!r}', event)
        log.debug('Join message: {0!r}', message)
        log.debug('Join api: {0!r}', join_api)
        log.debug('Join devices: {0!r}', join_device)

	post_data = {'title': event, 'text': message, 'deviceId': join_device, 'apikey': join_api, 'icon': icon_url}
	urllib.quote_plus=urllib.quote
	params = urllib.urlencode(post_data)

	r = requests.get(self.url, params=params)

        try:
            response = r.json()
        except ValueError:
            log.warning('Join notification failed. Could not parse join response.')
            push_result['error'] = 'Join notification failed. Could not parse join response.'
            return push_result

        failed = response.pop('errorMessage', {})
        if failed:
            log.warning('Join notification failed: {0}', failed.get('message'))
            push_result['error'] = 'Join notification failed: {0}'.format(failed.get('message'))
        else:
            log.debug('Join notification sent.')
            push_result['success'] = True

        return push_result
