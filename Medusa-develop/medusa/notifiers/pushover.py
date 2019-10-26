# coding=utf-8

"""Pushover notifier module."""
from __future__ import unicode_literals

import logging
import time

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

from requests.compat import urlencode

from six.moves.http_client import HTTPSConnection

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

API_URL = 'https://api.pushover.net/1/messages.json'


class Notifier(object):
    """Pushover notifier class."""

    def __init__(self):
        """Initialize Pushover notifier."""
        pass

    def test_notify(self, user_key=None, api_key=None):
        """
        Send a test notification.

        :return: True for no issue or False if there was an error
        """
        return self._notify_pushover('This is a test notification from Medusa', 'Test', user_key=user_key, api_key=api_key, force=True)

    def _send_pushover(self, msg, title, sound=None, user_key=None, api_key=None, priority=None):
        """
        Send a pushover notification to the address provided.

        :param msg: The message to send (unicode)
        :param title: The title of the message
        :param sound: The notification sound to use
        :param user_key: The pushover user id to send the message to (or to subscribe with)
        :param api_key: The pushover api key to use
        :param priority: The pushover priority to use
        :return: True if the message succeeded, False otherwise
        """
        if user_key is None:
            user_key = app.PUSHOVER_USERKEY

        if api_key is None:
            api_key = app.PUSHOVER_APIKEY

        if sound is None:
            sound = app.PUSHOVER_SOUND

        if priority is None:
            priority = app.PUSHOVER_PRIORITY

        # build up the URL and parameters
        msg = msg.strip()

        # default args
        args = {
            'token': api_key,
            'user': user_key,
            'title': title.encode('utf-8'),
            'message': msg.encode('utf-8'),
            'timestamp': int(time.time()),
            'retry': 60,
            'expire': 3600,
            'priority': priority,
        }

        # If sound is not default, add it.
        if sound != 'default':
            args['sound'] = sound

        if app.PUSHOVER_DEVICE:
            args['device'] = ','.join(app.PUSHOVER_DEVICE)

        log.debug('PUSHOVER: Sending notice with details: title="{0}" message="{1}", priority={2}, sound={3}',
                  title, msg, priority, sound)

        conn = HTTPSConnection('api.pushover.net:443')
        conn.request('POST', '/1/messages.json',
                     urlencode(args), {'Content-type': 'application/x-www-form-urlencoded'})
        conn_resp = conn.getresponse()

        if conn_resp.status == 200:
            log.info('Pushover notification successful.')
            return True

        # HTTP status 404 if the provided email address isn't a Pushover user.
        elif conn_resp.status == 404:
            log.warning('Username is wrong/not a pushover email. Pushover will send an email to it')
            return False

        # For HTTP status code 401's, it is because you are passing in either an invalid token, or the user has not added your service.
        elif conn_resp.status == 401:
            # HTTP status 401 if the user doesn't have the service added
            subscribe_note = self._send_pushover(msg, title, sound=sound, user_key=user_key, api_key=api_key)
            if subscribe_note:
                log.debug('Subscription sent')
                return True
            else:
                log.error('Subscription could not be sent')

        # If you receive an HTTP status code of 400, it is because you failed to send the proper parameters
        elif conn_resp.status == 400:
            log.error('Wrong keys sent to pushover')
            return False

        # If you receive a HTTP status code of 429, it is because the message limit has been reached (free limit is 7,500)
        elif conn_resp.status == 429:
            log.error('Pushover API message limit reached - try a different API key')
            return False

        # Something else has gone wrong... who knows what's really happening
        else:
            log.error('Pushover notification failed. HTTP response code: {0}', conn_resp.status)
            return False

    def notify_snatch(self, title, message):
        """
        Send a notification that an episode was snatched.

        :param ep_obj: The object of the episode snatched
        :param is_proper: Boolean. If snatch is proper or not
        """
        if app.PUSHOVER_NOTIFY_ONSNATCH:
            self._notify_pushover(title, message)

    def notify_download(self, ep_obj, title=notifyStrings[NOTIFY_DOWNLOAD]):
        """
        Send a notification that an episode was downloaded.

        :param ep_obj: The object of the episode downloaded
        :param title: The title of the notification to send
        """
        if app.PUSHOVER_NOTIFY_ONDOWNLOAD:
            self._notify_pushover(title, ep_obj.pretty_name_with_quality())

    def notify_subtitle_download(self, ep_obj, lang, title=notifyStrings[NOTIFY_SUBTITLE_DOWNLOAD]):
        """
        Send a notification that subtitles for an episode were downloaded.

        :param ep_obj: The object of the episode subtitles were downloaded for
        :param lang: The language of the downloaded subtitles
        :param title: The title of the notification to send
        """
        if app.PUSHOVER_NOTIFY_ONSUBTITLEDOWNLOAD:
            self._notify_pushover(title, ep_obj.pretty_name() + ': ' + lang)

    def notify_git_update(self, new_version='??'):
        """
        Send a notification that Medusa was updated.

        :param new_version: The commit Medusa was updated to
        """
        if app.USE_PUSHOVER:
            update_text = notifyStrings[NOTIFY_GIT_UPDATE_TEXT]
            title = notifyStrings[NOTIFY_GIT_UPDATE]
            self._notify_pushover(title, update_text + new_version)

    def notify_login(self, ipaddress=''):
        """
        Send a notification that Medusa was logged into remotely.

        :param ipaddress: The IP address Medusa was logged into from
        """
        if app.USE_PUSHOVER:
            update_text = notifyStrings[NOTIFY_LOGIN_TEXT]
            title = notifyStrings[NOTIFY_LOGIN]
            self._notify_pushover(title, update_text.format(ipaddress))

    def _notify_pushover(self, title, message, sound=None, user_key=None, api_key=None, priority=None, force=False):
        """
        Send a pushover notification based on the provided info or Medusa config.

        :param title: The title of the notification to send
        :param message: The message string to send
        :param sound: The notification sound to use
        :param user_key: The userKey to send the notification to
        :param api_key: The apiKey to use to send the notification
        :param priority: The pushover priority to use
        :param force: Enforce sending, for instance for testing
        """
        if not app.USE_PUSHOVER and not force:
            log.debug('Notification for Pushover not enabled, skipping this notification')
            return False

        log.debug('Sending notification for {0}', message)

        return self._send_pushover(message, title, sound=sound, user_key=user_key, api_key=api_key, priority=priority)
