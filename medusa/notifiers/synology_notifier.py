# coding=utf-8

from __future__ import unicode_literals

import logging
import os
import subprocess
from builtins import object

from medusa import app, common
from medusa.helper.exceptions import ex
from medusa.logger.adapters.style import BraceAdapter

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    def notify_snatch(self, ep_name, is_proper):
        if app.SYNOLOGYNOTIFIER_NOTIFY_ONSNATCH:
            self._send_synologyNotifier(ep_name, common.notifyStrings[(common.NOTIFY_SNATCH, common.NOTIFY_SNATCH_PROPER)[is_proper]])

    def notify_download(self, ep_name):
        if app.SYNOLOGYNOTIFIER_NOTIFY_ONDOWNLOAD:
            self._send_synologyNotifier(ep_name, common.notifyStrings[common.NOTIFY_DOWNLOAD])

    def notify_subtitle_download(self, ep_name, lang):
        if app.SYNOLOGYNOTIFIER_NOTIFY_ONSUBTITLEDOWNLOAD:
            self._send_synologyNotifier(ep_name + ': ' + lang, common.notifyStrings[common.NOTIFY_SUBTITLE_DOWNLOAD])

    def notify_git_update(self, new_version='??'):
        if app.USE_SYNOLOGYNOTIFIER:
            update_text = common.notifyStrings[common.NOTIFY_GIT_UPDATE_TEXT]
            title = common.notifyStrings[common.NOTIFY_GIT_UPDATE]
            self._send_synologyNotifier(update_text + new_version, title)

    def notify_login(self, ipaddress=''):
        if app.USE_SYNOLOGYNOTIFIER:
            update_text = common.notifyStrings[common.NOTIFY_LOGIN_TEXT]
            title = common.notifyStrings[common.NOTIFY_LOGIN]
            self._send_synologyNotifier(update_text.format(ipaddress), title)

    def _send_synologyNotifier(self, message, title):
        synodsmnotify_cmd = ['/usr/syno/bin/synodsmnotify', '@administrators', title, message]
        log.info(u'Executing command {0}', synodsmnotify_cmd)
        log.debug(u'Absolute path to command: {0}', os.path.abspath(synodsmnotify_cmd[0]))
        try:
            p = subprocess.Popen(synodsmnotify_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 cwd=app.PROG_DIR)
            out, _ = p.communicate()
            log.debug(u'Script result: {0}', out)
        except OSError as e:
            log.info(u'Unable to run synodsmnotify: {0}', ex(e))
