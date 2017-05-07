# coding=utf-8

import os
from .indexer_config import indexerConfig, initConfig
from .. import app
from ..helper.common import try_int


class indexerApi(object):
    def __init__(self, indexer_id=None):
        self.indexer_id = try_int(indexer_id, None)

    def __del__(self):
        pass

    def indexer(self, *args, **kwargs):
        if self.indexer_id:
            return indexerConfig[self.indexer_id]['module'](*args, **kwargs)

    @property
    def config(self):
        if self.indexer_id:
            return indexerConfig[self.indexer_id]
        _ = initConfig
        if app.INDEXER_DEFAULT_LANGUAGE in _:
            del _[_['valid_languages'].index(app.INDEXER_DEFAULT_LANGUAGE)]
        _['valid_languages'].sort()
        _['valid_languages'].insert(0, app.INDEXER_DEFAULT_LANGUAGE)
        return _

    @property
    def name(self):
        if self.indexer_id:
            return indexerConfig[self.indexer_id]['name']

    @property
    def api_params(self):
        if self.indexer_id:
            if app.CACHE_DIR:
                indexerConfig[self.indexer_id]['api_params']['cache'] = os.path.join(app.CACHE_DIR, 'indexers', self.name)
            if app.PROXY_SETTING and app.PROXY_INDEXERS:
                indexerConfig[self.indexer_id]['api_params']['proxy'] = app.PROXY_SETTING

            return indexerConfig[self.indexer_id]['api_params']

    @property
    def cache(self):
        if app.CACHE_DIR:
            return self.api_params['cache']

    @property
    def indexers(self):
        return dict((int(x['id']), x['name']) for x in indexerConfig.values() if x.get('enabled', None))

    @property
    def session(self):
        if self.indexer_id:
            return indexerConfig[self.indexer_id]['api_params']['session']
