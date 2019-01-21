# coding=utf-8

from __future__ import unicode_literals

import logging

from medusa import app
from medusa.logger.adapters.style import BraceAdapter
from medusa.updater.source_updater import SourceUpdateManager


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class DockerUpdateManager(SourceUpdateManager):
    def __init__(self):
        super(DockerUpdateManager, self).__init__()

    def __str__(self):
        return 'Docker Updater'

    def need_update(self):
        if self.branch != self._find_installed_branch():
            log.debug(u'Branch checkout: {0}->{1}', self._find_installed_branch(), self.branch)
            return True

        if self.branch == 'master' and not self.is_latest_version():
            self._set_update_text()
            return True

        return False

    def can_update(self):
        """Whether or not the update can be performed.

        :return:
        :rtype: bool
        """
        return False

    def _set_update_text(self):
        """Set an update text, when running in a Docker container."""
        log.debug('There is an update available, Medusa is running in a Docker container,'
                  ' so auto updating is disabled.')

        url = 'http://github.com/' + self.github_org + '/' + self.github_repo + '/releases'
        newest_text = 'There is a <a href="' + url + '" onclick="window.open(this.href); return false;">newer version available</a>'
        newest_text += ' (' + self.newest_version + ') &mdash; Pull the latest Docker image and rebuild your container to update'
        app.NEWEST_VERSION_STRING = newest_text

    def update(self):
        """Download the latest version."""
        return False
