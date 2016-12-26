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
import threading
import time
import app

from six import text_type

from . import db, helpers, network_timezones, ui
from .helper.exceptions import CantRefreshShowException, CantUpdateShowException
from .indexers.indexer_api import indexerApi
from .indexers.indexer_exceptions import IndexerUnavailable
from .show.show import Show

logger = logging.getLogger(__name__)


class ShowUpdater(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.amActive = False
        self.session = helpers.make_session()
        self.last_update = ShowUpdate()

    def run(self, force=False):

        self.amActive = True
        refresh_shows = []  # A list of shows, that need to be refreshed
        season_updates = []  # A list of show seasons that have passed their next_update timestamp
        update_max_weeks = 12

        network_timezones.update_network_dict()
        logger.info(u'Started periodic show updates')

        # Initialize the indexer_update table. Add seasons with next_update, if they don't already exist.
        self.last_update.initialize_indexer_update(app.showList)

        # Get a list of seasons that have reached their update timer
        expired_seasons = self.last_update.expired_seasons()

        # Loop through the list of shows, and per show evaluate if we can use the .get_last_updated_seasons()
        for show in app.showList:
            indexer_api_params = indexerApi(show.indexer).api_params.copy()
            try:
                t = indexerApi(show.indexer).indexer(**indexer_api_params)

                if hasattr(t, 'get_last_updated_seasons'):
                    # Returns in the following format: {dict} {indexer: {indexerid: {season: next_update_timestamp} }}
                    last_update = self.last_update.get_last_indexer_update(indexerApi(show.indexer).name)
                    if not last_update or last_update < time.time() - 604800 * update_max_weeks:
                        # no entry in lastUpdate, or last update was too long ago,
                        # let's refresh the show for this indexer
                        refresh_shows.append(show)
                    else:
                        # Get updated seasons and add them to the season update list.
                        updated_seasons = t.get_last_updated_seasons([show.indexerid], last_update, update_max_weeks)
                        for season in updated_seasons[show.indexerid]:
                            season_updates.append((show.indexer, show, season))
            except IndexerUnavailable:
                logger.warning(u'Problem running show_updater, Indexer {indexer_name} seems to be having '
                               u'connectivity issues. While trying to look for showupdates on show: {show}',
                               indexer_name=indexerApi(show.indexer).name, show=show.name)
                continue

        for indexer in expired_seasons:
            try:
                # Set refresh to True, to force refreshing of the entire show.
                refresh = False

                # Query the indexer for changed shows, since last update
                # refresh network timezones
                # network_timezones.update_network_dict()
                # Returns in the following format: {dict} {indexer: {indexerid: {season: next_update_timestamp} }}
                last_update = self.last_update.get_last_indexer_update(indexerApi(indexer).name)

                if not last_update or last_update < time.time() - 604800 * update_max_weeks:
                    # no entry in lastUpdate, or last update was too long ago, let's refresh the show for this indexer
                    refresh = True
                else:
                    indexer_api_params = indexerApi(indexer).api_params.copy()
                    t = indexerApi(indexer).indexer(**indexer_api_params)
                    updated_shows = t.get_last_updated_series(last_update, update_max_weeks)

                # Move through each show from the expired season cache table.
                # And run the full show or per season update.
                for show_id in expired_seasons[indexer]:
                    # Loop through the shows.

                    # Get the show object and check, to prevent issues further down the line.
                    show = Show.find_by_id(app.showList, indexer, show_id)

                    if not show:
                        logger.warning(u'Could not get show object for indexer id: {show_id} '
                                       u'and indexer: {indexer}', show_id=show_id, indexer=indexer)
                        continue

                    # Check if this indexer/show combination is already scheduled for updating through a show refresh.
                    # probably it was scheduled for refresh using the get_last_updated_seasons method.
                    if [_ for _ in refresh_shows if _.indexer == indexer and _.indexerid == show_id]:
                        continue

                    # Check if this indexer/show combination is already scheduled for updating through a
                    # season expiration. probably it was scheduled for update using the get_last_updated_seasons method.
                    if show in [_[1] for _ in season_updates]:
                        continue

                    if refresh:
                        # Marked as a refresh, we don't need to check on season.
                        refresh_shows.append(show)
                    else:
                        # These support getting a list of seasons updated per show.

                        # We only know the show has been updated, so let's be smart about it, and only update those
                        # seasons, that got back from the expired_seasons list.
                        if updated_shows and show_id in updated_shows:
                            # Refresh this season, because it was expired AND it's in the indexer updated shows list.
                            # Meaning A change to a episode occurred. Altough we don't update all seasons. But only
                            # the expired one.
                            for season in expired_seasons[indexer][show_id]:
                                season_updates.append((indexer, show, season))
            except IndexerUnavailable:
                logger.warning(u'Problem running show_updater, Indexer {indexer_name} seems to be having '
                               u'connectivity issues', indexer_name=indexerApi(show.indexer).name)
                continue

            # update the lastUpdate for this indexer
            self.last_update.set_last_indexer_update(indexerApi(indexer).name)

        pi_list = []

        # Full refreshes
        for show in refresh_shows:
            # If the cur_show is not 'paused' then add to the show_queue_scheduler
            if not show.paused:
                logger.info(u'Full update on show: {show}', show=show.name)
                try:
                    pi_list.append(app.show_queue_scheduler.action.updateShow(show))
                except (CantUpdateShowException, CantRefreshShowException) as e:
                    logger.warning(u'Automatic update failed. Error: {error}', error=e)
                except Exception as e:
                    logger.error(u'Automatic update failed: Error: {error}', error=e)
            else:
                logger.info(u'Show update skipped, show: {show} is paused.', show=show.name)

        # Only update expired season
        for show in season_updates:
            # If the cur_show is not 'paused' then add to the show_queue_scheduler
            if not show[1].paused:
                logger.info(u'Updating season {season} for show: {show}.', season=show[2], show=show[1].name)
                try:
                    pi_list.append(app.show_queue_scheduler.action.updateShow(show[1], season=show[2]))
                except (CantUpdateShowException, CantRefreshShowException) as e:
                    logger.warning(u'Automatic update failed. Error: {error}', error=e)
                except Exception as e:
                    logger.error(u'Automatic update failed: Error: {error}', error=e)
            else:
                logger.info(u'Show update skipped, show: {show} is paused.', show=show[1].name)

        ui.ProgressIndicators.setIndicator('dailyUpdate', ui.QueueProgressIndicator("Daily Update", pi_list))

        if refresh_shows or season_updates:
            logger.info(u'Completed updates on shows')
        else:
            logger.info(u'Completed but there was nothing to update')

        self.amActive = False

    def __del__(self):
        pass


class ShowUpdate(db.DBConnection):
    def __init__(self):
        db.DBConnection.__init__(self, 'cache.db')

    def initialize_indexer_update(self, show_list):
        """Add initial next_update to new seasons or shows.

        And cleanup the indexer_update table with shows that have been removed.
        :param show_list: List of show objects.
        """
        for show in show_list:
            for season in show.get_all_seasons(True):
                if not self.get_next_season_update(show.indexer, show.indexerid, season):
                    show.create_next_season_update(season)

        # Cleanup
        self.clean_expired_seasons(show_list)

    def get_next_season_update(self, indexer, indexer_id, season):
        """Get the next season update for a show, the date a season should be refreshed from indexer."""
        next_refresh = self.select('SELECT next_update FROM indexer_update WHERE indexer = ? AND indexer_id = ?'
                                   ' AND season = ?',
                                   [indexer, indexer_id, season])

        return next_refresh[0]['next_update'] if next_refresh else 0

    def set_next_season_update(self, indexer, indexer_id, season):
        """Set the last update to now, for a show (indexer_id) and it's indexer."""
        return self.upsert('indexer_update',
                           {'next_update': int(time.time())},
                           {'indexer': indexer, 'indexer_id': indexer_id, 'season': season})

    def expired_seasons(self):
        """Get the next season update for a show, the date a season should be refreshed from indexer."""
        show_seasons = self.select('SELECT * FROM indexer_update where next_update < ? ', [int(time.time())])

        seasons_dict = {}
        for season in show_seasons:
            if season['indexer'] not in seasons_dict:
                seasons_dict[season['indexer']] = {}
            if season['indexer_id'] not in seasons_dict[season['indexer']]:
                seasons_dict[season['indexer']][season['indexer_id']] = {}
            seasons_dict[season['indexer']][season['indexer_id']][season['season']] = season['next_update']

        return seasons_dict

    def clean_expired_seasons(self, show_list):
        """Remove show/season combination from the indexer_update table.

        :param show_list: A list of show_objects, used to clean up the indexer_update table.
        :return: returns a list with show_id's removed.
        """
        remove_row = []
        remove_show = []

        next_updates = self.select(b'SELECT indexer_update_id, indexer, indexer_id FROM indexer_update')

        for row in next_updates:
            if not [show for show in show_list if
                    show.indexer == row['indexer'] and
                    show.indexerid == row['indexer_id']]:

                remove_row.append(row['indexer_update_id'])
                remove_show.append(row['indexer_id'])

        def get_rows_by_slice(seq, row_len):
            """Simple pagination/slice method. Will transform [1,2,3,4] into [[1,2],[3,4]] when provided rowlen=2."""
            for start in xrange(0, len(seq), row_len):
                yield seq[start:start + row_len]

        if remove_row:
            remove_show = ','.join(text_type(s) for s in set(remove_show))
            for paged_list in get_rows_by_slice(remove_row, 50):
                self.action(
                    b'DELETE FROM indexer_update '
                    b'WHERE indexer_update_id IN (%s)' % ','.join('?' * len(paged_list)),
                    paged_list
                )
            logger.info(u'Removed following shows from season update cache: [{shows}]',
                        shows=remove_show)

        return remove_show

    def get_last_indexer_update(self, indexer):
        """Get the last update timestamp from the lastUpdate table.

        :param indexer:
        :type indexer: string, name respresentation, like 'theTVDB'. Check the indexer_config's name attribute.
        :return: epoch timestamp
        :rtype: int
        """
        last_update_indexer = self.select('SELECT time FROM lastUpdate WHERE provider = ?', [indexer])
        return last_update_indexer[0]['time'] if last_update_indexer else None

    def set_last_indexer_update(self, indexer):
        """Set the last update timestamp from the lastUpdate table.

        :param indexer:
        :type indexer: string, name respresentation, like 'theTVDB'. Check the indexer_config's name attribute.
        :return: epoch timestamp
        :rtype: int
        """
        return self.upsert('lastUpdate',
                           {'time': int(time.time())},
                           {'provider': indexer})
