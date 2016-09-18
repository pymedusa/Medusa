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
from __future__ import unicode_literals

import traceback

import medusa as sickbeard
from medusa import helpers, logger
from simpleanidb import (Anidb, REQUEST_HOT)
from simpleanidb.exceptions import GeneralError
from .recommended import RecommendedShow


class AnidbPopular(object):  # pylint: disable=too-few-public-methods
    def __init__(self):
        """Class retrieves a specified recommended show list from Trakt.

        List of returned shows is mapped to a RecommendedShow object
        """
        self.cache_subfolder = __name__.split('.')[-1] if '.' in __name__ else __name__
        self.session = helpers.make_session()
        self.recommender = "Anidb Popular"
        self.base_url = 'https://anidb.net/perl-bin/animedb.pl?show=anime&aid={aid}'
        self.anidb = Anidb(cache_dir=sickbeard.CACHE_DIR)

    def _create_recommended_show(self, show_obj):
        """Create the RecommendedShow object from the returned showobj"""
        try:
            tvdb_id = self.anidb.aid_to_tvdb_id(show_obj.aid)
        except Exception:
            logger.log("Couldn't map aid [{0}] to tvdbid ".format(show_obj.aid), logger.WARNING)
            return None

        # If the anime can't be mapped to a tvdb_id, return none, and move on to the next.
        if not tvdb_id:
            return tvdb_id

        rec_show = RecommendedShow(self,
                                   show_obj.aid,
                                   show_obj.title,
                                   1,
                                   tvdb_id,
                                   **{'rating': show_obj.rating_permanent,
                                      'votes': show_obj.count_permanent,
                                      'image_href': self.base_url.format(aid=show_obj.aid),
                                      'ids': {'tvdb': tvdb_id,
                                              'aid': show_obj.aid
                                              }
                                      }
                                   )

        # Check cache or get and save image
        rec_show.cache_image(show_obj.picture.url)

        # By default pre-configure the show option anime = True
        rec_show.is_anime = True

        return rec_show

    def fetch_popular_shows(self, list_type=REQUEST_HOT):
        """Get popular show information from IMDB"""
        shows = []
        result = []

        try:
            shows = self.anidb.get_list(list_type)
        except GeneralError as e:
            logger.log('Could not connect to Anidb service: {0!r}'.format(e), logger.WARNING)

        for show in shows:
            try:
                recommended_show = self._create_recommended_show(show)
                if recommended_show:
                    result.append(recommended_show)
            except Exception:
                logger.log('Could not parse Anidb show, with exception: {0!r}'.format(traceback.format_exc()), logger.WARNING)

        return result
