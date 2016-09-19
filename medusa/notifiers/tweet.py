# coding=utf-8

# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
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

import medusa as app
import oauth2 as oauth
import pythontwitter as twitter
from six.moves.urllib.parse import parse_qsl
from .. import common, logger


class Notifier(object):
    consumer_key = "vHHtcB6WzpWDG6KYlBMr8g"
    consumer_secret = "zMqq5CB3f8cWKiRO2KzWPTlBanYmV0VYxSXZ0Pxds0E"

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

    def notify_git_update(self, new_version="??"):
        if app.USE_TWITTER:
            update_text = common.notifyStrings[common.NOTIFY_GIT_UPDATE_TEXT]
            title = common.notifyStrings[common.NOTIFY_GIT_UPDATE]
            self._notifyTwitter('{0} - {1}{2}'.format(title, update_text, new_version))

    def notify_login(self, ipaddress=""):
        if app.USE_TWITTER:
            update_text = common.notifyStrings[common.NOTIFY_LOGIN_TEXT]
            title = common.notifyStrings[common.NOTIFY_LOGIN]
            self._notifyTwitter('{0} - {1}'.format(title, update_text.format(ipaddress)))

    def test_notify(self):
        return self._notifyTwitter("This is a test notification from Medusa", force=True)

    def _get_authorization(self):

        oauth_consumer = oauth.Consumer(key=self.consumer_key, secret=self.consumer_secret)
        oauth_client = oauth.Client(oauth_consumer)

        logger.log(u'Requesting temp token from Twitter', logger.DEBUG)

        resp, content = oauth_client.request(self.REQUEST_TOKEN_URL, 'GET')

        if resp['status'] != '200':
            logger.log(u'Invalid response from Twitter requesting temp token: {0}'.format(resp['status']), logger.ERROR)
        else:
            request_token = dict(parse_qsl(content))

            app.TWITTER_USERNAME = request_token['oauth_token']
            app.TWITTER_PASSWORD = request_token['oauth_token_secret']

            return self.AUTHORIZATION_URL + "?oauth_token=" + request_token['oauth_token']

    def _get_credentials(self, key):
        request_token = {
            'oauth_token': app.TWITTER_USERNAME,
            'oauth_token_secret': app.TWITTER_PASSWORD,
            'oauth_callback_confirmed': 'true'
        }

        token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
        token.set_verifier(key)

        logger.log(u'Generating and signing request for an access token using key {0}'.format(key), logger.DEBUG)

        oauth_consumer = oauth.Consumer(key=self.consumer_key, secret=self.consumer_secret)
        logger.log(u'oauth_consumer: {0}'.format(oauth_consumer), logger.DEBUG)
        oauth_client = oauth.Client(oauth_consumer, token)
        logger.log(u'oauth_client: {0}'.format(oauth_client), logger.DEBUG)
        resp, content = oauth_client.request(self.ACCESS_TOKEN_URL, method='POST', body='oauth_verifier=%s' % key)
        logger.log(u'resp, content: {0}, {1}'.format(resp, content), logger.DEBUG)

        access_token = dict(parse_qsl(content))
        logger.log(u'access_token: {0}'.format(access_token), logger.DEBUG)

        logger.log(u'resp[status] = {0}'.format(resp['status']), logger.DEBUG)
        if resp['status'] != '200':
            logger.log(u'The request for a token with did not succeed: {0}'.format(resp['status']), logger.ERROR)
            return False
        else:
            logger.log(u'Your Twitter Access Token key: {0}'.format(access_token['oauth_token']), logger.DEBUG)
            logger.log(u'Access Token secret: {0}'.format(access_token['oauth_token_secret']), logger.DEBUG)
            app.TWITTER_USERNAME = access_token['oauth_token']
            app.TWITTER_PASSWORD = access_token['oauth_token_secret']
            return True

    def _send_tweet(self, message=None):

        username = self.consumer_key
        password = self.consumer_secret
        access_token_key = app.TWITTER_USERNAME
        access_token_secret = app.TWITTER_PASSWORD

        logger.log(u'Sending tweet: {0}'.format(message), logger.DEBUG)

        api = twitter.Api(username, password, access_token_key, access_token_secret)

        try:
            api.PostUpdate(message.encode('utf8')[:139])
        except Exception as e:
            logger.log(u'Error Sending Tweet: {!r}'.format(e), logger.ERROR)
            return False

        return True

    def _send_dm(self, message=None):

        username = self.consumer_key
        password = self.consumer_secret
        dmdest = app.TWITTER_DMTO
        access_token_key = app.TWITTER_USERNAME
        access_token_secret = app.TWITTER_PASSWORD

        logger.log(u'Sending DM: {0} {1}'.format(dmdest, message), logger.DEBUG)

        api = twitter.Api(username, password, access_token_key, access_token_secret)

        try:
            api.PostDirectMessage(dmdest, message.encode('utf8')[:139])
        except Exception as e:
            logger.log(u'Error Sending Tweet (DM): {!r}'.format(e), logger.ERROR)
            return False

        return True

    def _notifyTwitter(self, message='', force=False):
        prefix = app.TWITTER_PREFIX

        if not app.USE_TWITTER and not force:
            return False

        if app.TWITTER_USEDM and app.TWITTER_DMTO:
            return self._send_dm(prefix + ": " + message)
        else:
            return self._send_tweet(prefix + ": " + message)
