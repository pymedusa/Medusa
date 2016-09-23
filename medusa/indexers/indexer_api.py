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

import os

import medusa as app
from .indexer_config import indexerConfig, initConfig
from ..helper.common import try_int


class indexerApi(object):
    def __init__(self, indexerID=None):
        self.indexerID = try_int(indexerID, None)

    def __del__(self):
        pass

    def indexer(self, *args, **kwargs):
        if self.indexerID:
            return indexerConfig[self.indexerID]['module'](*args, **kwargs)

    @property
    def config(self):
        if self.indexerID:
            return indexerConfig[self.indexerID]
        _ = initConfig
        if app.INDEXER_DEFAULT_LANGUAGE in _:
            del _[_['valid_languages'].index(app.INDEXER_DEFAULT_LANGUAGE)]
        _['valid_languages'].sort()
        _['valid_languages'].insert(0, app.INDEXER_DEFAULT_LANGUAGE)
        return _

    @property
    def name(self):
        if self.indexerID:
            return indexerConfig[self.indexerID]['name']

    @property
    def api_params(self):
        if self.indexerID:
            if app.CACHE_DIR:
                indexerConfig[self.indexerID]['api_params']['cache'] = os.path.join(app.CACHE_DIR, 'indexers', self.name)
            if app.PROXY_SETTING and app.PROXY_INDEXERS:
                indexerConfig[self.indexerID]['api_params']['proxy'] = app.PROXY_SETTING

            return indexerConfig[self.indexerID]['api_params']

    @property
    def cache(self):
        if app.CACHE_DIR:
            return self.api_params['cache']

    @property
    def indexers(self):
        return dict((int(x['id']), x['name']) for x in indexerConfig.values())

    @property
    def session(self):
        if self.indexerID:
            return indexerConfig[self.indexerID]['session']
