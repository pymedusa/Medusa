# coding=utf-8
#
# URL: https://sickrage.github.io
#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage. If not, see <http://www.gnu.org/licenses/>.

import requests
import sickbeard
from sickbeard import logger
from sickrage.helper.common import try_int

from libtrakt.trakt import TraktApi
from libtrakt.exceptions import TraktAuthException, TraktException

from sickrage.show.Show import Show
from sickrage.helper.exceptions import ex
from sickrage.helper.exceptions import MultipleShowObjectsException
from .recommended import RecommendedShow


class TraktPopular(object):
    """This class retrieves a speficed recommended show list from Trakt
    The list of returned shows is mapped to a RecommendedShow object"""
    def __init__(self):
        self.cache_subfolder = __name__.split('.')[-1] if '.' in __name__ else __name__
        self.session = requests.Session()
        self.recommender = "Trakt Popular"
        self.default_img_src = 'http://www.trakt.tv/assets/placeholders/thumb/poster-2d5709c1b640929ca1ab60137044b152.png'

    def _create_recommended_show(self, show_obj):
        """creates the RecommendedShow object from the returned showobj"""
        rec_show = RecommendedShow(self,
                                   show_obj['show']['ids'], show_obj['show']['title'],
                                   1,  # indexer
                                   show_obj['show']['ids']['tvdb'],
                                   rating=str(show_obj['show']['rating']),
                                   votes=str(try_int(show_obj['show']['votes'], 0)),
                                   image_href='http://www.trakt.tv/shows/%s' % show_obj['show']['ids']['slug'])

        rec_show.cache_image(show_obj['show']['images']['poster']['thumb'] or self.default_img_src)

        return rec_show

    def fetch_and_refresh_token(self, trakt_api, path):
        try:
            library_shows = trakt_api.request(path) or []
            if trakt_api.access_token_refreshed:
                sickbeard.TRAKT_ACCESS_TOKEN = trakt_api.access_token
                sickbeard.TRAKT_REFRESH_TOKEN = trakt_api.refresh_token
        except TraktAuthException:
            logger.log(u"Refreshing Trakt token", logger.DEBUG)
            (access_token, refresh_token) = trakt_api.get_token(sickbeard.TRAKT_REFRESH_TOKEN)
            if access_token:
                sickbeard.TRAKT_ACCESS_TOKEN = access_token
                sickbeard.TRAKT_REFRESH_TOKEN = refresh_token
                library_shows = trakt_api.request(path) or []

        return library_shows

    def fetch_popular_shows(self, page_url=None, trakt_list=None):  # pylint: disable=too-many-nested-blocks,too-many-branches
        """
        Get a list of popular shows from different Trakt lists based on a provided trakt_list
        :param page_url: the page url opened to the base api url, for retreiving a specific list
        :param trakt_list: a description of the trakt list
        :return: A list of RecommendedShow objects, an empty list of none returned
        :throw: ``Exception`` if an Exception is thrown not handled by the libtrats exceptions
        """
        trending_shows = []

        # Create a trakt settings dict
        trakt_settings = {"trakt_api_secret": sickbeard.TRAKT_API_SECRET, "trakt_api_key": sickbeard.TRAKT_API_KEY,
                          "trakt_access_token": sickbeard.TRAKT_ACCESS_TOKEN}

        trakt_api = TraktApi(sickbeard.SSL_VERIFY, sickbeard.TRAKT_TIMEOUT, **trakt_settings)

        try:  # pylint: disable=too-many-nested-blocks
            not_liked_show = ""
            if sickbeard.TRAKT_ACCESS_TOKEN != '':
                library_shows = self.fetch_and_refresh_token(trakt_api, "sync/collection/shows?extended=full")

                if sickbeard.TRAKT_BLACKLIST_NAME is not None and sickbeard.TRAKT_BLACKLIST_NAME:
                    not_liked_show = trakt_api.request("users/" + sickbeard.TRAKT_USERNAME + "/lists/" +
                                                       sickbeard.TRAKT_BLACKLIST_NAME + "/items") or []
                else:
                    logger.log(u"Trakt blacklist name is empty", logger.DEBUG)

            if trakt_list not in ["recommended", "newshow", "newseason"]:
                limit_show = "?limit=" + str(100 + len(not_liked_show)) + "&"
            else:
                limit_show = "?"

            shows = self.fetch_and_refresh_token(trakt_api, page_url + limit_show + "extended=full,images") or []

            if sickbeard.TRAKT_ACCESS_TOKEN != '':
                library_shows = self.fetch_and_refresh_token(trakt_api, "sync/collection/shows?extended=full") or []

            for show in shows:
                try:
                    if 'show' not in show:
                        show['show'] = show

                    if sickbeard.TRAKT_ACCESS_TOKEN != '':
                        if show['show']['ids']['tvdb'] not in (lshow['show']['ids']['tvdb']
                                                               for lshow in library_shows):
                            if not_liked_show:
                                if show['show']['ids']['tvdb'] not in (show['show']['ids']['tvdb']
                                                                       for show in not_liked_show if show['type'] == 'show'):
                                    trending_shows.append(self._create_recommended_show(show))
                            else:
                                trending_shows.append(self._create_recommended_show(show))
                    else:
                        if not_liked_show:
                            if show['show']['ids']['tvdb'] not in (show['show']['ids']['tvdb']
                                                                   for show in not_liked_show if show['type'] == 'show'):
                                trending_shows.append(self._create_recommended_show(show))
                        else:
                            trending_shows.append(self._create_recommended_show(show))

                except MultipleShowObjectsException:
                    continue

            blacklist = sickbeard.TRAKT_BLACKLIST_NAME not in ''

        except TraktException as e:
            logger.log(u"Could not connect to Trakt service: %s" % ex(e), logger.WARNING)

        return (blacklist, trending_shows)
