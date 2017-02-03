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
# pylint:disable=too-many-lines
"""Externals helper functions."""

import logging
from traktor import TokenExpiredException, TraktApi, TraktException
from .. import app
from ..indexers.indexer_api import indexerApi
from ..indexers.indexer_config import indexerConfig
from ..indexers.indexer_exceptions import IndexerException, IndexerShowAllreadyInLibrary, IndexerUnavailable


logger = logging.getLogger(__name__)


def get_trakt_externals(externals):
    """Small trakt api wrapper, to request trakt externals using multiple external id's.

    :param externals: Dictionary of key/value pairs with external id's.
    """
    def trakt_request(api, url):
        """Perform the request and handle possible token refresh."""
        try:
            result = api.request(url) or []
            if api.access_token_refreshed:
                app.TRAKT_ACCESS_TOKEN = api.access_token
                app.TRAKT_REFRESH_TOKEN = api.refresh_token
                app.instance.save_config()
        except (TokenExpiredException, TraktException) as e:
            logger.info(u'Could not use Trakt to enrich with externals. Cause: {cause}', cause=e)
            return []
        else:
            return result

    trakt_settings = {'trakt_api_key': app.TRAKT_API_KEY,
                      'trakt_api_secret': app.TRAKT_API_SECRET,
                      'trakt_access_token': app.TRAKT_ACCESS_TOKEN,
                      'trakt_refresh_token': app.TRAKT_REFRESH_TOKEN}
    trakt_api = TraktApi(app.SSL_VERIFY, app.TRAKT_TIMEOUT, **trakt_settings)

    id_lookup = '/search/{external_key}/{external_value}?type=show'
    trakt_mapping = {'tvdb_id': 'tvdb', 'imdb_id': 'imdb', 'tmdb_id': 'tmdb', 'trakt_id': 'trakt'}
    trakt_mapping_rev = {v: k for k, v in trakt_mapping.items()}

    for external_key in externals:
        if not trakt_mapping.get(external_key) or not externals[external_key]:
            continue

        url = id_lookup.format(external_key=trakt_mapping[external_key], external_value=externals[external_key])
        logger.debug(u"Looking for externals using Trakt and {indexer_name}'s {id}",
                     indexer_name=trakt_mapping[external_key], id=externals[external_key])
        result = trakt_request(trakt_api, url)
        if result and len(result) and result[0].get('show') and result[0]['show'].get('ids'):
            ids = {trakt_mapping_rev[k]: v for k, v in result[0]['show'].get('ids').items()
                   if v and trakt_mapping_rev.get(k)}
            return ids
    return {}


def get_externals(show=None, indexer=None, indexed_show=None):
    """Use as much as possible sources to map known id's.

    Provide the external id's you have in a dictionary, and use as much available resources as possible to retrieve
    external id's.
    :param show: Series object.
    :param indexer: Indexer id. For example 1 for tvdb or 4 for tmdb.
    :param indexed_show: The result of a fully indexed shows. For example after an t['12345']
    """
    if show:
        indexer = show.indexer
        new_show_externals = show.externals
    else:
        if not indexer or not indexed_show:
            raise Exception('Need a minimum of a show object or an indexer + indexer_api '
                            '(Show searched through indexerApi.')
        new_show_externals = getattr(indexed_show, 'externals', {})

    # For this show let's get all externals, and use them.
    mappings = {indexer: indexerConfig[indexer]['mapped_to'] for indexer in indexerConfig}
    other_indexers = [mapped_indexer for mapped_indexer in mappings if mapped_indexer != indexer]

    # We for example want to add through tmdb, but the show is already added through tvdb.
    # If tmdb doesn't have a mapping to imdb, but tvmaze does, there is a small chance we can use that.

    for other_indexer in other_indexers:
        lindexer_api_pararms = indexerApi(other_indexer).api_params.copy()
        try:
            t = indexerApi(other_indexer).indexer(**lindexer_api_pararms)
        except IndexerUnavailable:
            continue
        if hasattr(t, 'get_id_by_external'):
            logger.debug(u"Trying other indexers {indexer_name} get_id_by_external",
                         indexer_name=indexerApi(other_indexer).name)
            # Call the get_id_by_external and pass all the externals we have, except for the indexers own.
            try:
                new_show_externals.update(t.get_id_by_external(**new_show_externals))
            except IndexerException as e:
                logger.warning(u'Error getting external ids for other indexer {indexer_name} with cause {cause}',
                               indexer_name=indexerApi(show.indexer).name, cause=e)

    # Try to update with the Trakt externals.
    new_show_externals.update(get_trakt_externals(new_show_externals))

    return new_show_externals


def check_existing_shows(indexed_show, indexer):
    """Check if the searched show already exists in the current library.

    :param indexed_show: (Indexer Show object) The indexed show from -for example- tvdb. It might already have some
    externals like imdb_id which can be used to search at tmdb, tvmaze or trakt.
    :param indexer: (int) The indexer id, which has been used to search the indexed_show with.
    :return: Raises the exception IndexerShowAllreadyInLibrary() when the show is already in your library.
    """
    # For this show let's get all externals, and use them.
    mappings = {indexer: indexerConfig[indexer]['mapped_to'] for indexer in indexerConfig}
    other_indexers = [mapped_indexer for mapped_indexer in mappings if mapped_indexer != indexer]

    new_show_externals = get_externals(indexer=indexer, indexed_show=indexed_show)

    # Iterate through all shows in library, and see if one of our externals matches it's indexer_id
    # Or one of it's externals.
    for show in app.showList:

        # Check if the new shows indexer id matches the external for the show in library
        if show.externals.get(mappings[indexer]) and indexed_show['id'] == show.externals.get(mappings[indexer]):
            logger.debug(u"The Show {show_name} was already added. Found it because the show's added id ({id}),"
                         u" is already known it the db", show_name=show.name, id=indexed_show['id'])
            raise IndexerShowAllreadyInLibrary('The show {0} has already been added by the indexer {1}. '
                                               'Please remove the show, before you can add it through {2}.'
                                               .format(show.name, indexerApi(show.indexer).name,
                                                       indexerApi(indexer).name))

        for new_show_external_key in new_show_externals.keys():
            if show.indexer not in other_indexers:
                continue

            # Check if one of the new shows externals matches one of the externals for the show in library.
            if not new_show_externals.get(new_show_external_key) or not show.externals.get(new_show_external_key):
                continue

            if new_show_externals.get(new_show_external_key) == show.externals.get(new_show_external_key):
                logger.debug(u"The Show {show_name} was already added. Found it because one of show's externals "
                             u'({external_id}) matches one of an existing shows external with value ({id})',
                             show_name=show.name, external_id=new_show_external_key,
                             id=show.externals.get(new_show_external_key))
                raise IndexerShowAllreadyInLibrary('The show {0} has already been added by the indexer {1}. '
                                                   'Please remove the show, before you can add it through {2}.'
                                                   .format(show.name, indexerApi(show.indexer).name,
                                                           indexerApi(indexer).name))
