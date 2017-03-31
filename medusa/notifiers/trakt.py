# coding=utf-8

from __future__ import unicode_literals

import logging

from medusa import app
from medusa.helpers import get_title_without_year
from medusa.indexers.indexer_config import get_trakt_indexer
from medusa.logger.adapters.style import BraceAdapter

from traktor import AuthException, ServerBusy, TraktApi, TraktException

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    """A "notifier" for trakt.tv which keeps track of what has and hasn't been added to your library."""

    def notify_snatch(self, ep_name, is_proper):
        pass

    def notify_download(self, ep_name):
        pass

    def notify_subtitle_download(self, ep_name, lang):
        pass

    def notify_git_update(self, new_version):
        pass

    def notify_login(self, ipaddress=''):
        pass

    @staticmethod
    def update_library(ep_obj):
        """
        Sends a request to trakt indicating that the given episode is part of our library.

        ep_obj: The Episode object to add to trakt
        """
        # Check if TRAKT supports that indexer
        if not get_trakt_indexer(ep_obj.show.indexer):
            return

        # Create a trakt settings dict
        trakt_settings = {'trakt_api_secret': app.TRAKT_API_SECRET,
                          'trakt_api_key': app.TRAKT_API_KEY,
                          'trakt_access_token': app.TRAKT_ACCESS_TOKEN,
                          'trakt_refresh_token': app.TRAKT_REFRESH_TOKEN}

        trakt_api = TraktApi(app.SSL_VERIFY, app.TRAKT_TIMEOUT, **trakt_settings)

        if app.USE_TRAKT:
            try:
                # URL parameters
                title = get_title_without_year(ep_obj.show.name, ep_obj.show.start_year)
                data = {
                    'shows': [
                        {
                            'title': title,
                            'year': ep_obj.show.start_year,
                            'ids': {},
                        }
                    ]
                }

                data['shows'][0]['ids'][get_trakt_indexer(ep_obj.show.indexer)] = ep_obj.show.indexerid

                if app.TRAKT_SYNC_WATCHLIST:
                    if app.TRAKT_REMOVE_SERIESLIST:
                        trakt_api.request('sync/watchlist/remove', data, method='POST')

                # Add Season and Episode + Related Episodes
                data['shows'][0]['seasons'] = [{'number': ep_obj.season, 'episodes': []}]

                for relEp_Obj in [ep_obj] + ep_obj.related_episodes:
                    data['shows'][0]['seasons'][0]['episodes'].append({'number': relEp_Obj.episode})

                if app.TRAKT_SYNC_WATCHLIST:
                    if app.TRAKT_REMOVE_WATCHLIST:
                        trakt_api.request('sync/watchlist/remove', data, method='POST')

                # update library
                trakt_api.request('sync/collection', data, method='POST')

            except (TraktException, AuthException, ServerBusy) as error:
                log.debug('Unable to update Trakt: {0}', error.message)

    @staticmethod
    def update_watchlist(show_obj=None, s=None, e=None, data_show=None, data_episode=None, update='add'):

        """
        Sends a request to trakt indicating that the given episode is part of our library.

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

        trakt_settings = {'trakt_api_secret': app.TRAKT_API_SECRET,
                          'trakt_api_key': app.TRAKT_API_KEY,
                          'trakt_access_token': app.TRAKT_ACCESS_TOKEN,
                          'trakt_refresh_token': app.TRAKT_REFRESH_TOKEN}

        trakt_api = TraktApi(app.SSL_VERIFY, app.TRAKT_TIMEOUT, **trakt_settings)

        if app.USE_TRAKT:

            data = {}
            try:
                # URL parameters
                if show_obj is not None:
                    title = get_title_without_year(show_obj.name, show_obj.start_year)
                    data = {
                        'shows': [
                            {
                                'title': title,
                                'year': show_obj.start_year,
                                'ids': {},
                            }
                        ]
                    }
                    data['shows'][0]['ids'][get_trakt_indexer(show_obj.indexer)] = show_obj.indexerid
                elif data_show is not None:
                    data.update(data_show)
                else:
                    log.warning(
                        "There's a coding problem contact developer. It's needed to be provided at"
                        " least one of the two: data_show or show_obj",
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

                trakt_url = 'sync/watchlist'
                if update == 'remove':
                    trakt_url += '/remove'

                trakt_api.request(trakt_url, data, method='POST')

            except (TraktException, AuthException, ServerBusy) as error:
                log.debug('Unable to update Trakt watchlist: {0}', error.message)
                return False

        return True

    @staticmethod
    def trakt_show_data_generate(data):

        showList = []
        for indexer, indexerid, title, year in data:
            show = {'title': title, 'year': year, 'ids': {}}
            show['ids'][get_trakt_indexer(indexer)] = indexerid
            showList.append(show)

        post_data = {'shows': showList}

        return post_data

    @staticmethod
    def trakt_episode_data_generate(data):

        # Find how many unique season we have
        uniqueSeasons = []
        for season, episode in data:
            if season not in uniqueSeasons:
                uniqueSeasons.append(season)

        # build the query
        seasonsList = []
        for searchedSeason in uniqueSeasons:
            episodesList = []
            for season, episode in data:
                if season == searchedSeason:
                    episodesList.append({'number': episode})
            seasonsList.append({'number': searchedSeason, 'episodes': episodesList})

        post_data = {'seasons': seasonsList}

        return post_data

    @staticmethod
    def test_notify(username, blacklist_name=None):
        """
        Sends a test notification to trakt with the given authentication info and returns a boolean
        representing success.

        api: The api string to use
        username: The username to use
        blacklist_name: slug of trakt list used to hide not interested show

        Returns: True if the request succeeded, False otherwise
        """
        try:
            trakt_settings = {'trakt_api_secret': app.TRAKT_API_SECRET,
                              'trakt_api_key': app.TRAKT_API_KEY,
                              'trakt_access_token': app.TRAKT_ACCESS_TOKEN,
                              'trakt_refresh_token': app.TRAKT_REFRESH_TOKEN}

            trakt_api = TraktApi(app.SSL_VERIFY, app.TRAKT_TIMEOUT, **trakt_settings)
            trakt_api.validate_account()
            if blacklist_name and blacklist_name is not None:
                trakt_lists = trakt_api.request('users/' + username + '/lists')
                found = False
                for trakt_list in trakt_lists:
                    if trakt_list['ids']['slug'] == blacklist_name:
                        return 'Test notice sent successfully to Trakt'
                if not found:
                    return "Trakt blacklist doesn't exists"
            else:
                return 'Test notice sent successfully to Trakt'
        except (TraktException, AuthException, ServerBusy) as error:
            log.warning('Unable to test TRAKT: {0}', error.message)
            return 'Test notice failed to Trakt: {0}'.format(error.message)
