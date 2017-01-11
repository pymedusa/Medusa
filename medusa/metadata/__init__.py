# coding=utf-8

# Author: Nic Wolfe <nic@wolfeden.ca>
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

import sys

from ..metadata import generic, helpers, kodi, kodi_12plus, mede8er, media_browser, ps3, tivo, wdtv

__all__ = ['generic', 'helpers', 'kodi', 'kodi_12plus', 'media_browser', 'ps3', 'wdtv', 'tivo', 'mede8er']


def available_generators():
    return [x for x in __all__ if x not in ['generic', 'helpers']]


def _getMetadataModule(name):
    name = name.lower()
    prefix = __name__ + '.'
    if name in available_generators() and prefix + name in sys.modules:
        return sys.modules[prefix + name]
    else:
        return None


def _getMetadataClass(name):
    module = _getMetadataModule(name)

    if not module:
        return None

    return module.metadata_class()


class MetaDataProvidersDict(dict):
    """A custom dict class, used to reset the indexer_api attribute of an individual indexer.

    Therefor the app.metadata_provider_dict may only be itterated through the .values() method.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the metadatadict object instance."""
        super(MetaDataProvidersDict, self).__init__(*args, **kwargs)

    def __getitem__(self, key):
        """Get the dict value, and reset the indexer_api to None.

        This was needed because we initialize the metadata provider object once, and then store it in this dict.
        We've implemented the indexer_api, to cache the indexer api information, when using it for images,
        season banners, actor data, show info etc.
        """
        val = dict.__getitem__(self, key)
        val.indexer_api = None
        return val

    def values(self):
        """Override values method."""
        providers = []
        for metadata_provider in self:
            providers.append(self[metadata_provider])
        return providers


def get_metadata_generator_dict():
    result = MetaDataProvidersDict()
    for cur_generator_id in available_generators():
        cur_generator = _getMetadataClass(cur_generator_id)
        if not cur_generator:
            continue
        result[cur_generator.name] = cur_generator

    return result
