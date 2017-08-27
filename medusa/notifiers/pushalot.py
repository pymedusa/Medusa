# coding=utf-8

from __future__ import unicode_literals

import logging

from medusa import app, common
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import MedusaSession

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    def __init__(self):
        self.session = MedusaSession()

    def test_notify(self, pushalot_authorizationtoken):
        return self._sendPushalot(
            pushalot_authorizationtoken=pushalot_authorizationtoken,
            event='Test',
            message='Testing Pushalot settings from Medusa',
            force=True
        )

    def notify_snatch(self, ep_name, is_proper):
        if app.PUSHALOT_NOTIFY_ONSNATCH:
            self._sendPushalot(
                pushalot_authorizationtoken=None,
                event=common.notifyStrings[(common.NOTIFY_SNATCH, common.NOTIFY_SNATCH_PROPER)[is_proper]],
                message=ep_name
            )

    def notify_download(self, ep_name):
        if app.PUSHALOT_NOTIFY_ONDOWNLOAD:
            self._sendPushalot(
                pushalot_authorizationtoken=None,
                event=common.notifyStrings[common.NOTIFY_DOWNLOAD],
                message=ep_name
            )

    def notify_subtitle_download(self, ep_name, lang):
        if app.PUSHALOT_NOTIFY_ONSUBTITLEDOWNLOAD:
            self._sendPushalot(
                pushalot_authorizationtoken=None,
                event=common.notifyStrings[common.NOTIFY_SUBTITLE_DOWNLOAD],
                message='{}:{}'.format(ep_name, lang)
            )

    def notify_git_update(self, new_version='??'):
        update_text = common.notifyStrings[common.NOTIFY_GIT_UPDATE_TEXT]
        title = common.notifyStrings[common.NOTIFY_GIT_UPDATE]
        self._sendPushalot(
            pushalot_authorizationtoken=None,
            event=title,
            message=update_text + new_version
        )

    def notify_login(self, ipaddress=''):
        update_text = common.notifyStrings[common.NOTIFY_LOGIN_TEXT]
        title = common.notifyStrings[common.NOTIFY_LOGIN]
        self._sendPushalot(
            pushalot_authorizationtoken=None,
            event=title,
            message=update_text.format(ipaddress)
        )

    def _sendPushalot(self, pushalot_authorizationtoken=None, event=None, message=None, force=False):

        if not (app.USE_PUSHALOT or force):
            return False

        pushalot_authorizationtoken = pushalot_authorizationtoken or app.PUSHALOT_AUTHORIZATIONTOKEN

        log.debug('Pushalot event: {0}', event)
        log.debug('Pushalot message: {0}', message)
        log.debug('Pushalot api: {0}', pushalot_authorizationtoken)

        post_data = {
            'AuthorizationToken': pushalot_authorizationtoken,
            'Title': event or '',
            'Body': message or ''
        }

        # TODO: SESSION: Check if this needs exception handling.
        jdata = self.session.post(
            'https://pushalot.com/api/sendmessage',
            data=post_data).json() or {}

        #  {'Status': 200, 'Description': 'The request has been completed successfully.', 'Success': True}

        success = jdata.pop('Success', False)
        if success:
            log.debug('Pushalot notifications sent.')
        else:
            log.error(
                'Pushalot notification failed: {0} {1}',
                jdata.get('Status', ''),
                jdata.get('Description', 'Unknown')
            )

        return success
