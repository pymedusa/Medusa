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

    def __init__(self, dir_name, resource, episodes=[]):
        """Initialize the class.

        :param dir_name: Full path to the folder of the failed download
        :param resource: Full name of the file/subfolder that failed
        :param episodes: Optionally passed array of episode objects. When we know for which episodes
            whe're trying to process the resource as failed, we don't need to parse the release name.
            We can just straight away call the FailedQueueItem.
        """
        self.dir_name = dir_name
        self.resource = resource
        self.episodes = episodes

        self._output = []

    def _process_release_name(self):
        """Parse the release name for a show title and episode(s)."""
        release_name = naming.determine_release_name(self.dir_name, self.resource)
        if not release_name:
            self.log(logger.WARNING, 'Warning: unable to find a valid release name.')
            raise FailedPostProcessingFailedException()

        try:
            parse_result = NameParser().parse(release_name, use_cache=False)
        except (InvalidNameException, InvalidShowException):
            self.log(logger.WARNING, 'Not enough information to parse release name into a valid show. '
                     'Consider adding scene exceptions or improve naming for: {release}'.format
                     (release=release_name))
            raise FailedPostProcessingFailedException()

        self.log(logger.DEBUG, 'Parsed info: {result}'.format(result=parse_result))

        segment = []
        if not parse_result.episode_numbers:
            # Get all episode objects from that season
            self.log(logger.DEBUG, 'Detected as season pack: {release}'.format(release=release_name))
            segment.extend(parse_result.series.get_all_episodes(parse_result.season_number))
        else:
            self.log(logger.DEBUG, 'Detected as single/multi episode: {release}'.format(release=release_name))
            for episode in parse_result.episode_numbers:
                segment.append(parse_result.series.get_episode(parse_result.season_number, episode))

        if segment:
            self.log(logger.DEBUG, 'Created segment of episodes [{segment}] from release: {release}'.format(
                segment=','.join(str(ep.episode) for ep in segment),
                release=release_name
            ))

        return segment

    def process(self):
        """
        Do the actual work.

        :return: True
        """
        self.log(logger.INFO, 'Failed download detected: (resource: {nzb}, dir: {dir})'.format(nzb=self.resource, dir=self.dir_name))

        segment = []
        if self.episodes:
            # If we have episodes, we dont need the release name to know we want to fail these episodes.
            self.log(logger.INFO, 'Episodes where found for this failed processor, using those instead of a release name')
            segment = self.episodes
        else:
            segment = self._process_release_name()

        if segment:
            # This will only work with single episodes or season packs.
            cur_failed_queue_item = FailedQueueItem(segment[0].series, segment)
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
