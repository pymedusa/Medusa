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
from collections import defaultdict
from datetime import datetime
from os.path import join

from medusa import app, db, helpers
from medusa.cache import recommended_series_cache
from medusa.helpers import ensure_list
from medusa.helpers.externals import load_externals_from_db, save_externals_to_db, show_in_library
from medusa.imdb import Imdb
from medusa.indexers.config import EXTERNAL_ANIDB, EXTERNAL_ANILIST, EXTERNAL_IMDB, EXTERNAL_TRAKT
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import MedusaSession

from simpleanidb import Anidb

from six import PY2, ensure_text

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

session = MedusaSession()


class LazyApi(object):
    """Decorators to lazily construct API classes."""

    imdb_api = None
    anidb_api = None

    @classmethod
    def load_anidb_api(cls, func):
        """
        Decorate a function to lazy load the anidb_api.

        We need to do this, because we're passing the Medusa cache location to the lib. As the module is imported before
        the app.CACHE_DIR location has been read, we can't initialize it at module level.
        """
        def func_wrapper(*args, **kwargs):
            if cls.anidb_api is None:
                cls.anidb_api = Anidb(cache_dir=join(app.CACHE_DIR, 'simpleanidb'))
            return func(*args, **kwargs)
        return func_wrapper

    @classmethod
    def load_imdb_api(cls, func):
        """
        Decorate a function to lazy load the imdb_api.

        We need to do this, because we're overriding the cache location of the library.
        As the module is imported before the app.CACHE_DIR location has been read, we can't initialize it at module level.
        """
        def func_wrapper(*args, **kwargs):
            if cls.imdb_api is None:
                cls.imdb_api = Imdb(session=session)
            return func(*args, **kwargs)
        return func_wrapper


class MissingTvdbMapping(Exception):
    """Exception used when a show can't be mapped to a tvdb indexer id."""


class BasePopular(object):
    """BasePopular class."""

    def __init__(self, recommender=None, source=None, cache_subfoler=None):
        """Recommended show base class (AnidbPopular, TraktPopular, etc)."""
        self.session = MedusaSession()
        self.recommender = recommender
        self.source = source
        self.cache_subfolder = 'recommended'
        self.default_img_src = 'poster.png'
        self.mapped_indexer = None
        self.mapped_series_id = None
        self.mapped_indexer_name = None


