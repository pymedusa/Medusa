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
from sickbeard import logger
from sickrage.helper.exceptions import ex

from sickbeard import helpers
from sickrage.helper.common import try_int
from adba.aniDBtvDBmaper import TvDBMap
from simpleanidb import (Anidb, REQUEST_CATEGORY_LIST, REQUEST_HOT, REQUEST_RANDOM_RECOMMENDATION)
from simpleanidb.exceptions import GeneralError
from .recommended import RecommendedShow


class AnidbPopular(object):  # pylint: disable=too-few-public-methods
    def __init__(self):
        """This class retrieves a speficed recommended show list from Trakt
        The list of returned shows is mapped to a RecommendedShow object"""
        self.cache_subfolder = __name__.split('.')[-1] if '.' in __name__ else __name__
        self.session = helpers.make_session()
        self.recommender = "Anidb Popular"
        self.default_img_src = ''

    def _create_recommended_show(self, show_obj):
        """creates the RecommendedShow object from the returned showobj"""
        try:
            tvdb_id = TvDBMap().get_tvdb_for_anidb(show_obj.aid)
        except Exception:
            tvdb_id = None
            logger.log("Couldn't map aid [{0}] to tvdbid ".format(show_obj.aid), logger.WARNING)
            return

        rec_show = RecommendedShow(self, show_obj.aid, show_obj.title['x-jat'], 1, tvdb_id,
                                   **{'rating': show_obj.ratings['permanent']['votes'],
                                      'votes': show_obj.ratings['permanent']['count'],
                                      'image_href': show_obj.url})

        # Check cache or get and save image
        rec_show.cache_image("http://img7.anidb.net/pics/anime/{0}".format(show_obj.picture))

        return rec_show

    def fetch_popular_shows(self, list_type=REQUEST_HOT):
        """Get popular show information from IMDB"""
        shows = []
        result = []

        try:
            shows = Anidb().get_list(list_type)
        except GeneralError, e:
            logger.log(u"Could not connect to Anidb service: %s" % ex(e), logger.WARNING)

        for show in shows:
            try:
                result.append(self._create_recommended_show(show))
            except Exception, e:
                logger.log(u"Could not parse Anidb show, with exception: %s" % ex(e), logger.WARNING)

        return result

anidb_popular = AnidbPopular()
