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

import datetime
from enum import Enum
import logging

from medusa import (
    app,
    generic_queue,
)

from medusa.logger.adapters.style import BraceAdapter

from requests import RequestException

from medusa.show.recommendations.anidb import AnidbPopular
from medusa.show.recommendations.imdb import ImdbPopular
from medusa.show.recommendations.trakt import TraktPopular
from simpleanidb import REQUEST_HOT

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class UpdateQueueActions(Enum):
    """Enum with update actions."""

    UPDATE_RECOMMENDED_LIST_TRAKT = 10
    UPDATE_RECOMMENDED_LIST_IMDB = 20
    UPDATE_RECOMMENDED_LIST_ANIDB = 30
    UPDATE_RECOMMENDED_LIST_ALL = 1000


class UpdateQueue(generic_queue.GenericQueue):

    def __init__(self):
        generic_queue.GenericQueue.__init__(self)
        self.queue_name = 'UPDATEQUEUE'

    def is_action_in_queue(self, action_id):
        return action_id in self.queue


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
                    for page_url in (
                        'shows/trending',
                        'shows/popular',
                        'shows/anticipated',
                        'shows/collected',
                        'shows/watched',
                        'shows/played',
                        'recommendations/shows',
                        'calendars/all/shows/new/%s/30' % datetime.date.today().strftime('%Y-%m-%d'),
                        'calendars/all/shows/premieres/%s/30' % datetime.date.today().strftime('%Y-%m-%d')
                    ):
                        try:
                            TraktPopular().fetch_popular_shows(page_url=page_url)
                        except Exception as error:
                            log.info(u'Could not get trakt recommended shows for %s because of error: %s', page_url,
                                        error)
                            log.debug(u'Not bothering getting the other trakt lists')

                if self.recommended_list in (
                    UpdateQueueActions.UPDATE_RECOMMENDED_LIST_IMDB, UpdateQueueActions.UPDATE_RECOMMENDED_LIST_ALL
                ):
                    # Cache imdb shows
                    try:
                        ImdbPopular().fetch_popular_shows()
                    except (RequestException, Exception) as error:
                        log.info(u'Could not get imdb recommended shows because of error: %s', error)

                if self.recommended_list in (
                    UpdateQueueActions.UPDATE_RECOMMENDED_LIST_ANIDB, UpdateQueueActions.UPDATE_RECOMMENDED_LIST_ALL
                ):
                    # Cache anidb shows
                    try:
                        AnidbPopular().fetch_popular_shows(REQUEST_HOT)
                    except Exception as error:
                        log.info(u'Could not get anidb recommended shows because of error: %s', error)

                log.info(u'Finished caching recommended shows')

        except Exception as error:
            self.success = False
            log.exception('DailySearchQueueItem Exception, error: {error}', {'error': error})

        self.success = bool(self.success)

        self.finish()