class RecommendedShow(BasePopular):
    """Base class for show recommendations."""

    def __init__(self, rec_show_prov, series_id, title, **show_attr):
        """Create a show recommendation.

        :param rec_show_prov: Recommended shows provider. Used to keep track of the provider,
                              which facilitated the recommended shows list.
        :param series_id: as provided by the list provider
        :param title: of the show as displayed in the recommended show page
        :param rating: of the show in percent
        :param votes: number of votes
        :param image_href: the href when clicked on the show image (poster)
        :param image_src: the local url to the "cached" image (poster)
        :param default_img_src: a default image when no poster available
        :param
        """
        super(RecommendedShow, self).__init__(rec_show_prov, rec_show_prov.source)
        self.cache_subfolder = rec_show_prov.cache_subfolder or 'recommended'
        self.default_img_src = getattr(rec_show_prov, 'default_img_src', '')

        self.series_id = series_id
        self.title = title

        # The slug to the show in the library if already added.
        self.library_slug = None

        self.rating = float(show_attr.get('rating') or 0)

        self.votes = show_attr.get('votes')
        if self.votes and not isinstance(self.votes, int):
            trans_mapping = {ord(c): None for c in ['.', ',']}
            if PY2:
                self.votes = int(self.votes.decode('utf-8').translate(trans_mapping))
            else:
                self.votes = int(self.votes.translate(trans_mapping))

        self.image_href = show_attr.get('image_href')
        self.image_src = show_attr.get('image_src')
        self.ids = show_attr.get('ids', {})
        self.is_anime = show_attr.get('is_anime', False)
        self.subcat = show_attr.get('subcat')
        self.genres = show_attr.get('genres', [])
        self.plot = show_attr.get('plot', '')

        self.show_in_list = None
        show_obj = show_in_library(self.source, self.series_id)
        if show_obj:
            self.show_in_list = show_obj.identifier.slug

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

    def save_to_db(self):
        """Insert or update the recommended show to db."""
        recommended_db_con = db.DBConnection('recommended.db')
        # Add to db

        existing_show = recommended_db_con.select(
            'SELECT recommended_show_id from shows WHERE source = ? AND series_id = ?',
            [self.source, self.series_id]
        )
        if not existing_show:
            recommended_db_con.action(
                'INSERT INTO shows '
                '    (source, series_id, mapped_indexer, '
                '     mapped_series_id, title, rating, '
                '     votes, is_anime, image_href, '
                '     image_src, subcat, added, genres, plot) '
                'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                [self.source, self.series_id, self.mapped_indexer, self.mapped_series_id, self.title, self.rating, self.votes,
                 int(self.is_anime), self.image_href, self.image_src, self.subcat, datetime.now(), ','.join(self.genres), self.plot]
            )
        else:
            query = """UPDATE shows SET title = ?, rating = ?, votes = ?,
                    is_anime = ?, image_href = ?, image_src = ?, subcat = ?, genres = ?, plot = ?
                    WHERE recommended_show_id = ?"""
            params_set = [
                self.title, self.rating, self.votes, int(self.is_anime),
                self.image_href, self.image_src, self.subcat, ','.join(self.genres), self.plot
            ]
            params_where = [existing_show[0]['recommended_show_id']]

            if self.mapped_indexer and self.mapped_series_id:
                query = query.format(mapped_indexer_and_id=', mapped_indexer = ?, mapped_series_id = ?')
                params_set += [self.mapped_indexer, self.mapped_series_id]
            else:
                query = query.format(mapped_indexer_and_id='')

            recommended_db_con.action(query, params_set + params_where)
        # If there are any external id's, save them to main/indexer_mappings
        if self.ids:
            save_externals_to_db(self.source, self.series_id, self.ids)

    def to_json(self):
        """Return JSON representation."""
        data = {}
        data['source'] = self.source
        data['cacheSubfolder'] = self.cache_subfolder
        data['seriesId'] = self.series_id
        data['title'] = self.title
        data['mappedIndexer'] = self.mapped_indexer
        data['mappedIndexerName'] = self.mapped_indexer_name
        data['mappedSeriesId'] = self.mapped_series_id
        data['rating'] = self.rating
        data['votes'] = self.votes
        data['imageHref'] = self.image_href
        data['imageSrc'] = self.image_src
        data['externals'] = self.ids
        data['isAnime'] = self.is_anime
        data['showInLibrary'] = self.show_in_list
        data['trakt'] = {
            'blacklisted': False
        },
        data['subcat'] = self.subcat
        data['genres'] = self.genres
        data['plot'] = self.plot

        return data


def get_recommended_shows(source=None, series_id=None):
    """
    Retrieve recommended shows from the db cache/recommended table.

    All shows are transformed to Recommended objects.
    :param source: The Indexer or External source ID
    :returns: A list of Rcommended objects.
    """
    recommended_db_con = db.DBConnection('recommended.db')
    query = 'SELECT * FROM shows {where}'
    where = []
    params = []

    # Query filter options
    if source:
        where.append('source = ?')
        params.append(source)

    if series_id:
        where.append('series_id = ?')
        params.append(series_id)

    shows = recommended_db_con.select(
        query.format(where='' if not where else ' WHERE ' + ' AND '.join(where)), params
    )

    recommended_shows = []
    from medusa.show.recommendations.anidb import AnidbPopular
    from medusa.show.recommendations.imdb import ImdbPopular
    from medusa.show.recommendations.trakt import TraktPopular
    from medusa.show.recommendations.anilist import AniListPopular

    mapped_source = {
        EXTERNAL_TRAKT: TraktPopular,
        EXTERNAL_ANIDB: AnidbPopular,
        EXTERNAL_IMDB: ImdbPopular,
        EXTERNAL_ANILIST: AniListPopular
    }

    for show in shows:
        # Get the external id's
        externals = load_externals_from_db(show['source'], show['series_id'])

        recommended_shows.append(
            RecommendedShow(
                BasePopular(
                    recommender=mapped_source.get(show['source']).TITLE,
                    source=show['source'],
                    cache_subfoler=mapped_source.get(show['source']).CACHE_SUBFOLDER
                ),
                show['series_id'],
                show['title'],
                **{
                    'rating': show['rating'],
                    'votes': show['votes'],
                    'image_href': show['image_href'],
                    'image_src': show['image_src'],
                    'ids': externals,
                    'subcat': show['subcat'],
                    'mapped_indexer': show['mapped_indexer'],
                    'mapped_series_id': show['mapped_series_id'],
                    'genres': [genre for genre in show['genres'].split(',') if genre],
                    'plot': show['plot']
                }
            )
        )
    return recommended_shows


