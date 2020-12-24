"""Trakt notifier module."""
# coding=utf-8

from __future__ import unicode_literals

import logging
from builtins import object

from medusa import app
from medusa.helpers import get_title_without_year
from medusa.helpers.trakt import get_trakt_user
from medusa.indexers.utils import get_trakt_indexer
from medusa.logger.adapters.style import BraceAdapter

from trakt import sync, tv

# from traktor import AuthException, TokenExpiredException, TraktApi, TraktException

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    """A "notifier" for trakt.tv which keeps track of what has and hasn't been added to your library."""

    def notify_snatch(self, title, message):
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
                        # trakt_api.request('sync/watchlist/remove', data, method='POST')
                        sync.remove_from_watchlist(data)

                # update library
                # trakt_api.request('sync/collection', data, method='POST')
                sync.add_to_collection(data)

            # TODO: Add more reasonable exceptions.
            except Exception as error:
                log.debug('Unable to update Trakt: {0!r}', error)

    @staticmethod
    def update_watchlist_show(show_obj, remove=False):
        """Use Trakt sync/watchlist to updata a show."""
        title = get_title_without_year(show_obj.name, show_obj.start_year)
        data = {
            'year': show_obj.start_year,
            'ids': {},
        }
        data['ids'][get_trakt_indexer(show_obj.indexer)] = show_obj.indexerid
        trakt_tv_show = tv.TVShow(title, '', **data)

        if remove:
            sync.remove_from_watchlist(trakt_tv_show)
        else:
            sync.add_to_watchlist(trakt_tv_show)

    @staticmethod
    def update_watchlist_episode(ep_obj, remove=False):
        """Use Trakt sync/watchlist to updata an episode."""
        title = get_title_without_year(ep_obj.show_obj.name, ep_obj.show_obj.start_year)
        data = {
            'year': ep_obj.show_obj.start_year,
            'ids': {},
        }
        data['ids'][get_trakt_indexer(ep_obj.show_obj.indexer)] = ep_obj.show_obj.indexerid
        trakt_tv_episode = tv.TVEpisode(title, ep_obj.season, ep_obj.episode, **data)

        if remove:
            sync.remove_from_watchlist(trakt_tv_episode)
        else:
            sync.add_to_watchlist(trakt_tv_episode)

    @staticmethod
    def update_watchlist(show_obj=None, s=None, e=None, data_show=None, data_episode=None, update='add'):
        """Send a request to trakt indicating that the given episode is part of our library.

        show_obj: The Series object to add to trakt
        s: season number
        e: episode number
        data_show: structured object of shows trakt type
        data_episode: structured object of episodes trakt type
        update: type o action add or remove
        """
        # Check if TRAKT supports that indexer
        if not get_trakt_indexer(show_obj.indexer):
            return

        if app.USE_TRAKT:

            data = {}
            trakt_tv_show = None
            trakt_tv_episode = None
            try:
                # URL parameters
                if show_obj is not None:
                    title = get_title_without_year(show_obj.name, show_obj.start_year)
                    data = {
                        'title': title,
                        'year': show_obj.start_year,
                        'ids': {},
                    }
                    data['ids'][get_trakt_indexer(show_obj.indexer)] = show_obj.indexerid
                    trakt_tv_show = tv.TVShow(title, '', **data)
                elif data_show is not None:
                    trakt_tv_show = tv.TVShow(title, '', **data_show)
                else:
                    log.warning(
                        "There's a coding problem contact developer. It's needed to be provided at"
                        ' least one of the two: data_show or show_obj',
                    )
                    return False

                if data_episode is not None:
                    data['shows'][0].update(data_episode)

                elif s is not None:
                    # trakt URL parameters
                    season = {
                        'season': [
                            {
                                'number': s,
                            }
                        ]
                    }

                    if e is not None:
                        # trakt URL parameters
                        episode = {
                            'episodes': [
                                {
                                    'number': e
                                }
                            ]
                        }

                        season['season'][0].update(episode)

                    data['shows'][0].update(season)

                if update == 'add':
                    sync.add_to_watchlist(data)
                else:
                    sync.remove_from_watchlist(data)

            # TODO: add more meaningfull exception
            except Exception as error:
                log.debug('Unable to update Trakt watchlist: {0!r}', error)
                return False

        return True

    @staticmethod
    def add_episode_to_watchlist(episode):
        """
        Add an episode to the trakt watchlist.

        :params episode: Episode Object.
        """
        show_id = None

        tv_show = tv.TVShow(show_id)
        tv_episode = tv.TVEpisode(tv_show, episode.season, episode.episode)
        tv_episode.add_to_watchlist()

    @staticmethod
    def trakt_episode_data_generate(data):
        """Build the JSON structure to send back to Trakt."""
        # Find how many unique season we have
        unique_seasons = []
        for season, episode in data:
            if season not in unique_seasons:
                unique_seasons.append(season)

        # build the query
        seasons_list = []
        for searchedSeason in unique_seasons:
            episodes_list = []
            for season, episode in data:
                if season == searchedSeason:
                    episodes_list.append({'number': episode})
            seasons_list.append({'number': searchedSeason, 'episodes': episodes_list})

        post_data = {'seasons': seasons_list}

        return post_data

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
        except Exception as error:
            log.warning('Unable to test TRAKT: {0!r}', error)
            return 'Test notice failed to Trakt: {0!r}'.format(error)
