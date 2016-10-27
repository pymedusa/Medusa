# coding=utf-8
# Author: p0psicles
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

"""Contains included user interface for TVmaze show selection."""

import logging
import warnings
from indexer_exceptions import IndexerUserAbort


__author__ = 'p0psicles'
__version__ = '1.0'


def log():
    """Get logging object."""
    return logging.getLogger(__name__)


class BaseUI(object):
    """Default non-interactive UI, which auto-selects first results."""

    def __init__(self, config, enable_logging=None):
        """Init object."""
        self.config = config
        if enable_logging is not None:
            warnings.warn("the UI's log parameter is deprecated, instead use\n"
                          "use import logging; logging.getLogger('ui').info('blah')\n"
                          "The self.log attribute will be removed in the next version")
            self.log = logging.getLogger(__name__)

    def select_series(self, all_series):
        """Return all series."""
        return all_series[0]


class ConsoleUI(BaseUI):
    """Interactively allows the user to select a show from a console based UI."""

    def _display_series(self, all_series, limit=6):
        """Helper function, lists series with corresponding ID."""
        if limit is not None:
            toshow = all_series[:limit]
        else:
            toshow = all_series

        print 'Show Search Results:'
        for i, cshow in enumerate(toshow):
            i_show = i + 1  # Start at more human readable number 1 (not 0)
            log().debug('Showing all_series[%s], series %s)', i_show, all_series[i]['seriesname'])
            if i == 0:
                extra = ' (default)'
            else:
                extra = ''

            # TODO: Change into something more generic.
            print '%s -> %s [%s] # http://thetvdb.com/?tab=series&id=%s&lid=%s%s' % (
                i_show,
                cshow['seriesname'].encode('UTF-8', 'ignore'),
                cshow['language'].encode('UTF-8', 'ignore'),
                str(cshow['id']),
                cshow['lid'],
                extra
            )

    def select_series(self, all_series):
        """Select and return shows, based on users input."""
        self._display_series(all_series)

        if len(all_series) == 1:
            # Single result, return it!
            print 'Automatically selecting only result'
            return all_series[0]

        if self.config['select_first'] is True:
            print 'Automatically returning first search result'
            return all_series[0]

        while True:  # return breaks this loop
            try:
                print "Enter choice (first number, return for default, 'all', ? for help):"
                ans = raw_input()
            except KeyboardInterrupt:
                raise IndexerUserAbort('User aborted (^c keyboard interupt)')
            except EOFError:
                raise IndexerUserAbort('User aborted (EOF received)')

            log().debug('Got choice of: %s', ans)
            try:
                selected_id = int(ans) - 1  # The human entered 1 as first result, not zero
            except ValueError:  # Input was not number
                if len(ans.strip()) == 0:
                    # Default option
                    log().debug('Default option, returning first series')
                    return all_series[0]
                if ans == 'q':
                    log().debug('Got quit command (q)')
                    raise IndexerUserAbort("User aborted ('q' quit command)")
                elif ans == '?':
                    print '## Help'
                    print '# Enter the number that corresponds to the correct show.'
                    print '# a - display all results'
                    print '# all - display all results'
                    print '# ? - this help'
                    print '# q - abort tvnamer'
                    print '# Press return with no input to select first result'
                elif ans.lower() in ['a', 'all']:
                    self._display_series(all_series, limit=None)
                else:
                    log().debug('Unknown keypress %s', ans)
            else:
                log().debug('Trying to return ID: %d', selected_id)
                try:
                    return all_series[selected_id]
                except IndexError:
                    log().debug('Invalid show number entered!')
                    print 'Invalid number (%s) selected!'
                    self._display_series(all_series)
