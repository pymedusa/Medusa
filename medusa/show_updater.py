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

from __future__ import unicode_literals

import logging
import threading
import time
from builtins import object

from medusa import app, db, network_timezones, ui
from medusa.helper.exceptions import CantRefreshShowException, CantUpdateShowException
from medusa.indexers.indexer_api import indexerApi
from medusa.indexers.indexer_exceptions import IndexerException, IndexerUnavailable
from medusa.scene_exceptions import refresh_exceptions_cache
from medusa.session.core import MedusaSession

from requests.exceptions import HTTPError, RequestException

logger = logging.getLogger(__name__)


class ShowUpdater(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.amActive = False
        self.session = MedusaSession()
        self.update_cache = UpdateCache()

    def run(self, force=False):

        self.amActive = True
        refresh_shows = []  # A list of shows, that need to be refreshed
        season_updates = []  # A list of show seasons that have passed their next_update timestamp
        update_max_weeks = 12

        network_timezones.update_network_dict()

        # Refresh the exceptions_cache from db.
        refresh_exceptions_cache()

        logger.info(u'Started periodic show updates')

        # Cache for the indexers list of updated show
        indexer_updated_shows = {}
        # Cache for the last indexer update timestamp
        last_updates = {}

        # Loop through the list of shows, and per show evaluate if we can use the .get_last_updated_seasons()
        for show in app.showList:
            if show.paused:
                logger.info(u'The show {show} is paused, not updating it.', show=show.name)
                continue

            indexer_api_params = indexerApi(show.indexer).api_params.copy()
            try:
                indexer_api = indexerApi(show.indexer).indexer(**indexer_api_params)
            except IndexerUnavailable:
                logger.warning(u'Problem running show_updater, Indexer {indexer_name} seems to be having '
                               u'connectivity issues. While trying to look for show updates on show: {show}',
                               indexer_name=indexerApi(show.indexer).name, show=show.name)
                continue

            # Get the lastUpdate timestamp for this indexer.
            if indexerApi(show.indexer).name not in last_updates:
                last_updates[indexerApi(show.indexer).name] = \
                    self.update_cache.get_last_indexer_update(indexerApi(show.indexer).name)
            last_update = last_updates[indexerApi(show.indexer).name]

            # Get a list of updated shows from the indexer, since last update.
            # Use the list, to limit the shows for which are requested for the last updated seasons.
            if last_update and last_update > time.time() - (604800 * update_max_weeks):
                if show.indexer not in indexer_updated_shows:
                    try:
                        indexer_updated_shows[show.indexer] = indexer_api.get_last_updated_series(
                            last_update, update_max_weeks
                        )
                    except IndexerUnavailable:
                        logger.warning(u'Problem running show_updater, Indexer {indexer_name} seems to be having '
                                       u'connectivity issues while trying to look for show updates on show: {show}',
                                       indexer_name=indexerApi(show.indexer).name, show=show.name)
                        continue
                    except IndexerException as error:
                        logger.warning(u'Problem running show_updater, Indexer {indexer_name} seems to be having '
                                       u'issues while trying to get updates for show {show}. Cause: {cause}',
                                       indexer_name=indexerApi(show.indexer).name, show=show.name, cause=error.message)
                        continue
                    except RequestException as error:
                        logger.warning(u'Problem running show_updater, Indexer {indexer_name} seems to be having '
                                       u'issues while trying to get updates for show {show}. ',
                                       indexer_name=indexerApi(show.indexer).name, show=show.name)

                        if isinstance(error, HTTPError):
                            if error.response.status_code == 503:
                                logger.warning(u'API Service offline: '
                                               u'This service is temporarily offline, try again later.')
                            elif error.response.status_code == 429:
                                logger.warning(u'Your request count (#) is over the allowed limit of (40).')

                        logger.warning(u'Cause: {cause}.', cause=error)
                        continue
                    except Exception as error:
                        logger.exception(u'Problem running show_updater, Indexer {indexer_name} seems to be having '
                                         u'issues while trying to get updates for show {show}. Cause: {cause}.',
                                         indexer_name=indexerApi(show.indexer).name, show=show.name, cause=error)
                        continue

                # If the current show is not in the list, move on to the next.
                # Only do this for shows, if the indexer has had a successful update run within the last 12 weeks.
                if all([isinstance(indexer_updated_shows[show.indexer], list),
                        show.indexerid not in indexer_updated_shows.get(show.indexer)]):
                    logger.debug(u'Skipping show update for {show}. As the show is not '
                                 u'in the indexers {indexer_name} list with updated '
                                 u'shows within the last {weeks} weeks.', show=show.name,
                                 indexer_name=indexerApi(show.indexer).name, weeks=update_max_weeks)
                    continue

            # These are the criteria for performing a full show refresh.
            if any([not hasattr(indexer_api, 'get_last_updated_seasons'),
                    not last_update,
                    last_update < time.time() - 604800 * update_max_weeks]):
                # no entry in lastUpdate, or last update was too long ago,
                # let's refresh the show for this indexer
                logger.debug(u'Trying to update {show}. Your lastUpdate for {indexer_name} is older then {weeks} weeks,'
                             u" or the indexer doesn't support per season updates. Doing a full update.",
                             show=show.name, indexer_name=indexerApi(show.indexer).name,
                             weeks=update_max_weeks)
                refresh_shows.append(show)

            # Else fall back to per season updates.
            elif hasattr(indexer_api, 'get_last_updated_seasons'):
                # Get updated seasons and add them to the season update list.
                try:
                    updated_seasons = indexer_api.get_last_updated_seasons([show.indexerid], last_update,
                                                                           update_max_weeks)
                except IndexerUnavailable:
                    logger.warning(u'Problem running show_updater, Indexer {indexer_name} seems to be having '
                                   u'connectivity issues while trying to look for showupdates on show: {show}',
                                   indexer_name=indexerApi(show.indexer).name, show=show.name)
                    continue
                except IndexerException as e:
                    logger.warning(u'Problem running show_updater, Indexer {indexer_name} seems to be having '
                                   u'issues while trying to get updates for show {show}. Cause: {cause}',
                                   indexer_name=indexerApi(show.indexer).name, show=show.name, cause=e.message)
                    continue
                except Exception as e:
                    logger.exception(u'Problem running show_updater, Indexer {indexer_name} seems to be having '
                                     u'issues while trying to get updates for show {show}. Cause: {cause}',
                                     indexer_name=indexerApi(show.indexer).name, show=show.name, cause=e)
                    continue

                if updated_seasons[show.indexerid]:
                    logger.info(u'{show_name}: Adding the following seasons for update to queue: {seasons}',
                                show_name=show.name, seasons=updated_seasons[show.indexerid])
                    for season in updated_seasons[show.indexerid]:
                        season_updates.append((show.indexer, show, season))

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
                except CantUpdateShowException as e:
                    logger.warning(u'Automatic update failed. Error: {error}', error=e)
                except Exception as e:
                    logger.error(u'Automatic update failed: Error: {error}', error=e)
            else:
                logger.info(u'Show update skipped, show: {show} is paused.', show=show[1].name)

        ui.ProgressIndicators.setIndicator('dailyUpdate', ui.QueueProgressIndicator("Daily Update", pi_list))

        # Only refresh updated shows that have been updated using the season updates.
        # The full refreshed shows, are updated from the queueItem.
        for show in set(show[1] for show in season_updates):
            if not show.paused:
                try:
                    app.show_queue_scheduler.action.refreshShow(show, True)
                except CantRefreshShowException as e:
                    logger.warning(u'Show refresh on show {show_name} failed. Error: {error}',
                                   show_name=show.name, error=e)
                except Exception as e:
                    logger.error(u'Show refresh on show {show_name} failed: Unexpected Error: {error}',
                                 show_name=show.name, error=e)
            else:
                logger.info(u'Show refresh skipped, show: {show_name} is paused.', show_name=show.name)

        if refresh_shows or season_updates:
            for indexer in set([show.indexer for show in refresh_shows] + [s[1].indexer for s in season_updates]):
                indexer_api = indexerApi(indexer)
                self.update_cache.set_last_indexer_update(indexer_api.name)
                logger.info(u'Updated lastUpdate timestamp for {indexer_name}', indexer_name=indexer_api.name)
            logger.info(u'Completed scheduling updates on shows')
        else:
            logger.info(u'Completed but there was nothing to update')

        self.amActive = False

    def __del__(self):
        pass


class UpdateCache(db.DBConnection):
    def __init__(self):
        super(UpdateCache, self).__init__('cache.db')

    def get_last_indexer_update(self, indexer):
        """Get the last update timestamp from the lastUpdate table.

        :param indexer:
        :type indexer: Indexer name from indexer_config's name attribute.
        :return: epoch timestamp
        :rtype: int
        """
        last_update_indexer = self.select(
            'SELECT time '
            'FROM lastUpdate '
            'WHERE provider = ?',
            [indexer]
        )
        return last_update_indexer[0][b'time'] if last_update_indexer else None

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
