# coding=utf-8
#
# Git: https://github.com/PyMedusa/SickRage.git
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

from collections import namedtuple
from datetime import datetime, timedelta

from six import text_type

from sickbeard.common import Quality
from sickbeard.db import DBConnection

from sickrage.helper.common import try_int


class History(object):
    date_format = '%Y%m%d%H%M%S'

    def __init__(self):
        self.db = DBConnection()

    def clear(self):
        """
        Clear all the history
        """
        self.db.action(
            'DELETE '
            'FROM history '
            'WHERE 1 = 1'
        )

    def get(self, limit=100, action=None):
        """
        :param limit: The maximum number of elements to return
        :param action: The type of action to filter in the history. Either 'downloaded' or 'snatched'. Anything else or
                        no value will return everything (up to ``limit``)
        :return: The last ``limit`` elements of type ``action`` in the history
        """

        # TODO: Make this a generator instead
        # TODO: Split compact and detailed into separate methods
        # TODO: Add a date limit as well
        # TODO: Clean up history.mako

        actions = History._get_actions(action)
        limit = max(try_int(limit), 0)

        common_sql = 'SELECT s.show_name, h.showid, h.season, h.episode, h.quality, e.is_proper, ' \
                     'h.action, h.provider, h.resource, h.date ' \
                     'FROM history h, tv_shows s, tv_episodes e ' \
                     'WHERE h.showid = s.indexer_id ' \
                     'AND h.showid = e.showid AND h.season = e.season AND h.episode = e.episode '
        filter_sql = 'AND action in (' + ','.join(['?'] * len(actions)) + ') '
        order_sql = 'ORDER BY date DESC '

        if actions:
            sql_results = self.db.select(common_sql + filter_sql + order_sql,
                                         actions)
        else:
            sql_results = self.db.select(common_sql + order_sql)

        detailed = []
        compact = dict()

        # TODO: Convert to a defaultdict and compact items as needed
        # TODO: Convert to using operators to combine items
        for row in sql_results:
            row = History.Item(*row)
            if row.index in compact:
                compact[row.index].actions.append(row.cur_action)
            elif not limit or len(compact) < limit:
                compact[row.index] = row.compacted()
            elif not limit or len(detailed) < limit:
                detailed.append(row)

        results = namedtuple('results', ['detailed', 'compact'])
        return results(detailed, compact.values())

    def trim(self, days=30):
        """
        Remove expired elements from history

        :param days: number of days to keep
        """
        date = datetime.today() - timedelta(days)
        self.db.action(
            'DELETE '
            'FROM history '
            'WHERE date < ?',
            [date.strftime(History.date_format)]
        )

    @staticmethod
    def _get_actions(action):
        action = action.lower() if isinstance(action, (str, text_type)) else ''

        result = None
        if action == 'downloaded':
            result = Quality.DOWNLOADED
        elif action == 'snatched':
            result = Quality.SNATCHED

        return result or []

    action_fields = ('action', 'provider', 'resource', 'date', )
    # A specific action from history
    Action = namedtuple('Action', action_fields)
    Action.width = len(action_fields)

    index_fields = ('show_id', 'season', 'episode', 'quality', 'is_proper')
    # An index for an item or compact item from history
    Index = namedtuple('Index', index_fields)
    Index.width = len(index_fields)

    compact_fields = ('show_name', 'index', 'actions', 'is_proper')
    # Related items compacted with a list of actions from history
    CompactItem = namedtuple('CompactItem', compact_fields)

    item_fields = tuple(  # make it a tuple so its immutable
        ['show_name'] + list(index_fields) + list(action_fields)
    )

    class Item(namedtuple('Item', item_fields)):
        # TODO: Allow items to be added to a compact item
        """
        An individual row item from history
        """
        # prevent creation of a __dict__ when subclassing
        # from a class that uses __slots__
        __slots__ = ()

        @property
        def index(self):
            """
            Create a look-up index for the item
            """
            return History.Index(
                self.show_id,
                self.season,
                self.episode,
                self.quality,
                self.is_proper
            )

        @property
        def cur_action(self):
            """
            Create the current action from action_fields
            """
            return History.Action(
                self.action,
                self.provider,
                self.resource,
                self.date,
            )

        def compacted(self):
            """
            Create a CompactItem

            :returns: the current item in compact form
            """
            result = History.CompactItem(
                self.show_name,
                self.index,
                [self.cur_action],  # actions
                self.is_proper,
            )
            return result

        def __add__(self, other):
            """
            Combines two history items with the same index

            :param other: The other item to add
            :returns: a compact item with elements from both items
            :raises AssertionError: if indexes do not match
            """
            # Index comparison and validation is done by _radd_
            return self.compacted() + other

        def __radd__(self, other):
            """
            Adds a history item to a compact item

            :param other: The compact item to append
            :returns: the updated compact item
            :raises AssertionError: if indexes do not match
            """
            if self.index == other.index:
                other.actions.append(self.cur_action)
                return other
            else:
                raise AssertionError('cannot add items with different indexes')
