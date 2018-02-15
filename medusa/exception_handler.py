# coding=utf-8
"""Exception Handler."""
from __future__ import unicode_literals

import logging

from medusa.logger.adapters.style import BraceAdapter

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log = BraceAdapter(log)


def handle(err, message='', *args, **kwargs):
    """Single entry point to handle unhandled exceptions.

    :param err:
    :param message:
    :type err: Exception
    """
    m = message.format(*args, **kwargs) + ': ' if message else ''
    if isinstance(err, EnvironmentError):
        if err.errno == 28:
            log.warning('{m}Out of disk space: {error_msg}',
                        {'m': m, 'error_msg': err})
        elif err.errno == 13:
            log.warning('{m}Permission denied: {error_msg}',
                        {'m': m, 'error_msg': err})
        else:
            log.exception('{m}Environment error: {error_msg}',
                          {'m': m, 'error_msg': err})
    else:
        log.exception('{m}Exception generated: {error_msg}',
                      {'m': m, 'error_msg': err})
