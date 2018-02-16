import logging
import threading
import time

from requests.exceptions import HTTPError

from medusa import app, db, network_timezones, ui
from medusa.helper.exceptions import (
    CantRefreshShowException,
    CantUpdateShowException,
)
from medusa.indexers.api import indexerApi
from medusa.indexers.exceptions import IndexerException, IndexerUnavailable
from medusa.logger.adapters.style import BraceAdapter
from medusa.scene_exceptions import refresh_exceptions_cache
from medusa.session.core import MedusaSession

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log = BraceAdapter(log)


class ShowUpdater(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.am_active = False
        self.session = MedusaSession()
        self.update_cache = UpdateCache()

    def run(self, force=False):

        self.am_active = True
        refresh_shows = []  # A list of shows, that need to be refreshed
        season_updates = []  # A list of show seasons that have passed their next_update timestamp
        update_max_weeks = 12

        network_timezones.update_network_dict()

        # Refresh the exceptions_cache from db.
        refresh_exceptions_cache()

        log.info(u'Started periodic show updates')

        # Cache for the indexers list of updated show
        indexer_updated_shows = {}
        # Cache for the last indexer update timestamp
        last_updates = {}

        # Loop through the list of shows, and per show evaluate if we can use the .get_last_updated_seasons()
        for show in app.showList:
            if show.paused:
                log.info(u'The show {show} is paused, not updating it.',
                         {'show': show.name})
                continue
            show_indexer = indexerApi(show.indexer)
            indexer_api_params = show_indexer.api_params.copy()
            indexer_name = show_indexer.name
            try:
                indexer_api = show_indexer.indexer(**indexer_api_params)
            except IndexerUnavailable:
                log.warning(
                    u'Problem running show_updater, Indexer {indexer_name}'
                    u' seems to be having connectivity issues. While trying'
                    u' to look for show updates on show: {show}', {
                        'indexer_name': indexer_name,
                        'show': show.name,
                    }
                )
                continue

            # Get the lastUpdate timestamp for this indexer.
            if indexer_name not in last_updates:
                last_updates[indexer_name] = \
                    self.update_cache.get_last_indexer_update(indexer_name)
            last_update = last_updates[indexer_name]

            # Get a list of updated shows from the indexer, since last update.
            # Use the list, to limit the shows for which are requested for the last updated seasons.
            if last_update and last_update > time.time() - (604800 * update_max_weeks):
                if show.indexer not in indexer_updated_shows:
                    try:
                        indexer_updated_shows[show.indexer] = indexer_api.get_last_updated_series(
                            last_update, update_max_weeks
                        )
                    except IndexerUnavailable:
                        log.warning(
                            u'Problem running show_updater,'
                            u' Indexer {indexer_name} seems to be having'
                            u' connectivity issues while trying to look for'
                            u' show updates on show: {show}', {
                                'indexer_name': indexer_name,
                                'show': show.name,
                            }
                        )
                        continue
                    except IndexerException as e:
                        log.warning(
                            u'Problem running show_updater,'
                            u' Indexer {indexer_name} seems to be having'
                            u' issues while trying to get updates for'
                            u' show {show}. Cause: {cause}', {
                                'indexer_name': indexer_name,
                                'show': show.name,
                                'cause': e.message,
                            }
                        )
                        continue
                    except HTTPError as error:
                        if error.response.status_code == 503:
                            log.warning(
                                u'Problem running show_updater,'
                                u' Indexer {indexer_name} seems to be having'
                                u' issues while trying to get updates for'
                                u' show {show}.'
                                u' Cause: TMDB api Service offline: '
                                u'This service is temporarily offline,'
                                u' try again later.', {
                                    'indexer_name': indexer_name,
                                    'show': show.name,
                                }
                            )
                        if error.response.status_code == 429:
                            log.warning(
                                u'Problem running show_updater,'
                                u' Indexer {indexer_name} seems to be having'
                                u' issues while trying to get updates for'
                                u' show {show}.'
                                u' Cause: Your request count (#) is over the'
                                u' allowed limit of (40)..', {
                                    'indexer_name': indexer_name,
                                    'show': show.name,
                                }
                            )
                        continue
                    except Exception as e:
                        log.exception(
                            u'Problem running show_updater,'
                            u' Indexer {indexer_name} seems to be having'
                            u' issues while trying to get updates for'
                            u' show {show}. Cause: {cause}.', {
                                'indexer_name': indexer_name,
                                'show': show.name,
                                'cause': e.message,
                            }
                        )
                        continue

                # If the current show is not in the list, move on to the next.
                # Only do this for shows, if the indexer has had a successful update run within the last 12 weeks.
                if all([isinstance(indexer_updated_shows[show.indexer], list),
                        show.indexerid not in indexer_updated_shows.get(show.indexer)]):
                    log.debug(
                        u'Skipping show update for {show}. As the show is not'
                        u' in the indexers {indexer_name} list with updated'
                        u' shows within the last {weeks} weeks.', {
                            'indexer_name': indexer_name,
                            'show': show.name,
                            'weeks': update_max_weeks,
                        }
                    )
                    continue

            # These are the criteria for performing a full show refresh.
            if any([not hasattr(indexer_api, 'get_last_updated_seasons'),
                    not last_update,
                    last_update < time.time() - 604800 * update_max_weeks]):
                # no entry in lastUpdate, or last update was too long ago,
                # let's refresh the show for this indexer
                log.debug(
                    u'Trying to update {show}. Your lastUpdate for'
                    u' {indexer_name} is older then {weeks} weeks,'
                    u' or the indexer doesn\'t support per season updates.'
                    u' Doing a full update.', {
                        'indexer_name': indexer_name,
                        'show': show.name,
                        'weeks': update_max_weeks,
                    }
                )
                refresh_shows.append(show)

            # Else fall back to per season updates.
            elif hasattr(indexer_api, 'get_last_updated_seasons'):
                # Get updated seasons and add them to the season update list.
                try:
                    updated_seasons = indexer_api.get_last_updated_seasons([show.indexerid], last_update, update_max_weeks)
                except IndexerUnavailable:
                    log.warning(
                        u'Problem running show_updater,'
                        u' Indexer {indexer_name} seems to be having'
                        u' connectivity issues while trying to look for'
                        u' showupdates on show: {show}', {
                            'indexer_name': indexer_name,
                            'show': show.name,
                        }
                    )
                    continue
                except IndexerException as e:
                    log.warning(
                        u'Problem running show_updater,'
                        u' Indexer {indexer_name} seems to be having'
                        u' issues while trying to get updates for show {show}.'
                        u' Cause: {cause}', {
                            'indexer_name': indexer_name,
                            'show': show.name,
                            'cause': e.message,
                        }
                    )
                    continue
                except Exception as e:
                    log.exception(
                        u'Problem running show_updater,'
                        u' Indexer {indexer_name} seems to be having'
                        u' issues while trying to get updates for show {show}.'
                        u' Cause: {cause}', {
                            'indexer_name': indexer_name,
                            'show': show.name,
                            'cause': e.message,
                        }
                    )
                    continue

                if updated_seasons[show.indexerid]:
                    log.info(
                        u'{show_name}: Adding the following seasons for update'
                        u' to queue: {seasons}', {
                            'show_name': show.name,
                            'seasons': updated_seasons[show.indexerid],
                        }
                    )
                    for season in updated_seasons[show.indexerid]:
                        season_updates.append((show.indexer, show, season))

        pi_list = []

        # Full refreshes
        for show in refresh_shows:
            # If the cur_show is not 'paused' then add to the show_queue_scheduler
            if not show.paused:
                log.info(u'Full update on show: {show}', {'show': show.name})
                try:
                    pi_list.append(app.show_queue_scheduler.action.update_show(show))
                except (CantUpdateShowException, CantRefreshShowException) as e:
                    log.warning(u'Automatic update failed. Error: {error}',
                                {'error': e})
                except Exception as e:
                    log.error(u'Automatic update failed: Error: {error}',
                              {'error': e})
            else:
                log.info(u'Show update skipped, show: {show} is paused.',
                         {'show': show.name})

        # Only update expired season
        for show in season_updates:
            # If the cur_show is not 'paused' then add to the show_queue_scheduler
            if not show[1].paused:
                log.info(u'Updating season {season} for show: {show}.',
                         {'season': show[2], 'show': show[1].name})
                try:
                    pi_list.append(app.show_queue_scheduler.action.update_show(show[1], season=show[2]))
                except CantUpdateShowException as e:
                    log.warning(u'Automatic update failed. Error: {error}',
                                {'error': e})
                except Exception as e:
                    log.error(u'Automatic update failed: Error: {error}',
                              {'error': e})
            else:
                log.info(u'Show update skipped, show: {show} is paused.',
                         {'show': show[1].name})

        ui.ProgressIndicators.set_indicator('dailyUpdate', ui.QueueProgressIndicator("Daily Update", pi_list))

        # Only refresh updated shows that have been updated using the season updates.
        # The full refreshed shows, are updated from the queueItem.
        for show in set(show[1] for show in season_updates):
            if not show.paused:
                try:
                    app.show_queue_scheduler.action.refresh_show(show, True)
                except CantRefreshShowException as e:
                    log.warning(u'Show refresh on show {show_name} failed.'
                                u' Error: {error}',
                                {'show_name': show.name, 'error': e})
                except Exception as e:
                    log.error(u'Show refresh on show {show_name} failed:'
                              u' Unexpected Error: {error}',
                              {'show_name': show.name, 'error': e})
            else:
                log.info(u'Show refresh skipped, show: {show_name} is paused.',
                         {'show_name': show.name})

        if refresh_shows or season_updates:
            for indexer in set([show.indexer for show in refresh_shows] + [s[1].indexer for s in season_updates]):
                indexer_api = indexerApi(indexer)
                self.update_cache.set_last_indexer_update(indexer_api.name)
                log.info(u'Updated lastUpdate timestamp for {indexer_name}',
                         {'indexer_name': indexer_api.name})
            log.info(u'Completed scheduling updates on shows')
        else:
            log.info(u'Completed but there was nothing to update')

        self.am_active = False

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
