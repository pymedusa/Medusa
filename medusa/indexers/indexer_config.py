# coding=utf-8

from .tvdbv2.tvdbv2_api import TVDBv2
from .. import helpers

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
# INDEXER_TVMAZE = 3

indexerConfig = {
    INDEXER_TVDBV2: {
        'enabled': True,
        'id': INDEXER_TVDBV2,
        'name': 'TVDBv2',
        'module': TVDBv2,
        'api_params': {
            'language': 'en',
            'useZip': True,
            'session': helpers.make_session(cache_etags=False),
        },
        'trakt_id': 'tvdb_id',
        'xem_origin': 'tvdb',
        'icon': 'thetvdb16.png',
        'scene_loc': 'https://cdn.pymedusa.com/scene_exceptions/scene_exceptions.json',
        'base_url': 'https://api.thetvdb.com',
        'show_url': 'http://thetvdb.com/?tab=series&id=',
        'mapped_to': 'tvdbid'  # The attribute to which other indexers can map there thetvdb id to
    }
}