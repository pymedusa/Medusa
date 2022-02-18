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

from __future__ import unicode_literals

import sys

from medusa.metadata import (
    generic,
    kodi,
    kodi_12plus,
    mede8er,
    media_browser,
    ps3,
    tivo,
    wdtv,
)

__all__ = [
    'generic',
    'kodi',
    'kodi_12plus',
    'mede8er',
    'media_browser',
    'ps3',
    'tivo',
    'wdtv',
]


def available_generators():
    return [x for x in __all__ if x not in ['generic']]


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


def get_metadata_generator_dict():
    result = dict()
    for cur_generator_id in available_generators():
        cur_generator = _getMetadataClass(cur_generator_id)
        if not cur_generator:
            continue
        result[cur_generator.name] = cur_generator

    return result
