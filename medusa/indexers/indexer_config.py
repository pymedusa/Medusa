# coding=utf-8
# Author: p0psicles
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

from .tmdb.tmdb import Tmdb
from .tvdbv2.tvdbv2_api import TVDBv2
from .tvmaze.tvmaze_api import TVmaze
from ..helpers import make_session

initConfig = {
    'valid_languages': [
        "da", "fi", "nl", "de", "it", "es", "fr", "pl", "hu", "el", "tr",
        "ru", "he", "ja", "pt", "zh", "cs", "sl", "hr", "ko", "en", "sv", "no"
    ],
    'langabbv_to_id': {
        'el': 20, 'en': 7, 'zh': 27,
        'it': 15, 'cs': 28, 'es': 16, 'ru': 22, 'nl': 13, 'pt': 26, 'no': 9,
        'tr': 21, 'pl': 18, 'fr': 17, 'hr': 31, 'de': 14, 'da': 10, 'fi': 11,
        'hu': 19, 'ja': 25, 'he': 24, 'ko': 32, 'sv': 8, 'sl': 30
    }
}

INDEXER_TVDBV2 = 1
INDEXER_TVRAGE = 2  # Must keep
INDEXER_TVMAZE = 3
INDEXER_TMDB = 4
EXTERNAL_IMDB = 10
EXTERNAL_ANIDB = 11

EXTERNAL_MAPPINGS = {EXTERNAL_IMDB: 'imdb_id', EXTERNAL_ANIDB: 'anidb_id', INDEXER_TVRAGE: 'tvrage_id'}

indexerConfig = {
    INDEXER_TVDBV2: {
        'enabled': True,
        'id': INDEXER_TVDBV2,
        'name': 'TVDBv2',
        'module': TVDBv2,
        'api_params': {
            'language': 'en',
            'use_zip': True,
            'session': make_session(cache_etags=False),
        },
        'trakt_id': 'tvdb_id',
        'xem_origin': 'tvdb',
        'icon': 'thetvdb16.png',
        'scene_loc': 'https://cdn.pymedusa.com/scene_exceptions/scene_exceptions_tvdb.json',
        'base_url': 'https://api.thetvdb.com',
        'show_url': 'http://thetvdb.com/?tab=series&id=',
        'mapped_to': 'tvdb_id',  # The attribute to which other indexers can map there thetvdb id to
        'identifier': 'tvdb',  # Also used as key for the custom scenename exceptions. (_get_custom_exceptions())
    },
    INDEXER_TVMAZE: {
        'enabled': True,
        'id': INDEXER_TVMAZE,
        'name': 'TVmaze',
        'module': TVmaze,
        'api_params': {
            'language': 'en',
            'use_zip': True,
            'session': make_session(cache_etags=False),
        },
        'trakt_id': 'tvdb_id',
        'xem_mapped_to': INDEXER_TVDBV2,
        'icon': 'tvmaze16.png',
        'scene_loc': 'https://cdn.pymedusa.com/scene_exceptions/scene_exceptions_tvmaze.json',
        'show_url': 'http://www.tvmaze.com/shows/',
        'base_url': 'http://api.tvmaze.com/',
        'mapped_to': 'tvmaze_id',  # The attribute to which other indexers can map there tvmaze id to
        'identifier': 'tvmaze',  # Also used as key for the custom scenename exceptions. (_get_custom_exceptions())
    },
    INDEXER_TMDB: {
        'enabled': True,
        'id': INDEXER_TMDB,
        'name': 'TMDB',
        'module': Tmdb,
        'api_params': {
            'language': 'en',
            'use_zip': True,
            'session': make_session(cache_etags=False),
        },
        'trakt_id': 'tvdb_id',
        'icon': 'tmdb16.png',
        'scene_loc': 'https://cdn.pymedusa.com/scene_exceptions/scene_exceptions_tmdb.json',
        'base_url': 'https://www.themoviedb.org',
        'show_url': 'https://www.themoviedb.org/tv/',
        'mapped_to': 'tmdb_id',  # The attribute to which other indexers can map there tmdb id to
        'identifier': 'tmdb',  # Also used as key for the custom scenename exceptions. (_get_custom_exceptions())
    }
}

# For example: {1: 'tvdb_id', 3: 'tvmaze_id', 4: 'tmdb_id'}
mappings = {indexer: indexerConfig[indexer]['mapped_to'] for indexer in indexerConfig}
mappings.update(EXTERNAL_MAPPINGS)

# For example: {'tvdb_id': 1, 'tvmaze_id': 3, 'tmdb_id': 4}
reverse_mappings = {indexerConfig[indexer]['mapped_to']: indexer for indexer in indexerConfig}
reverse_mappings.update({v: k for k, v in EXTERNAL_MAPPINGS.items()})
