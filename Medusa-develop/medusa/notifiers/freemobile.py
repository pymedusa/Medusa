# coding=utf-8

from __future__ import unicode_literals

import logging

from medusa import app
from medusa.common import (
    NOTIFY_DOWNLOAD,
    NOTIFY_GIT_UPDATE,
    NOTIFY_GIT_UPDATE_TEXT,
    NOTIFY_LOGIN,
    NOTIFY_LOGIN_TEXT,
    NOTIFY_SUBTITLE_DOWNLOAD,
    notifyStrings,
)
from medusa.logger.adapters.style import BraceAdapter

from requests.compat import quote

from six.moves.urllib.request import Request, urlopen

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    def test_notify(self, cust_id=None, apiKey=None):
        return self._notifyFreeMobile('Test', 'This is a test notification from Medusa', cust_id, apiKey, force=True)

    def _sendFreeMobileSMS(self, title, msg, cust_id=None, apiKey=None):
        """
        Send a SMS notification

        msg: The message to send (unicode)
        title: The title of the message
        userKey: The pushover user id to send the message to (or to subscribe with)

        return: True if the message succeeded, False otherwise
        """
        if cust_id is None:
            cust_id = app.FREEMOBILE_ID
        if apiKey is None:
            apiKey = app.FREEMOBILE_APIKEY

        log.debug(u'Free Mobile in use with API KEY: {0}', apiKey)

        # build up the URL and parameters
        msg = '{0}: {1}'.format(title, msg.strip())
        msg_quoted = quote(msg.encode('utf-8'))
        URL = 'https://smsapi.free-mobile.fr/sendmsg?user={user}&pass={api_key}&msg={msg}'.format(
            user=cust_id,
            api_key=apiKey,
            msg=msg_quoted,
        )

        req = Request(URL)
        # send the request to Free Mobile
        try:
            urlopen(req)
        except IOError as e:
            if hasattr(e, 'code'):
                error_message = {
                    400: 'Missing parameter(s).',
                    402: 'Too much SMS sent in a short time.',
                    403: 'API service is not enabled in your account or ID / API key is incorrect.',
                    500: 'Server error. Please retry in few moment.',
                }
                message = error_message.get(e.code)
                if message:
                    log.error(message)
                    return False, message
        except Exception as e:
            message = u'Error while sending SMS: {0}'.format(e)
            log.error(message)
            return False, message

        message = 'Free Mobile SMS successful.'
        log.info(message)
        return True, message

    def notify_snatch(self, title, message):
        if app.FREEMOBILE_NOTIFY_ONSNATCH:
            self._notifyFreeMobile(title, message)

    def notify_download(self, ep_obj, title=notifyStrings[NOTIFY_DOWNLOAD]):
        if app.FREEMOBILE_NOTIFY_ONDOWNLOAD:
            self._notifyFreeMobile(title, ep_obj.pretty_name_with_quality())

    def notify_subtitle_download(self, ep_obj, lang, title=notifyStrings[NOTIFY_SUBTITLE_DOWNLOAD]):
        if app.FREEMOBILE_NOTIFY_ONSUBTITLEDOWNLOAD:
            self._notifyFreeMobile(title, ep_obj.pretty_name() + ': ' + lang)

    def notify_git_update(self, new_version='??'):
        if app.USE_FREEMOBILE:
            update_text = notifyStrings[NOTIFY_GIT_UPDATE_TEXT]
            title = notifyStrings[NOTIFY_GIT_UPDATE]
            self._notifyFreeMobile(title, update_text + new_version)

    def notify_login(self, ipaddress=''):
        if app.USE_FREEMOBILE:
            update_text = notifyStrings[NOTIFY_LOGIN_TEXT]
            title = notifyStrings[NOTIFY_LOGIN]
            self._notifyFreeMobile(title, update_text.format(ipaddress))

    def _notifyFreeMobile(self, title, message, cust_id=None, apiKey=None, force=False):  # pylint: disable=too-many-arguments
        """
        Sends a SMS notification

        title: The title of the notification to send
        message: The message string to send
        cust_id: Your Free Mobile customer ID
        apikey: Your Free Mobile API key
        force: Enforce sending, for instance for testing
        """

        if not app.USE_FREEMOBILE and not force:
            log.debug(u'Notification for Free Mobile not enabled, skipping this notification')
            return False, 'Disabled'

        log.debug(u'Sending a SMS for {0}', message)

        return self._sendFreeMobileSMS(title, message, cust_id, apiKey)
