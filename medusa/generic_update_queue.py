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
from enum import Enum

from medusa import app
from medusa.logger.adapters.style import BraceAdapter
from medusa.queues import generic_queue
from medusa.show.recommendations.anidb import AnidbPopular
from medusa.show.recommendations.imdb import ImdbPopular
from medusa.show.recommendations.trakt import TraktPopular

from requests import RequestException

from simpleanidb import REQUEST_HOT

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class UpdateQueueActions(Enum):
    """Enum with update actions."""

    UPDATE_RECOMMENDED_LIST_TRAKT = 10
    UPDATE_RECOMMENDED_LIST_IMDB = 20
    UPDATE_RECOMMENDED_LIST_ANIDB = 30
    UPDATE_RECOMMENDED_LIST_ALL = 1000


class GenericQueueScheduler(generic_queue.GenericQueue):
    def __init__(self):
        generic_queue.GenericQueue.__init__(self)
        self.queue_name = 'GENERICQUEUESCHEDULER'

    def is_action_in_queue(self, action_id):
        return action_id in self.queue


class RecommendedShowUpdateScheduler(object):
    """Recommended show update scheduler."""

    def __init__(self):
        """Initialize the class."""
        self.amActive = False

    def run(self):
        """Schedule recommendedShowQueueItems if needed."""
        self.amActive = True
        try:
            if not app.CACHE_RECOMMENDED_SHOWS:
                return

            if app.CACHE_RECOMMENDED_TRAKT:
                app.generic_queue_scheduler.action.add_item(
                    RecommendedShowQueueItem(update_action=UpdateQueueActions.UPDATE_RECOMMENDED_LIST_TRAKT)
                )

            if app.CACHE_RECOMMENDED_IMDB:
                app.generic_queue_scheduler.action.add_item(
                    RecommendedShowQueueItem(update_action=UpdateQueueActions.UPDATE_RECOMMENDED_LIST_IMDB)
                )

            if app.CACHE_RECOMMENDED_ANIDB:
                app.generic_queue_scheduler.action.add_item(
                    RecommendedShowQueueItem(update_action=UpdateQueueActions.UPDATE_RECOMMENDED_LIST_ANIDB)
                )

        except Exception as error:
            log.exception('Recommended show queue item Exception, error: {error}', {'error': error})

        self.amActive = True


class RecommendedShowQueueItem(generic_queue.QueueItem):
    """Recommended show update queue item class."""

    def __init__(self, update_action):
        """Initialize the class."""
        generic_queue.QueueItem.__init__(self, name=str(update_action).split('.')[-1], action_id=update_action)
        self.recommended_list = update_action
        self.started = False
        self.success = False

    def run(self):
        """Run recommended show update thread."""
        generic_queue.QueueItem.run(self)
        self.started = True

        try:
            # Update recommended shows from trakt, imdb and anidb
            # recommended shows are dogpilled into cache/recommended.dbm

            log.info(u'Started caching recommended shows')

            if self.recommended_list in (
                UpdateQueueActions.UPDATE_RECOMMENDED_LIST_TRAKT, UpdateQueueActions.UPDATE_RECOMMENDED_LIST_ALL
            ):
                # Cache trakt shows
                for trakt_list in TraktPopular.CATEGORIES:
                    try:
                        TraktPopular().fetch_popular_shows(trakt_list=trakt_list)
                    except Exception as error:
                        log.info(u'Could not get trakt recommended shows for {trakt_list} because of error: {error}',
                                 {'trakt_list': trakt_list, 'error': error})
                        log.debug(u'Not bothering getting the other trakt lists')

            if self.recommended_list in (
                UpdateQueueActions.UPDATE_RECOMMENDED_LIST_IMDB, UpdateQueueActions.UPDATE_RECOMMENDED_LIST_ALL
            ):
                # Cache imdb shows
                try:
                    ImdbPopular().fetch_popular_shows()
                except (RequestException, Exception) as error:
                    log.info(u'Could not get imdb recommended shows because of error: {error}', {'error': error})

            if self.recommended_list in (
                UpdateQueueActions.UPDATE_RECOMMENDED_LIST_ANIDB, UpdateQueueActions.UPDATE_RECOMMENDED_LIST_ALL
            ):
                # Cache anidb shows
                try:
                    AnidbPopular().fetch_popular_shows(REQUEST_HOT)
                except Exception as error:
                    log.info(u'Could not get anidb recommended shows because of error: {error}', {'error': error})

            log.info(u'Finished caching recommended shows')

        except Exception as error:
            self.success = False
            log.exception('DailySearchQueueItem Exception, error: {error}', {'error': error})

        self.success = bool(self.success)

        self.finish()
