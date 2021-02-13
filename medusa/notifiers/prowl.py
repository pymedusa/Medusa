# coding=utf-8

from __future__ import unicode_literals

import json
import logging
import socket
from builtins import object

from medusa import app, common, db
from medusa.logger.adapters.style import BraceAdapter

from requests.compat import urlencode

from six.moves.http_client import HTTPException, HTTPSConnection

try:
    # this only exists in 2.6
    from ssl import SSLError
except ImportError:
    # make a fake one since I don't know what it is supposed to be in 2.5
    class SSLError(Exception):
        pass

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    def test_notify(self, prowl_api, prowl_priority):
        return self._send_prowl(prowl_api, prowl_priority, event='Test', message='Testing Prowl settings from Medusa', force=True)

    def notify_snatch(self, title, message):
        if app.PROWL_NOTIFY_ONSNATCH:
            show = self._parse_episode(message)
            recipients = self._generate_recipients(show)
            if not recipients:
                log.debug('Skipping prowl notify because there are no configured recipients')
            else:
                for api in recipients:
                    self._send_prowl(prowl_api=api, prowl_priority=None,
                                     event=title,
                                     message=message)

    def notify_download(self, ep_obj):
        ep_name = ep_obj.pretty_name_with_quality()
        if app.PROWL_NOTIFY_ONDOWNLOAD:
            show = self._parse_episode(ep_name)
            recipients = self._generate_recipients(show)
            if not recipients:
                log.debug('Skipping prowl notify because there are no configured recipients')
            else:
                for api in recipients:
                    self._send_prowl(prowl_api=api, prowl_priority=None,
                                     event=common.notifyStrings[common.NOTIFY_DOWNLOAD],
                                     message=ep_name)

    def notify_subtitle_download(self, ep_obj, lang):
        ep_name = ep_obj.pretty_name()
        if app.PROWL_NOTIFY_ONSUBTITLEDOWNLOAD:
            show = self._parse_episode(ep_name)
            recipients = self._generate_recipients(show)
            if not recipients:
                log.debug('Skipping prowl notify because there are no configured recipients')
            else:
                for api in recipients:
                    self._send_prowl(prowl_api=api, prowl_priority=None,
                                     event=common.notifyStrings[common.NOTIFY_SUBTITLE_DOWNLOAD],
                                     message=ep_name + ' [' + lang + ']')

    def notify_git_update(self, new_version='??'):
        if app.USE_PROWL:
            update_text = common.notifyStrings[common.NOTIFY_GIT_UPDATE_TEXT]
            title = common.notifyStrings[common.NOTIFY_GIT_UPDATE]
            self._send_prowl(prowl_api=None, prowl_priority=None,
                             event=title, message=update_text + new_version)

    def notify_login(self, ipaddress=''):
        if app.USE_PROWL:
            update_text = common.notifyStrings[common.NOTIFY_LOGIN_TEXT]
            title = common.notifyStrings[common.NOTIFY_LOGIN]
            self._send_prowl(prowl_api=None, prowl_priority=None,
                             event=title, message=update_text.format(ipaddress))

    @staticmethod
    def _generate_recipients(show=None):
        apis = []
        mydb = db.DBConnection()

        # Grab the global recipient(s)
        if app.PROWL_API:
            for api in app.PROWL_API:
                if api.strip():
                    apis.append(api)

        # Grab the per-show-notification recipients
        if show is not None:
            for value in show:
                for subs in mydb.select('SELECT notify_list FROM tv_shows WHERE show_name = ?', (value,)):
                    if subs['notify_list']:
                        entries = json.loads(subs['notify_list'])
                        if entries:
                            for api in entries['prowlAPIs'].split(','):
                                if api.strip():
                                    apis.append(api)

        apis = set(apis)
        return apis

    @staticmethod
    def _send_prowl(prowl_api=None, prowl_priority=None, event=None, message=None, force=False):

        if not app.USE_PROWL and not force:
            return False

        if prowl_api is None:
            prowl_api = ','.join(app.PROWL_API)
            if not prowl_api:
                return False

        if prowl_priority is None:
            prowl_priority = app.PROWL_PRIORITY

        title = app.PROWL_MESSAGE_TITLE

        log.debug(u'PROWL: Sending notice with details: title="{0}" event="{1}", message="{2}", priority={3}, api={4}',
                  title, event, message, prowl_priority, prowl_api)

        http_handler = HTTPSConnection('api.prowlapp.com')

        data = {'apikey': prowl_api,
                'application': title,
                'event': event,
                'description': message.encode('utf-8'),
                'priority': prowl_priority}

        try:
            http_handler.request('POST',
                                 '/publicapi/add',
                                 headers={'Content-type': 'application/x-www-form-urlencoded'},
                                 body=urlencode(data))
        except (SSLError, HTTPException, socket.error):
            log.error(u'Prowl notification failed.')
            return False
        response = http_handler.getresponse()
        request_status = response.status

        if request_status == 200:
            log.info(u'Prowl notifications sent.')
            return True
        elif request_status == 401:
            log.error(u'Prowl auth failed: {0}', response.reason)
            return False
        else:
            log.error(u'Prowl notification failed.')
            return False

    @staticmethod
    def _parse_episode(ep_name):
        sep = ' - '
        titles = ep_name.split(sep)
        titles.sort(key=len, reverse=True)
        log.debug('TITLES: {0}', titles)

        return titles
