# coding=utf-8
"""Generic utils for indexers."""
from __future__ import unicode_literals

import re

from medusa.indexers.config import EXTERNAL_MAPPINGS, TRAKT_INDEXERS, indexerConfig

from six import viewitems

SHOW_SLUG_PATTERN = re.compile(r'([a-z]+)([0-9]+)')

# For example: {1: 'tvdb_id', 3: 'tvmaze_id', 4: 'tmdb_id'}
mappings = {indexer: indexerConfig[indexer]['mapped_to'] for indexer in indexerConfig}
mappings.update(EXTERNAL_MAPPINGS)

# For example: {'tvdb_id': 1, 'tvmaze_id': 3, 'tmdb_id': 4}
reverse_mappings = {indexerConfig[indexer]['mapped_to']: indexer for indexer in indexerConfig}
reverse_mappings.update({v: k for k, v in viewitems(EXTERNAL_MAPPINGS)})

# For example: {'tvdb': 1, 'tvmaze': 3, 'tmdb': 4}
indexer_name_mapping = {indexerConfig[indexer]['identifier']: indexer for indexer in indexerConfig}


def indexer_name_to_id(indexer_name):
    """Reverse translate the indexer identifier to it's id.

    :param indexer_name: Identifier of the indexer. Example: will return 1 for 'tvdb'.
    :return: The indexer id.
    """
    return {v['identifier']: k for k, v in viewitems(indexerConfig)}.get(indexer_name)


def indexer_id_to_name(indexer):
    """Reverse translate the indexer identifier to it's id.

    :param indexer: Indexer id. E.g.: 1.
    :return: The indexer name. E.g.: tvdb
    """
    return indexerConfig[indexer]['identifier']


def indexer_id_to_slug(indexer, series_id):
    """Translate a shows indexer and series id to a slug.

    :param indexer: The indexer id. For example 1 for tvdb and 3 for tvmaze.
    :param series_id: The shows id, for the specific indexer.
    :return: A slug. For example tvdb1234 for indexer 1 and indexer id 1234.
    """
    return '{name}{series_id}'.format(name=indexerConfig[indexer]['identifier'], series_id=series_id)


def slug_to_indexer_id(slug):
    """Translate a shows slug to it's indexer and indexer id.

    :param slug: the slug used for the indexer and indexer id.
    :return: A tuple with the indexer id and show id, for the specific indexer.
    """
    if not slug:
        return None, None
    result = SHOW_SLUG_PATTERN.match(slug)
    if result:
        return indexer_name_to_id(result.group(1)), int(result.group(2))


def get_trakt_indexer(indexer):
    """Get trakt indexer name using given indexer number."""
    for trakt_indexer in TRAKT_INDEXERS:
        if TRAKT_INDEXERS[trakt_indexer] == indexer:
            return trakt_indexer
    return None
