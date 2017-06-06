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
"""Failed processor module."""
from . import app, logger
from .helper.exceptions import FailedPostProcessingFailedException
from .name_parser.parser import InvalidNameException, InvalidShowException, NameParser
from .search.queue import FailedQueueItem


class FailedProcessor(object):
    """Take appropriate action when a download fails to complete."""

    def __init__(self, dir_name, nzb_name):
        """Initialize the class.

        :param dir_name: Full path to the folder of the failed download
        :param nzb_name: Full name of the nzb file that failed
        """
        self.dir_name = dir_name
        self.nzb_name = nzb_name

        self.log = ""

    def process(self):
        """
        Do the actual work.

        :return: True
        """
        self._log(u"Failed download detected. NZB name: '{nzb}'. Folder name: '{dir}'".format
                  (nzb=self.nzb_name, dir=self.dir_name))

        try:
            parsed = NameParser().parse(self.nzb_name or self.dir_name)
        except (InvalidNameException, InvalidShowException):
            self._log(u'Not enough information to parse release name into a valid show. '
                      u'Consider adding scene exceptions or improve naming for: {release}'.format
                      (release=parsed.original_name), logger.WARNING)
            raise FailedPostProcessingFailedException()

        self._log(u'Parsed info: {result}'.format(result=parsed), logger.DEBUG)

        segment = []
        if not parsed.episode_numbers:
            # Get all episode objects from that season
            self._log(u'Detected as season pack: {release}'.format(release=parsed.original_name), logger.DEBUG)
            segment.extend(parsed.show.get_all_episodes(parsed.season_number))
        else:
            self._log(u'Detected as single/multi episode: {release}'.format(release=parsed.original_name), logger.DEBUG)
            for episode in parsed.episode_numbers:
                segment.append(parsed.show.get_episode(parsed.season_number, episode))

        if segment:
            self._log(u'Adding this release to failed queue: {release}'.format(release=parsed.original_name), logger.DEBUG)
            cur_failed_queue_item = FailedQueueItem(parsed.show, segment)
            app.forced_search_queue_scheduler.action.add_item(cur_failed_queue_item)

        return True

    def _log(self, message, level=logger.INFO):
        """Log to regular logfile and save for return for PP script log."""
        logger.log(message, level)
        self.log += message + "\n"
