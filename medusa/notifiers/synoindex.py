# coding=utf-8

from __future__ import unicode_literals

import logging
import os
import subprocess
from builtins import object

from medusa import app
from medusa.helper.exceptions import ex
from medusa.logger.adapters.style import BraceAdapter

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    def notify_snatch(self, title, message):
        pass

    def notify_download(self, ep_obj):
        pass

    def notify_subtitle_download(self, ep_obj, lang):
        pass

    def notify_git_update(self, new_version):
        pass

    def notify_login(self, ipaddress=''):
        pass

    def moveFolder(self, old_path, new_path):
        self.moveObject(old_path, new_path)

    def move_file(self, old_file, new_file):
        self.moveObject(old_file, new_file)

    def moveObject(self, old_path, new_path):
        if app.USE_SYNOINDEX:
            synoindex_cmd = ['/usr/syno/bin/synoindex', '-N', os.path.abspath(new_path),
                             os.path.abspath(old_path)]
            log.debug(u'Executing command {0}', synoindex_cmd)
            log.debug(u'Absolute path to command: {0}', os.path.abspath(synoindex_cmd[0]))
            try:
                p = subprocess.Popen(synoindex_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     cwd=app.PROG_DIR)
                out, _ = p.communicate()
                log.debug(u'Script result: {0}', out)
            except OSError as e:
                log.error(u'Unable to run synoindex: {0}', ex(e))

    def deleteFolder(self, cur_path):
        self.makeObject('-D', cur_path)

    def addFolder(self, cur_path):
        self.makeObject('-A', cur_path)

    def deleteFile(self, cur_file):
        self.makeObject('-d', cur_file)

    def addFile(self, cur_file):
        self.makeObject('-a', cur_file)

    def makeObject(self, cmd_arg, cur_path):
        if app.USE_SYNOINDEX:
            synoindex_cmd = ['/usr/syno/bin/synoindex', cmd_arg, os.path.abspath(cur_path)]
            log.debug(u'Executing command {0}', synoindex_cmd)
            log.debug(u'Absolute path to command: {0}', os.path.abspath(synoindex_cmd[0]))
            try:
                p = subprocess.Popen(synoindex_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     cwd=app.PROG_DIR)
                out, _ = p.communicate()
                log.debug(u'Script result: {0}', out)
            except OSError as e:
                log.error(u'Unable to run synoindex: {0}', ex(e))
