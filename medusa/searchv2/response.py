import logging

from medusa.common import Quality
from medusa.logger.adapters.style import BraceAdapter

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


SINGLE_EP = 1
MULTI_EP = 2
SEASON_PACK = 3
COMPLETE_SERIES = 4


class SearchResult(object):
    """Represents a search result from an indexer."""

    def __init__(self, episodes=None, provider=None):
        # searched episode object
        self.searched_episode = None

        # SearchRequest object
        self.search_request = None

        # list of Episode objects that this result is associated with
        self.episodes = episodes

        # the search provider
        self.provider = provider

        # release show object
        self.show = self.series = None

        # URL to the NZB/torrent file
        self.url = u''

        # used by some providers to store extra info associated with the result
        self.extraInfo = []

        # quality of the release
        self.quality = Quality.UNKNOWN

        # release name
        self.name = u''

        # size of the release (-1 = n/a)
        self.size = -1

        # seeders of the release
        self.seeders = -1

        # leechers of the release
        self.leechers = -1

        # update date
        self.date = None

        # release publish date
        self.pubdate = None

        # release group
        self.release_group = u''

        # version
        self.version = -1

        # hash
        self.hash = None

        # proper_tags
        self.proper_tags = u''

        # manually_searched
        self.manually_searched = False

        # content
        self.content = None

        # Result type like: nzb, nzbdata, torrent
        self.resultType = u''

        # Store the parse result, as it might be useful for other information later on.
        self.parsed_result = None

        # Reference to the search_provider
        self.provider = provider

        # Raw result in a dictionary
        self.item = None

        # Store if the search was started by a forced search.
        self.forced_search = None

        # Search flag for specifying if we want to re-download the already downloaded quality.
        self.download_current_quality = None

        # Search flag for adding or not adding the search result to cache.
        self.add_cache_entry = True

        # Search flag for flagging if this is a same-day-special.
        self.same_day_special = False

        # Keep track if we really want to result.
        self.result_wanted = False

        # The actual parsed season. Stored as an integer.
        self.actual_season = None

        # The actual parsed episode. Stored as an iterable of integers.
        self._actual_episodes = None

        # Some of the searches, expect a max of one episode object, per search result. Then this episode can be used
        # to store a single episode number, as an int.
        self._actual_episode = None

        # Search type. For example MANUAL_SEARCH, FORCED_SEARCH, DAILY_SEARCH, PROPER_SEARCH
        self.search_type = None

        # Explicitly set the results episode packing. Like single episode, multi-ep, season pack, complete series pack.
        self.packaged = None

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
        for extra in self.extraInfo:
            my_string += u' {0}\n'.format(extra)

        my_string += u'Episodes:\n'
        for ep in self.episodes:
            my_string += u' {0}\n'.format(ep)

        my_string += u'Quality: {0}\n'.format(Quality.qualityStrings[self.quality])
        my_string += u'Name: {0}\n'.format(self.name)
        my_string += u'Size: {0}\n'.format(self.size)
        my_string += u'Release Group: {0}\n'.format(self.release_group)

        return my_string

    def file_name(self):
        return u'{0}.{1}'.format(self.episodes[0].pretty_name(), self.resultType)

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
        if self.actual_season and self.actual_episodes and self.series:
            self.episodes = [self.series.get_episode(self.actual_season, ep) for ep in self.actual_episodes]
        return self.episodes

    def finish_search_result(self, provider):
        self.size = provider._get_size(self.item)
        self.pubdate = provider._get_pubdate(self.item)


class NZBSearchResult(SearchResult):
    """Regular NZB result with an URL to the NZB."""

    def __init__(self, episodes, provider=None):
        super(NZBSearchResult, self).__init__(episodes, provider=provider)
        self.resultType = u'nzb'


class NZBDataSearchResult(SearchResult):
    """NZB result where the actual NZB XML data is stored in the extraInfo."""

    def __init__(self, episodes, provider=None):
        super(NZBDataSearchResult, self).__init__(episodes, provider=provider)
        self.resultType = u'nzbdata'


class TorrentSearchResult(SearchResult):
    """Torrent result with an URL to the torrent."""

    def __init__(self, episodes, provider=None):
        super(TorrentSearchResult, self).__init__(episodes, provider=provider)
        self.resultType = u'torrent'
