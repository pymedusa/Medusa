# coding=utf-8
"""Exception Handler."""
from __future__ import unicode_literals

import logging

logger = logging.getLogger(__name__)


def handle(thread_name, err):
    """Single entry point to handle unhandled exceptions.

    :param thread_name:
    :type thread_name: string
    :param err:
    :type err: Exception
    """
    if isinstance(err, OSError):
        if err.errno == 28:
            logger.warning('Out of disk space: {error_msg}', error_msg=err.message)
        else:
            logger.warning('OS error: {error_msg}', error_msg=err.message)
    else:
        logger.exception("Exception generated in thread {thread_name}: {error_msg}",
                         thread_name=thread_name, error_msg=err.message)
