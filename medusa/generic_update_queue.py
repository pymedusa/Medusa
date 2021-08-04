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
from datetime import date, datetime, timedelta

from medusa import app, ws
from medusa.helper.exceptions import CantUpdateRecommendedShowsException
from medusa.logger.adapters.style import BraceAdapter
from medusa.queues import generic_queue
from medusa.show.recommendations.anidb import AnidbPopular
from medusa.show.recommendations.anilist import AniListPopular
from medusa.show.recommendations.imdb import ImdbPopular
from medusa.show.recommendations.trakt import TraktPopular

from requests import RequestException

from simpleanidb import REQUEST_HOT

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class GenericQueueActions(object):
    """Generic queue action id's."""

    UPDATE_RECOMMENDED_LIST_TRAKT = 1
    UPDATE_RECOMMENDED_LIST_IMDB = 2
    UPDATE_RECOMMENDED_LIST_ANIDB = 3
    UPDATE_RECOMMENDED_LIST_ANILIST = 4
    UPDATE_RECOMMENDED_LIST_ALL = 10

    names = {
        UPDATE_RECOMMENDED_LIST_TRAKT: 'Update recommended Trakt',
        UPDATE_RECOMMENDED_LIST_IMDB: 'Update recommended Imdb',
        UPDATE_RECOMMENDED_LIST_ANIDB: 'Update recommended Anidb',
        UPDATE_RECOMMENDED_LIST_ANILIST: 'Update recommended AniList',
        UPDATE_RECOMMENDED_LIST_ALL: 'Update all recommended lists',
    }


class GenericQueueScheduler(generic_queue.GenericQueue):
    """General purpose queue scheduler."""

    def __init__(self):
        generic_queue.GenericQueue.__init__(self)
        self.queue_name = 'GENERICQUEUESCHEDULER'

    def is_action_in_queue(self, action_id):
        """Check if the queue_item has already been queued."""
        return len([queue_item for queue_item in self.queue if queue_item.action_id == action_id]) > 0

    def is_action_active(self, action_id):
        """Check if the queue_item is already running."""
        return self.current_item is not None and self.current_item.action_id == action_id

    def add_recommended_show_update(self, action):
        """Queue a new recommended show update."""
        if self.is_action_active(action):
            raise CantUpdateRecommendedShowsException(
                f'{GenericQueueActions.names[action]} is already running'
            )

        if self.is_action_in_queue(action):
            raise CantUpdateRecommendedShowsException(
                f'{GenericQueueActions.names[action]} is already queued'
            )

        queue_item = RecommendedShowQueueItem(update_action=action)
        self.add_item(queue_item)
        return queue_item


class RecommendedShowUpdateScheduler(object):
    """Recommended show update scheduler."""

    def __init__(self):
        """Initialize the class."""
        self.amActive = False

    def run(self, force=False):
        """Schedule recommendedShowQueueItems if needed."""
        self.amActive = True
        try:
            if not app.CACHE_RECOMMENDED_SHOWS:
                return

            if app.CACHE_RECOMMENDED_TRAKT:
                app.generic_queue_scheduler.action.add_recommended_show_update(
                    GenericQueueActions.UPDATE_RECOMMENDED_LIST_TRAKT
                )

            if app.CACHE_RECOMMENDED_IMDB:
                app.generic_queue_scheduler.action.add_recommended_show_update(
                    GenericQueueActions.UPDATE_RECOMMENDED_LIST_IMDB
                )

            if app.CACHE_RECOMMENDED_ANIDB:
                app.generic_queue_scheduler.action.add_recommended_show_update(
                    GenericQueueActions.UPDATE_RECOMMENDED_LIST_ANIDB
                )

            if app.CACHE_RECOMMENDED_ANILIST:
                app.generic_queue_scheduler.action.add_recommended_show_update(
                    GenericQueueActions.UPDATE_RECOMMENDED_LIST_ANILIST
                )

        except Exception as error:
            log.exception('Recommended show queue item Exception, error: {error}', {'error': error})

        self.amActive = True


