# connectors/pyodbc.py
# Copyright (C) 2005-2018 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from . import Connector
from .. import util


import re


class PyODBCConnector(Connector):
    driver = 'pyodbc'

    supports_sane_rowcount_returning = False
    supports_sane_multi_rowcount = False

    supports_unicode_statements = True
    supports_unicode_binds = True

    supports_native_decimal = True
    default_paramstyle = 'named'

    # for non-DSN connections, this *may* be used to
    # hold the desired driver name
    pyodbc_driver_name = None

    def __init__(self, supports_unicode_binds=None, **kw):
        super(PyODBCConnector, self).__init__(**kw)
        if supports_unicode_binds is not None:
            self.supports_unicode_binds = supports_unicode_binds

    @classmethod
    def dbapi(cls):
        return __import__('pyodbc')

    def create_connect_args(self, url):
        opts = url.translate_connect_args(username='user')
        opts.update(url.query)

        keys = opts

        query = url.query

        connect_args = {}
        for param in ('ansi', 'unicode_results', 'autocommit'):
            if param in keys:
                connect_args[param] = util.asbool(keys.pop(param))

        if 'odbc_connect' in keys:
            connectors = [util.unquote_plus(keys.pop('odbc_connect'))]
        else:
            def check_quote(token):
                if ";" in str(token):
                    token = "'%s'" % token
                return token

            keys = dict(
                (k, check_quote(v)) for k, v in keys.items()
            )

            dsn_connection = 'dsn' in keys or \
                ('host' in keys and 'database' not in keys)
            if dsn_connection:
                connectors = ['dsn=%s' % (keys.pop('host', '') or
                                          keys.pop('dsn', ''))]
            else:
                port = ''
                if 'port' in keys and 'port' not in query:
                    port = ',%d' % int(keys.pop('port'))

                connectors = []
                driver = keys.pop('driver', self.pyodbc_driver_name)
                if driver is None:
                    util.warn(
                        "No driver name specified; "
                        "this is expected by PyODBC when using "
                        "DSN-less connections")
                else:
                    connectors.append("DRIVER={%s}" % driver)

                connectors.extend(
                    [
                        'Server=%s%s' % (keys.pop('host', ''), port),
                        'Database=%s' % keys.pop('database', '')
                    ])

            user = keys.pop("user", None)
            if user:
                connectors.append("UID=%s" % user)
                connectors.append("PWD=%s" % keys.pop('password', ''))
            else:
                connectors.append("Trusted_Connection=Yes")

            # if set to 'Yes', the ODBC layer will try to automagically
            # convert textual data from your database encoding to your
            # client encoding.  This should obviously be set to 'No' if
            # you query a cp1253 encoded database from a latin1 client...
            if 'odbc_autotranslate' in keys:
                connectors.append("AutoTranslate=%s" %
                                  keys.pop("odbc_autotranslate"))

            connectors.extend(['%s=%s' % (k, v) for k, v in keys.items()])

        return [[";".join(connectors)], connect_args]

    def is_disconnect(self, e, connection, cursor):
        if isinstance(e, self.dbapi.ProgrammingError):
            return "The cursor's connection has been closed." in str(e) or \
                'Attempt to use a closed connection.' in str(e)
        else:
            return False

    # def initialize(self, connection):
    #   super(PyODBCConnector, self).initialize(connection)

    def _dbapi_version(self):
        if not self.dbapi:
            return ()
        return self._parse_dbapi_version(self.dbapi.version)

    def _parse_dbapi_version(self, vers):
        m = re.match(
            r'(?:py.*-)?([\d\.]+)(?:-(\w+))?',
            vers
        )
        if not m:
            return ()
        vers = tuple([int(x) for x in m.group(1).split(".")])
        if m.group(2):
            vers += (m.group(2),)
        return vers

    def _get_server_version_info(self, connection):
        # NOTE: this function is not reliable, particularly when
        # freetds is in use.   Implement database-specific server version
        # queries.
        dbapi_con = connection.connection
        version = []
        r = re.compile(r'[.\-]')
        for n in r.split(dbapi_con.getinfo(self.dbapi.SQL_DBMS_VER)):
            try:
                version.append(int(n))
            except ValueError:
                version.append(n)
        return tuple(version)

    def set_isolation_level(self, connection, level):
        # adjust for ConnectionFairy being present
        # allows attribute set e.g. "connection.autocommit = True"
        # to work properly
        if hasattr(connection, 'connection'):
            connection = connection.connection

        if level == 'AUTOCOMMIT':
            connection.autocommit = True
        else:
            connection.autocommit = False
            super(PyODBCConnector, self).set_isolation_level(connection,
                                                             level)
