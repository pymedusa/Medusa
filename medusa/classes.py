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
"""Collection of generic used classes."""
import logging

from dateutil import parser

from medusa import app
from medusa.common import Quality, USER_AGENT
from medusa.logger.adapters.style import BraceAdapter

from six.moves.urllib.request import FancyURLopener

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class ApplicationURLopener(FancyURLopener, object):
    version = USER_AGENT


class SearchResult(object):
    """Represents a search result from an indexer."""

    def __init__(self, episodes=None, provider=None):
        # list of Episode objects that this result is associated with
        self.episodes = episodes

        # the search provider
        self.provider = provider

        # release show object
        self.show = None

        # URL to the NZB/torrent file
        self.url = u''

        # used by some providers to store extra info associated with the result
        self.extra_info = []

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
        self.result_type = u''

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
        if self.actual_season and self.actual_episodes and self.show:
            self.episodes = [self.show.get_episode(self.actual_season, ep) for ep in self.actual_episodes]
        return self.episodes

    def finish_search_result(self, provider):
        self.size = provider._get_size(self.item)
        self.pubdate = provider._get_pubdate(self.item)


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


class AllShowsListUI(object):  # pylint: disable=too-few-public-methods
    """This class is for indexer api.

    Instead of prompting with a UI to pick the desired result out of a
    list of shows it tries to be smart about it based on what shows
    are in the application.
    """

    def __init__(self, config, log=None):
        self.config = config
        self.log = log

    def select_series(self, all_series):
        from .helper.common import dateTimeFormat

        search_results = []
        series_names = []

        # get all available shows
        if all_series:
            if 'searchterm' in self.config:
                search_term = self.config['searchterm']
                # try to pick a show that's in my show list
                for cur_show in all_series:
                    if cur_show in search_results:
                        continue

                    if 'seriesname' in cur_show:
                        series_names.append(cur_show['seriesname'])
                    if 'aliasnames' in cur_show:
                        series_names.extend(cur_show['aliasnames'].split('|'))

                    for name in series_names:
                        if search_term.lower() in name.lower():
                            if 'firstaired' not in cur_show:
                                default_date = parser.parse('1900-01-01').date()
                                cur_show['firstaired'] = default_date.strftime(dateTimeFormat)

                            if cur_show not in search_results:
                                search_results += [cur_show]

        return search_results


class ShowListUI(object):  # pylint: disable=too-few-public-methods
    """This class is for tvdb-api.

    Instead of prompting with a UI to pick the desired result out of a
    list of shows it tries to be smart about it based on what shows
    are in the application.
    """

    def __init__(self, config, log=None):
        self.config = config
        self.log = log

    @staticmethod
    def select_series(all_series):
        try:
            # try to pick a show that's in my show list
            show_id_list = [int(x.indexerid) for x in app.showList]
            for cur_show in all_series:
                if int(cur_show['id']) in show_id_list:
                    return cur_show
        except Exception:
            pass

        # if nothing matches then return first result
        return all_series[0]


class Viewer(object):
    """Keep the Errors to be displayed in the UI."""

    def __init__(self):
        """Initialize class with the default constructor."""
        self._errors = dict()

    def add(self, logline):
        """Add the logline to the collection.

        :param logline:
        :type logline: medusa.logger.LogLine
        """
        self._errors[logline.key] = logline

    def remove(self, logline):
        """Remove the logline from the collection.

        :param logline:
        :type logline: medusa.logger.LogLine
        """
        if logline.key in self._errors:
            del self._errors[logline.key]

    def clear(self):
        """Clear the logline collection."""
        self._errors.clear()

    @property
    def errors(self):
        """Return the logline values sorted in descending order.

        :return:
        :rtype: list of medusa.logger.LogLine
        """
        return sorted(self._errors.values(), key=lambda error: error.timestamp, reverse=True)


try:
    import urllib
    urllib._urlopener = ApplicationURLopener()
except ImportError:
    log.debug(u'Unable to import _urlopener, not using user_agent for urllib')


# The warning viewer: TODO: Change CamelCase to snake_case
WarningViewer = Viewer()

# The error viewer: TODO: Change CamelCase to snake_case
ErrorViewer = Viewer()
