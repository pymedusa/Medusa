# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>

#
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.
from __future__ import unicode_literals

import datetime
from os.path import basename

from medusa import db, ws
from medusa.common import DOWNLOADED, FAILED, SNATCHED, SUBTITLED, statusStrings
from medusa.schedulers.download_handler import ClientStatus, ClientStatusEnum
from medusa.show.history import History


def create_history_item(history_row, compact=False):
    """
    Create a history object, using the data from a history db row item.

    Calculate additional data, where needed.
    :param history_row: a main.db history row.
    :param compact: A boolean indicating if this is used for a compact layout.
    :returns: A dict with history information.
    """
    from medusa.providers import get_provider_class
    from medusa.providers.generic_provider import GenericProvider
    from medusa.tv.series import Series, SeriesIdentifier

    provider = {}
    release_group = None
    release_name = None
    file_name = None
    subtitle_language = None
    show_slug = None
    client_status = None
    show_slug = None
    show_title = 'Missing Show'

    if history_row['action'] in (SNATCHED, FAILED):
        provider_id = GenericProvider.make_id(history_row['provider'])
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
                'name': history_row['provider'],
                'imageName': f'{provider_id}.png'
            })
        release_name = history_row['resource']

    if history_row['action'] == DOWNLOADED:
        release_group = history_row['provider']
        file_name = history_row['resource']

    if history_row['action'] == SUBTITLED:
        subtitle_language = history_row['resource']
        provider['name'] = history_row['provider']

    if history_row['client_status'] is not None:
        status = ClientStatus(status=history_row['client_status'])
        client_status = {
            'status': [s.value for s in status],
            'string': status.status_to_array_string()
        }

    if history_row['indexer_id'] and history_row['showid']:
        identifier = SeriesIdentifier.from_id(history_row['indexer_id'], history_row['showid'])
        show_slug = identifier.slug
        show = Series.find_by_identifier(identifier)
        if show:
            show_title = show.title

    history_row['episodeTitle'] = '{0} - s{1:02d}e{2:02d}'.format(
        show_title, history_row['season'], history_row['episode']
    )

    return {
        'series': show_slug,
        'status': history_row['action'],
        'statusName': statusStrings.get(history_row['action']),
        'actionDate': history_row['date'],
        'quality': history_row['quality'],
        'resource': basename(history_row['resource']),
        'size': history_row['size'],
        'properTags': history_row['proper_tags'],
        'season': history_row['season'],
        'episode': history_row['episode'],
        'episodeTitle': history_row['episodeTitle'],
        'manuallySearched': bool(history_row['manually_searched']),
        'infoHash': history_row['info_hash'],
        'provider': provider,
        'releaseName': release_name,
        'releaseGroup': release_group,
        'fileName': file_name,
        'subtitleLanguage': subtitle_language,
        'showSlug': show_slug,
        'showTitle': show_title,
        'providerType': history_row['provider_type'],
        'clientStatus': client_status,
        'partOfBatch': bool(history_row['part_of_batch'])
    }


def _log_history_item(action, ep_obj, resource=None, provider=None, proper_tags='',
                      manually_searched=False, info_hash=None, size=-1, search_result=None,
                      part_of_batch=False):
    """
    Insert a history item in DB.

    If search_result it passed, it will overwrite other passed named paramaters.

    :param action: action taken (snatch, download, etc)
    :param ep_obj: episode object
    :param resource: resource used
    :param provider: provider class used
    :param search_result: SearchResult object
    """
    log_date = datetime.datetime.today().strftime(History.date_format)
    provider_type = None
    client_status = None
    version = ep_obj.version

    if search_result:
        resource = search_result.name
        version = search_result.version
        proper_tags = '|'.join(search_result.proper_tags)
        manually_searched = search_result.manually_searched
        size = search_result.size

        provider_class = search_result.provider
        if provider_class is not None:
            provider = provider_class.name
            provider_type = provider_class.provider_type
        else:
            provider = 'unknown'
            provider_type = 'unknown'

        if (search_result.result_type == 'torrent' and search_result.hash) \
                or (search_result.result_type == 'nzb' and search_result.nzb_id):
            if search_result.result_type == 'torrent':
                info_hash = search_result.hash.lower()
            elif search_result.result_type == 'nzb':
                info_hash = search_result.nzb_id
            client_status = ClientStatusEnum.SNATCHED.value

    main_db_con = db.DBConnection()
    sql_result = main_db_con.action(
        'INSERT INTO history '
        '(action, date, indexer_id, showid, season, episode, quality, '
        'resource, provider, version, proper_tags, manually_searched, '
        'info_hash, size, provider_type, client_status, part_of_batch) '
        'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        [action, log_date, ep_obj.series.indexer, ep_obj.series.series_id,
         ep_obj.season, ep_obj.episode, ep_obj.quality, resource, provider,
         version, proper_tags, manually_searched, info_hash, size,
         provider_type, client_status, part_of_batch])

    # Update the history page in frontend.
    ws.Message('historyUpdate', create_history_item(
        main_db_con.select('SELECT * FROM history WHERE rowid = ?', [sql_result.lastrowid])[0]
    )).push()


def log_snatch(search_result):
    """
    Log history of snatch.

    :param search_result: search result object
    """
    part_of_batch = len(search_result.episodes) > 1
    for ep_obj in search_result.episodes:
        action = SNATCHED
        ep_obj.quality = search_result.quality
        _log_history_item(action, ep_obj, search_result=search_result, part_of_batch=part_of_batch)


def log_download(ep_obj, filename, release_group=None):
    """
    Log history of download.

    :param ep_obj: episode object of show
    :param filename: file on disk where the download is
    :param new_ep_quality: Quality of download
    :param release_group: Release group
    :param version: Version of file (defaults to -1)
    """
    size = int(ep_obj.file_size)

    # store the release group as the provider if possible
    if release_group:
        provider = release_group
    else:
        provider = -1

    action = ep_obj.status

    _log_history_item(action, ep_obj, filename, provider, size=size)


def log_subtitle(ep_obj, subtitle_result):
    """
    Log download of subtitle.

    :param showid: Showid of download
    :param season: Show season
    :param ep_obj: Show episode object
    :param status: Status of download
    :param subtitle_result: Result object
    """
    resource = subtitle_result.language.opensubtitles
    provider = subtitle_result.provider_name

    _log_history_item(SUBTITLED, ep_obj, resource, provider)


def log_failed(ep_obj, release, provider=None):
    """
    Log a failed download.

    :param ep_obj: Episode object
    :param release: Release group
    :param provider: Provider used for snatch
    """
    _log_history_item(FAILED, ep_obj, release, provider)
