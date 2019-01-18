# coding=utf-8

from __future__ import unicode_literals

import logging
from distutils.version import LooseVersion

from medusa import app
from medusa.logger.adapters.style import BraceAdapter

from six import text_type


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class UpdateManager(object):
    def __init__(self):
        """Update manager initialization."""
        # Initialize the app.RUNS_IN_DOCKER variable
        # self.runs_in_docker()

    @staticmethod
    def get_github_org():
        return app.GIT_ORG

    @staticmethod
    def get_github_repo():
        return app.GIT_REPO

    @staticmethod
    def get_update_url():
        return app.WEB_ROOT + '/home/update/?pid=' + text_type(app.PID)

    def is_latest_version(self):
        """Compare the current installed version with the remote version."""
        if LooseVersion(self.newest_version) > LooseVersion(self.current_version):
            return False
        return True
