# coding=utf-8
"""IMDbPie shim."""

from __future__ import unicode_literals

import os.path

from imdbpie import imdbpie

from medusa import app


class Imdb(imdbpie.Imdb):
    """Subclass imdbpie.Imdb to override the cache folder location."""

    def __init__(self, *args, **kwargs):
        super(Imdb, self).__init__(*args, **kwargs)
        # Just to make sure new versions of `imdbpie` won't break this fix
        assert hasattr(self, '_cachedir')
        # Override the cache location
        self._cachedir = os.path.join(app.CACHE_DIR, 'diskcache')
