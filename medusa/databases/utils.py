# coding=utf-8

"""General database utility functions."""
from __future__ import unicode_literals

import logging
import sys

from medusa import helpers
from medusa.logger.adapters.style import BraceAdapter

from six import itervalues


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


def backup_database(path, version):
    """Back up the database."""
    log.info('Backing up database before upgrade')
    if not helpers.backup_versioned_file(path, version):
        log.error('Database backup failed, abort upgrading database')
        sys.exit(1)
    else:
        log.info('Proceeding with upgrade')


def split_composite_status(status):
    """
    Split an old composite status code into a status and quality.

    Used by the following migrations:
        * main_db.py / AddSeparatedStatusQualityFields
        * failed_db.py / UpdateHistoryTableQuality

    Note: Uses the old quality codes, where UNKNOWN = (1 << 15) = 32768

    :param status: to split
    :returns: a tuple containing (status, quality)
    """
    status_unset = -1
    qualities = {
        'NONE': 0,
        'SDTV': 1,
        'SDDVD': 2,
        'HDTV': 4,
        'RAWHDTV': 8,
        'FULLHDTV': 16,
        'HDWEBDL': 32,
        'FULLHDWEBDL': 64,
        'HDBLURAY': 128,
        'FULLHDBLURAY': 256,
        'UHD_4K_TV': 512,
        'UHD_4K_WEBDL': 1024,
        'UHD_4K_BLURAY': 2048,
        'UHD_8K_TV': 4096,
        'UHD_8K_WEBDL': 8192,
        'UHD_8K_BLURAY': 16384,
        'UNKNOWN': 32768
    }

    status = int(status)
    if status == status_unset:
        return (status_unset, qualities['NONE'])

    for q in sorted(itervalues(qualities), reverse=True):
        if status > q * 100:
            return (status - q * 100, q)

    return (status, qualities['UNKNOWN'])
