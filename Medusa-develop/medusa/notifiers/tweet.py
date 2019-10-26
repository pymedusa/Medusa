# coding=utf-8

"""Twitter notifier module."""
from __future__ import unicode_literals

import logging

from medusa import app, common
from medusa.logger.adapters.style import BraceAdapter

from requests.exceptions import RequestException

from requests_oauthlib import OAuth1Session

from six import PY2, text_type

import twitter

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    """Twitter notifier class."""

    consumer_key = 'vHHtcB6WzpWDG6KYlBMr8g'
    consumer_secret = 'zMqq5CB3f8cWKiRO2KzWPTlBanYmV0VYxSXZ0Pxds0E'

    REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'
    ACCESS_TOKEN_URL = 'https://api.twitter.com/oauth/access_token'
    AUTHORIZATION_URL = 'https://api.twitter.com/oauth/authorize'

    def notify_snatch(self, title, message):
        """
        Send a notification that an episode was snatched.

        :param ep_name: The name of the episode snatched
        :param is_proper: Boolean. If snatch is proper or not
        """
        if app.TWITTER_NOTIFY_ONSNATCH:
            self._notify_twitter('{0}: {1}'.format(title, message))

    def notify_download(self, ep_obj):
        """
        Send a notification that an episode was downloaded.

        :param ep_name: The name of the episode downloaded
        """
        if app.TWITTER_NOTIFY_ONDOWNLOAD:
            self._notify_twitter('{0}: {1}'.format(common.notifyStrings[common.NOTIFY_DOWNLOAD],
                                                   ep_obj.pretty_name_with_quality()))

    def notify_subtitle_download(self, ep_obj, lang):
        """
        Send a notification that subtitles for an episode were downloaded.

        :param ep_name: The name of the episode subtitles were downloaded for
        :param lang: The language of the downloaded subtitles
        """
        if app.TWITTER_NOTIFY_ONSUBTITLEDOWNLOAD:
            self._notify_twitter('{0} {1}: {2}'.format(common.notifyStrings[common.NOTIFY_SUBTITLE_DOWNLOAD],
                                                       ep_obj.pretty_name(), lang))

    def notify_git_update(self, new_version='??'):
        """
        Send a notification that Medusa was updated.

        :param new_version: The commit Medusa was updated to
        """
        if app.USE_TWITTER:
            update_text = common.notifyStrings[common.NOTIFY_GIT_UPDATE_TEXT]
            title = common.notifyStrings[common.NOTIFY_GIT_UPDATE]
            self._notify_twitter('{0} - {1}{2}'.format(title, update_text, new_version))

    def notify_login(self, ipaddress=''):
        """
        Send a notification that Medusa was logged into remotely.

        :param ipaddress: The ip Medusa was logged into from
        """
        if app.USE_TWITTER:
            update_text = common.notifyStrings[common.NOTIFY_LOGIN_TEXT]
            title = common.notifyStrings[common.NOTIFY_LOGIN]
            self._notify_twitter('{0} - {1}'.format(title, update_text.format(ipaddress)))

    def test_notify(self):
        """
        Send a test notification.

        :return: True for no issue or False if there was an error
        """
        return self._notify_twitter('This is a test notification from Medusa', force=True)

    def _get_authorization(self):
        """
        Step 1 of authorization - get app authorization URL.

        :param key: Authorization key received from twitter
        :return: Authorization URL if succeeded, `None` otherwise
        """
        log.debug('Requesting temp token from Twitter')

        oauth_session = OAuth1Session(client_key=self.consumer_key, client_secret=self.consumer_secret)
        try:
            request_token = oauth_session.fetch_request_token(self.REQUEST_TOKEN_URL)
        except RequestException as error:
            log.error('Invalid response from Twitter requesting temp token: {0}', error)
            return None

        app.TWITTER_USERNAME = request_token['oauth_token']
        app.TWITTER_PASSWORD = request_token['oauth_token_secret']

        return oauth_session.authorization_url(self.AUTHORIZATION_URL)

    def _get_credentials(self, key):
        """
        Step 2 of authorization - poll server for access token.

        :param key: Authorization key received from twitter
        :return: True if succeeded, False otherwise
        """
        log.debug('Generating and signing request for an access token using key {0}', key)
        oauth_session = OAuth1Session(
            client_key=self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=app.TWITTER_USERNAME,
            resource_owner_secret=app.TWITTER_PASSWORD
        )

        try:
            access_token = oauth_session.fetch_access_token(
                self.ACCESS_TOKEN_URL,
                verifier=text_type(key)
            )
        except Exception as error:
            log.error('The request for a token with did not succeed: {0}', error)
            return False

        log.debug('Your Twitter Access Token key: {0}', access_token['oauth_token'])
        log.debug('Access Token secret: {0}', access_token['oauth_token_secret'])
        app.TWITTER_USERNAME = access_token['oauth_token']
        app.TWITTER_PASSWORD = access_token['oauth_token_secret']
        return True

    def _send_tweet(self, message=None):
        """
        Send a tweet.

        :param message: Message to send
        :return: True if succeeded, False otherwise
        """
        api = twitter.Api(
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            access_token_key=app.TWITTER_USERNAME,
            access_token_secret=app.TWITTER_PASSWORD
        )

        log.debug('Sending tweet: {0}', message)
        try:
            api.PostUpdate(message.encode('utf-8')[:279])
        except Exception as error:
            log.error('Error Sending Tweet: {0!r}', error)
            return False

        return True

    def _send_dm(self, message=None):
        """
        Send a direct message.

        :param message: Message to send
        :return: True if succeeded, False otherwise
        """
        dmdest = app.TWITTER_DMTO

        api = twitter.Api(
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            access_token_key=app.TWITTER_USERNAME,
            access_token_secret=app.TWITTER_PASSWORD
        )

        log.debug('Sending DM @{user}: {message}', {
            'user': dmdest,
            'message': message
        })
        try:
            if PY2:
                message = message.encode('utf-8')
            api.PostDirectMessage(message, screen_name=dmdest)
        except Exception as error:
            log.error('Error Sending Tweet (DM): {0!r}', error)
            return False

        return True

    def _notify_twitter(self, message='', force=False):
        prefix = app.TWITTER_PREFIX

        if not app.USE_TWITTER and not force:
            return False

        message = '{prefix}: {message}'.format(prefix=prefix, message=message)
        if app.TWITTER_USEDM and app.TWITTER_DMTO:
            return self._send_dm(message)
        else:
            return self._send_tweet(message)
