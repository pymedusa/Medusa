# -*- coding: utf-8 -*-
"""Contains various MixIns"""

__author__ = 'Jon Nappi, Elan Ruusamäe'


def data_class_factory(data_class):
    """
    A Mixin for inheriting @dataclass or NamedTuple, via composition rather inheritance.
    """
    class DataClassMixinClass:
        def __init__(self, **kwargs):
            self.data = data_class(**kwargs)

        def __getattr__(self, item):
            return getattr(self.data, item)

    return DataClassMixinClass


DataClassMixin = data_class_factory


class IdsMixin:
    """
    Provides Mixin to translate "ids" array
    to appropriate provider ids in base class.

    This is replacement for extract_ids() utility method.
    """

    __ids = ['imdb', 'slug', 'tmdb', 'trakt']

    def __init__(self, ids=None):
        if ids is None:
            ids = {}
        self._ids = ids

    @property
    def ids(self):
        """
        Accessor to the trakt, imdb, and tmdb ids,
        as well as the trakt.tv slug
        """
        ids = {k: getattr(self, k, None) for k in self.__ids}
        return {
            'ids': ids
        }

    @ids.setter
    def ids(self, value):
        self._ids = value

    @property
    def imdb(self):
        return self._ids.get('imdb', None)

    @property
    def tmdb(self):
        return self._ids.get('tmdb', None)

    @property
    def trakt(self):
        return self._ids.get('trakt', None)

    @property
    def tvdb(self):
        return self._ids.get('tvdb', None)

    @property
    def tvrage(self):
        return self._ids.get('tvrage', None)

    @property
    def slug(self):
        return self._ids.get('slug', None)

    @slug.setter
    def slug(self, value):
        self._ids['slug'] = value
