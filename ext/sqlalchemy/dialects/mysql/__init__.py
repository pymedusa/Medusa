# mysql/__init__.py
# Copyright (C) 2005-2018 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from . import base, mysqldb, oursql, \
    pyodbc, zxjdbc, mysqlconnector, pymysql, \
    gaerdbms, cymysql

from .base import \
    BIGINT, BINARY, BIT, BLOB, BOOLEAN, CHAR, DATE, DATETIME, \
    DECIMAL, DOUBLE, ENUM, DECIMAL,\
    FLOAT, INTEGER, INTEGER, JSON, LONGBLOB, LONGTEXT, MEDIUMBLOB, \
    MEDIUMINT, MEDIUMTEXT, NCHAR, \
    NVARCHAR, NUMERIC, SET, SMALLINT, REAL, TEXT, TIME, TIMESTAMP, \
    TINYBLOB, TINYINT, TINYTEXT,\
    VARBINARY, VARCHAR, YEAR

from .dml import insert, Insert

# default dialect
base.dialect = dialect = mysqldb.dialect


__all__ = (
    'BIGINT', 'BINARY', 'BIT', 'BLOB', 'BOOLEAN', 'CHAR', 'DATE', 'DATETIME',
    'DECIMAL', 'DOUBLE', 'ENUM', 'DECIMAL', 'FLOAT', 'INTEGER', 'INTEGER',
    'JSON', 'LONGBLOB', 'LONGTEXT', 'MEDIUMBLOB', 'MEDIUMINT', 'MEDIUMTEXT',
    'NCHAR', 'NVARCHAR', 'NUMERIC', 'SET', 'SMALLINT', 'REAL', 'TEXT', 'TIME',
    'TIMESTAMP', 'TINYBLOB', 'TINYINT', 'TINYTEXT', 'VARBINARY', 'VARCHAR',
    'YEAR', 'dialect'
)
