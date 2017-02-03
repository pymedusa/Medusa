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

import logging

from dateutil import parser

from six.moves.urllib.request import FancyURLopener

from . import app
from .common import Quality, USER_AGENT
from .indexers.indexer_api import indexerApi


logger = logging.getLogger(__name__)


class ApplicationURLopener(FancyURLopener, object):
    version = USER_AGENT


class SearchResult(object):
    """Represents a search result from an indexer."""

    def __init__(self, episodes):
        self.provider = None

        # release show object
        self.show = None

        # URL to the NZB/torrent file
        self.url = u''

        # used by some providers to store extra info associated with the result
        self.extraInfo = []

        # list of Episode objects that this result is associated with
        self.episodes = episodes

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

        self.resultType = u''

    def __str__(self):

        if self.provider is None:
            return u'Invalid provider, unable to print self'

        my_string = u'{} @ {}\n'.format(self.provider.name, self.url)
        my_string += u'Extra Info:\n'
        for extra in self.extraInfo:
            my_string += u' {}\n'.format(extra)

        my_string += u'Episodes:\n'
        for ep in self.episodes:
            my_string += u' {}\n'.format(ep)

        my_string += u'Quality: {}\n'.format(Quality.qualityStrings[self.quality])
        my_string += u'Name: {}\n'.format(self.name)
        my_string += u'Size: {}\n'.format(self.size)
        my_string += u'Release Group: {}\n'.format(self.release_group)

        return my_string

    def file_name(self):
        return u'{}.{}'.format(self.episodes[0].pretty_name(), self.resultType)


class NZBSearchResult(SearchResult):
    """Regular NZB result with an URL to the NZB."""

    def __init__(self, episodes):
        super(NZBSearchResult, self).__init__(episodes)
        self.resultType = u'nzb'


class NZBDataSearchResult(SearchResult):
    """NZB result where the actual NZB XML data is stored in the extraInfo."""

    def __init__(self, episodes):
        super(NZBDataSearchResult, self).__init__(episodes)
        self.resultType = u'nzbdata'


class TorrentSearchResult(SearchResult):
    """Torrent result with an URL to the torrent."""

    def __init__(self, episodes):
        super(TorrentSearchResult, self).__init__(episodes)
        self.resultType = u'torrent'


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


class Proper(object):
    def __init__(self, name, url, date, show, seeders, leechers, size, pubdate, proper_tags):
        self.name = name
        self.url = url
        self.date = date
        self.provider = None
        self.quality = Quality.UNKNOWN
        self.release_group = None
        self.version = -1
        self.seeders = seeders
        self.leechers = leechers
        self.size = size
        self.pubdate = pubdate
        self.proper_tags = proper_tags
        self.hash = None
        self.show = show
        self.indexer = None
        self.indexerid = -1
        self.season = -1
        self.episode = -1
        self.scene_season = -1
        self.scene_episode = -1

    def __str__(self):
        return u'{date} {name} {season}x{episode} of {series_id} from {indexer}'.format(
            date=self.date, name=self.name, season=self.season, episode=self.episode,
            series_id=self.indexerid, indexer=indexerApi(self.indexer).name)


class Viewer(object):
    """Keep the Errors to be displayed in the UI."""

    def __init__(self):
        """Default constructor."""
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
    logger.debug(u'Unable to import _urlopener, not using user_agent for urllib')


# The warning viewer: TODO: Change CamelCase to snake_case
WarningViewer = Viewer()

# The error viewer: TODO: Change CamelCase to snake_case
ErrorViewer = Viewer()
