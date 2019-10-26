"""Discord notifier."""
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
    Use Discord to send notifications.

    https://discordapp.com
    """

    def _send_discord_msg(self, title, msg, webhook=None, tts=False):
        """Collect the parameters and send the message to the discord webhook."""
        webhook = app.DISCORD_WEBHOOK if webhook is None else webhook
        tts = app.DISCORD_TTS if tts is None else tts

        log.debug('Discord in use with API webhook: {webhook}', {'webhook': webhook})

        message = '{0} : {1}'.format(title, msg)

        headers = {'Content-Type': 'application/json'}
        payload = {
            'content': message,
            'username': app.DISCORD_NAME,
            'avatar_url': app.DISCORD_AVATAR_URL,
            'tts': tts
        }

        success = False
        try:
            r = requests.post(webhook, json=payload, headers=headers)
            r.raise_for_status()
            message = 'Discord message sent successfully.'
            success = True
        except RequestException as error:
            message = 'Unknown IO error: %s' % error
            if hasattr(error, 'response') and error.response is not None:
                error_message = {
                    400: 'Missing parameter(s). Double check your settings or if the channel/user exists.',
                    401: 'Authentication failed, check your webhook url',
                    420: 'Too many messages.',
                    500: 'Server error. Please retry in a few moments.',
                }
                if error.response.status_code in error_message:
                    message = error_message.get(error.response.status_code)
                else:
                    message = http_status_code.get(error.response.status_code, message)
        except Exception as error:
            message = 'Error while sending Discord message: {0} '.format(error)
        finally:
            log.info(message)
        return success, message

    def notify_snatch(self, title, message):
        """
        Send a Discord notification when an episode is snatched.

        :param ep_name: The name of the episode snatched
        :param is_proper: Boolean. If snatch is proper or not
        """
        if app.DISCORD_NOTIFY_ONSNATCH:
            self._notify_discord(title, message)

    def notify_download(self, ep_obj, title=notifyStrings[NOTIFY_DOWNLOAD]):
        """
        Send a Discord notification when an episode is downloaded.

        :param ep_name: The name of the episode downloaded
        :param title: The title of the notification to send
        """
        if app.DISCORD_NOTIFY_ONDOWNLOAD:
            self._notify_discord(title, ep_obj.pretty_name_with_quality())

    def notify_subtitle_download(self, ep_obj, lang, title=notifyStrings[NOTIFY_SUBTITLE_DOWNLOAD]):
        """
        Send a Discord notification when subtitles for an episode are downloaded.

        :param ep_name: The name of the episode subtitles were downloaded for
        :param lang: The language of the downloaded subtitles
        :param title: The title of the notification to send
        """
        if app.DISCORD_NOTIFY_ONSUBTITLEDOWNLOAD:
            self._notify_discord(title, '{name}: {lang}'.format(name=ep_obj.pretty_name(), lang=lang))

    def notify_git_update(self, new_version='??'):
        """
        Send a Discord notification for git updates.

        :param new_version: The new version available from git
        """
        if app.USE_DISCORD:
            update_text = notifyStrings[NOTIFY_GIT_UPDATE_TEXT]
            title = notifyStrings[NOTIFY_GIT_UPDATE]
            self._notify_discord(title, update_text + new_version)

    def notify_login(self, ipaddress=''):
        """
        Send a Discord notification on login.

        :param ipaddress: The ip address the login is originating from
        """
        if app.USE_DISCORD:
            update_text = notifyStrings[NOTIFY_LOGIN_TEXT]
            title = notifyStrings[NOTIFY_LOGIN]
            self._notify_discord(title, update_text.format(ipaddress))

    def test_notify(self, discord_webhook=None, discord_tts=None):
        """Create the test notification."""
        return self._notify_discord('test', 'This is a test notification from Medusa', webhook=discord_webhook, tts=discord_tts, force=True)

    def _notify_discord(self, title='', message='', webhook=None, tts=False, force=False):
        """Validate if USE_DISCORD or Force is enabled and send."""
        if not app.USE_DISCORD and not force:
            return False

        return self._send_discord_msg(title, message, webhook, tts)
