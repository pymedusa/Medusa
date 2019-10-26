# coding=utf-8
"""Indexer class."""
from __future__ import unicode_literals

from builtins import str

from medusa.indexers.utils import indexer_id_to_name, indexer_name_to_id
from medusa.tv.base import Identifier


class Indexer(Identifier):
    """Represent an Indexer with id and slug name."""

    def __init__(self, identifier):
        """Constructor.

        :param identifier:
        :type identifier: int
        """
        self.id = identifier

    @classmethod
    def from_slug(cls, slug):
        """Create Indexer from slug."""
        identifier = indexer_name_to_id(slug)
        if identifier is not None:
            return Indexer(identifier)

    @classmethod
    def from_id(cls, pk):
        """Create Indexer from id."""
        return Indexer(pk)

    @property
    def slug(self):
        """Slug name."""
        return indexer_id_to_name(self.id)

    def __bool__(self):
        """Magic method bool."""
        return self.id is not None

    def __repr__(self):
        """Magic method."""
        return '<Indexer [{0}:{1}]>'.format(self.slug, self.id)

    def __str__(self):
        """Magic method."""
        return str(self.slug)

    def __hash__(self):
        """Magic method."""
        return hash(self.id)

    def __eq__(self, other):
        """Magic method."""
        return isinstance(other, Indexer) and self.id == other.id