class RecommendedShowQueueItem(generic_queue.QueueItem):
    """Recommended show update queue item class."""

    def __init__(self, update_action):
        """Initialize the class."""
        update_action_name = GenericQueueActions.names.get(update_action)
        generic_queue.QueueItem.__init__(self, name=update_action_name.split('.')[-1], action_id=update_action)
        self.recommended_list = update_action
        self.started = False
        self.success = False

    def run(self):
        """Run recommended show update thread."""
        generic_queue.QueueItem.run(self)
        self.started = True

        # Push an update to any open Web UIs through the WebSocket
        ws.Message('QueueItemUpdate', self.to_json).push()

        try:
            # Update recommended shows from trakt, imdb and anidb
            # recommended shows are dogpilled into cache/recommended.dbm

            log.info(u'Started caching recommended shows')

            if self.recommended_list in (
                GenericQueueActions.UPDATE_RECOMMENDED_LIST_TRAKT, GenericQueueActions.UPDATE_RECOMMENDED_LIST_ALL
            ):
                # Only cache the trakt lists that have been enabled.
                for trakt_list in app.CACHE_RECOMMENDED_TRAKT_LISTS:
                    try:
                        TraktPopular().fetch_popular_shows(trakt_list)
                    except Exception as error:
                        log.info(u'Could not get trakt recommended shows for {trakt_list} because of error: {error}',
                                 {'trakt_list': trakt_list, 'error': error})
                        log.debug(u'Not bothering getting the other trakt lists')

            if self.recommended_list in (
                GenericQueueActions.UPDATE_RECOMMENDED_LIST_IMDB, GenericQueueActions.UPDATE_RECOMMENDED_LIST_ALL
            ):
                # Cache imdb shows
                try:
                    ImdbPopular().fetch_popular_shows()
                except (RequestException, Exception) as error:
                    log.info(u'Could not get imdb recommended shows because of error: {error}', {'error': error})

            if self.recommended_list in (
                GenericQueueActions.UPDATE_RECOMMENDED_LIST_ANIDB, GenericQueueActions.UPDATE_RECOMMENDED_LIST_ALL
            ):
                # Cache anidb shows
                try:
                    AnidbPopular().fetch_popular_shows(REQUEST_HOT)
                except Exception as error:
                    log.info(u'Could not get anidb recommended shows because of error: {error}', {'error': error})

            if self.recommended_list in (
                GenericQueueActions.UPDATE_RECOMMENDED_LIST_ANILIST, GenericQueueActions.UPDATE_RECOMMENDED_LIST_ALL
            ):
                season_dates = (
                    date.today() - timedelta(days=90),  # Previous season
                    date.today(),  # Current season
                    date.today() + timedelta(days=90)  # Next season
                )
                # Cache anilist shows
                try:
                    for season_date in season_dates:
                        AniListPopular().fetch_popular_shows(season_date.year, get_season(season_date))
                except Exception as error:
                    log.info(u'Could not get anidb recommended shows because of error: {error}', {'error': error})

            log.info(u'Finished caching recommended shows')
            self.success = True

        except Exception as error:
            self.success = False
            log.exception('DailySearchQueueItem Exception, error: {error}', {'error': error})

        self.success = bool(self.success)
        # Push an update to any open Web UIs through the WebSocket
        ws.Message('QueueItemUpdate', self.to_json).push()

        self.finish()


Y = 2000  # dummy leap year to allow input X-02-29 (leap day)
seasons = [
    ('winter', (date(Y, 1, 1), date(Y, 3, 20))),
    ('spring', (date(Y, 3, 21), date(Y, 6, 20))),
    ('summer', (date(Y, 6, 21), date(Y, 9, 22))),
    ('fall', (date(Y, 9, 23), date(Y, 12, 20))),
    ('winter', (date(Y, 12, 21), date(Y, 12, 31)))
]


def get_season(now):
    """
    Calculate a season from a datetime.

    :param now: A datetime or date object.
    :return: Season as a string.
    """
    if isinstance(now, datetime):
        now = now.date()
    now = now.replace(year=Y)
    return next(season for season, (start, end) in seasons
                if start <= now <= end)
