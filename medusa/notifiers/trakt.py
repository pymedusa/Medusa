"""Trakt notifier module."""
# coding=utf-8

from __future__ import unicode_literals

import logging
from builtins import object
from json.decoder import JSONDecodeError

from medusa import app
from medusa.helpers import get_title_without_year
from medusa.helpers.trakt import create_episode_structure, create_show_structure, get_trakt_user
from medusa.indexers.utils import get_trakt_indexer
from medusa.logger.adapters.style import BraceAdapter

from requests.exceptions import RequestException

from trakt import sync, tv
from trakt.errors import TraktException


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    """A "notifier" for trakt.tv which keeps track of what has and hasn't been added to your library."""

    def notify_snatch(self, title, message, **kwargs):
        """Trakt don't support this method."""
        pass

    def notify_download(self, ep_obj):
        """Trakt don't support this method."""
        pass

    def notify_subtitle_download(self, ep_obj, lang):
        """Trakt don't support this method."""
        pass

    def notify_git_update(self, new_version):
        """Trakt don't support this method."""
        pass

    def notify_login(self, ipaddress=''):
        """Trakt don't support this method."""
        pass

    @staticmethod
    def update_library(ep_obj):
        """Send a request to trakt indicating that the given episode is part of our library.

        ep_obj: The Episode object to add to trakt
        """
        # Check if TRAKT supports that indexer
        if not get_trakt_indexer(ep_obj.series.indexer):
            return

        if app.USE_TRAKT:
            try:
                # URL parameters
                title = get_title_without_year(ep_obj.series.name, ep_obj.series.start_year)
                data = {
                    'shows': [
                        {
                            'title': title,
                            'year': ep_obj.series.start_year,
                            'ids': {},
                        }
                    ]
                }

                data['shows'][0]['ids'][get_trakt_indexer(ep_obj.series.indexer)] = ep_obj.series.indexerid

                # Add Season and Episode + Related Episodes
                data['shows'][0]['seasons'] = [{'number': ep_obj.season, 'episodes': []}]

                for rel_ep_obj in [ep_obj] + ep_obj.related_episodes:
                    data['shows'][0]['seasons'][0]['episodes'].append({'number': rel_ep_obj.episode})

                if app.TRAKT_SYNC_WATCHLIST:
                    if app.TRAKT_REMOVE_SERIESLIST:
                        sync.remove_from_watchlist(data)

                # update library
                sync.add_to_collection(data)
            except (TraktException, RequestException, JSONDecodeError) as error:
                log.warning('Unable to update Trakt: {error!r}', {'error': error})

    @staticmethod
    def update_watchlist_show(show_obj, remove=False):
        """Use Trakt sync/watchlist to updata a show."""
        trakt_media_object = {'shows': [create_show_structure(show_obj)]}

        try:
            if remove:
                result = sync.remove_from_watchlist(trakt_media_object)
            else:
                result = sync.add_to_watchlist(trakt_media_object)
        except (TraktException, RequestException, JSONDecodeError) as error:
            log.warning('Unable to update Trakt: {error!r}', {'error': error})
            return False

        if result and (result.get('added') or result.get('existing')):
            if result['added']['shows']:
                return True

        return False

    @staticmethod
    def update_watchlist_episode(show_obj, episodes, remove=False):
        """
        Use Trakt sync/watchlist to updata an episode.

        As we want to prevent Trakt.tv api rate limiting. Try to use the array of episodes
            as much as possible.
        :param episodes: An episode object or array of episode objects.
        """
        try:
            if remove:
                result = sync.remove_from_watchlist({'shows': [create_episode_structure(show_obj, episodes)]})
            else:
                result = sync.add_to_watchlist({'shows': [create_episode_structure(show_obj, episodes)]})
        except (TraktException, RequestException, JSONDecodeError) as error:
            log.warning('Unable to update Trakt watchlist: {error!r}', {'error': error})
            return False

        if result and (result.get('added') or result.get('existing')):
            if result['added']['episodes']:
                return True

        return False

    @staticmethod
    def add_episode_to_watchlist(episode):
        """
        Add an episode to the trakt watchlist.

        :params episode: Episode Object.
        """
        show_id = str(episode.series.externals.get('trakt_id', episode.series.name))

        try:
            tv_episode = tv.TVEpisode(show_id, episode.season, episode.episode)
            tv_episode.add_to_watchlist()
        except (TraktException, RequestException, JSONDecodeError) as error:
            log.warning('Unable to add episode to watchlist: {error!r}', {'error': error})

    @staticmethod
    def test_notify(blacklist_name=None):
        """Send a test notification to trakt with the given authentication info and returns a boolean.

        api: The api string to use
        username: The username to use
        blacklist_name: slug of trakt list used to hide not interested show
        Returns: True if the request succeeded, False otherwise
        """
        try:
            trakt_user = get_trakt_user()
            if blacklist_name and blacklist_name is not None:
                trakt_lists = trakt_user.lists

                found = False
                for trakt_list in trakt_lists:
                    if trakt_list.slug == blacklist_name:
                        return 'Test notice sent successfully to Trakt'
                if not found:
                    return "Trakt blacklist doesn't exists"
            else:
                return 'Test notice sent successfully to Trakt'
        except (TraktException, RequestException, JSONDecodeError) as error:
            log.warning('Unable to test TRAKT: {error!r}', {'error': error})
            return 'Test notice failed to Trakt: {0!r}'.format(error)
