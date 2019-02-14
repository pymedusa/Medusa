# coding=utf-8

from __future__ import unicode_literals

import logging
from builtins import object

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
from medusa.helper.common import http_status_code
from medusa.logger.adapters.style import BraceAdapter

import requests
from requests.exceptions import RequestException

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    """
    Use Telegram to send notifications

    https://telegram.org/
    """
    def test_notify(self, user_id=None, api_key=None):
        """
        Send a test notification
        :param user_id: The Telegram user/group id to send the message to
        :param api_key: Your Telegram bot API token
        :returns: the notification
        """
        return self._notify_telegram('Test', 'This is a test notification from Medusa', user_id, api_key, force=True)

    def _send_telegram_msg(self, title, msg, user_id=None, api_key=None):
        """
        Sends a Telegram notification

        :param title: The title of the notification to send
        :param msg: The message string to send
        :param id: The Telegram user/group id to send the message to
        :param api_key: Your Telegram bot API token

        :returns: True if the message succeeded, False otherwise
        """
        user_id = app.TELEGRAM_ID if user_id is None else user_id
        api_key = app.TELEGRAM_APIKEY if api_key is None else api_key

        log.debug('Telegram in use with API KEY: {0}', api_key)

        message = '{0} : {1}'.format(title, msg).encode('utf-8')
        payload = {'chat_id': user_id, 'text': message}
        telegram_api = 'https://api.telegram.org/bot{api_key}/sendMessage'

        success = False
        try:
            r = requests.post(telegram_api.format(api_key=api_key), data=payload)
            r.raise_for_status()
            message = 'Telegram message sent successfully.'
            success = True
        except RequestException as error:
            message = 'Unknown IO error: %s' % error
            if hasattr(error, 'response') and error.response is not None:
                error_message = {
                    400: 'Missing parameter(s). Double check your settings or if the channel/user exists.',
                    401: 'Authentication failed.',
                    420: 'Too many messages.',
                    500: 'Server error. Please retry in a few moments.',
                }
                if error.response.status_code in error_message:
                    message = error_message.get(error.response.status_code)
                else:
                    message = http_status_code.get(error.response.status_code, message)
        except Exception as e:
            message = 'Error while sending Telegram message: %s ' % e
        finally:
            log.info(message)
        return success, message

    def notify_snatch(self, title, message):
        """
        Sends a Telegram notification when an episode is snatched

        :param ep_name: The name of the episode snatched
        :param is_proper: Boolean. If snatch is proper or not
        """
        if app.TELEGRAM_NOTIFY_ONSNATCH:
            self._notify_telegram(title, message)

    def notify_download(self, ep_obj, title=notifyStrings[NOTIFY_DOWNLOAD]):
        """
        Sends a Telegram notification when an episode is downloaded

        :param ep_name: The name of the episode downloaded
        :param title: The title of the notification to send
        """
        if app.TELEGRAM_NOTIFY_ONDOWNLOAD:
            self._notify_telegram(title, ep_obj.pretty_name_with_quality())

    def notify_subtitle_download(self, ep_obj, lang, title=notifyStrings[NOTIFY_SUBTITLE_DOWNLOAD]):
        """
        Sends a Telegram notification when subtitles for an episode are downloaded

        :param ep_name: The name of the episode subtitles were downloaded for
        :param lang: The language of the downloaded subtitles
        :param title: The title of the notification to send
        """
        if app.TELEGRAM_NOTIFY_ONSUBTITLEDOWNLOAD:
            self._notify_telegram(title, '%s: %s' % (ep_obj.pretty_name(), lang))

    def notify_git_update(self, new_version='??'):
        """
        Sends a Telegram notification for git updates

        :param new_version: The new version available from git
        """
        if app.USE_TELEGRAM:
            update_text = notifyStrings[NOTIFY_GIT_UPDATE_TEXT]
            title = notifyStrings[NOTIFY_GIT_UPDATE]
            self._notify_telegram(title, update_text + new_version)

    def notify_login(self, ipaddress=''):
        """
        Sends a Telegram notification on login

        :param ipaddress: The ip address the login is originating from
        """
        if app.USE_TELEGRAM:
            update_text = notifyStrings[NOTIFY_LOGIN_TEXT]
            title = notifyStrings[NOTIFY_LOGIN]
            self._notify_telegram(title, update_text.format(ipaddress))

    def _notify_telegram(self, title, message, user_id=None, api_key=None, force=False):
        """
        Sends a Telegram notification

        :param title: The title of the notification to send
        :param message: The message string to send
        :param id: The Telegram user/group id to send the message to
        :param api_key: Your Telegram bot API token
        :param force: Enforce sending, for instance for testing

        :returns: the message to send
        """

        if not (force or app.USE_TELEGRAM):
            log.debug('Notification for Telegram not enabled, skipping this notification')
            return False, 'Disabled'

        log.debug('Sending a Telegram message for {0}', message)

        return self._send_telegram_msg(title, message, user_id, api_key)
