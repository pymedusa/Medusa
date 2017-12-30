# coding=utf-8

"""Indexer config module."""

import re

from medusa.app import BASE_PYMEDUSA_URL
from medusa.indexers.tmdb.tmdb import Tmdb
from medusa.indexers.tvdb.api import TVDBv2
from medusa.indexers.tvmaze.api import TVmaze
from medusa.session.core import MedusaSession


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
EXTERNAL_TRAKT = 12

EXTERNAL_MAPPINGS = {EXTERNAL_IMDB: 'imdb_id', EXTERNAL_ANIDB: 'anidb_id',
                     INDEXER_TVRAGE: 'tvrage_id', EXTERNAL_TRAKT: 'trakt_id'}

# trakt indexer name vs Medusa indexer
TRAKT_INDEXERS = {'tvdb': INDEXER_TVDBV2, 'tmdb': INDEXER_TMDB, 'imdb': EXTERNAL_IMDB, 'trakt': EXTERNAL_TRAKT}

STATUS_MAP = {
    'returning series': 'Continuing',
    'canceled/ended': 'Ended',
    'tbd/on the bubble': 'Continuing',
    'in development': 'Continuing',
    'new series': 'Continuing',
    'never aired': 'Ended',
    'final season': 'Continuing',
    'on hiatus': 'Continuing',
    'pilot ordered': 'Continuing',
    'pilot rejected': 'Ended',
    'canceled': 'Ended',
    'ended': 'Ended',
    'to be determined': 'Continuing',
    'running': 'Continuing',
    'planned': 'Continuing',
    'in production': 'Continuing',
    'pilot': 'Continuing',
    'cancelled': 'Ended',
    'continuing': 'Continuing'
}

indexerConfig = {
    INDEXER_TVDBV2: {
        'enabled': True,
        'id': INDEXER_TVDBV2,
        'name': 'TVDBv2',
        'module': TVDBv2,
        'api_params': {
            'language': 'en',
            'use_zip': True,
            'session': MedusaSession(cache_control={'cache_etags': False}),
        },
        'xem_origin': 'tvdb',
        'icon': 'thetvdb16.png',
        'scene_loc': '{base_url}/scene_exceptions/scene_exceptions_tvdb.json'.format(base_url=BASE_PYMEDUSA_URL),
        'base_url': 'https://api.thetvdb.com/',
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
            'session': MedusaSession(cache_control={'cache_etags': False}),
        },
        'xem_mapped_to': INDEXER_TVDBV2,
        'icon': 'tvmaze16.png',
        'scene_loc': '{base_url}/scene_exceptions/scene_exceptions_tvmaze.json'.format(base_url=BASE_PYMEDUSA_URL),
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
            'session': MedusaSession(cache_control={'cache_etags': False}),
        },
        'icon': 'tmdb16.png',
        'scene_loc': '{base_url}/scene_exceptions/scene_exceptions_tmdb.json'.format(base_url=BASE_PYMEDUSA_URL),
        'base_url': 'https://www.themoviedb.org/',
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


def indexer_name_to_id(indexer_name):
    """Reverse translate the indexer identifier to it's id.

    :param indexer_name: Identifier of the indexer. Example: will return 1 for 'tvdb'.
    :return: The indexer id.
    """
    return {v['identifier']: k for k, v in indexerConfig.items()}.get(indexer_name)


def indexer_id_to_name(indexer):
    """Reverse translate the indexer identifier to it's id.

    :param indexer: Indexer id. E.g.: 1.
    :return: The indexer name. E.g.: tvdb
    """
    return indexerConfig[indexer]['identifier']


def indexer_id_to_slug(indexer, indexer_id):
    """Translate a shows indexex and indexer id to a slug.

    :param indexer: The indexer id. For example 1 for tvdb and 3 for tvmaze.
    :param indexer_id: The shows id, for the specific indexer.
    :return: A slug. For example tvdb1234 for indexer 1 and indexer id 1234.
    """
    return '{name}{indexer_id}'.format(name=indexerConfig[indexer]['identifier'], indexer_id=indexer_id)


def slug_to_indexer_id(slug):
    """Translate a shows slug to it's indexer and indexer id.

    :param slug: the slug used for the indexer and indexer id.
    :return: A tuple with the indexer id and show id, for the specific indexer.
    """
    if not slug:
        return None, None
    result = re.compile(r'([a-z]+)([0-9]+)').match(slug)
    if result:
        return indexer_name_to_id(result.group(1)), int(result.group(2))


def get_trakt_indexer(indexer):
    """Get trakt indexer name using given indexer number."""
    for trakt_indexer in TRAKT_INDEXERS:
        if TRAKT_INDEXERS[trakt_indexer] == indexer:
            return trakt_indexer
    return None
