# coding=utf-8
"""Request handler for alias (scene exceptions)."""
from __future__ import unicode_literals

from os.path import basename

from medusa import db
from medusa.common import DOWNLOADED, FAILED, SNATCHED, SUBTITLED, statusStrings
from medusa.indexers.utils import indexer_id_to_name
from medusa.providers.generic_provider import GenericProvider
from medusa.schedulers.download_handler import ClientStatus
from medusa.server.api.v2.base import BaseRequestHandler
from medusa.tv.series import Series, SeriesIdentifier


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

        if return_last:
            # Return the last history row
            results = db.DBConnection().select('select * from history ORDER BY date DESC LIMIT 1')
            if not results:
                return self._not_found('History data not found')
            return self._ok(data=results[0])

        if series_slug is not None:
            series_identifier = SeriesIdentifier.from_slug(series_slug)
            if not series_identifier:
                return self._bad_request('Invalid series')

            sql_base += ' WHERE indexer_id = ? AND showid = ?'
            params += [series_identifier.indexer.id, series_identifier.id]

        if total_rows:
            sql_base += ' LIMIT ?'
            params += [total_rows]

        sql_base += ' ORDER BY date DESC'
        results = db.DBConnection().select(sql_base, params)

        if not results:
            return self._not_found('History data not found')

        if compact_layout:
            from collections import OrderedDict
            res = OrderedDict()

            for item in results:
                if item.get('showid') and item.get('season') and item.get('episode') and item.get('indexer_id'):
                    item['showslug'] = f"{indexer_id_to_name(item['indexer_id'])}{item['showid']}"
                    my_key = f"{item['showslug']}S{item['season']}E{item['episode']}"
                    res.setdefault(my_key, []).append(item)
            results = res

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
                show_title = 'Unknown Show'

                if item['action'] in (SNATCHED, FAILED):
                    provider.update({
                        'id': GenericProvider.make_id(item['provider']),
                        'name': item['provider']
                    })
                    release_name = item['resource']

                if item['action'] == DOWNLOADED:
                    release_group = item['provider']
                    file_name = item['resource']

                if item['action'] == SUBTITLED:
                    subtitle_language = item['resource']

                if item['action'] == SUBTITLED:
                    subtitle_language = item['resource']

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
                        provider.update({
                            'id': GenericProvider.make_id(item['provider']),
                            'name': item['provider']
                        })
                        release_name = item['resource']

                    if item['action'] == DOWNLOADED:
                        release_group = item['provider']
                        file_name = item['resource']

                    if item['action'] == SUBTITLED:
                        subtitle_language = item['resource']

                    if item['action'] == SUBTITLED:
                        subtitle_language = item['resource']

                    item['showSlug'] = None
                    item['showTitle'] = 'Unknown Show'
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
            return self._paginate(data_generator=data_generator_compact)

        return self._paginate(data_generator=data_generator)

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
