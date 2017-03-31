# coding=utf-8
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

import os
import posixpath

from ... import app, helpers


class MissingTvdbMapping(Exception):
    """Exception used when a show can't be mapped to a tvdb indexer id."""


class RecommendedShow(object):
    """Base class for show recommendations."""
    def __init__(self, rec_show_prov, show_id, title, indexer, indexer_id, **show_attr):
        """Create a show recommendation

        :param rec_show_prov: Recommended shows provider. Used to keep track of the provider,
                              which facilitated the recommended shows list.
        :param show_id: as provided by the list provider
        :param title: of the show as displayed in the recommended show page
        :param indexer: used to map the show to
        :param indexer_id: a mapped indexer_id for indexer
        :param rating: of the show in percent
        :param votes: number of votes
        :param image_href: the href when clicked on the show image (poster)
        :param image_src: the local url to the "cached" image (poster)
        :param default_img_src: a default image when no poster available
        """
        self.recommender = rec_show_prov.recommender
        self.cache_subfolder = rec_show_prov.cache_subfolder or 'recommended'
        self.default_img_src = getattr(rec_show_prov, 'default_img_src', '')

        self.show_id = show_id
        self.title = title
        self.indexer = int(indexer)
        try:
            self.indexer_id = int(indexer_id)
        except ValueError:
            raise MissingTvdbMapping('Could not parse the indexer_id [%s]' % indexer_id)

        self.rating = show_attr.get('rating') or 0

        self.votes = show_attr.get('votes')
        if self.votes and not isinstance(self.votes, int):
            trans_mapping = {ord(c): None for c in ['.', ',']}
            self.votes = int(self.votes.decode('utf-8').translate(trans_mapping))

        self.image_href = show_attr.get('image_href')
        self.image_src = show_attr.get('image_src')
        self.ids = show_attr.get('ids', {})
        self.is_anime = False

        # Check if the show is currently already in the db
        self.show_in_list = self.indexer_id in {show.indexerid for show in app.showList if show.indexerid}
        self.session = helpers.make_session()

    def cache_image(self, image_url, default=None):
        """Store cache of image in cache dir

        :param image_url: Source URL
        :param default: default folder
        """
        if default:
            self.image_src = posixpath.join('images', default)
            return

        if not self.cache_subfolder:
            return

        path = os.path.abspath(os.path.join(app.CACHE_DIR, 'images', self.cache_subfolder))

        if not os.path.exists(path):
            os.makedirs(path)

        full_path = os.path.join(path, os.path.basename(image_url))

        self.image_src = posixpath.join('cache', 'images', self.cache_subfolder, os.path.basename(image_url))

        if not os.path.isfile(full_path):
            helpers.download_file(image_url, full_path, session=self.session)

    def check_if_anime(self, anidb, tvdbid):
        """Use the simpleanidb lib, to check the anime-lists.xml for an anime show mapping with this tvdbid.

        The show if flagged as anime, through the is_anime attribute.
        :param anidb: simpleanidb.Anidb() class instance, for reducing the amounts of objects that are instantiated
        :param tvdbid: thetvdb id of the show, for which you want to try mapping to an anidb show
        :return: Returns True, when the show can be mapped to anidb.net, False if not.
        """
        try:
            anime = anidb.tvdb_id_to_aid(tvdbid=tvdbid)
        except Exception:
            return False
        else:
            if anime:
                # flag the show as anime
                self.is_anime = True
                # Write the anidb aid to the dictionary of id's
                self.ids['aid'] = anime[0]
                return True
        return False

    def __str__(self):
        """Return a string repr of the recommended list."""
        return 'Recommended show {0} from recommended list: {1}'.format(self.title, self.recommender)
