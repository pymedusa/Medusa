# coding=utf-8

"""Indexer config module."""

from medusa import app
from medusa.indexers.tmdb.api import Tmdb
from medusa.indexers.tvdb.api import TVDB
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

INDEXER_TVDB = 1
INDEXER_TVRAGE = 2  # Must keep
INDEXER_TVMAZE = 3
INDEXER_TMDB = 4
EXTERNAL_IMDB = 10
EXTERNAL_ANIDB = 11
EXTERNAL_TRAKT = 12

EXTERNAL_MAPPINGS = {
    EXTERNAL_IMDB: 'imdb_id',
    EXTERNAL_ANIDB: 'anidb_id',
    INDEXER_TVRAGE: 'tvrage_id',
    EXTERNAL_TRAKT: 'trakt_id'
}

# trakt indexer name vs Medusa indexer
TRAKT_INDEXERS = {
    'tvdb': INDEXER_TVDB,
    'tmdb': INDEXER_TMDB,
    'imdb': EXTERNAL_IMDB,
    'trakt': EXTERNAL_TRAKT
}

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
    INDEXER_TVDB: {
        'enabled': True,
        'id': INDEXER_TVDB,
        'name': 'TVDB',
        'module': TVDB,
        'api_params': {
            'language': 'en',
            'use_zip': True,
            'session': MedusaSession(cache_control={'cache_etags': False}),
        },
        'xem_origin': 'tvdb',
        'icon': 'thetvdb16.png',
        'scene_loc': '{base_url}/scene_exceptions/scene_exceptions_tvdb.json'.format(base_url=app.GITHUB_IO_URL),
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
        'xem_mapped_to': INDEXER_TVDB,
        'icon': 'tvmaze16.png',
        'scene_loc': '{base_url}/scene_exceptions/scene_exceptions_tvmaze.json'.format(base_url=app.GITHUB_IO_URL),
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
        'scene_loc': '{base_url}/scene_exceptions/scene_exceptions_tmdb.json'.format(base_url=app.GITHUB_IO_URL),
        'base_url': 'https://www.themoviedb.org/',
        'show_url': 'https://www.themoviedb.org/tv/',
        'mapped_to': 'tmdb_id',  # The attribute to which other indexers can map there tmdb id to
        'identifier': 'tmdb',  # Also used as key for the custom scenename exceptions. (_get_custom_exceptions())
    }
}
