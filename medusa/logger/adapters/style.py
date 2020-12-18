# coding=utf-8

"""Style Adapters for Python logging."""

from __future__ import unicode_literals

import functools
import logging
import traceback

from medusa.app import app

from six import text_type, viewitems
from six.moves import collections_abc

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class BraceException(Exception):
    """Custom exception for BraceMessage."""


class BraceMessage(object):
    """Lazily convert a Brace-formatted message."""

    def __init__(self, msg, *args, **kwargs):
        """Initialize a lazy-formatted message."""
        self.msg = msg
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        """Convert to string."""
        args = self.args
        kwargs = self.kwargs
        if args and len(args) == 1:
            if args[0] and isinstance(args[0], collections_abc.Mapping):
                args = []
                kwargs = self.args[0]

        try:
            exc_origin = ''
            try:
                return self.msg.format(*args, **kwargs)
            except IndexError:
                try:
                    return self.msg.format(**kwargs)
                except KeyError:
                    return self.msg
                except Exception as error:
                    exc_origin = traceback.format_exc(error)
            except KeyError:
                try:
                    return self.msg.format(*args)
                except Exception as error:
                    exc_origin = traceback.format_exc(error)
            except Exception as error:
                exc_origin = traceback.format_exc(error)
            finally:
                if exc_origin:
                    raise BraceException(self.msg)
        except BraceException:
            log.exception(
                'BraceMessage string formatting failed. '
                'Using representation instead.\n{0}'.format(exc_origin)
            )
            return repr(self)

    def __repr__(self):
        """Convert to class representation."""
        sep = ', '
        kw_repr = '{key}={value!r}'
        name = self.__class__.__name__
        args = sep.join(list(map(text_type, self.args)))
        kwargs = sep.join(kw_repr.format(key=k, value=v)
                          for k, v in viewitems(self.kwargs))
        return '{cls}({args})'.format(
            cls=name,
            args=sep.join([repr(self.msg), args, kwargs])
        )

    def format(self, *args, **kwargs):
        """Format a BraceMessage string."""
        return text_type(self).format(*args, **kwargs)


class BraceAdapter(logging.LoggerAdapter):
    """Adapt logger to use Brace-formatted messages."""

    def __init__(self, logger, extra=None):
        """Initialize the Brace adapter with a logger."""
        super(BraceAdapter, self).__init__(logger, extra)
        self.debug = functools.partial(self.log, logging.DEBUG)
        self.info = functools.partial(self.log, logging.INFO)
        self.warning = functools.partial(self.log, logging.WARNING)
        self.error = functools.partial(self.log, logging.ERROR)
        self.critical = functools.partial(self.log, logging.CRITICAL)

    def log(self, level, msg, *args, **kwargs):
        """Log a message at the specified level using Brace-formatting."""
        if self.isEnabledFor(level):
            msg, kwargs = self.process(msg, kwargs)
            if not isinstance(msg, BraceMessage):
                msg = BraceMessage(msg, *args, **kwargs)
            self.logger.log(level, msg, **kwargs)

    def exception(self, msg, *args, **kwargs):
        """Add exception information before delegating to self.log."""
        kwargs['exc_info'] = 1
        self.log(logging.ERROR, msg, *args, **kwargs)


class CustomBraceAdapter(BraceAdapter):
    """Add custom log level ovvrides to the Brace-formatted messages."""

    def log(self, level, msg, *args, **kwargs):
        """Log a message at the specified level using Brace-formatting."""
        # Set level
        if msg in app.CUSTOM_LOGS and app.CUSTOM_LOGS[msg] > 0:
            level = app.CUSTOM_LOGS[msg]

        super(CustomBraceAdapter, self).log(level, msg, *args, **kwargs)
