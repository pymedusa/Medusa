# coding=utf-8

# Author: Dieter Blomme <dieterblomme@gmail.com>
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

from traktor import AuthException, ServerBusy, TraktApi, TraktException
from .. import app, logger
from ..helper.exceptions import ex
from ..indexers.indexer_api import indexerApi


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

        ep_obj: The TVEpisode object to add to trakt
        """

        trakt_id = indexerApi(ep_obj.show.indexer).config['trakt_id']
        # Create a trakt settings dict
        trakt_settings = {'trakt_api_secret': app.TRAKT_API_SECRET,
                          'trakt_api_key': app.TRAKT_API_KEY,
                          'trakt_access_token': app.TRAKT_ACCESS_TOKEN,
                          'trakt_refresh_token': app.TRAKT_REFRESH_TOKEN}

        trakt_api = TraktApi(app.SSL_VERIFY, app.TRAKT_TIMEOUT, **trakt_settings)

        if app.USE_TRAKT:
            try:
                # URL parameters
                data = {
                    'shows': [
                        {
                            'title': ep_obj.show.name,
                            'year': ep_obj.show.start_year,
                            'ids': {},
                        }
                    ]
                }

                if trakt_id == 'tvdb_id':
                    data['shows'][0]['ids']['tvdb'] = ep_obj.show.indexerid
                else:
                    data['shows'][0]['ids']['tvrage'] = ep_obj.show.indexerid

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

            except (TraktException, AuthException, ServerBusy) as trakt_ex:
                logger.log('Could not connect to Trakt service: {0}'.format(ex(trakt_ex)), logger.WARNING)

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
                    trakt_id = indexerApi(show_obj.indexer).config['trakt_id']
                    data = {
                        'shows': [
                            {
                                'title': show_obj.name,
                                'year': show_obj.start_year,
                                'ids': {},
                            }
                        ]
                    }

                    if trakt_id == 'tvdb_id':
                        data['shows'][0]['ids']['tvdb'] = show_obj.indexerid
                    else:
                        data['shows'][0]['ids']['tvrage'] = show_obj.indexerid
                elif data_show is not None:
                    data.update(data_show)
                else:
                    logger.log("There's a coding problem contact developer. "
                               "It's needed to be provided at least one of the two: data_show or show_obj",
                               logger.WARNING)
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

            except (TraktException, AuthException, ServerBusy) as trakt_ex:
                logger.log('Could not connect to Trakt service: {0}'.format(ex(trakt_ex)), logger.WARNING)
                return False

        return True

    @staticmethod
    def trakt_show_data_generate(data):

        showList = []
        for indexer, indexerid, title, year in data:
            trakt_id = indexerApi(indexer).config['trakt_id']
            show = {'title': title, 'year': year, 'ids': {}}
            if trakt_id == 'tvdb_id':
                show['ids']['tvdb'] = indexerid
            else:
                show['ids']['tvrage'] = indexerid
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
        except (TraktException, AuthException, ServerBusy) as trakt_ex:
            logger.log('Could not connect to Trakt service: {0}'.format(ex(trakt_ex)), logger.WARNING)
            return 'Test notice failed to Trakt: {0}'.format(ex(trakt_ex))
