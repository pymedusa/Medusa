# coding=utf-8

from __future__ import unicode_literals

import logging
from builtins import object

from medusa import app, common
from medusa.helper.common import http_code_description
from medusa.logger.adapters.style import BraceAdapter

from pynma import pynma

from six import text_type

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    def test_notify(self, nma_api, nma_priority):
        return self._sendNMA(nma_api, nma_priority, event='Test', message='Testing NMA settings from Medusa',
                             force=True)

    def notify_snatch(self, ep_name, is_proper):
        if app.NMA_NOTIFY_ONSNATCH:
            self._sendNMA(nma_api=None, nma_priority=None,
                          event=common.notifyStrings[(common.NOTIFY_SNATCH, common.NOTIFY_SNATCH_PROPER)[is_proper]],
                          message=ep_name)

    def notify_download(self, ep_name):
        if app.NMA_NOTIFY_ONDOWNLOAD:
            self._sendNMA(nma_api=None, nma_priority=None, event=common.notifyStrings[common.NOTIFY_DOWNLOAD],
                          message=ep_name)

    def notify_subtitle_download(self, ep_name, lang):
        if app.NMA_NOTIFY_ONSUBTITLEDOWNLOAD:
            self._sendNMA(nma_api=None, nma_priority=None, event=common.notifyStrings[common.NOTIFY_SUBTITLE_DOWNLOAD],
                          message=ep_name + ': ' + lang)

    def notify_git_update(self, new_version='??'):
        if app.USE_NMA:
            update_text = common.notifyStrings[common.NOTIFY_GIT_UPDATE_TEXT]
            title = common.notifyStrings[common.NOTIFY_GIT_UPDATE]
            self._sendNMA(nma_api=None, nma_priority=None, event=title, message=update_text + new_version)

    def notify_login(self, ipaddress=''):
        if app.USE_NMA:
            update_text = common.notifyStrings[common.NOTIFY_LOGIN_TEXT]
            title = common.notifyStrings[common.NOTIFY_LOGIN]
            self._sendNMA(nma_api=None, nma_priority=None, event=title, message=update_text.format(ipaddress))

    def _sendNMA(self, nma_api=None, nma_priority=None, event=None, message=None, force=False):

        title = 'Medusa'

        if not app.USE_NMA and not force:
            return False

        if nma_api is None:
            nma_api = app.NMA_API
        elif isinstance(nma_api, text_type):
            nma_api = [nma_api]

        if nma_priority is None:
            nma_priority = app.NMA_PRIORITY

        batch = False

        p = pynma.PyNMA()
        keys = nma_api
        p.addkey(keys)

        if len(keys) > 1:
            batch = True

        log.debug(u'NMA: Sending notice with details: event="{0}, message="{1}", priority={2}, batch={3}',
                  event, message, nma_priority, batch)
        response = p.push(application=title, event=event, description=message, priority=nma_priority, batch_mode=batch)

        response_status_code = response[','.join(nma_api)][u'code']
        log_message = u'NMA: Could not send notification to NotifyMyAndroid.'

        if response_status_code == u'200':
            log.info(u'NMA: Notification sent to NotifyMyAndroid')
            return True
        elif response_status_code == u'402':
            log.info(u'{0} Maximum number of API calls per hour exceeded', log_message)
        elif response_status_code == u'401':
            log.warning(u'{0} The apikey provided is not valid', log_message)
        elif response_status_code == u'400':
            log.error(u'{0} Data supplied is in the wrong format, invalid length or null', log_message)
        else:
            log.warning(u'{0} Error: {1}', log_message, http_code_description(response_status_code))
        return False
