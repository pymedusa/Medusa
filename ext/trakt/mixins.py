# -*- coding: utf-8 -*-
"""Contains various MixIns"""

__author__ = 'Jon Nappi, Elan Ruusamäe'

from dataclasses import fields


def data_class_factory(data_class):
    """
    A Mixin for inheriting @dataclass or NamedTuple, via composition rather inheritance.
    """
    field_names = set(f.name for f in fields(data_class))

    class DataClassMixinClass:
        def __init__(self, **kwargs):
            # https://stackoverflow.com/questions/54678337/how-does-one-ignore-extra-arguments-passed-to-a-dataclass/54678706#54678706
            values = {k: v for k, v in kwargs.items() if k in field_names}
            self.data = data_class(**values)

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
