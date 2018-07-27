# coding=utf-8
from __future__ import unicode_literals

import logging

from medusa.common import Quality
from medusa.logger.adapters.style import BraceAdapter

from six import string_types

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class SearchResult(object):
    """Represents a search result."""

    def __init__(self, episodes=None, provider=None):
        # list of Episode objects that this result is associated with
        self.episodes = episodes
        # the search provider
        self.provider = provider
        # release series object
        self._series = None
        # URL to the NZB/torrent file
        self.url = ''
        # quality of the release
        self._quality = Quality.UNKNOWN
        # release name
        self.name = ''
        # size of the release (-1 = n/a)
        self._size = -1
        # release group
        self.release_group = ''
        # version
        self._version = -1
        # proper_tags
        self._proper_tags = []
        # seeders of the release
        self._seeders = -1
        # leechers of the release
        self._leechers = -1
        # update date
        self.date = None
        # release publish date
        self.pubdate = None
        # hash
        self.hash = None
        # used by some providers to store extra info associated with the result
        self.extra_info = []
        # manually_searched
        self.manually_searched = False
        # content
        self.content = None
        # Result type like: nzb, nzbdata, torrent
        self.result_type = ''
        # Store the parse result, as it might be useful for other information later on.
        self.parsed_result = None
        # Raw result in a dictionary
        self.item = None
        # Store if the search was started by a forced search.
        self.forced_search = False
        # Search flag for specifying if we want to re-download the already downloaded quality.
        self.download_current_quality = False
        # Search flag for adding or not adding the search result to cache.
        self.add_cache_entry = True
        # Search flag for flagging if this is a same-day-special.
        self.same_day_special = False
        # Keep track if we really want to result.
        self.result_wanted = False
        # The actual parsed season. Stored as an integer.
        self._actual_season = None
        # The actual parsed episode. Stored as an iterable of integers.
        self._actual_episodes = []
        # Some of the searches, expect a max of one episode object, per search result. Then this episode can be used
        # to store a single episode number, as an int.
        self._actual_episode = None
        # Search type. For example MANUAL_SEARCH, FORCED_SEARCH, DAILY_SEARCH, PROPER_SEARCH
        self.search_type = None

    @property
    def series(self):
        return self._series or self.episodes[0].series

    @series.setter
    def series(self, value):
        self._series = value

    @property
    def quality(self):
        return self._quality

    @quality.setter
    def quality(self, value):
        self._quality = int(value)

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, value):
        self._size = int(value)

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, value):
        self._version = int(value)

    @property
    def proper_tags(self):
        return self._proper_tags

    @proper_tags.setter
    def proper_tags(self, value):
        if isinstance(string_types, value):
            self._proper_tags = value.split('|')
        else:
            self._proper_tags = value

    @property
    def actual_season(self):
        return self._actual_season or self.episodes[0].season

    @actual_season.setter
    def actual_season(self, value):
        self._actual_season = int(value)

    @property
    def actual_episode(self):
        return self._actual_episode

    @actual_episode.setter
    def actual_episode(self, value):
        self._actual_episode = value

    @property
    def actual_episodes(self):
        return self._actual_episodes

    @actual_episodes.setter
    def actual_episodes(self, value):
        self._actual_episodes = value
        if len(value) == 1:
            self._actual_episode = value[0]

    def __str__(self):

        if self.provider is None:
            return u'Invalid provider, unable to print self'

        my_string = u'{0} @ {1}\n'.format(self.provider.name, self.url)
        my_string += u'Extra Info:\n'
        for extra in self.extra_info:
            my_string += u' {0}\n'.format(extra)

        my_string += u'Episodes:\n'
        for ep in self.episodes:
            my_string += u' {0}\n'.format(ep)

        my_string += u'Quality: {0}\n'.format(Quality.qualityStrings[self.quality])
        my_string += u'Name: {0}\n'.format(self.name)
        my_string += u'Size: {0}\n'.format(self.size)
        my_string += u'Release Group: {0}\n'.format(self.release_group)

        return my_string

    # Python 2 compatibility
    __unicode__ = __str__

    def __repr__(self):
        if not self.provider:
            result = '{0}'.format(self.name)
        else:
            result = '{0} from {1}'.format(self.name, self.provider.name)

        return '<{0}: {1}>'.format(type(self).__name__, result)

    def file_name(self):
        return u'{0}.{1}'.format(self.episodes[0].pretty_name(), self.result_type)

    def add_result_to_cache(self, cache):
        """Cache the item if needed."""
        if self.add_cache_entry:
            # FIXME: Added repr parsing, as that prevents the logger from throwing an exception.
            # This can happen when there are unicode decoded chars in the release name.
            log.debug('Adding item from search to cache: {release_name!r}', release_name=self.name)
            return cache.add_cache_entry(self.name, self.url, self.seeders,
                                         self.leechers, self.size, self.pubdate, parsed_result=self.parsed_result)
        return None

    def create_episode_object(self):
        """Use this result to create an episode segment out of it."""
        if self.actual_season and self.series:
            if self.actual_episodes:
                self.episodes = [self.series.get_episode(self.actual_season, ep) for ep in self.actual_episodes]
            else:
                self.episodes = self.series.get_all_episodes(self.actual_season)
        return self.episodes

    def finish_search_result(self, provider):
        self.size = provider._get_size(self.item)
        self.pubdate = provider._get_pubdate(self.item)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


class NZBSearchResult(SearchResult):
    """Regular NZB result with an URL to the NZB."""

    def __init__(self, episodes, provider=None):
        super(NZBSearchResult, self).__init__(episodes, provider=provider)
        self.result_type = u'nzb'


class NZBDataSearchResult(SearchResult):
    """NZB result where the actual NZB XML data is stored in the extra_info."""

    def __init__(self, episodes, provider=None):
        super(NZBDataSearchResult, self).__init__(episodes, provider=provider)
        self.result_type = u'nzbdata'


class TorrentSearchResult(SearchResult):
    """Torrent result with an URL to the torrent."""

    def __init__(self, episodes, provider=None):
        super(TorrentSearchResult, self).__init__(episodes, provider=provider)
        self.result_type = u'torrent'

    @property
    def seeders(self):
        return self._seeders

    @seeders.setter
    def seeders(self, value):
        self._seeders = int(value)

    @property
    def leechers(self):
        return self._leechers

    @leechers.setter
    def leechers(self, value):
        self._leechers = int(value)
