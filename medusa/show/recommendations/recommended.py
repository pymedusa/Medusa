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

import logging
import os
import posixpath

from imdbpie import imdbpie

from medusa import (
    app,
    helpers,
)
from medusa.cache import recommended_series_cache
from medusa.helpers import ensure_list
from medusa.indexers.utils import indexer_id_to_name
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import MedusaSession

from simpleanidb import Anidb

from six import binary_type


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

session = MedusaSession()
imdb_api = imdbpie.Imdb(session=session)

anidb_api = None


def load_anidb_api(func):
    """
    Decorate a function to lazy load the anidb_api.

    We need to do this, because we're passing the Medusa cache location to the lib. As the module is imported before
    the app.CACHE_DIR location has been read, we can't initialize it at module level.
    """
    def func_wrapper(aid):
        global anidb_api
        if anidb_api is None:
            anidb_api = Anidb(cache_dir=app.CACHE_DIR)
        return func(aid)
    return func_wrapper


class MissingTvdbMapping(Exception):
    """Exception used when a show can't be mapped to a tvdb indexer id."""


class RecommendedShow(object):
    """Base class for show recommendations."""

    def __init__(self, rec_show_prov, series_id, title, mapped_indexer, mapped_series_id, **show_attr):
        """Create a show recommendation.

        :param rec_show_prov: Recommended shows provider. Used to keep track of the provider,
                              which facilitated the recommended shows list.
        :param series_id: as provided by the list provider
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

        self.series_id = series_id
        self.title = title
        self.mapped_indexer = int(mapped_indexer)
        self.mapped_indexer_name = indexer_id_to_name(mapped_indexer)
        try:
            self.mapped_series_id = int(mapped_series_id)
        except ValueError:
            raise MissingTvdbMapping('Could not parse the indexer_id [%s]' % mapped_series_id)

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
        self.show_in_list = bool([show.indexerid for show in app.showList
                                 if show.series_id == self.mapped_series_id
                                 and show.indexer == self.mapped_indexer])
        self.session = session

    def cache_image(self, image_url, default=None):
        """Store cache of image in cache dir.

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

    def flag_as_anime(self, tvdbid):
        """Use the simpleanidb lib, to check the anime-lists.xml for an anime show mapping with this tvdbid.

        The show if flagged as anime, through the is_anime attribute.
        :param anidb: simpleanidb.Anidb() class instance, for reducing the amounts of objects that are instantiated
        :param tvdbid: thetvdb id of the show, for which you want to try mapping to an anidb show
        :return: Returns True, when the show can be mapped to anidb.net, False if not.
        """
        try:
            anime = cached_tvdb_to_aid(tvdbid)
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


@load_anidb_api
@recommended_series_cache.cache_on_arguments()
def cached_tvdb_to_aid(tvdb_id):
    """
    Try to match an anidb id with a tvdb id.

    Use dogpile cache to return a cached id if available.
    """
    return anidb_api.tvdb_id_to_aid(tvdbid=tvdb_id)


@load_anidb_api
@recommended_series_cache.cache_on_arguments()
def cached_aid_to_tvdb(aid):
    """
    Try to match a tvdb id with an anidb id.

    Use dogpile cache to return a cached id if available.
    """
    return anidb_api.aid_to_tvdb_id(aid=aid)


@recommended_series_cache.cache_on_arguments()
def cached_get_imdb_series_details(imdb_id):
    """
    Request the series details from the imdbpie api.

    Use dogpile cache to return a cached id if available.
    """
    return imdb_api.get_title(imdb_id)


def create_key_from_series(namespace, fn, **kw):
    """Generate a key limiting the amount of dictionaries keys that are allowed to be used."""
    def generate_key(*arg, **kwargs):
        """
        Generate the key.

        The key is passed to the decorated function using the kwargs `storage_key`.
        Following this standard we can cache every object, using this key_generator.
        """
        try:
            return binary_type(kwargs['storage_key'])
        except KeyError:
            log.exception('Make sure you pass kwargs parameter `storage_key` to configure the key,'
                          ' that is used in the dogpile cache.')

    return generate_key


def update_recommended_series_cache_index(indexer, new_index):
    """
    Create a key that's used to store an index with all shows saved in cache for a specific indexer. For example 'imdb'.

    :param indexer: Indexer in the form of a string. For example: 'imdb', 'trakt', 'anidb'.
    :new_index: Iterable with series id's.
    """
    index = recommended_series_cache.get(binary_type(indexer)) or set()
    index.update(set(new_index))
    recommended_series_cache.set(binary_type(indexer), index)


def get_all_recommended_series_from_cache(indexers):
    """
    Retrieve all recommended show objects from the dogpile cache for a specific indexer or a number of indexers.

    For example: `get_all_recommended_series_from_cache(['imdb', 'anidb'])` will return all recommended show objects, for the
    indexers imdb and anidb.

    :param indexers: indexer or list of indexers. Indexers need to be passed as a string. For example: 'imdb', 'anidb' or 'trakt'.
    :return: List of recommended show objects.
    """
    indexers = ensure_list(indexers)
    all_series = []
    for indexer in indexers:
        index = recommended_series_cache.get(binary_type(indexer))
        if not index:
            continue

        for index_item in index:
            key = b'{indexer}_{series_id}'.format(indexer=indexer, series_id=index_item)
            series = recommended_series_cache.get(binary_type(key))
            if series:
                all_series.append(series)

    return all_series
