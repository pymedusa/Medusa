# coding=utf-8

"""
This file is for automated updates of old versions prior to the
refactor, or for migration from SickRage
"""

# oldest db version we support migrating from
MIN_DB_VERSION = 9

# Max version is not the actual version number, (that is in main_db)
# it just guarantees that an "upgrade" status will be reported
MAX_DB_VERSION = 99
