# coding=utf-8

from __future__ import unicode_literals

import logging
import threading
import time
from builtins import object

from medusa import app, db, network_timezones, ui
from medusa.helper.exceptions import CantRefreshShowException, CantUpdateShowException
from medusa.indexers.api import indexerApi
from medusa.indexers.exceptions import IndexerException, IndexerUnavailable
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

            indexer_name = indexerApi(show.indexer).name
            indexer_api_params = indexerApi(show.indexer).api_params.copy()
            try:
                indexer_api = indexerApi(show.indexer).indexer(**indexer_api_params)
            except IndexerUnavailable:
                logger.warning(u'Problem running show_updater, Indexer {indexer_name} seems to be having '
                               u'connectivity issues. While trying to look for show updates on show: {show}',
                               indexer_name=indexer_name, show=show.name)
                continue

            # Get the lastUpdate timestamp for this indexer.
            if indexer_name not in last_updates:
                last_indexer_update = self.update_cache.get_last_indexer_update(indexer_name)
                if not last_indexer_update:
                    last_updates[indexer_name] = int(time.time() - 86400)  # 1 day ago
                elif last_indexer_update < time.time() - 604800 * update_max_weeks:
                    last_updates[indexer_name] = int(time.time() - 604800)  # 1 week ago
                else:
                    last_updates[indexer_name] = last_indexer_update

            # Get a list of updated shows from the indexer, since last update.
            if show.indexer not in indexer_updated_shows:
                try:
                    indexer_updated_shows[show.indexer] = indexer_api.get_last_updated_series(
                        last_updates[indexer_name], update_max_weeks
                    )
                except IndexerUnavailable:
                    logger.warning(u'Problem running show_updater, Indexer {indexer_name} seems to be having '
                                   u'connectivity issues while trying to look for show updates on show: {show}',
                                   indexer_name=indexer_name, show=show.name)
                    continue
                except IndexerException as error:
                    logger.warning(u'Problem running show_updater, Indexer {indexer_name} seems to be having '
                                   u'issues while trying to get updates for show {show}. Cause: {cause!r}',
                                   indexer_name=indexer_name, show=show.name, cause=error)
                    continue
                except RequestException as error:
                    logger.warning(u'Problem running show_updater, Indexer {indexer_name} seems to be having '
                                   u'issues while trying to get updates for show {show}. Cause: {cause!r}',
                                   indexer_name=indexer_name, show=show.name, cause=error)

                    if isinstance(error, HTTPError):
                        if error.response.status_code == 503:
                            logger.warning(u'API Service offline: '
                                           u'This service is temporarily offline, try again later.')
                        elif error.response.status_code == 429:
                            logger.warning(u'Your request count (#) is over the allowed limit of (40).')
                    continue
                except Exception as error:
                    logger.exception(u'Problem running show_updater, Indexer {indexer_name} seems to be having '
                                     u'issues while trying to get updates for show {show}. Cause: {cause!r}.',
                                     indexer_name=indexer_name, show=show.name, cause=error)
                    continue

            # Update shows that were updated in the last X weeks
            # or were not updated within the last X weeks
            if show.indexerid not in indexer_updated_shows.get(show.indexer, []):
                if show.last_update_indexer > time.time() - 604800 * update_max_weeks:
                    logger.debug(u'Skipping show update for {show}. Show was not in the '
                                 u'indexers {indexer_name} list with updated shows and it '
                                 u'was updated within the last {weeks} weeks.', show=show.name,
                                 indexer_name=indexer_name, weeks=update_max_weeks)
                    continue

            # If indexer doesn't have season updates.
            if not hasattr(indexer_api, 'get_last_updated_seasons'):
                logger.debug(u'Adding the following show for full update to queue: {show}', show=show.name)
                refresh_shows.append(show)

            # Else fall back to per season updates.
            elif hasattr(indexer_api, 'get_last_updated_seasons'):
                # Get updated seasons and add them to the season update list.
                try:
                    updated_seasons = indexer_api.get_last_updated_seasons(
                        [show.indexerid], show.last_update_indexer, update_max_weeks)
                except IndexerUnavailable:
                    logger.warning(u'Problem running show_updater, Indexer {indexer_name} seems to be having '
                                   u'connectivity issues while trying to look for show updates for show: {show}',
                                   indexer_name=indexer_name, show=show.name)
                    continue
                except IndexerException as error:
                    logger.warning(u'Problem running show_updater, Indexer {indexer_name} seems to be having '
                                   u'issues while trying to get updates for show {show}. Cause: {cause!r}',
                                   indexer_name=indexer_name, show=show.name, cause=error)
                    continue
                except Exception as error:
                    logger.exception(u'Problem running show_updater, Indexer {indexer_name} seems to be having '
                                     u'issues while trying to get updates for show {show}. Cause: {cause!r}',
                                     indexer_name=indexer_name, show=show.name, cause=error)
                    continue

                if updated_seasons[show.indexerid]:
                    logger.info(u'{show_name}: Adding the following seasons for update to queue: {seasons}',
                                show_name=show.name, seasons=updated_seasons[show.indexerid])
                    season_updates.append((show.indexer, show, updated_seasons[show.indexerid]))

        pi_list = []
        # Full refreshes
        for show in refresh_shows:
            logger.info(u'Full update on show: {show}', show=show.name)
            try:
                pi_list.append(app.show_queue_scheduler.action.updateShow(show))
            except (CantUpdateShowException, CantRefreshShowException) as e:
                logger.warning(u'Automatic update failed. Error: {error}', error=e)
            except Exception as e:
                logger.error(u'Automatic update failed: Error: {error}', error=e)

        # Only update expired season
        for show in season_updates:
            logger.info(u'Updating season {season} for show: {show}.', season=show[2], show=show[1].name)
            try:
                pi_list.append(app.show_queue_scheduler.action.updateShow(show[1], season=show[2]))
            except CantUpdateShowException as e:
                logger.warning(u'Automatic update failed. Error: {error}', error=e)
            except Exception as e:
                logger.error(u'Automatic update failed: Error: {error}', error=e)

        ui.ProgressIndicators.setIndicator('dailyUpdate', ui.QueueProgressIndicator('Daily Update', pi_list))

        # Only refresh updated shows that have been updated using the season updates.
        # The full refreshed shows, are updated from the queueItem.
        for show in set(show[1] for show in season_updates):
            try:
                app.show_queue_scheduler.action.refreshShow(show, True)
            except CantRefreshShowException as e:
                logger.warning(u'Show refresh on show {show_name} failed. Error: {error}',
                               show_name=show.name, error=e)
            except Exception as e:
                logger.error(u'Show refresh on show {show_name} failed: Unexpected Error: {error}',
                             show_name=show.name, error=e)

        if refresh_shows or season_updates:
            for indexer in set([s.indexer for s in refresh_shows] + [s[1].indexer for s in season_updates]):
                indexer_api = indexerApi(indexer)
                self.update_cache.set_last_indexer_update(indexer_api.name)
                logger.info(u'Updated lastUpdate timestamp for {indexer_name}', indexer_name=indexer_api.name)
            logger.info(u'Completed scheduling updates on shows')
        else:
            logger.info(u'Completed scheduling updates on shows, but there was nothing to update')

        self.amActive = False


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
        last_indexer_update = self.select(
            'SELECT time '
            'FROM lastUpdate '
            'WHERE provider = ?',
            [indexer]
        )
        return last_indexer_update[0]['time'] if last_indexer_update else None

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
