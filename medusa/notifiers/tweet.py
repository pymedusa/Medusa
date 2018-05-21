# coding=utf-8

from __future__ import unicode_literals

import logging
from builtins import object

from medusa import app, common
from medusa.logger.adapters.style import BraceAdapter

import oauth2 as oauth

import pythontwitter as twitter

from six.moves.urllib.parse import parse_qsl

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    consumer_key = 'vHHtcB6WzpWDG6KYlBMr8g'
    consumer_secret = 'zMqq5CB3f8cWKiRO2KzWPTlBanYmV0VYxSXZ0Pxds0E'

    REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'
    ACCESS_TOKEN_URL = 'https://api.twitter.com/oauth/access_token'
    AUTHORIZATION_URL = 'https://api.twitter.com/oauth/authorize'
    SIGNIN_URL = 'https://api.twitter.com/oauth/authenticate'

    def notify_snatch(self, ep_name, is_proper):
        if app.TWITTER_NOTIFY_ONSNATCH:
            self._notifyTwitter('{0}: {1}'.format(common.notifyStrings[(common.NOTIFY_SNATCH, common.NOTIFY_SNATCH_PROPER)[is_proper]], ep_name))

    def notify_download(self, ep_name):
        if app.TWITTER_NOTIFY_ONDOWNLOAD:
            self._notifyTwitter('{0}: {1}'.format(common.notifyStrings[common.NOTIFY_DOWNLOAD], ep_name))

    def notify_subtitle_download(self, ep_name, lang):
        if app.TWITTER_NOTIFY_ONSUBTITLEDOWNLOAD:
            self._notifyTwitter('{0} {1}: {2}'.format(common.notifyStrings[common.NOTIFY_SUBTITLE_DOWNLOAD], ep_name, lang))

    def notify_git_update(self, new_version='??'):
        if app.USE_TWITTER:
            update_text = common.notifyStrings[common.NOTIFY_GIT_UPDATE_TEXT]
            title = common.notifyStrings[common.NOTIFY_GIT_UPDATE]
            self._notifyTwitter('{0} - {1}{2}'.format(title, update_text, new_version))

    def notify_login(self, ipaddress=''):
        if app.USE_TWITTER:
            update_text = common.notifyStrings[common.NOTIFY_LOGIN_TEXT]
            title = common.notifyStrings[common.NOTIFY_LOGIN]
            self._notifyTwitter('{0} - {1}'.format(title, update_text.format(ipaddress)))

    def test_notify(self):
        return self._notifyTwitter('This is a test notification from Medusa', force=True)

    def _get_authorization(self):

        oauth_consumer = oauth.Consumer(key=self.consumer_key, secret=self.consumer_secret)
        oauth_client = oauth.Client(oauth_consumer)

        log.debug(u'Requesting temp token from Twitter')

        resp, content = oauth_client.request(self.REQUEST_TOKEN_URL, 'GET')

        if resp['status'] != '200':
            log.error(u'Invalid response from Twitter requesting temp token: {0}', resp['status'])
        else:
            request_token = dict(parse_qsl(content))

            app.TWITTER_USERNAME = request_token['oauth_token']
            app.TWITTER_PASSWORD = request_token['oauth_token_secret']

            return self.AUTHORIZATION_URL + '?oauth_token=' + request_token['oauth_token']

    def _get_credentials(self, key):
        request_token = {
            'oauth_token': app.TWITTER_USERNAME,
            'oauth_token_secret': app.TWITTER_PASSWORD,
            'oauth_callback_confirmed': 'true'
        }

        token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
        token.set_verifier(key)

        log.debug(u'Generating and signing request for an access token using key {0}', key)

        oauth_consumer = oauth.Consumer(key=self.consumer_key, secret=self.consumer_secret)
        log.debug(u'oauth_consumer: {0}', oauth_consumer)
        oauth_client = oauth.Client(oauth_consumer, token)
        log.debug(u'oauth_client: {0}', oauth_client)
        resp, content = oauth_client.request(self.ACCESS_TOKEN_URL, method='POST', body='oauth_verifier=%s' % key)
        log.debug(u'resp, content: {0}, {1}', resp, content)

        access_token = dict(parse_qsl(content))
        log.debug(u'access_token: {0}', access_token)

        log.debug(u'resp[status] = {0}', resp['status'])
        if resp['status'] != '200':
            log.error(u'The request for a token with did not succeed: {0}', resp['status'])
            return False
        else:
            log.debug(u'Your Twitter Access Token key: {0}', access_token['oauth_token'])
            log.debug(u'Access Token secret: {0}', access_token['oauth_token_secret'])
            app.TWITTER_USERNAME = access_token['oauth_token']
            app.TWITTER_PASSWORD = access_token['oauth_token_secret']
            return True

    def _send_tweet(self, message=None):

        username = self.consumer_key
        password = self.consumer_secret
        access_token_key = app.TWITTER_USERNAME
        access_token_secret = app.TWITTER_PASSWORD

        log.debug(u'Sending tweet: {0}', message)

        api = twitter.Api(username, password, access_token_key, access_token_secret)

        try:
            api.PostUpdate(message.encode('utf8')[:279])
        except Exception as e:
            log.error(u'Error Sending Tweet: {!r}', e)
            return False

        return True

    def _send_dm(self, message=None):

        username = self.consumer_key
        password = self.consumer_secret
        dmdest = app.TWITTER_DMTO
        access_token_key = app.TWITTER_USERNAME
        access_token_secret = app.TWITTER_PASSWORD

        log.debug(u'Sending DM: {0} {1}', dmdest, message)

        api = twitter.Api(username, password, access_token_key, access_token_secret)

        try:
            api.PostDirectMessage(message.encode('utf8'), screen_name=dmdest)
        except Exception as error:
            log.error(u'Error Sending Tweet (DM): {!r}', error)
            return False

        return True

    def _notifyTwitter(self, message='', force=False):
        prefix = app.TWITTER_PREFIX

        if not app.USE_TWITTER and not force:
            return False

        if app.TWITTER_USEDM and app.TWITTER_DMTO:
            return self._send_dm(prefix + ': ' + message)
        else:
            return self._send_tweet(prefix + ': ' + message)
