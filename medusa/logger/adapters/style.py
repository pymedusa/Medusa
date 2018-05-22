# coding=utf-8

"""Style Adapters for Python logging."""

from __future__ import unicode_literals

import collections
import functools
import logging
import traceback
from builtins import map
from builtins import object
from builtins import str

from six import text_type, viewitems

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


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
            if args[0] and isinstance(args[0], collections.Mapping):
                args = []
                kwargs = self.args[0]

        try:
            return self.msg.format(*args, **kwargs)
        except IndexError:
            try:
                return self.msg.format(**kwargs)
            except KeyError:
                return self.msg
        except KeyError as error:
            try:
                return self.msg.format(*args)
            except KeyError:
                raise error
        except Exception:
            log.error(
                'BraceMessage string formatting failed. '
                'Using representation instead.\n{0!r}'.format(
                    ''.join(traceback.format_stack()),
                )
            )
            return repr(self)

    def __repr__(self):
        """Convert to class representation."""
        sep = ', '
        kw_repr = '{key}={value!r}'
        name = self.__class__.__name__
        args = sep.join(map(text_type, self.args))
        kwargs = sep.join(kw_repr.format(key=k, value=v)
                          for k, v in viewitems(self.kwargs))
        return '{cls}({args})'.format(
            cls=name,
            args=sep.join([repr(self.msg), args, kwargs])
        )

    def format(self, *args, **kwargs):
        """Format a BraceMessage string."""
        return str(self).format(*args, **kwargs)


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
