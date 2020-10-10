# coding=utf-8
"""Monkey-patch logger functions to accept enhanced format styles."""
from __future__ import unicode_literals

import logging
from builtins import object

try:
    from inspect import getfullargspec
except ImportError:
    from inspect import getargspec as getfullargspec

from six import text_type


class StyleAdapter(logging.LoggerAdapter):
    """Logger Adapter with new string format style."""

    adapter_members = {
        attr: attr for attr in dir(logging.LoggerAdapter) if not callable(attr) and not attr.startswith('__')
    }
    adapter_members.update({'warn': 'warning', 'fatal': 'critical'})
    reserved_keywords = getfullargspec(logging.Logger._log).args[1:]

    def __init__(self, target_logger, extra=None):
        """Init StyleAdapter.

        :param target_logger:
        :type target_logger: logging.Logger
        :param extra:
        :type extra: dict
        """
        super(StyleAdapter, self).__init__(target_logger, extra)

    def __getattr__(self, name):
        """Wrap to the actual logger.

        :param name:
        :type name: str
        :return:
        """
        if name not in self.adapter_members:
            return getattr(self.logger, name)

        return getattr(self, self.adapter_members[name])

    def __setattr__(self, key, value):
        """Wrap to the actual logger.

        :param key:
        :type key: str
        :param value:
        """
        self.__dict__[key] = value

    def process(self, msg, kwargs):
        """Enhance default process to use BraceMessage and remove unsupported keyword args for the actual logger method.

        :param msg:
        :param kwargs:
        :return:
        """
        reserved = {k: kwargs[k] for k in self.reserved_keywords if k in kwargs}
        kwargs = {k: kwargs[k] for k in kwargs if k not in self.reserved_keywords}
        return BraceMessage(msg, (), kwargs), reserved


class BraceMessage(object):
    """Log Message wrapper that applies new string format style."""

    def __init__(self, fmt, args, kwargs):
        """Init BraceMessage.

        :param fmt:
        :type fmt: logging.Formatter
        :param args:
        :param kwargs:
        """
        self.fmt = fmt
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        """Represent a string.

        :return:
        :rtype: str
        """
        result = text_type(self.fmt)
        return result.format(*self.args, **self.kwargs) if self.args or self.kwargs else result


def initialize():
    """Replace standard getLogger with our enhanced one."""
    def enhanced_get_logger(name=None):
        """Enhanced logging.getLogger function.

        :param name:
        :return:
        """
        return StyleAdapter(standard_logger(name))

    logging.getLogger = enhanced_get_logger


# Keeps the standard logging.getLogger to be used by StyleAdapter
standard_logger = logging.getLogger
