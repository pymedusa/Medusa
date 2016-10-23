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


import medusa as app
from . import db, helpers, network_timezones, ui
from .helper.exceptions import CantRefreshShowException, CantUpdateShowException
from .show.Show import Show

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
        season_updates = []
        update_max_weeks = 12

        # Initialize the indexer_update table. Add seasons with next_update, if they don't already exist.
        self.last_update.initialize_indexer_update(app.showList)

        # Get a list of seasons that have reached their update timer
        expired_seasons = self.last_update.expired_seasons()

        for indexer in expired_seasons:
            refresh = False
            # Query the indexer for changed shows, since last update
            # refresh network timezones
            network_timezones.update_network_dict()

            # TODO: is not working for tvdbapiv2
            last_update = self.last_update.get_last_indexer_update(app.indexerApi(indexer).name)

            if not last_update or last_update < time.time() - 86400 * update_max_weeks:
                # no entry in lastUpdate, or last update was too long ago, let's refresh the show for this indexer
                refresh = True
            else:
                indexer_api_params = app.indexerApi(indexer).api_params.copy()
                t = app.indexerApi(indexer).indexer(**indexer_api_params)
                updated_shows = t.get_last_updated_series(last_update, update_max_weeks)

            for show_id in expired_seasons[indexer]:
                # Loop through the shows
                show = Show.find_by_id(app.showList, indexer, show_id)
                if refresh:
                    # Marked as a refresh, we don't need to check on season
                    refresh_shows.append(show)
                else:
                    # We know there is a season
                    if updated_shows and show_id in [_.id for _ in updated_shows]:
                        # Refresh this season, because it was expired AND it's in the indexer updated shows list. Meaning
                        # A change to a episode occurred. Altough we don't update all seasons. But only the expired one.
                        for season in expired_seasons[indexer][show_id]:
                            season_updates.append((show, season))

            # update the lastUpdate for this indexer
            self.last_update.set_last_indexer_update(app.indexerApi(indexer).name)

        pi_list = []

        try:
            # Full refreshes
            for show in refresh_shows:
                # If the cur_show is not 'paused' then add to the showQueueSchedular
                if not show.paused:
                    pi_list.append(app.showQueueScheduler.action.updateShow(show))
                else:
                    logger.info(u'Show update skipped, show: {show} is paused.', show=show.name)

            # Only update expired season
            for show in season_updates:
                # If the cur_show is not 'paused' then add to the showQueueSchedular
                if not show[0].paused:
                    logger.info(u'Updating season {season} for show: {show}.', season=show[0], show=show[0].name)
                    pi_list.append(app.showQueueScheduler.action.updateShow(show[0], season=show[1]))
                else:
                    logger.info(u'Show update skipped, show: {show} is paused.', show=show[0].name)
        except (CantUpdateShowException, CantRefreshShowException) as e:
            logger.warning(u'Automatic update failed. Error: {error}', error=e)
        except Exception as e:
            logger.error(u'Automatic update failed: Error: {error}', error=e)

        ui.ProgressIndicators.setIndicator('dailyUpdate', ui.QueueProgressIndicator("Daily Update", pi_list))

        logger.info(u'Completed full update on all shows')

        self.amActive = False

    def __del__(self):
        pass


class ShowUpdate(db.DBConnection):
    def __init__(self):
        db.DBConnection.__init__(self, 'cache.db')

    def initialize_indexer_update(self, show_list):
        for show in show_list:
            for season in show.get_all_seasons(True):
                if not self.get_next_season_update(show.indexer, show.indexerid, season):
                    show.create_next_season_update(season)

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

    def get_last_indexer_update(self, indexer):
        """Get the last update timestamp from the lastUpdate table.

        :param indexer:
        :type indexer: string, name respresentation, like 'theTVDB'. Check the indexer_config's name attribute.
        :return: epoch timestamp
        :rtype: int
        """
        last_update_indexer = self.select("SELECT `time` FROM lastUpdate WHERE provider = ?", [indexer])
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
