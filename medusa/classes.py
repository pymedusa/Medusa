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
from __future__ import unicode_literals

import logging
from datetime import datetime

from dateutil import parser

from medusa import app, ws
from medusa.common import (
    MULTI_EP_RESULT,
    Quality,
    SEASON_RESULT,
)
from medusa.logger.adapters.style import BraceAdapter
from medusa.search import SearchType

from six import itervalues

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class SearchResult(object):
    """Represents a search result from a provider."""

    def __init__(self, provider, series, item=None, cache=None):
        # the search provider
        self.provider = provider
        # release series object
        self.series = series
        # Raw result in a dictionary
        self.item = item
        # Cached search result
        self.cache = cache

        # list of Episode objects that this result is associated with
        self.episodes = None
        # URL to the NZB/torrent file
        self.url = ''
        # used by some providers to store extra info associated with the result
        self.extra_info = []
        # quality of the release
        self.quality = Quality.UNKNOWN
        # release name
        self.name = ''
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
        self.release_group = ''
        # version
        self.version = -1
        # hash
        self.hash = None
        # proper_tags
        self.proper_tags = []
        # manually_searched
        self._manually_searched = False
        # content
        self.content = None
        # Result type like: nzb, nzbdata, torrent
        self.result_type = ''
        # Store the parse result, as it might be useful for other information later on.
        self.parsed_result = None
        # Store the epsiode number we use internally.
        # This can be the single episode number, MULTI_EP_RESULT or SEASON_RESULT
        self.episode_number = None
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
        # Some of the searches, expect a max of one episode object, per search result.
        # Then this episode can be used to store a single episode number, as an int.
        self._actual_episode = None
        # Search type. Use the medusa.search.SearchType enum, as value.
        # For example SearchType.MANUAL_SEARCH, SearchType.FORCED_SEARCH,
        # SearchType.DAILY_SEARCH, SearchType.PROPER_SEARCH
        self.search_type = None

        if item is not None:
            self.update_search_result()
        elif cache is not None:
            self.update_from_db()

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

    @property
    def identifier(self):
        return self.provider._get_identifier(self)

    @property
    def show(self):
        log.warning(
            'Please use SearchResult.series and not show. Show has been deprecated.',
            DeprecationWarning,
        )
        return self.series

    @show.setter
    def show(self, value):
        log.warning(
            'Please use SearchResult.series and not show. Show has been deprecated.',
            DeprecationWarning,
        )
        self.series = value

    @property
    def manually_searched(self):
        """
        Shortcut to check if the result was retrieved using a manual search.

        Preferably this property is not used, and the self.search_type property is directly evaluated.
        """
        return self._manually_searched or self.search_type == SearchType.MANUAL_SEARCH

    @manually_searched.setter
    def manually_searched(self, value):
        """
        Shortcut to check if the result was retrieved using a manual search.

        Preferably this property is not used, and the self.search_type property is directly evaluated.
        """
        self._manually_searched = value

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

    def to_json(self):
        """Return JSON representation."""
        return {
            'identifier': self.identifier,
            'release': self.name,
            'season': self.actual_season,
            'episodes': self.actual_episodes,
            'seasonPack': len(self.actual_episodes) == 0 or len(self.actual_episodes) > 1,
            'indexer': self.series.indexer,
            'seriesId': self.series.series_id,
            'showSlug': self.series.identifier.slug,
            'url': self.url,
            'time': datetime.now().replace(microsecond=0).isoformat(),
            'quality': self.quality,
            'releaseGroup': self.release_group,
            'dateAdded': datetime.now().replace(microsecond=0).isoformat(),
            'version': self.version,
            'seeders': self.seeders,
            'size': self.size,
            'leechers': self.leechers,
            'pubdate': self.pubdate.replace(microsecond=0).isoformat() if self.pubdate else None,
            'provider': {
                'id': self.provider.get_id(),
                'name': self.provider.name,
                'imageName': self.provider.image_name()
            }
        }

    def file_name(self):
        return u'{0}.{1}'.format(self.episodes[0].pretty_name(), self.result_type)

    def add_result_to_cache(self, cache):
        """Cache the item if needed."""
        if self.add_cache_entry:
            # FIXME: Added repr parsing, as that prevents the logger from throwing an exception.
            # This can happen when there are unicode decoded chars in the release name.
            log.debug('Adding item from search to cache: {release_name!r}', release_name=self.name)

            # Push an update to any open Web UIs through the WebSocket
            ws.Message('addManualSearchResult', self.to_json()).push()

            return cache.add_cache_entry(self, parsed_result=self.parsed_result)

    def _create_episode_objects(self):
        """Use this result to create an episode segment out of it."""
        if self.actual_season is not None and self.series:
            if self.actual_episodes:
                self.episodes = [self.series.get_episode(self.actual_season, ep) for ep in self.actual_episodes]
                if len(self.actual_episodes) == 1:
                    self.episode_number = self.actual_episodes[0]
                else:
                    self.episode_number = MULTI_EP_RESULT
            else:
                self.episodes = self.series.get_all_episodes(self.actual_season)
                self.actual_episodes = [ep.episode for ep in self.episodes]
                self.episode_number = SEASON_RESULT

        return self.episodes

    def update_search_result(self):
        self._create_episode_objects()

        self.name, self.url = self.provider._get_title_and_url(self.item)
        self.seeders, self.leechers = self.provider._get_result_info(self.item)
        self.size = self.provider._get_size(self.item)
        self.pubdate = self.provider._get_pubdate(self.item)
        self.date = datetime.today()

    def _episodes_from_cache(self):
        series_obj = self.series
        cached_data = self.cache

        actual_season = int(cached_data['season'])
        self.actual_season = actual_season

        sql_episodes = cached_data['episodes'].strip('|')
        # Season result
        if not sql_episodes:
            ep_objs = series_obj.get_all_episodes(actual_season)
            self.actual_episodes = [ep.episode for ep in ep_objs]
            self.episode_number = SEASON_RESULT

        # Multi or single episode result
        else:
            actual_episodes = [int(ep) for ep in sql_episodes.split('|')]
            ep_objs = [series_obj.get_episode(actual_season, ep) for ep in actual_episodes]

            self.actual_episodes = actual_episodes
            if len(actual_episodes) == 1:
                self.episode_number = actual_episodes[0]
            else:
                self.episode_number = MULTI_EP_RESULT

        return ep_objs

    def update_from_db(self):
        """Update local attributes from the cached result, recovered from db."""
        cached_result = self.cache
        self.episodes = self._episodes_from_cache()
        self.url = cached_result['url']
        self.quality = int(cached_result['quality'])
        self.name = cached_result['name']
        self.size = int(cached_result['size'])
        self.seeders = int(cached_result['seeders'])
        self.leechers = int(cached_result['leechers'])
        self.release_group = cached_result['release_group']
        self.version = int(cached_result['version'])
        self.pubdate = parser.parse(cached_result['pubdate']) if cached_result['pubdate'] else None
        self.proper_tags = cached_result['proper_tags'].split('|') \
            if cached_result['proper_tags'] else []
        self.date = datetime.today()

    def __eq__(self, other):
        return self.identifier == other.identifier


