# coding=utf-8

from __future__ import unicode_literals

import logging
import time
from builtins import object

from medusa import app
from medusa.common import (
    NOTIFY_DOWNLOAD,
    NOTIFY_GIT_UPDATE,
    NOTIFY_GIT_UPDATE_TEXT,
    NOTIFY_LOGIN,
    NOTIFY_LOGIN_TEXT,
    NOTIFY_SNATCH,
    NOTIFY_SNATCH_PROPER,
    NOTIFY_SUBTITLE_DOWNLOAD,
    notifyStrings,
)
from medusa.helper.exceptions import ex
from medusa.logger.adapters.style import BraceAdapter

from requests.compat import urlencode

from six.moves.http_client import HTTPSConnection
from six.moves.urllib.error import HTTPError

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

API_URL = 'https://api.pushover.net/1/messages.json'


class Notifier(object):
    def __init__(self):
        pass

    def test_notify(self, userKey=None, apiKey=None):
        return self._notifyPushover('This is a test notification from Medusa', 'Test', userKey=userKey, apiKey=apiKey, force=True)

    def _sendPushover(self, msg, title, sound=None, userKey=None, apiKey=None):
        """
        Sends a pushover notification to the address provided

        msg: The message to send (unicode)
        title: The title of the message
        sound: The notification sound to use
        userKey: The pushover user id to send the message to (or to subscribe with)
        apiKey: The pushover api key to use
        returns: True if the message succeeded, False otherwise
        """

        if userKey is None:
            userKey = app.PUSHOVER_USERKEY

        if apiKey is None:
            apiKey = app.PUSHOVER_APIKEY

        if sound is None:
            sound = app.PUSHOVER_SOUND

        log.debug(u'Pushover API KEY in use: {0}', apiKey)

        # build up the URL and parameters
        msg = msg.strip()

        # send the request to pushover
        try:
            if app.PUSHOVER_SOUND != 'default':
                args = {
                    'token': apiKey,
                    'user': userKey,
                    'title': title.encode('utf-8'),
                    'message': msg.encode('utf-8'),
                    'timestamp': int(time.time()),
                    'retry': 60,
                    'expire': 3600,
                    'sound': sound,
                }
            else:
                # sound is default, so don't send it
                args = {
                    'token': apiKey,
                    'user': userKey,
                    'title': title.encode('utf-8'),
                    'message': msg.encode('utf-8'),
                    'timestamp': int(time.time()),
                    'retry': 60,
                    'expire': 3600,
                }

            if app.PUSHOVER_DEVICE:
                args['device'] = ','.join(app.PUSHOVER_DEVICE)

            conn = HTTPSConnection('api.pushover.net:443')
            conn.request('POST', '/1/messages.json',
                         urlencode(args), {'Content-type': 'application/x-www-form-urlencoded'})

        except HTTPError as e:
            # if we get an error back that doesn't have an error code then who knows what's really happening
            if not hasattr(e, 'code'):
                log.error(u'Pushover notification failed. {}', ex(e))
                return False
            else:
                log.error(u'Pushover notification failed. Error code: {0}', e.code)

            # HTTP status 404 if the provided email address isn't a Pushover user.
            if e.code == 404:
                log.warning(u'Username is wrong/not a pushover email. Pushover will send an email to it')
                return False

            # For HTTP status code 401's, it is because you are passing in either an invalid token, or the user has not added your service.
            elif e.code == 401:

                # HTTP status 401 if the user doesn't have the service added
                subscribeNote = self._sendPushover(msg, title, sound=sound, userKey=userKey, apiKey=apiKey)
                if subscribeNote:
                    log.debug(u'Subscription sent')
                    return True
                else:
                    log.error(u'Subscription could not be sent')
                    return False

            # If you receive an HTTP status code of 400, it is because you failed to send the proper parameters
            elif e.code == 400:
                log.error(u'Wrong data sent to pushover')
                return False

            # If you receive a HTTP status code of 429, it is because the message limit has been reached (free limit is 7,500)
            elif e.code == 429:
                log.error(u'Pushover API message limit reached - try a different API key')
                return False

        log.info(u'Pushover notification successful.')
        return True

    def notify_snatch(self, ep_name, is_proper):
        title=notifyStrings[(NOTIFY_SNATCH, NOTIFY_SNATCH_PROPER)[is_proper]]
        if app.PUSHOVER_NOTIFY_ONSNATCH:
            self._notifyPushover(title, ep_name)

    def notify_download(self, ep_name, title=notifyStrings[NOTIFY_DOWNLOAD]):
        if app.PUSHOVER_NOTIFY_ONDOWNLOAD:
            self._notifyPushover(title, ep_name)

    def notify_subtitle_download(self, ep_name, lang, title=notifyStrings[NOTIFY_SUBTITLE_DOWNLOAD]):
        if app.PUSHOVER_NOTIFY_ONSUBTITLEDOWNLOAD:
            self._notifyPushover(title, ep_name + ': ' + lang)

    def notify_git_update(self, new_version='??'):
        if app.USE_PUSHOVER:
            update_text = notifyStrings[NOTIFY_GIT_UPDATE_TEXT]
            title = notifyStrings[NOTIFY_GIT_UPDATE]
            self._notifyPushover(title, update_text + new_version)

    def notify_login(self, ipaddress=''):
        if app.USE_PUSHOVER:
            update_text = notifyStrings[NOTIFY_LOGIN_TEXT]
            title = notifyStrings[NOTIFY_LOGIN]
            self._notifyPushover(title, update_text.format(ipaddress))

    def _notifyPushover(self, title, message, sound=None, userKey=None, apiKey=None, force=False):
        """
        Sends a pushover notification based on the provided info or Medusa config

        title: The title of the notification to send
        message: The message string to send
        sound: The notification sound to use
        userKey: The userKey to send the notification to
        apiKey: The apiKey to use to send the notification
        force: Enforce sending, for instance for testing
        """

        if not app.USE_PUSHOVER and not force:
            log.debug(u'Notification for Pushover not enabled, skipping this notification')
            return False

        log.debug(u'Sending notification for {0}', message)

        return self._sendPushover(message, title, sound=sound, userKey=userKey, apiKey=apiKey)
