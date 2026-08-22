# coding=utf-8
"""Request handler for alias (scene exceptions)."""
from __future__ import unicode_literals

import json
import logging
import re
from os.path import basename

from medusa import db
from medusa.common import DOWNLOADED, FAILED, SNATCHED, SUBTITLED, statusStrings
from medusa.indexers.utils import indexer_id_to_name
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers import get_provider_class
from medusa.providers.generic_provider import GenericProvider
from medusa.schedulers.download_handler import ClientStatus
from medusa.server.api.v2.base import BaseRequestHandler
from medusa.tv.series import Series, SeriesIdentifier


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

SQLITE_MAX_INTEGER = (1 << 63) - 1


def _normalize_text_filter(value):
    """Normalize Episode or Provider text while preserving quoted boundary whitespace."""
    if not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    wrappers = "'\"`"
    if value[0] in wrappers or value[-1] in wrappers:
        if len(value) >= 2 and value[0] == value[-1]:
            value = value[1:-1]
            return value if value else None
        value = value.strip(wrappers).strip()
        return value or None

    return value


def _parse_size_filter(value):
    """Return a validated size operator and byte value, or None."""
    if not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    if len(value) >= 2 and value[0] in "'\"`" and value[-1] == value[0]:
        value = value[1:-1].strip()

    match = re.fullmatch(r'(?P<operator>[<>])\s*(?P<size>[0-9]{1,6})', value)
    if not match:
        return None

    return match.group('operator'), int(match.group('size')) * 1024 * 1024


def _parse_series_identifier_slug(value):
    """Return an identifier for an exact canonical series slug, if present."""
    if not isinstance(value, str):
        return None

    slug = value.lower()
    try:
        identifier = SeriesIdentifier.from_slug(slug)
    except (TypeError, ValueError):
        return None
    if identifier and identifier.id > SQLITE_MAX_INTEGER:
        return None
    if identifier and identifier.slug.lower() == slug:
        return identifier


