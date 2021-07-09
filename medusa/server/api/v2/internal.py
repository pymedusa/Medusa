# coding=utf-8
"""Request handler for internal data."""
from __future__ import unicode_literals

import logging
import os
import re

from medusa import app, classes, db
from medusa.helper.common import sanitize_filename, try_int
from medusa.indexers.api import indexerApi
from medusa.indexers.exceptions import IndexerException, IndexerUnavailable
from medusa.indexers.utils import reverse_mappings
from medusa.logger.adapters.style import BraceAdapter
from medusa.server.api.v2.base import BaseRequestHandler
from medusa.tv.series import Series, SeriesIdentifier

from six import ensure_text, iteritems, itervalues

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


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

        return resource_function()

    def post(self, resource, path_param=None):
        """Post internal data.

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

        return resource_function()

    # existingSeries
    def resource_existing_series(self):
        """Generate existing series folders data for adding existing shows."""
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
            'SELECT location '
            'FROM tv_shows'
        )
        root_dirs_tuple = tuple(root_dirs)
        dir_results = [
            series['location'] for series in dir_results
            if series['location'].startswith(root_dirs_tuple)
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
                        'seriesId': None,
                        'seriesName': None,
                        'indexer': None
                    }
                }

                # Check if the folder is already in the library
                cur_dir['alreadyAdded'] = next((True for path in dir_results if path == cur_path), False)

                if not cur_dir['alreadyAdded']:
                    # You may only call .values() on metadata_provider_dict! As on values() call the indexer_api attribute
                    # is reset. This will prevent errors, when using multiple indexers and caching.
                    for cur_provider in itervalues(app.metadata_provider_dict):
                        (series_id, series_name, indexer) = cur_provider.retrieveShowMetadata(cur_path)
                        if all((series_id, series_name, indexer)):
                            cur_dir['metadata'] = {
                                'seriesId': try_int(series_id),
                                'seriesName': series_name,
                                'indexer': try_int(indexer)
                            }
                            break

                    series_identifier = SeriesIdentifier(indexer, series_id)
                    cur_dir['alreadyAdded'] = bool(Series.find_by_identifier(series_identifier))

                dir_list.append(cur_dir)

        return self._ok(data=dir_list)

    # searchIndexersForShowName
    def resource_search_indexers_for_show_name(self):
        """
        Search indexers for show name.

        Query parameters:
        :param query: Search term
        :param indexerId: Indexer to search, defined by ID. '0' for all indexers.
        :param language: 2-letter language code to search the indexer(s) in
        """
        query = self.get_argument('query', '').strip()
        indexer_id = self.get_argument('indexerId', '0').strip()
        language = self.get_argument('language', '').strip()

        if not query:
            return self._bad_request('No search term provided.')

        enabled_indexers = indexerApi().indexers
        indexer_id = try_int(indexer_id)
        if indexer_id > 0 and indexer_id not in enabled_indexers:
            return self._bad_request('Invalid indexer id.')

        if not language or language == 'null':
            language = app.INDEXER_DEFAULT_LANGUAGE

        search_terms = [query]

        # If search term ends with what looks like a year, enclose it in ()
        matches = re.match(r'^(.+ |)([12][0-9]{3})$', query)
        if matches:
            search_terms.append('{0}({1})'.format(matches.group(1), matches.group(2)))

        for search_term in search_terms:
            # If search term begins with an article, let's also search for it without
            matches = re.match(r'^(?:a|an|the) (.+)$', search_term, re.I)
            if matches:
                search_terms.append(matches.group(1))

        results = {}
        final_results = []

        # Query indexers for each search term and build the list of results
        for indexer in enabled_indexers if indexer_id == 0 else [indexer_id]:
            indexer_instance = indexerApi(indexer)
            custom_api_params = indexer_instance.api_params.copy()
            custom_api_params['language'] = language
            custom_api_params['custom_ui'] = classes.AllShowsListUI

            try:
                indexer_api = indexer_instance.indexer(**custom_api_params)
            except IndexerUnavailable as msg:
                log.info('Could not initialize indexer {indexer}: {error}',
                         {'indexer': indexer_instance.name, 'error': msg})
                continue

            log.debug('Searching for show with search term(s): {terms} on indexer: {indexer}',
                      {'terms': search_terms, 'indexer': indexer_api.name})
            for search_term in search_terms:
                try:
                    indexer_results = indexer_api[search_term]
                    # add search results
                    results.setdefault(indexer, []).extend(indexer_results)
                except IndexerException as error:
                    log.info('Error searching for show. term(s): {terms} indexer: {indexer} error: {error}',
                             {'terms': search_terms, 'indexer': indexer_api.name, 'error': error})
                except Exception as error:
                    log.error('Internal Error searching for show. term(s): {terms} indexer: {indexer} error: {error}',
                              {'terms': search_terms, 'indexer': indexer_api.name, 'error': error})

        # Get all possible show ids
        all_show_ids = {}
        for show in app.showList:
            for ex_indexer_name, ex_show_id in iteritems(show.externals):
                ex_indexer_id = reverse_mappings.get(ex_indexer_name)
                if not ex_indexer_id:
                    continue
                all_show_ids[(ex_indexer_id, ex_show_id)] = (show.indexer_name, show.series_id)

        for indexer, shows in iteritems(results):
            indexer_api = indexerApi(indexer)
            indexer_results_set = set()
            for show in shows:
                show_id = int(show['id'])
                indexer_results_set.add(
                    (
                        indexer_api.name,
                        indexer,
                        indexer_api.config['show_url'],
                        show_id,
                        show['seriesname'],
                        show['firstaired'] or 'N/A',
                        show.get('network', '') or 'N/A',
                        sanitize_filename(show['seriesname']),
                        all_show_ids.get((indexer, show_id), False)
                    )
                )

            final_results.extend(indexer_results_set)

        language_id = indexerApi().config['langabbv_to_id'][language]
        data = {
            'results': final_results,
            'languageId': language_id
        }
        return self._ok(data=data)

    def resource_check_for_existing_folder(self):
        """Check if the show selected, already has a folder located in one of the root dirs."""
        show_dir = self.get_argument('showdir' '').strip()
        root_dir = self.get_argument('rootdir', '').strip()
        title = self.get_argument('title', '').strip()

        if not show_dir and not(root_dir and title):
            return self._bad_request({
                'showDir': show_dir,
                'rootDir': root_dir,
                'title': title, 'error': 'missing information to determin location'
            })

        path = ''
        if show_dir:
            path = ensure_text(show_dir)
        elif root_dir and title:
            path = os.path.join(root_dir, sanitize_filename(title))

        path_info = {'path': path}
        path_info['pathExists'] = os.path.exists(path)
        if path_info['pathExists']:
            for cur_provider in itervalues(app.metadata_provider_dict):
                (series_id, series_name, indexer) = cur_provider.retrieveShowMetadata(path_info['path'])
                if all((series_id, series_name, indexer)):
                    path_info['metadata'] = {
                        'seriesId': int(series_id),
                        'seriesName': series_name,
                        'indexer': int(indexer)
                    }
                    break

        return self._ok(data={'pathInfo': path_info})
