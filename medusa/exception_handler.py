# coding=utf-8
"""Exception Handler."""
from __future__ import unicode_literals

import errno
import logging

logger = logging.getLogger(__name__)


def handle(err, message='', *args, **kwargs):
    """Single entry point to handle unhandled exceptions.

    :param err:
    :param message:
    :type err: Exception
    """
    m = message.format(*args, **kwargs) + ': ' if message else ''
    if isinstance(err, EnvironmentError):
        if err.errno == errno.ENOSPC:
            logger.warning('{m}Out of disk space: {error_msg}'.format(m=m, error_msg=err))
        elif err.errno == errno.EACCES:
            logger.warning('{m}Permission denied: {error_msg}'.format(m=m, error_msg=err))
        else:
            logger.exception('{m}Environment error: {error_msg}'.format(m=m, error_msg=err))
    else:
        logger.exception('{m}Exception generated: {error_msg}'.format(m=m, error_msg=err))