class NZBSearchResult(SearchResult):
    """Regular NZB result with an URL to the NZB."""

    def __init__(self, provider, series, item=None, cache=None):
        super(NZBSearchResult, self).__init__(provider, series=series, item=item, cache=cache)
        self.result_type = u'nzb'


class NZBDataSearchResult(SearchResult):
    """NZB result where the actual NZB XML data is stored in the extra_info."""

    def __init__(self, provider, series, item=None, cache=None):
        super(NZBDataSearchResult, self).__init__(provider, series=series, item=item, cache=cache)
        self.result_type = u'nzbdata'


class TorrentSearchResult(SearchResult):
    """Torrent result with an URL to the torrent."""

    def __init__(self, provider, series, item=None, cache=None):
        super(TorrentSearchResult, self).__init__(provider, series=series, item=item, cache=cache)
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
        from medusa.helper.common import dateFormat

        search_results = []
        series_names = []

        # get all available shows
        if all_series:
            if 'searchterm' in self.config:
                search_term = self.config['searchterm']
                # try to pick a show that's in my show list
                for cur_show in all_series:
                    if [result for result in search_results if str(cur_show['id']) == str(result['id'])]:
                        continue

                    if 'seriesname' in cur_show:
                        series_names.append(cur_show['seriesname'])
                    if 'aliases' in cur_show:
                        series_names.extend(cur_show['aliases'].split('|'))

                    if search_term.isdigit():
                        series_names.append(search_term)

                    for name in series_names:
                        if search_term.lower() in name.lower():
                            if 'firstaired' not in cur_show:
                                default_date = parser.parse('1900-01-01').date()
                                cur_show['firstaired'] = default_date.strftime(dateFormat)

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
        return sorted(list(itervalues(self._errors)), key=lambda error: error.timestamp, reverse=True)


# The warning viewer: TODO: Change CamelCase to snake_case
WarningViewer = Viewer()

# The error viewer: TODO: Change CamelCase to snake_case
ErrorViewer = Viewer()
