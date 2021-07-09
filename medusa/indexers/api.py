# coding=utf-8

from __future__ import unicode_literals

import os
from builtins import object

from medusa import app
from medusa.helper.common import try_int
from medusa.indexers.config import indexerConfig, init_config
from medusa.indexers.tvdbv2.fallback import PlexFallBackConfig

from six import itervalues


class indexerApi(object):
    def __init__(self, indexer_id=None):
        self.indexer_id = try_int(indexer_id, None)

    def __del__(self):
        pass

    @PlexFallBackConfig
    def indexer(self, *args, **kwargs):
        if self.indexer_id:
            indexer_obj = indexerConfig[self.indexer_id]['module'](*args, **kwargs)
            indexer_obj.indexer = self.config['id']
            indexer_obj.name = self.config['identifier']
            return indexer_obj

    @property
    def config(self):
        if self.indexer_id:
            return indexerConfig[self.indexer_id]
        # Sort and put the default language first
        init_config['valid_languages'].sort(key=lambda i: '\0' if i == app.INDEXER_DEFAULT_LANGUAGE else i)
        return init_config

    @property
    def name(self):
        if self.indexer_id:
            return indexerConfig[self.indexer_id]['name']

    @property
    def api_params(self):
        if self.indexer_id:
            if app.CACHE_DIR:
                indexerConfig[self.indexer_id]['api_params']['cache'] = os.path.join(app.CACHE_DIR, 'indexers',
                                                                                     self.name)
            if app.PROXY_SETTING and app.PROXY_INDEXERS:
                indexerConfig[self.indexer_id]['api_params']['proxy'] = app.PROXY_SETTING

            return indexerConfig[self.indexer_id]['api_params']

    @property
    def cache(self):
        if app.CACHE_DIR:
            return self.api_params['cache']

    @property
    def indexers(self):
        return dict((int(x['id']), x['name']) for x in itervalues(indexerConfig) if x.get('enabled', None))

    @property
    def session(self):
        if self.indexer_id:
            return indexerConfig[self.indexer_id]['api_params']['session']
