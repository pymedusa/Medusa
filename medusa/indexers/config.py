# coding=utf-8

"""Indexer config module."""
from __future__ import unicode_literals

from builtins import str

from medusa.app import app
from medusa.indexers.tmdb.api import Tmdb
from medusa.indexers.tvdbv2.api import TVDBv2
from medusa.indexers.tvmaze.api import TVmaze
from medusa.session.core import MedusaSession

from six import iteritems


init_config = {
    'valid_languages': [
        'da', 'fi', 'nl', 'de', 'it', 'es', 'fr', 'pl', 'hu', 'el', 'tr',
        'ru', 'he', 'ja', 'pt', 'zh', 'cs', 'sl', 'hr', 'ko', 'en', 'sv', 'no'
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
    'Continuing': [
        'returning series',
        'tbd/on the bubble',
        'in development',
        'new series',
        'final season',
        'on hiatus',
        'pilot ordered',
        'to be determined',
        'running',
        'planned',
        'in production',
        'pilot',
        'continuing',
        'upcoming'
    ],
    'Ended': [
        'canceled/ended',
        'never aired',
        'pilot rejected',
        'canceled',
        'ended',
        'cancelled'
    ]
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
        'scene_loc': '{base_url}/scene_exceptions/scene_exceptions_tvdb.json'.format(base_url=app.BASE_PYMEDUSA_URL),
        'base_url': 'https://api.thetvdb.com/',
        'show_url': 'https://www.thetvdb.com/dereferrer/series/',
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
        'scene_loc': '{base_url}/scene_exceptions/scene_exceptions_tvmaze.json'.format(base_url=app.BASE_PYMEDUSA_URL),
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
        'scene_loc': '{base_url}/scene_exceptions/scene_exceptions_tmdb.json'.format(base_url=app.BASE_PYMEDUSA_URL),
        'base_url': 'https://www.themoviedb.org/',
        'show_url': 'https://www.themoviedb.org/tv/',
        'mapped_to': 'tmdb_id',  # The attribute to which other indexers can map there tmdb id to
        'identifier': 'tmdb',  # Also used as key for the custom scenename exceptions. (_get_custom_exceptions())
    }
}


def create_config_json(indexer):
    """Create a json (pickable) compatible dict, for using as an apiv2 resource."""
    return {
        'enabled': indexer['enabled'],
        'id': indexer['id'],
        'name': indexer['name'],
        'apiParams': {
            'language': indexer['api_params']['language'],
            'useZip': indexer['api_params']['use_zip'],
        },
        'xemOrigin': indexer.get('xem_origin'),
        'icon': indexer.get('icon'),
        'scene_loc': indexer.get('scene_loc'),
        'baseUrl': indexer.get('base_url'),
        'showUrl': indexer.get('show_url'),
        'mappedTo': indexer.get('mapped_to'),  # The attribute to which other indexers can map there thetvdb id to
        'identifier': indexer.get('identifier'),  # Also used as key for the custom scenename exceptions. (_get_custom_exceptions())
    }


def get_indexer_config():
    """Create a per indexer and main indexer config, used by the apiv2."""
    indexers = {
        indexerConfig[indexer]['identifier']: create_config_json(indexerConfig[indexer]) for indexer in indexerConfig
    }

    main = {
        'validLanguages': init_config['valid_languages'],
        'langabbvToId': init_config['langabbv_to_id'],
        'externalMappings': {str(k): v for k, v in iteritems(EXTERNAL_MAPPINGS)},
        'traktIndexers': TRAKT_INDEXERS,
        'statusMap': STATUS_MAP
    }

    return {'indexers': indexers, 'main': main}
