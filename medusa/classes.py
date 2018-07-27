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

from medusa import app
from medusa.logger.adapters.style import BraceAdapter

from six import itervalues

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


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
