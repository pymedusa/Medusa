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
from medusa.tv.show import Show, ShowIdentifier

from six import itervalues

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

    def get(self, resource, path_param=None):
        """Query internal data.

        :param resource: a resource name
        :param path_param:
        :type path_param: str
        """
        if resource is None:
            return self._bad_request('You must provide a resource name')

        # Convert 'camelCase' to 'resource_snake_case'
        resource_function_name = 'resource_' + re.sub('([A-Z]+)', r'_\1', resource).lower()
        resource_function = getattr(self, resource_function_name, None)

        if resource_function is None:
            log.error('Unable to get function "{func}" for resource "{resource}"',
                      {'func': resource_function_name, 'resource': resource})
            return self._bad_request('{key} is a invalid resource'.format(key=resource))

        data = resource_function()
        return self._ok(data=data)

    # existingShow
    def resource_existing_show(self):
        """Generate existing show folders data for adding existing shows."""
        if not app.ROOT_DIRS:
            return self._not_found('No configured root dirs')

        root_dirs = app.ROOT_DIRS[1:]
        root_dirs_indices = self.get_argument('rootDirs', '')

        if root_dirs_indices:
            root_dirs_indices = set(root_dirs_indices.split(','))

            try:
                root_dirs_indices = sorted(map(int, root_dirs_indices))
            except ValueError as error:
                log.warning('Unable to parse root dirs indices: {indices}. Error: {error}',
                            {'indices': root_dirs_indices, 'error': error})
                return self._bad_request('Invalid root dirs indices')

            root_dirs = [root_dirs[idx] for idx in root_dirs_indices]

        dir_list = []

        # Get a unique list of shows
        main_db_con = db.DBConnection()
        dir_results = main_db_con.select(
            b'SELECT location '
            b'FROM tv_shows'
        )
        root_dirs_tuple = tuple(root_dirs)
        dir_results = [
            show[b'location'] for show in dir_results
            if show[b'location'].startswith(root_dirs_tuple)
        ]

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
                    'metadata': {
                        'showId': None,
                        'showName': None,
                        'indexer': None
                    }
                }

                # Check if the folder is already in the library
                cur_dir['alreadyAdded'] = next((True for path in dir_results if path == cur_path), False)

                if not cur_dir['alreadyAdded']:
                    # You may only call .values() on metadata_provider_dict! As on values() call the indexer_api attribute
                    # is reset. This will prevent errors, when using multiple indexers and caching.
                    for cur_provider in itervalues(app.metadata_provider_dict):
                        (show_id, show_name, indexer) = cur_provider.retrieveShowMetadata(cur_path)
                        if all((show_id, show_name, indexer)):
                            cur_dir['metadata'] = {
                                'showId': try_int(show_id),
                                'showName': show_name,
                                'indexer': try_int(indexer)
                            }
                            break

                    show_identifier = ShowIdentifier(indexer, show_id)
                    cur_dir['alreadyAdded'] = bool(Show.find_by_identifier(show_identifier))

                dir_list.append(cur_dir)

        return self._ok(data=dir_list)
