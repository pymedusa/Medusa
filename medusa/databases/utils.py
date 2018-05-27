# coding=utf-8

"""General database utility functions."""
from __future__ import unicode_literals

import logging
import sys

from medusa import helpers
from medusa.logger.adapters.style import BraceAdapter


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
