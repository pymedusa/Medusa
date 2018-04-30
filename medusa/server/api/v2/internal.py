# coding=utf-8
"""Request handler for internal data."""
from __future__ import unicode_literals

import logging
import os
import re

from medusa import app, db
from medusa.helper.common import try_int
from medusa.logger.adapters.style import BraceAdapter
from medusa.server.api.v2.base import BaseRequestHandler
from medusa.tv.series import Series, SeriesIdentifier

from six import itervalues

from tornado.escape import json_decode

log = BraceAdapter(logging.getLogger(__name__))


class InternalHandler(BaseRequestHandler):
    """Internal data request handler."""

    #: resource name
    name = 'internal'
    #: identifier
    identifier = ('resource', r'\w+')
    #: path param
    path_param = None
    #: allowed HTTP methods
    allowed_methods = ('GET', )

    valid_resources = ('existingSeries', )

    def get(self, resource, path_param=None):
        """Query internal data.

        :param resource: a resource name
        :param path_param:
        :type path_param: str
        """
        if resource is None:
            return self._bad_request('You must provider a resource name')

        if resource not in self.valid_resources:
            return self._bad_request('{key} is a invalid resource'.format(key=resource))

        # Convert 'camelCase' to '_snake_case'
        resource_function = '_' + re.sub('([A-Z]+)', r'_\1', resource).lower()
        data = getattr(self, resource_function)()

        return self._ok(data=data)

    def _existing_series(self):
        """Generate existing series folders data for adding existing shows."""
        root_dirs = json_decode(self.get_argument('root-dir', '[]'))

        if not root_dirs:
            if app.ROOT_DIRS:
                root_dirs = app.ROOT_DIRS[1:]
            else:
                self._not_found('No configured root dirs')

        # Put the default root-dir first
        try:
            default_index = int(app.ROOT_DIRS[0])
            default_root_dir = root_dirs[default_index]
            root_dirs.remove(default_root_dir)
            root_dirs.insert(0, default_root_dir)
        except (IndexError, ValueError):
            pass

        dir_list = []

        # Get a unique list of shows
        query_where = b' OR '.join([b"location LIKE '{0}%'".format(rd) for rd in root_dirs])
        main_db_con = db.DBConnection()
        dir_results = main_db_con.select(
            b'SELECT location '
            b'FROM tv_shows '
            b'WHERE {0}'.format(query_where)
        )

        for root_dir in root_dirs:
            try:
                file_list = os.listdir(root_dir)
            except Exception as error:
                log.info('Unable to list directory {path}: {err!r}',
                         {'path': root_dir, 'err': error})
                continue

            for cur_file in file_list:
                try:
                    cur_path = os.path.normpath(os.path.join(root_dir, cur_file))
                    if not os.path.isdir(cur_path):
                        continue
                except Exception as error:
                    log.info('Unable to get current path {path} and {file}: {err!r}',
                             {'path': root_dir, 'file': cur_file, 'err': error})
                    continue

                cur_dir = {
                    'path': cur_path,
                    'alreadyAdded': False,
                    'existingInfo': {
                        'seriesId': None,
                        'seriesName': None,
                        'indexer': None
                    }
                }

                # Check if the folder is already in the library
                cur_dir['alreadyAdded'] = next((True for entry in dir_results if entry[b'location'] == cur_path), False)

                if not cur_dir['alreadyAdded']:
                    # You may only call .values() on metadata_provider_dict! As on values() call the indexer_api attribute
                    # is reset. This will prevent errors, when using multiple indexers and caching.
                    for cur_provider in itervalues(app.metadata_provider_dict):
                        (series_id, series_name, indexer) = cur_provider.retrieveShowMetadata(cur_path)
                        if all((series_id, series_name, indexer)):
                            cur_dir['existingInfo'] = {
                                'seriesId': try_int(series_id),
                                'seriesName': series_name,
                                'indexer': try_int(indexer)
                            }
                            break

                    series_identifier = SeriesIdentifier(indexer, series_id)
                    cur_dir['alreadyAdded'] = bool(Series.find_by_identifier(series_identifier))

                dir_list.append(cur_dir)

        return self._ok(data=dir_list)
