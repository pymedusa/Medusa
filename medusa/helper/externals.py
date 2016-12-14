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
from .. import app
from ..indexers.indexer_api import indexerApi
from ..indexers.indexer_config import mappings
from ..indexers.indexer_exceptions import IndexerShowAllreadyInLibrary



logger = logging.getLogger(__name__)


def check_existing_shows(indexer_object, indexer):
    """Check if the searched show already exists in the current library.

    :param indexer_object:
    :return:
    """

    # For this show let's get all externals, and use them.
    other_indexers = [mapped_indexer for mapped_indexer in mappings if mapped_indexer != indexer]
    new_show_externals = indexer_object['externals']

    # Iterate through all shows in library, and see if one of our externals matches it's indexer_id
    # Or one of it's externals.
    for show in app.showList:

        # Check if the new shows indexer id matches the external for the show in library
        if show.externals.get(mappings[indexer]) and indexer_object['id'] == show.externals.get(mappings[indexer]):
            raise IndexerShowAllreadyInLibrary('The show {0} has already been added by the indexer {1}. '
                                               'Please remove the show, before you can add it through {2.'
                                               .format(show.name, indexerApi(show.indexer).name,
                                                       indexerApi(indexer).name))

        for new_show_external_key in new_show_externals.keys():
            if show.indexer not in other_indexers:
                continue

            # Check if one of the new shows externals matches one of the externals for the show in library.
            if not new_show_externals.get(new_show_external_key) or not show.externals.get(new_show_external_key):
                continue

            if new_show_externals.get(new_show_external_key) == show.externals.get(new_show_external_key):
                raise IndexerShowAllreadyInLibrary('The show {0} has already been added by the indexer {1}. '
                                                   'Please remove the show, before you can add it through {2}.'
                                                   .format(show.name, indexerApi(show.indexer).name,
                                                           indexerApi(indexer).name))

