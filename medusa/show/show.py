# coding=utf-8
# This file is part of Medusa.
#

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

from __future__ import unicode_literals

import logging
from builtins import object
from datetime import date

from medusa import app
from medusa.common import (
    ARCHIVED,
    DOWNLOADED,
    SKIPPED,
    SNATCHED,
    SNATCHED_BEST,
    SNATCHED_PROPER,
    WANTED,
)
from medusa.db import DBConnection
from medusa.helper.exceptions import (
    CantRefreshShowException,
    CantRemoveShowException,
    MultipleShowObjectsException,
    ex,
)
from medusa.logger.adapters.style import BraceAdapter


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Show(object):
    def __init__(self):
        pass

    @staticmethod
    def delete(indexer_id, series_id, remove_files=False):
        """
        Try to delete a show.

        :param indexer_id: The unique id of the indexer, used to add the show.
        :param series_id: The unique id of the series.
        :param remove_files: ``True`` to remove the files associated with the show, ``False`` otherwise
        :return: A tuple containing:
         - an error message if the show could not be deleted, ``None`` otherwise
         - the show object that was deleted, if it exists, ``None`` otherwise
        """
        error, show = Show._validate_indexer_id(indexer_id, series_id)

        if error is not None:
            return error, show

        if show:
            try:
                app.show_queue_scheduler.action.removeShow(show, bool(remove_files))
            except CantRemoveShowException as exception:
                return ex(exception), show

        return None, show

    @staticmethod
    def find(shows, indexer_id, indexer=None):
        """
        Find a show by its indexer id in the provided list of shows.

        :param shows: The list of shows to search in
        :param indexer_id: The indexer id of the desired show
        :param indexer: The indexer to be used
        :return: The desired show if found, ``None`` if not found
        :throw: ``MultipleShowObjectsException`` if multiple shows match the provided ``indexer_id``
        """
        log.warning(
            'Please use show.show.find_by_id() with indexer_id and series_id instead.',
            DeprecationWarning,
        )

        from medusa.indexers.config import EXTERNAL_IMDB, EXTERNAL_TRAKT
        if indexer_id is None or shows is None or len(shows) == 0:
            return None

        indexer_ids = [indexer_id] if not isinstance(indexer_id, list) else indexer_id
        results = [show for show in shows if (indexer is None or show.indexer == indexer) and show.indexerid in indexer_ids]

        # if can't find with supported indexers try with IMDB and TRAKT
        if not results:
            results = [show for show in shows
                       if show.imdb_id and show.imdb_id == indexer_id and indexer == EXTERNAL_IMDB or
                       show.externals.get('trakt_id', None) == indexer_id and indexer == EXTERNAL_TRAKT]

        if not results:
            return None

        if len(results) == 1:
            return results[0]

        raise MultipleShowObjectsException()

    @staticmethod
    def find_by_id(series, indexer_id, series_id):
        """
        Find a show by its indexer id in the provided list of shows.

        :param series: The list of shows to search in
        :param indexer_id: shows indexer
        :param series_id: The indexers show id of the desired show
        :return: The desired show if found, ``None`` if not found
        :throw: ``MultipleShowObjectsException`` if multiple shows match the provided ``indexer_id``
        """
        from medusa.indexers.utils import indexer_name_to_id
        if not indexer_id or not series_id:
            return None

        try:
            indexer_id = int(indexer_id)
        except ValueError:
            indexer_id = indexer_name_to_id(indexer_id)

        try:
            series_id = int(series_id)
        except ValueError:
            log.warning('Invalid series id: {series_id}', {'series_id': series_id})

        if series_id is None or series is None or len(series) == 0:
            return None

        # indexer_ids = [show_id] if not isinstance(show_id, list) else show_id
        results = [show for show in series if show.indexer == indexer_id and show.indexerid == series_id]

        if not results:
            return None

        if len(results) == 1:
            return results[0]

    @staticmethod
    def overall_stats():
        db = DBConnection()
        shows = app.showList
        today = date.today().toordinal()

        downloaded_status = [DOWNLOADED, ARCHIVED]
        snatched_status = [SNATCHED, SNATCHED_PROPER, SNATCHED_BEST]
        total_status = [SKIPPED, WANTED]

        results = db.select(
            'SELECT airdate, status, quality '
            'FROM tv_episodes '
            'WHERE season > 0 '
            'AND episode > 0 '
            'AND airdate > 1'
        )

        stats = {
            'episodes': {
                'downloaded': 0,
                'snatched': 0,
                'total': 0,
            },
            'shows': {
                'active': len([show for show in shows if show.paused == 0 and show.status == 'Continuing']),
                'total': len(shows),
            },
        }

        for result in results:
            if result['status'] in downloaded_status:
                stats['episodes']['downloaded'] += 1
                stats['episodes']['total'] += 1
            elif result['status'] in snatched_status:
                stats['episodes']['snatched'] += 1
                stats['episodes']['total'] += 1
            elif result['airdate'] <= today and result['status'] in total_status:
                stats['episodes']['total'] += 1

        return stats

    @staticmethod
    def pause(indexer_id, series_id, pause=None):
        """
        Change the pause state of a show.

        :param indexer_id: The unique id of the show to update
        :param pause: ``True`` to pause the show, ``False`` to resume the show, ``None`` to toggle the pause state
        :return: A tuple containing:
         - an error message if the pause state could not be changed, ``None`` otherwise
         - the show object that was updated, if it exists, ``None`` otherwise
        """
        error, show = Show._validate_indexer_id(indexer_id, series_id)

        if error is not None:
            return error, show

        if pause is None:
            show.paused = not show.paused
        else:
            show.paused = pause

        show.save_to_db()

        return None, show

    @staticmethod
    def refresh(indexer_id, series_id):
        """
        Try to refresh a show.

        :param indexer_id: The unique id of the show to refresh
        :return: A tuple containing:
         - an error message if the show could not be refreshed, ``None`` otherwise
         - the show object that was refreshed, if it exists, ``None`` otherwise
        """
        error, series_obj = Show._validate_indexer_id(indexer_id, series_id)

        if error is not None:
            return error, series_obj

        try:
            app.show_queue_scheduler.action.refreshShow(series_obj)
        except CantRefreshShowException as exception:
            return ex(exception), series_obj

        return None, series_obj

    @staticmethod
    def _validate_indexer_id(indexer_id, series_id):
        """
        Check that the provided indexer_id is valid and corresponds with a known show.

        :param indexer_id: The indexer id to check
        :return: A tuple containing:
         - an error message if the indexer id is not correct, ``None`` otherwise
         - the show object corresponding to ``indexer_id`` if it exists, ``None`` otherwise
        """
        try:
            series = Show.find_by_id(app.showList, indexer_id, series_id)
        except MultipleShowObjectsException:
            return 'Unable to find the specified show', None

        return None, series
