# coding=utf-8
"""Request handler for internal data."""
from __future__ import unicode_literals

import datetime
import logging
import os
import re

import markdown2

from medusa import app, classes, db, network_timezones, providers
from medusa.common import (
    DOWNLOADED, Overview, Quality,
    SNATCHED, SNATCHED_BEST, SNATCHED_PROPER,
    statusStrings
)
from medusa.helper.common import episode_num, sanitize_filename, try_int
from medusa.indexers.api import indexerApi
from medusa.indexers.exceptions import IndexerException, IndexerUnavailable
from medusa.indexers.utils import reverse_mappings
from medusa.logger.adapters.style import BraceAdapter
from medusa.network_timezones import app_timezone
from medusa.providers.generic_provider import GenericProvider
from medusa.sbdatetime import sbdatetime
from medusa.server.api.v2.base import BaseRequestHandler
from medusa.subtitles import subtitle_code_filter, wanted_languages
from medusa.tv.episode import Episode, EpisodeNumber, RelativeNumber
from medusa.tv.series import Series, SeriesIdentifier

from six import ensure_text, iteritems, itervalues

from tornado.escape import json_decode

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
    allowed_methods = ('GET', 'POST')

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

    # deleteSceneExceptions
    def resource_delete_scene_exceptions(self):
        """Delete all automatically added scene exceptions.

        Custom added scene exceptions will be left alone, as these can already be removed manually.
        """
        main_db_con = db.DBConnection()
        main_db_con.action('DELETE FROM scene_exceptions WHERE custom = 0;')
        return self._ok()

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
                        indexer_api.config['show_url'].format(show_id),
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

    def resource_get_episode_backlog(self):
        """Collect backlog search information for each show."""
        status = self.get_argument('status' '').strip()
        period = self.get_argument('period', '').strip()

        available_backlog_status = {
            'all': [Overview.QUAL, Overview.WANTED],
            'quality': [Overview.QUAL],
            'wanted': [Overview.WANTED]
        }

        available_backlog_periods = {
            'all': None,
            'one_day': datetime.timedelta(days=1),
            'three_days': datetime.timedelta(days=3),
            'one_week': datetime.timedelta(days=7),
            'one_month': datetime.timedelta(days=30),
        }

        if status not in available_backlog_status:
            return self._bad_request("allowed status values are: 'all', 'quality' and 'wanted'")

        if period not in available_backlog_periods:
            return self._bad_request("allowed period values are: 'all', 'one_day', 'three_days', 'one_week' and 'one_month'")

        backlog_status = available_backlog_status.get(status)
        backlog_period = available_backlog_periods.get(period)

        main_db_con = db.DBConnection()
        results = []

        for cur_show in app.showList:
            if cur_show.paused:
                continue

            ep_counts = {
                'wanted': 0,
                'allowed': 0,
            }
            ep_cats = {}

            sql_results = main_db_con.select(
                """
                SELECT e.status, e.quality, e.season,
                e.episode, e.name, e.airdate, e.manually_searched
                FROM tv_episodes as e
                WHERE e.season IS NOT NULL AND
                      e.indexer = ? AND e.showid = ?
                ORDER BY e.season DESC, e.episode DESC
                """,
                [cur_show.indexer, cur_show.series_id]
            )

            filtered_episodes = []
            for cur_result in sql_results:
                cur_ep_cat = cur_show.get_overview(
                    cur_result['status'], cur_result['quality'], backlog_mode=True,
                    manually_searched=cur_result['manually_searched']
                )
                if cur_ep_cat:
                    if cur_ep_cat in backlog_status and cur_result['airdate'] != 1:
                        air_date = datetime.datetime.fromordinal(cur_result['airdate'])
                        if air_date.year >= 1970 or cur_show.network:
                            air_date = sbdatetime.convert_to_setting(
                                network_timezones.parse_date_time(
                                    cur_result['airdate'], cur_show.airs, cur_show.network
                                )
                            )
                            if backlog_period and air_date < datetime.datetime.now(app_timezone) - backlog_period:
                                continue
                        else:
                            air_date = None
                        episode_string = u'{ep}'.format(ep=(episode_num(cur_result['season'],
                                                                        cur_result['episode'])
                                                            or episode_num(cur_result['season'],
                                                                           cur_result['episode'],
                                                                           numbering='absolute')))
                        cur_ep_cat_string = Overview.overviewStrings[cur_ep_cat]
                        ep_cats[episode_string] = cur_ep_cat_string
                        ep_counts[cur_ep_cat_string] += 1
                        cur_result['airdate'] = air_date.isoformat('T') if air_date else ''
                        cur_result['manuallySearched'] = cur_result['manually_searched']
                        del cur_result['manually_searched']
                        cur_result['statusString'] = statusStrings[cur_result['status']]
                        cur_result['qualityString'] = Quality.qualityStrings[cur_result['quality']]

                        cur_result['slug'] = episode_string
                        filtered_episodes.append(cur_result)

            if filtered_episodes:
                results.append({
                    'slug': cur_show.identifier.slug,
                    'name': cur_show.name,
                    'quality': cur_show.quality,
                    'episodeCount': ep_counts,
                    'category': ep_cats,
                    'episodes': filtered_episodes
                })

        return self._ok(data=results)

    def resource_get_episode_status(self):
        """Return a list of episodes with a specific status."""
        status = self.get_argument('status' '').strip()

        status_list = [int(status)]

        if status_list:
            if status_list[0] == SNATCHED:
                status_list = [SNATCHED, SNATCHED_PROPER, SNATCHED_BEST]
        else:
            status_list = []

        main_db_con = db.DBConnection()
        status_results = main_db_con.select(
            'SELECT show_name, tv_shows.indexer, tv_shows.show_id, tv_shows.indexer_id AS indexer_id, '
            'tv_episodes.season AS season, tv_episodes.episode AS episode, tv_episodes.name as name '
            'FROM tv_episodes, tv_shows '
            'WHERE season != 0 '
            'AND tv_episodes.showid = tv_shows.indexer_id '
            'AND tv_episodes.indexer = tv_shows.indexer '
            'AND tv_episodes.status IN ({statuses}) '.format(statuses=','.join(['?'] * len(status_list))),
            status_list
        )

        episode_status = {}
        for cur_status_result in status_results:
            cur_indexer = int(cur_status_result['indexer'])
            cur_series_id = int(cur_status_result['indexer_id'])
            show_slug = SeriesIdentifier.from_id(cur_indexer, cur_series_id).slug

            if show_slug not in episode_status:
                episode_status[show_slug] = {
                    'selected': True,
                    'slug': show_slug,
                    'name': cur_status_result['show_name'],
                    'episodes': [],
                    'showEpisodes': False
                }

            episode_status[show_slug]['episodes'].append({
                'episode': cur_status_result['episode'],
                'season': cur_status_result['season'],
                'selected': True,
                'slug': str(RelativeNumber(cur_status_result['season'], cur_status_result['episode'])),
                'name': cur_status_result['name']
            })

        return self._ok(data={'episodeStatus': episode_status})

    def resource_update_episode_status(self):
        """
        Mass update episodes statuses for multiple shows at once.

        example: Pass the following structure:
            status: 3,
            shows: [
                {
                    'slug': 'tvdb1234',
                    'episodes': ['s01e01', 's02e03', 's10e10']
                },
            ]
        """
        data = json_decode(self.request.body)
        status = data.get('status')
        shows = data.get('shows', [])

        if status not in statusStrings:
            return self._bad_request('You need to provide a valid status code')

        ep_sql_l = []
        for show in shows:
            # Loop through the shows. Each show should have an array of episode slugs
            series_identifier = SeriesIdentifier.from_slug(show.get('slug'))
            if not series_identifier:
                log.warning('Could not create a show identifier with slug {slug}', {'slug': show.get('slug')})
                continue

            series = Series.find_by_identifier(series_identifier)
            if not series:
                log.warning('Could not match to a show in the library with slug {slug}', {'slug': show.get('slug')})
                continue

            episodes = []
            for episode_slug in show.get('episodes', []):
                episode_number = EpisodeNumber.from_slug(episode_slug)
                if not episode_number:
                    log.warning('Bad episode number from slug {slug}', {'slug': episode_slug})
                    continue

                episode = Episode.find_by_series_and_episode(series, episode_number)
                if not episode:
                    log.warning('Episode not found with slug {slug}', {'slug': episode_slug})

                ep_sql = episode.mass_update_episode_status(status)
                if ep_sql:
                    ep_sql_l.append(ep_sql)

                    # Keep an array of episodes for the trakt sync
                    episodes.append(episode)

            if episodes:
                series.sync_trakt_episodes(status, episodes)

        if ep_sql_l:
            main_db_con = db.DBConnection()
            main_db_con.mass_action(ep_sql_l)

        return self._ok(data={'count': len(ep_sql_l)})

    def resource_get_failed(self):
        """Get data from the failed.db/failed table."""
        limit = self.get_argument('limit' '').strip()

        failed_db_con = db.DBConnection('failed.db')
        if int(limit):
            sql_results = failed_db_con.select(
                'SELECT ROWID AS id, release, size, provider '
                'FROM failed '
                'LIMIT ?',
                [limit]
            )
        else:
            sql_results = failed_db_con.select(
                'SELECT ROWID AS id, release, size, provider '
                'FROM failed'
            )

        results = []
        for result in sql_results:
            provider = {}
            provider_id = GenericProvider.make_id(result['provider'])
            provider_class = providers.get_provider_class(provider_id)

            if provider_class:
                provider.update({
                    'id': provider_class.get_id(),
                    'name': provider_class.name,
                    'imageName': provider_class.image_name()
                })
            else:
                provider.update({
                    'id': provider_id,
                    'name': result['provider'],
                    'imageName': f'{provider_id}.png'
                })

            results.append({
                'id': result['id'],
                'release': result['release'],
                'size': result['size'],
                'provider': provider
            })

        return self._ok(data=results)

    def resource_remove_failed(self):
        """
        Remove rows from the failed.db/failed table.

        Pass an array of ROWID's.
        :example: {remove: [1, 2, 3, 4, 10]}
        """
        data = json_decode(self.request.body)
        remove = data.get('remove', [])
        if not remove:
            return self._bad_request('Nothing to remove')

        failed_db_con = db.DBConnection('failed.db')
        failed_db_con.action(
            'delete from failed WHERE ROWID in ({remove})'.format(remove=','.join(['?'] * len(remove))),
            remove
        )

        return self._ok()

    def resource_get_subtitle_missed(self):
        """Return a list of episodes which are missing a specific subtitle language."""
        language = self.get_argument('language' '').strip()

        main_db_con = db.DBConnection()
        results = main_db_con.select(
            'SELECT show_name, tv_shows.show_id, tv_shows.indexer, '
            'tv_shows.indexer_id AS indexer_id, tv_episodes.subtitles subtitles, '
            'tv_episodes.episode AS episode, tv_episodes.season AS season, '
            'tv_episodes.name AS name '
            'FROM tv_episodes, tv_shows '
            'WHERE tv_shows.subtitles = 1 '
            'AND tv_episodes.status = ? '
            'AND tv_episodes.season != 0 '
            "AND tv_episodes.location != '' "
            'AND tv_episodes.showid = tv_shows.indexer_id '
            'AND tv_episodes.indexer = tv_shows.indexer '
            'ORDER BY show_name',
            [DOWNLOADED]
        )

        subtitle_status = {}
        for cur_status_result in results:
            cur_indexer = int(cur_status_result['indexer'])
            cur_series_id = int(cur_status_result['indexer_id'])
            show_slug = SeriesIdentifier.from_id(cur_indexer, cur_series_id).slug
            subtitles = cur_status_result['subtitles'].split(',')

            if language == 'all':
                if not frozenset(wanted_languages()).difference(subtitles):
                    continue
            elif language in subtitles:
                continue

            if show_slug not in subtitle_status:
                subtitle_status[show_slug] = {
                    'selected': True,
                    'slug': show_slug,
                    'name': cur_status_result['show_name'],
                    'episodes': [],
                    'showEpisodes': False
                }

            subtitle_status[show_slug]['episodes'].append({
                'episode': cur_status_result['episode'],
                'season': cur_status_result['season'],
                'selected': True,
                'slug': str(RelativeNumber(cur_status_result['season'], cur_status_result['episode'])),
                'name': cur_status_result['name'],
                'subtitles': subtitles
            })

        return self._ok(data=subtitle_status)

    def resource_search_missing_subtitles(self):
        """
        Search missing subtitles for multiple episodes at once.

        example: Pass the following structure:
            language: 'all', // Or a three letter language code.
            shows: [
                {
                    'slug': 'tvdb1234',
                    'episodes': ['s01e01', 's02e03', 's10e10']
                },
            ]
        """
        data = json_decode(self.request.body)
        language = data.get('language', 'all')
        shows = data.get('shows', [])

        if language != 'all' and language not in subtitle_code_filter():
            return self._bad_request('You need to provide a valid subtitle code')

        for show in shows:
            # Loop through the shows. Each show should have an array of episode slugs
            series_identifier = SeriesIdentifier.from_slug(show.get('slug'))
            if not series_identifier:
                log.warning('Could not create a show identifier with slug {slug}', {'slug': show.get('slug')})
                continue

            series = Series.find_by_identifier(series_identifier)
            if not series:
                log.warning('Could not match to a show in the library with slug {slug}', {'slug': show.get('slug')})
                continue

            for episode_slug in show.get('episodes', []):
                episode_number = EpisodeNumber.from_slug(episode_slug)
                if not episode_number:
                    log.warning('Bad episode number from slug {slug}', {'slug': episode_slug})
                    continue

                episode = Episode.find_by_series_and_episode(series, episode_number)
                if not episode:
                    log.warning('Episode not found with slug {slug}', {'slug': episode_slug})

                episode.download_subtitles(lang=language if language != 'all' else None)

        return self._ok()

    def resource_get_news(self):
        """Retrieve news and convert the markdown to html."""
        news = app.version_check_scheduler.action.check_for_new_news(force=True)
        if not news:
            news = 'Could not load news from the repository. [Click here for news.md]({url})'.format(url=app.NEWS_URL)

        app.NEWS_LAST_READ = app.NEWS_LATEST
        app.NEWS_UNREAD = 0
        app.instance.save_config()

        data = markdown2.markdown(news if news else 'The was a problem connecting to GitHub, please refresh and try again', extras=['header-ids'])
        return self._ok(data)

    def resource_get_changelog(self):
        """Retrieve changelog and convert the markdown to html."""
        # TODO: SESSION: Check if this needs some more explicit exception handling.
        from medusa.session.core import MedusaSafeSession
        changes = MedusaSafeSession().get_text(app.CHANGES_URL)

        if not changes:
            changes = 'Could not load changes from the repo. [Click here for CHANGES.md]({url})'.format(url=app.CHANGES_URL)

        data = markdown2.markdown(
            changes if changes else 'The was a problem connecting to github, please refresh and try again', extras=['header-ids']
        )
        return self._ok(data)
