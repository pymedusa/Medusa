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

from simpleanidb import (Anidb, REQUEST_HOT)
from simpleanidb.exceptions import GeneralError
import sickbeard
from sickbeard import logger, helpers
from .recommended import RecommendedShow


class AnidbPopular(object):  # pylint: disable=too-few-public-methods
    def __init__(self):
        """This class retrieves a speficed recommended show list from Trakt
        The list of returned shows is mapped to a RecommendedShow object"""
        self.cache_subfolder = __name__.split('.')[-1] if '.' in __name__ else __name__
        self.session = helpers.make_session()
        self.recommender = "Anidb Popular"
        self.base_url = 'https://anidb.net/perl-bin/animedb.pl?show=anime&aid={aid}'
        self.anidb = Anidb(cache_dir=sickbeard.CACHE_DIR)

    def _create_recommended_show(self, show_obj):
        """creates the RecommendedShow object from the returned showobj"""
        try:
            tvdb_id = self.anidb.aid_to_tvdb_id(show_obj.aid)
        except Exception:
            tvdb_id = None
            logger.log("Couldn't map aid [{0}] to tvdbid ".format(show_obj.aid), logger.WARNING)
            return

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
        except GeneralError, e:
            logger.log('Could not connect to Anidb service: {0!r}'.format(e), logger.WARNING)

        for show in shows:
            try:
                result.append(self._create_recommended_show(show))
            except Exception as e:
                logger.log('Could not parse Anidb show, with exception: {0!r}'.format(e), logger.WARNING)

        return result

anidb_popular = AnidbPopular()
