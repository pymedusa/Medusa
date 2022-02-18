# coding=utf-8

from __future__ import unicode_literals

import time
from collections import namedtuple


class ExpiringList(list):
    """Smart custom list, with a cache expiration."""

    CachedResult = namedtuple('CachedResult', 'time value')

    def __init__(self, items=None, cache_timeout=3600, implicit_clean=False):
        """Initialize the MissingPosterList.

        :param items: Provide the initial list.
        :param cache_timeout: Timeout after which the item expires.
        :param implicit_clean: If enabled, run the clean() method, to check for expired items. Else you'll have to run
        this periodically.
        """
        list.__init__(self, items or [])
        self.cache_timeout = cache_timeout
        self.implicit_clean = implicit_clean

    def append(self, item):
        """Add new items to the list."""
        if self.implicit_clean:
            self.clean()
        super(ExpiringList, self).append((int(time.time()), item))

    def clean(self):
        """Use the cache_timeout to remove expired items."""
        new_list = [_ for _ in self if _[0] + self.cache_timeout > int(time.time())]
        self.__init__(new_list, self.cache_timeout, self.implicit_clean)

    def has(self, value):
        """Check if the value is in the list.

        We need a smarter method to check if an item is already in the list. This will return a list with items that
        match the value.
        :param value: The value to check for.
        :return: A list of tuples with matches. For example: (141234234, '12342').
        """
        if self.implicit_clean:
            self.clean()
        return [
            ExpiringList.CachedResult(time=match[0], value=match[1])
            for match in self if match[1] == value
        ]

    def get(self, value):
        """Check if the value is in the list.

        We need a smarter method to check if an item is already in the list. This will return a list with items that
        match the value.
        :param value: The value to check for.
        :return: A single item, if it matches. For example: <CachedResult()>.
        """
        if self.implicit_clean:
            self.clean()

        matches = [_ for _ in self if _[1] == value]

        if not matches:
            return None

        if len(matches) > 1:
            # If we detect more then one match, let's remove then all.
            for match in matches:
                self.remove(match)
            return None

        if len(matches):
            return ExpiringList.CachedResult(time=matches[0][0], value=matches[0][1])


class ExpiringKeyValue(list):
    """Smart custom list (that acts like a dictionary, with a cache expiration."""

    CachedResult = namedtuple('CachedResult', 'time key value')

    def __init__(self, items=None, cache_timeout=3600, implicit_clean=False):
        """Initialize the MissingPosterList.

        :param items: Provide the initial list.
        :param cache_timeout: Timeout after which the item expires.
        :param implicit_clean: If enabled, run the clean() method, to check for expired items. Else you'll have to run
        this periodically.
        """
        list.__init__(self, items or [])
        self.cache_timeout = cache_timeout
        self.implicit_clean = implicit_clean

    def append(self, key, value):
        """Add new items to the list."""
        if self.implicit_clean:
            self.clean()
        super(ExpiringKeyValue, self).append((int(time.time()), key, value))

    def clean(self):
        """Use the cache_timeout to remove expired items."""
        new_list = [_ for _ in self if _[0] + self.cache_timeout > int(time.time())]
        self.__init__(new_list, self.cache_timeout, self.implicit_clean)

    def has(self, value):
        """Check if the value is in the list.

        We need a smarter method to check if an item is already in the list. This will return a list with items that
        match the value.
        :param value: The key to check for.
        :return: A list of tuples with matches. For example: [<CachedResult()>, <CachedResult()>].
        """
        if self.implicit_clean:
            self.clean()
        return [
            ExpiringKeyValue.CachedResult(time=match[0], key=match[1], value=match[2])
            for match in self if match[2] == value
        ]

    def get(self, key):
        """Check if the key is in the list.

        We need a smarter method to check if an item is already in the list. This will return a list with items that
        match the value.
        :param key: The value to check for.
        :return: A single item, if it matches. For example: <CachedResult()>.
        """
        if self.implicit_clean:
            self.clean()

        matches = [_ for _ in self if _[1] == key]

        if not matches:
            return None

        if len(matches) > 1:
            # If we detect more then one match, let's remove then all.
            for match in matches:
                self.remove(match)
            return None

        if len(matches):
            return ExpiringKeyValue.CachedResult(time=matches[0][0], key=matches[0][1], value=matches[0][2])
