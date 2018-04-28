# coding=utf-8

from __future__ import unicode_literals

import logging
from builtins import object

from medusa import app, logger
from medusa.helper.exceptions import FailedPostProcessingFailedException
from medusa.logger.adapters.style import BraceAdapter
from medusa.name_parser.parser import InvalidNameException, InvalidShowException, NameParser
from medusa.search.queue import FailedQueueItem
from medusa.show import naming

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class FailedProcessor(object):
    """Take appropriate action when a download fails to complete."""

    def __init__(self, dirName, nzbName):
        """Initialize the class.

        :param dirName: Full path to the folder of the failed download
        :param nzbName: Full name of the nzb file that failed
        """
        self.dir_name = dirName
        self.nzb_name = nzbName

        self._output = []

    def process(self):
        """
        Do the actual work.

        :return: True
        """
        self.log(logger.INFO, u'Failed download detected: ({nzb}, {dir})'.format(nzb=self.nzb_name, dir=self.dir_name))

        releaseName = naming.determine_release_name(self.dir_name, self.nzb_name)
        if not releaseName:
            self.log(logger.WARNING, u'Warning: unable to find a valid release name.')
            raise FailedPostProcessingFailedException()

        try:
            parse_result = NameParser().parse(releaseName)
        except (InvalidNameException, InvalidShowException):
            self.log(logger.WARNING, u'Not enough information to parse release name into a valid show. '
                     u'Consider adding scene exceptions or improve naming for: {release}'.format
                     (release=releaseName))
            raise FailedPostProcessingFailedException()

        self.log(logger.DEBUG, u'Parsed info: {result}'.format(result=parse_result))

        segment = []
        if not parse_result.episode_numbers:
            # Get all episode objects from that season
            self.log(logger.DEBUG, 'Detected as season pack: {release}'.format(release=releaseName))
            segment.extend(parse_result.series.get_all_episodes(parse_result.season_number))
        else:
            self.log(logger.DEBUG, u'Detected as single/multi episode: {release}'.format(release=releaseName))
            for episode in parse_result.episode_numbers:
                segment.append(parse_result.series.get_episode(parse_result.season_number, episode))

        if segment:
            self.log(logger.DEBUG, u'Adding this release to failed queue: {release}'.format(release=releaseName))
            cur_failed_queue_item = FailedQueueItem(parse_result.series, segment)
            app.forced_search_queue_scheduler.action.add_item(cur_failed_queue_item)

        return True

    def log(self, level, message):
        """Log to regular logfile and save for return for PP script log."""
        log.log(level, message)
        self._output.append(message)

    @property
    def output(self):
        """Return the concatenated log messages."""
        return '\n'.join(self._output)
