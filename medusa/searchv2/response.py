import logging

from medusa.common import SINGLE_EP_RESULT, MULTI_EP_RESULT, SEASON_RESULT, Quality
from medusa.logger.adapters.style import BraceAdapter
from . import BACKLOG_SEARCH, DAILY_SEARCH, FORCED_SEARCH, PROPER_SEARCH, MANUAL_SEARCH

from filter import FilterVerifyPackage

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
        self.episodes = episodes or []

        # the search provider
        self.provider = provider

        # release show object
        self.show = None

        # self.show is deprecated.
        self.series = None

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

        # Search mode, like eponly of sponly. Determines if we need to run an episode, season search or fallback to one
        # or another.
        self.search_mode = None

        # Explicitly set the results episode packing. Like single episode, multi-ep, season pack, complete series pack.
        self.packaged = None

    def __setattr__(self, key, value):
        if key in ('download_current_quality', 'search_type'):
            log.warning(
                'Attribute {attr} is deprecated, please use SearchResult.search_request.options.{attr} in stead.',
                {'attr': key}
            )

        if key in ('forced_search', 'manually_searched'):
            log.warning(
                "You shouldn't use {attr} any more, this has been replaced with SearchResult.options.search_type. \n"
                "You can use the constants BACKLOG_SEARCH, DAILY_SEARCH, MANUAL_SEARCH, .. found in searchv2.__init__ for that.",
                {'attr': key}
            )
        super(SearchResult, self).__setattr__(key, value)

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

    def parse_provider(self):
        self.size = self.provider._get_size(self.item)
        self.pubdate = self.provider._get_pubdate(self.item)
        (self.name, self.url) = self.provider._get_title_and_url(self.item)
        (self.seeders, self.leechers) = self.provider._get_result_info(self.item)

    def map_parsed_results(self):
        self.series = self.parsed_result.series
        self.quality = self.parsed_result.quality
        self.release_group = self.parsed_result.release_group
        self.version = self.parsed_result.version
        self.actual_season = self.parsed_result.season_number
        self.actual_episodes = self.parsed_result.episode_numbers

    def configure_filters_backlog(self):
        self.search_request.options.backlog_search_filters = [FilterVerifyPackage]

    def filter_results(self, results):
        """
        Run a list of filters, on the search results.

        This will drop results early, reducing the amount of results we need to parse.
        """
        filters = None
        if self.search_request.options.search_type == BACKLOG_SEARCH:
            self.configure_filters_backlog()
            filters = self.search_request.options.backlog_search_filters
        elif self.search_request.options.search_type == DAILY_SEARCH:
            filters = self.search_request.options.daily_search_filters
        elif self.search_request.options.search_type == FORCED_SEARCH:
            filters = self.search_request.options.forced_search_filters
        elif self.search_request.options.search_type == PROPER_SEARCH:
            filters = self.search_request.options.proper_search_filters

        if not filters:
            log.info('No filters enabled for the search {search_type}.',
                     {'search_type': self.search_request.options.search_type})
            return

        for filter_result in filters:
            # If the result has been filtered, we do need to run any other.
            if not filter_result(self, results).filter():
                return False
            return True

    def set_package(self):
        if len(self.episodes) == 1:
            # single ep
            self.packaged = SINGLE_EP_RESULT
            log.debug('Found single episode result {0} at {1}', self.name, self.url)

        elif len(self.episodes) > 1:
            # multip ep
            self.packaged = MULTI_EP_RESULT
            log.debug('Found multi-episode ({0}) result {1} at {2}',
                      ', '.join(map(str, self.parsed_result.episode_numbers)),
                      self.name,
                      self.url)

        elif len(self.episodes) == 0:
            # season pack
            self.packaged = SEASON_RESULT
            log.debug('Found season pack result {0} at {1}', self.name, self.url)


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