class HistoryHandler(BaseRequestHandler):
    """History request handler."""

    #: resource name
    name = 'history'
    #: identifier
    identifier = ('series_slug', r'\w+')
    #: path param
    path_param = ('path_param', r'\w+')
    #: allowed HTTP methods
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    @staticmethod
    def _parse_episode_resource(resource):
        """Return title, season, and episode when the input is a rendered episode text."""
        match = re.fullmatch(
            r'(?P<title>.+?)\s+-\s+s(?P<season>\d+)e(?P<episode>\d+)',
            resource,
            re.IGNORECASE
        )
        if not match:
            return resource, None, None
        return match.group('title'), int(match.group('season')), int(match.group('episode'))

    def get(self, series_slug, path_param):
        """
        Get history records.

        History records can be specified using a show slug.
        """
        sql_base = """
            SELECT rowid, date, action, quality,
                   provider, version, resource, size, proper_tags,
                   indexer_id, showid, season, episode, manually_searched,
                   info_hash, provider_type, client_status, part_of_batch
            FROM history
        """
        params = []

        arg_page = self._get_page()
        arg_limit = self._get_limit(default=50)
        compact_layout = bool(self.get_argument('compact', default=False))
        return_last = bool(self.get_argument('last', default=False))
        total_rows = self.get_argument('total', default=None)
        sort = json.loads(self.get_argument('sort', default='null'))
        filter = json.loads(self.get_argument('filter', default='null'))

        headers = {}

        if return_last:
            # Return the last history row
            results = db.DBConnection().select('select * from history ORDER BY date DESC LIMIT 1')
            if not results:
                return self._not_found('History data not found')
            return self._ok(data=results[0])

        where = []
        where_with_ops = []

        if series_slug is not None:
            series_identifier = SeriesIdentifier.from_slug(series_slug)
            if not series_identifier:
                return self._bad_request('Invalid series')

            where += ['indexer_id', 'showid']
            params += [series_identifier.indexer.id, series_identifier.id]

        field_map = {
            'actiondate': 'date',
            'date': 'date',
            'action': 'action',
            'statusname': 'action',
            'providerId': 'provider',
            'clientstatus': 'client_status',
            'size': 'size',
            'quality': 'quality'
        }

        # Prepare an operator (> or <) and size, for the size query.
        size_filter = None
        provider = None
        resource = None

        if filter is not None and filter.get('columnFilters'):
            size = filter['columnFilters'].pop('size', None)
            provider = _normalize_text_filter(filter['columnFilters'].pop('providerId', None))
            resource = _normalize_text_filter(filter['columnFilters'].pop('resource', None))
            size_filter = _parse_size_filter(size)

            for filter_field, filter_value in filter['columnFilters'].items():
                # Loop through each column filter apply the mapping, and add to sql_base.
                filter_field = field_map.get(filter_field.lower())
                if not filter_field or not filter_value:
                    continue
                where += [filter_field]
                params += [filter_value]

        # Add size query (with operator)
        if size_filter:
            size_operator, size = size_filter
            where_with_ops += [f' size {size_operator} ? ']
            params.append(size)

        # Add provider with like %provider%
        if provider:
            where_with_ops += [' provider LIKE ? ']
            params.append(f'%%{provider}%%')

        cte_query = ''
        cte_params = []

        # Search resource with like %resource%
        if resource:
            (resource_title_filter, resource_season, resource_episode) = self._parse_episode_resource(resource)
            resource_identifier = _parse_series_identifier_slug(resource_title_filter)
            like_resource_title = f'%%{resource_title_filter}%%'
            like_resource = f'%%{resource}%%'
            cte_query = """
                WITH show_match_identities AS (
                    SELECT indexer, indexer_id
                    FROM tv_shows
                    WHERE LOWER(show_name) LIKE LOWER(?)
                    UNION
                    SELECT indexer, series_id AS indexer_id
                    FROM scene_exceptions
                    WHERE LOWER(title) LIKE LOWER(?)
            """
            cte_params.extend([like_resource_title, like_resource_title])
            cte_query += """
                )
            """
            if resource_season is not None and resource_episode is not None:
                direct_identity = ''
                direct_identity_params = []
                if resource_identifier:
                    direct_identity = (
                        ' OR (history.indexer_id = ? AND history.showid = ?'
                        ' AND history.season = ? AND history.episode = ?)'
                    )
                    direct_identity_params = [
                        resource_identifier.indexer.id,
                        resource_identifier.id,
                        resource_season,
                        resource_episode
                    ]
                where_with_ops += [
                    '(LOWER(resource) LIKE LOWER(?)'
                    + direct_identity
                    + ' OR EXISTS ('
                    ' SELECT 1 FROM show_match_identities sm'
                    ' WHERE sm.indexer = history.indexer_id'
                    ' AND sm.indexer_id = history.showid'
                    ' AND history.season = ? AND history.episode = ?'
                    '))'
                ]
                params += [like_resource] + direct_identity_params + [resource_season, resource_episode]
            else:
                direct_identity = ''
                direct_identity_params = []
                if resource_identifier:
                    direct_identity = ' OR (history.indexer_id = ? AND history.showid = ?)'
                    direct_identity_params = [resource_identifier.indexer.id, resource_identifier.id]
                where_with_ops += [
                    '(LOWER(resource) LIKE LOWER(?)'
                    + direct_identity
                    + ' OR EXISTS ('
                    ' SELECT 1 FROM show_match_identities sm'
                    ' WHERE sm.indexer = history.indexer_id'
                    ' AND sm.indexer_id = history.showid'
                    '))'
                ]
                params += [like_resource] + direct_identity_params

        if where:
            sql_base += ' WHERE ' + ' AND '.join(f'{item} = ?' for item in where)

        if where_with_ops:
            sql_base += ' WHERE ' if not where else ' AND '
            sql_base += ' AND '.join(where_with_ops)

        if sort is not None and len(sort) == 1:  # Only support one sort column right now.
            field = sort[0].get('field').lower()
            order = sort[0].get('type')
            if field_map.get(field):
                sql_base += f' ORDER BY {field_map[field]} {order} '

        if total_rows:
            sql_base += ' LIMIT ?'
            params += [total_rows]

        results = db.DBConnection().select(cte_query + sql_base, cte_params + params)

        if compact_layout:
            from collections import OrderedDict
            res = OrderedDict()

            for item in results:
                if item.get('showid') and item.get('season') and item.get('episode') and item.get('indexer_id'):
                    item['showslug'] = f"{indexer_id_to_name(item['indexer_id'])}{item['showid']}"
                    group_by_key = f"{item['showslug']}S{item['season']}E{item['episode']}Q{item['quality']}"
                    res.setdefault(group_by_key, []).append(item)
            results = res
        headers['X-Pagination-Count'] = len(results)

        def data_generator():
            """Read and paginate history records."""
            start = arg_limit * (arg_page - 1)

            for item in results[start:start + arg_limit]:
                provider = {}
                release_group = None
                release_name = None
                file_name = None
                subtitle_language = None
                show_slug = None
                client_status = None
                show_slug = None
                show_title = 'Missing Show'

                if item['action'] in (SNATCHED, FAILED):
                    provider_id = GenericProvider.make_id(item['provider'])
                    provider_class = get_provider_class(provider_id)

                    if provider_class:
                        provider.update({
                            'id': provider_class.get_id(),
                            'name': provider_class.name,
                            'imageName': provider_class.image_name()
                        })
                    else:
                        provider.update({
                            'id': provider_id,
                            'name': item['provider'],
                            'imageName': f'{provider_id}.png'
                        })
                    release_name = item['resource']

                if item['action'] == DOWNLOADED:
                    release_group = item['provider']
                    file_name = item['resource']

                if item['action'] == SUBTITLED:
                    subtitle_language = item['resource']
                    provider['name'] = item['provider']

                if item['client_status'] is not None:
                    status = ClientStatus(status=item['client_status'])
                    client_status = {
                        'status': [s.value for s in status],
                        'string': status.status_to_array_string()
                    }

                if item['indexer_id'] and item['showid']:
                    identifier = SeriesIdentifier.from_id(item['indexer_id'], item['showid'])
                    show_slug = identifier.slug
                    show = Series.find_by_identifier(identifier)
                    if show:
                        show_title = show.title

                item['episodeTitle'] = '{0} - s{1:02d}e{2:02d}'.format(
                    show_title, item['season'], item['episode']
                )

                yield {
                    'id': item['rowid'],
                    'series': show_slug,
                    'status': item['action'],
                    'statusName': statusStrings.get(item['action']),
                    'actionDate': item['date'],
                    'quality': item['quality'],
                    'resource': basename(item['resource']),
                    'size': item['size'],
                    'properTags': item['proper_tags'],
                    'season': item['season'],
                    'episode': item['episode'],
                    'episodeTitle': item['episodeTitle'],
                    'manuallySearched': bool(item['manually_searched']),
                    'infoHash': item['info_hash'],
                    'provider': provider,
                    'releaseName': release_name,
                    'releaseGroup': release_group,
                    'fileName': file_name,
                    'subtitleLanguage': subtitle_language,
                    'showSlug': show_slug,
                    'showTitle': show_title,
                    'providerType': item['provider_type'],
                    'clientStatus': client_status,
                    'partOfBatch': bool(item['part_of_batch'])
                }

        def data_generator_compact():
            """
            Read and paginate history records.

            Results are provided grouped per showid+season+episode.
            The results are flattened into a structure of [{'actionDate': .., 'showSlug':.., 'rows':Array(history_items)},]
            """
            start = arg_limit * (arg_page - 1)

            for compact_item in list(results.values())[start:start + arg_limit]:
                return_item = {'rows': []}
                for item in compact_item:
                    provider = {}
                    release_group = None
                    release_name = None
                    file_name = None
                    subtitle_language = None

                    if item['action'] in (SNATCHED, FAILED):
                        provider_id = GenericProvider.make_id(item['provider'])
                        provider_class = get_provider_class(provider_id)
                        if provider_class:
                            provider.update({
                                'id': provider_class.get_id(),
                                'name': provider_class.name,
                                'imageName': provider_class.image_name()
                            })
                        else:
                            provider.update({
                                'id': provider_id,
                                'name': item['provider'],
                                'imageName': f'{provider_id}.png'
                            })
                        release_name = item['resource']

                    if item['action'] == DOWNLOADED:
                        release_group = item['provider']
                        file_name = item['resource']

                    if item['action'] == SUBTITLED:
                        subtitle_language = item['resource']
                        provider['name'] = item['provider']

                    item['showSlug'] = None
                    item['showTitle'] = 'Missing Show'
                    if item['indexer_id'] and item['showid']:
                        identifier = SeriesIdentifier.from_id(item['indexer_id'], item['showid'])
                        item['showSlug'] = identifier.slug
                        show = Series.find_by_identifier(identifier)
                        if show:
                            item['showTitle'] = show.title

                    return_item['actionDate'] = item['date']
                    return_item['showSlug'] = item['showslug']
                    return_item['episodeTitle'] = '{0} - s{1:02d}e{2:02d}'.format(
                        item['showTitle'], item['season'], item['episode']
                    )
                    return_item['quality'] = item['quality']

                    return_item['rows'].append({
                        'actionDate': item['date'],
                        'id': item['rowid'],
                        'series': item['showSlug'],
                        'status': item['action'],
                        'statusName': statusStrings.get(item['action']),
                        'quality': item['quality'],
                        'resource': basename(item['resource']),
                        'size': item['size'],
                        'properTags': item['proper_tags'],
                        'season': item['season'],
                        'episode': item['episode'],
                        'manuallySearched': bool(item['manually_searched']),
                        'infoHash': item['info_hash'],
                        'provider': provider,
                        'release_name': release_name,
                        'releaseGroup': release_group,
                        'fileName': file_name,
                        'subtitleLanguage': subtitle_language,
                        'showSlug': item['showslug'],
                        'showTitle': item['showTitle']
                    })
                yield return_item

        if compact_layout:
            return self._paginate(data_generator=data_generator_compact, headers=headers)

        return self._paginate(data_generator=data_generator, headers=headers)

    def delete(self, identifier, **kwargs):
        """Delete a history record."""
        identifier = self._parse(identifier)
        if not identifier:
            return self._bad_request('Invalid history id')

        main_db_con = db.DBConnection()
        last_changes = main_db_con.connection.total_changes
        main_db_con.action('DELETE FROM history WHERE row_id = ?', [identifier])
        if main_db_con.connection.total_changes - last_changes <= 0:
            return self._not_found('History row not found')

        return self._no_content()
