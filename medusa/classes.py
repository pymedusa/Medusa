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

from dateutil import parser

from medusa import app, db
from medusa.common import statusStrings, Quality, UNSET, WANTED
from medusa.helper.common import episode_num
from medusa.logger.adapters.style import BraceAdapter
from medusa.search import SearchType

from six import itervalues

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class SearchResult(object):
    """Represents a search result from a provider."""

    def __init__(self, episodes=None, provider=None):
        # list of Episode objects that this result is associated with
        self.episodes = episodes

        # the search provider
        self.provider = provider

        # release series object
        self.series = None

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
        self.proper_tags = ''

        # manually_searched
        self._manually_searched = False

        # content
        self.content = None

        # Result type like: nzb, nzbdata, torrent
        self.result_type = ''

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

        # Search type. Use the medusa.search.SearchType enum, as value.
        # For example SearchType.MANUAL_SEARCH, SearchType.FORCED_SEARCH, SearchType.DAILY_SEARCH, SearchType.PROPER_SEARCH
        self.search_type = None

        # # Assign a score for the amount of preferred words there are in the release name
        self._preferred_words_score = None

    @property
    def preferred_words_score(self):
        """Calculate a score based on the amount of preferred words in release name."""
        if not app.PREFERRED_WORDS:
            return 0

        preferred_words = [word.lower() for word in app.PREFERRED_WORDS]
        self._preferred_words_score = round((len([word for word in preferred_words if word in self.name.lower()]) / float(len(preferred_words))) * 100)
        return self._preferred_words_score

    @staticmethod
    def __qualities_to_string(qualities=None):
        return ', '.join([Quality.qualityStrings[quality] for quality in qualities or []
                          if quality and quality in Quality.qualityStrings]) or 'None'

    def want_episode(self, season, episode, quality):
        """Whether or not the episode with the specified quality is wanted.

        :param season:
        :type season: int
        :param episode:
        :type episode: int
        :param quality:
        :type quality: int

        :return:
        :rtype: bool
        """
        # if the quality isn't one we want under any circumstances then just say no
        allowed_qualities, preferred_qualities = self.series.current_qualities
        log.debug(
            u'{id}: Allowed, Preferred = [ {allowed} ] [ {preferred} ] Found = [ {found} ]', {
                'id': self.series.series_id,
                'allowed': self.__qualities_to_string(allowed_qualities),
                'preferred': self.__qualities_to_string(preferred_qualities),
                'found': self.__qualities_to_string([quality]),
            }
        )

        if not Quality.wanted_quality(quality, allowed_qualities, preferred_qualities):
            log.debug(
                u"{id}: Ignoring found result for '{show}' {ep} with unwanted quality '{quality}'", {
                    'id': self.series.series_id,
                    'show': self.series.name,
                    'ep': episode_num(season, episode),
                    'quality': Quality.qualityStrings[quality],
                }
            )
            return False

        main_db_con = db.DBConnection()

        sql_results = main_db_con.select(
            'SELECT '
            '  status, quality, '
            '  manually_searched, preferred_words_score '
            'FROM '
            '  tv_episodes '
            'WHERE '
            '  indexer = ? '
            '  AND showid = ? '
            '  AND season = ? '
            '  AND episode = ?', [self.series.indexer, self.series.series_id, season, episode])

        if not sql_results or not len(sql_results):
            log.debug(
                u'{id}: Unable to find a matching episode in database.'
                u' Ignoring found result for {show} {ep} with quality {quality}', {
                    'id': self.series.series_id,
                    'show': self.series.name,
                    'ep': episode_num(season, episode),
                    'quality': Quality.qualityStrings[quality],
                }
            )
            return False

        cur_status, cur_quality, preferred_words_score = (
            int(sql_results[0]['status'] or UNSET),
            int(sql_results[0]['quality'] or Quality.NA),
            int(sql_results[0]['preferred_words_score'] or 0)
        )

        ep_status_text = statusStrings[cur_status]
        manually_searched = sql_results[0]['manually_searched']

        # if it's one of these then we want it as long as it's in our allowed initial qualities
        if cur_status == WANTED:
            should_replace, reason = (
                True, u"Current status is 'WANTED'. Accepting result with quality '{new_quality}'".format(
                    new_quality=Quality.qualityStrings[quality]
                )
            )
        else:
            upgrade_preferred_words = all([self.series.upgrade_preferred_words,
                                           self.preferred_words_score,
                                           self.preferred_words_score < self.series.preferred_words_score])
            should_replace, reason = Quality.should_replace(cur_status, cur_quality, quality, allowed_qualities,
                                                            preferred_qualities, self.download_current_quality,
                                                            self.forced_search, manually_searched, self.search_type,
                                                            upgrade_preferred_words=upgrade_preferred_words)

        log.debug(
            u"{id}: '{show}' {ep} status is: '{status}'."
            u" {action} result with quality '{new_quality}'."
            u' Reason: {reason}', {
                'id': self.series.series_id,
                'show': self.name,
                'ep': episode_num(season, episode),
                'status': ep_status_text,
                'action': 'Accepting' if should_replace else 'Ignoring',
                'new_quality': Quality.qualityStrings[quality],
                'reason': reason,
            }
        )
        return should_replace

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
        if self.actual_season is not None and self.series:
            if self.actual_episodes:
                self.episodes = [self.series.get_episode(self.actual_season, ep) for ep in self.actual_episodes]
            else:
                self.episodes = self.series.get_all_episodes(self.actual_season)
        return self.episodes

    def finish_search_result(self, provider):
        self.size = provider._get_size(self.item)
        self.pubdate = provider._get_pubdate(self.item)

    def update_from_db(self, show, episodes, cached_result):
        """Update local attributes from the cached result, recovered from db."""
        self.series = show
        self.episodes = episodes
        self.url = cached_result['url']
        self.quality = int(cached_result['quality'])
        self.name = cached_result['name']
        self.size = int(cached_result['size'])
        self.seeders = int(cached_result['seeders'])
        self.leechers = int(cached_result['leechers'])
        self.release_group = cached_result['release_group']
        self.version = int(cached_result['version'])
        self.proper_tags = cached_result['proper_tags'].split('|') \
            if cached_result['proper_tags'] else ''

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
