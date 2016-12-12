# coding=utf-8
# Author: Tyler Fenby <tylerfenby@gmail.com>

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

from . import app, logger, show_name_helpers
from .helper.exceptions import FailedPostProcessingFailedException
from .name_parser.parser import InvalidNameException, InvalidShowException, NameParser
from .search.queue import FailedQueueItem


class FailedProcessor(object):
    """Take appropriate action when a download fails to complete."""

    def __init__(self, dirName, nzbName):
        """
        :param dirName: Full path to the folder of the failed download
        :param nzbName: Full name of the nzb file that failed
        """
        self.dir_name = dirName
        self.nzb_name = nzbName

        self.log = ""

    def process(self):
        """
        Do the actual work

        :return: True
        """
        self._log(u"Failed download detected: (" + str(self.nzb_name) + ", " + str(self.dir_name) + ")")

        releaseName = show_name_helpers.determineReleaseName(self.dir_name, self.nzb_name)
        if not releaseName:
            self._log(u"Warning: unable to find a valid release name.", logger.WARNING)
            raise FailedPostProcessingFailedException()

        try:
            parsed = NameParser().parse(releaseName)
        except (InvalidNameException, InvalidShowException) as error:
            self._log(u"{}".format(error), logger.DEBUG)
            raise FailedPostProcessingFailedException()

        self._log(u"name_parser info: {result}".format(result=parsed), logger.DEBUG)

        segment = []
        if not parsed.episode_numbers:
            # Get all episode objects from that season
            self._log(u"Detected as season pack: {0}".format(releaseName), logger.DEBUG)
            segment.extend(parsed.show.get_all_episodes(parsed.season_number))
        else:
            self._log(u"Detected as single/multi episode: {0}".format(releaseName), logger.DEBUG)
            for episode in parsed.episode_numbers:
                segment.append(parsed.show.get_episode(parsed.season_number, episode))

        if segment:
            self._log(u"Adding this release to failed queue: {0}".format(releaseName), logger.DEBUG)
            cur_failed_queue_item = FailedQueueItem(parsed.show, segment)
            app.forcedSearchQueueScheduler.action.add_item(cur_failed_queue_item)

        return True

    def _log(self, message, level=logger.INFO):
        """Log to regular logfile and save for return for PP script log."""
        logger.log(message, level)
        self.log += message + "\n"
