# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
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
"""Post Processor Module."""
from __future__ import unicode_literals

import logging
import os.path

import medusa as app
from . import processTV


logger = logging.getLogger(__name__)


class PostProcessor(object):
    """Post Processor Scheduler Action."""

    def __init__(self):
        """Init method."""
        self.amActive = False

    def run(self, force=False):
        """Run the postprocessor.

        :param force: Forces postprocessing run
        :type force: bool
        """
        self.amActive = True
        try:
            if not os.path.isdir(app.TV_DOWNLOAD_DIR):
                logger.error(u"Automatic post-processing attempted but directory doesn't exist: {folder}",
                             folder=app.TV_DOWNLOAD_DIR)
                return

            if not (force or os.path.isabs(app.TV_DOWNLOAD_DIR)):
                logger.error(u"Automatic post-processing attempted but directory is relative "
                             u"(and probably not what you really want to process): {folder}",
                             folder=app.TV_DOWNLOAD_DIR)
                return

            processTV.processDir(app.TV_DOWNLOAD_DIR, force=force)
        finally:
            self.amActive = False
