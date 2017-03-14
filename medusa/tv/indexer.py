# coding=utf-8
"""Indexer class."""

from medusa.indexers.indexer_config import indexer_id_to_name, indexer_name_to_id
import six


class Indexer(object):
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

    @property
    def slug(self):
        """Slug name."""
        return indexer_id_to_name(self.id)

    def __bool__(self):
        """Magic method bool."""
        return self.id is not None

    __nonzero__ = __bool__

    def __repr__(self):
        """Magic method."""
        return '<Indexer [{0}:{1}]>'.format(self.slug, self.id)

    def __str__(self):
        """Magic method."""
        return str(self.slug)

    def __hash__(self):
        """Magic method."""
        return hash(str(self))

    def __eq__(self, other):
        """Magic method."""
        if isinstance(other, six.string_types):
            return str(self) == other
        if isinstance(other, int):
            return self.id == other
        if not isinstance(other, Indexer):
            return False
        return self.id == other.id

    def __ne__(self, other):
        """Magic method."""
        return not self == other