def get_categories():
    """Compile a structure with the sources and their available sub-categories."""
    recommended_db_con = db.DBConnection('recommended.db')
    results = recommended_db_con.select('SELECT source, subcat FROM shows GROUP BY source, subcat')
    categories = defaultdict(list)
    for result in results:
        categories[result['source']].append(result['subcat'])

    return categories


def create_key(namespace, fn, **kw):
    """Create key out of namespace + firs arg."""
    def generate_key(*args, **kw):
        show_key = f'{namespace}|{args[0]}'
        return show_key
    return generate_key


@LazyApi.load_anidb_api
@recommended_series_cache.cache_on_arguments(namespace='tvdb_to_anidb', function_key_generator=create_key)
def cached_tvdb_to_aid(tvdb_id):
    """
    Try to match an anidb id with a tvdb id.

    Use dogpile cache to return a cached id if available.
    """
    return LazyApi.anidb_api.tvdb_id_to_aid(tvdbid=tvdb_id)


@LazyApi.load_anidb_api
@recommended_series_cache.cache_on_arguments(namespace='anidb_to_tvdb', function_key_generator=create_key)
def cached_aid_to_tvdb(aid):
    """
    Try to match a tvdb id with an anidb id.

    Use dogpile cache to return a cached id if available.
    """
    return LazyApi.anidb_api.aid_to_tvdb_id(aid=aid)


@LazyApi.load_imdb_api
@recommended_series_cache.cache_on_arguments(namespace='series_details', function_key_generator=create_key)
def cached_get_imdb_series_details(imdb_id):
    """
    Request the series details from the imdbpie api.

    Use dogpile cache to return a cached id if available.
    """
    details = LazyApi.imdb_api.get_title(imdb_id)
    if not details:
        raise Exception(f'Could not get imdb details from {imdb_id}')
    return details


@LazyApi.load_imdb_api
@recommended_series_cache.cache_on_arguments(namespace='series_genres', function_key_generator=create_key)
def cached_get_imdb_series_genres(imdb_id):
    """
    Request the series genres from the imdbpie api.

    Use dogpile cache to return a cached id if available.
    """
    genres = LazyApi.imdb_api.get_title_genres(imdb_id)
    if not genres:
        raise Exception(f'Could not get imdb genres from {imdb_id}')
    return genres


def create_key_from_series(namespace, fn, **kw):
    """Create a key made of indexer name and show ID."""
    def generate_key(*args, **kw):
        if args[1].get('imdb_tt'):
            show_id = args[1]['imdb_tt']
        elif args[1].get('id'):
            show_id = args[1]['id']
        else:
            raise Exception('Could not get a show id for dogpile caching.')

        show_key = f'{namespace}_{show_id}'
        return show_key
    return generate_key


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
        index = recommended_series_cache.get(ensure_text(indexer))
        if not index:
            continue

        for index_item in index:
            key = '{indexer}_{series_id}'.format(indexer=indexer, series_id=index_item)
            series = recommended_series_cache.get(key)
            if series:
                all_series.append(series)

    return all_series
