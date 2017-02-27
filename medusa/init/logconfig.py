# coding=utf-8
"""Monkey-patch logger functions to accept enhanced format styles."""
import logging
from inspect import getargspec

from six import text_type


class StyleAdapter(logging.LoggerAdapter):
    """Logger Adapter with new string format style."""

    adapter_members = {attr: attr for attr in dir(logging.LoggerAdapter) if not callable(attr) and not attr.startswith('__')}
    adapter_members.update({'warn': 'warning', 'fatal': 'critical'})
    reserved_keywords = getargspec(logging.Logger._log).args[1:]

    def __init__(self, target_logger, extra=None):
        """Constructor.

        :param target_logger:
        :type target_logger: logging.Logger
        :param extra:
        :type extra: dict
        """
        super(StyleAdapter, self).__init__(target_logger, extra)

    def __getattr__(self, name):
        """Wrapper that delegates to the actual logger.

        :param name:
        :type name: str
        :return:
        """
        if name not in self.adapter_members:
            return getattr(self.logger, name)

        return getattr(self, self.adapter_members[name])

    def __setattr__(self, key, value):
        """Wrapper that delegates to the actual logger.

        :param key:
        :type key: str
        :param value:
        """
        self.__dict__[key] = value

    def debug(self, msg, *args, **kwargs):
        """Delegate a debug call to the underlying logger."""
        msg, kwargs = self.wrap_message(msg, args, kwargs)
        super(StyleAdapter, self).debug(msg, *(), **kwargs)

    def info(self, msg, *args, **kwargs):
        """Delegate a debug call to the underlying logger."""
        msg, kwargs = self.wrap_message(msg, args, kwargs)
        super(StyleAdapter, self).info(msg, *(), **kwargs)

    def warning(self, msg, *args, **kwargs):
        """Delegate a debug call to the underlying logger."""
        msg, kwargs = self.wrap_message(msg, args, kwargs)
        super(StyleAdapter, self).warning(msg, *(), **kwargs)

    def error(self, msg, *args, **kwargs):
        """Delegate a debug call to the underlying logger."""
        msg, kwargs = self.wrap_message(msg, args, kwargs)
        super(StyleAdapter, self).error(msg, *(), **kwargs)

    def exception(self, msg, *args, **kwargs):
        """Delegate a debug call to the underlying logger."""
        msg, kwargs = self.wrap_message(msg, args, kwargs)
        super(StyleAdapter, self).exception(msg, *(), **kwargs)

    def critical(self, msg, *args, **kwargs):
        """Delegate a debug call to the underlying logger."""
        msg, kwargs = self.wrap_message(msg, args, kwargs)
        super(StyleAdapter, self).critical(msg, *(), **kwargs)

    def log(self, level, msg, *args, **kwargs):
        """Delegate a debug call to the underlying logger."""
        msg, kwargs = self.wrap_message(msg, args, kwargs)
        super(StyleAdapter, self).log(level, msg, *(), **kwargs)

    def wrap_message(self, msg, args, kwargs):
        """Enhance default process to use BraceMessage and remove unsupported keyword args for the actual logger method.

        :param msg:
        :param kwargs:
        :return:
        """
        return BraceMessage(msg, args, kwargs), {k: kwargs[k] for k in self.reserved_keywords if k in kwargs}


class BraceMessage(object):
    """Log Message wrapper that applies new string format style."""

    def __init__(self, fmt, args, kwargs):
        """Constructor.

        :param fmt:
        :type fmt: logging.Formatter
        :param args:
        :param kwargs:
        """
        self.fmt = fmt
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        """String representation.

        :return:
        :rtype: str
        """
        result = text_type(self.fmt)
        kwargs = [a for a in self.args if isinstance(a, dict)]
        assert len(kwargs) < 2
        if kwargs:
            return result.format(*self.args, **kwargs[0])

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
