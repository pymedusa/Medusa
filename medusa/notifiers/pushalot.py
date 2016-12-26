# coding=utf-8

# Author: Maciej Olesinski (https://github.com/molesinski/)
# Based on prowl.py by Nic Wolfe <nic@wolfeden.ca>
#
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from .. import app, common, helpers, logger


class Notifier(object):
    def __init__(self):
        self.session = helpers.make_session()

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

        logger.log('Pushalot event: {}'.format(event), logger.DEBUG)
        logger.log('Pushalot message: {}'.format(message), logger.DEBUG)
        logger.log('Pushalot api: {}'.format(pushalot_authorizationtoken), logger.DEBUG)

        post_data = {
            'AuthorizationToken': pushalot_authorizationtoken,
            'Title': event or '',
            'Body': message or ''
        }

        jdata = helpers.get_url(
            'https://pushalot.com/api/sendmessage',
            post_data=post_data, session=self.session,
            returns='json'
        ) or {}

        #  {'Status': 200, 'Description': 'The request has been completed successfully.', 'Success': True}

        success = jdata.pop('Success', False)
        if success:
            logger.log('Pushalot notifications sent.', logger.DEBUG)
        else:
            logger.log('Pushalot notification failed: {} {}'.format(
                jdata.get('Status', ''),
                jdata.get('Description', 'Unknown')
            ), logger.ERROR)

        return success
