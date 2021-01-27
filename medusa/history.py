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

from medusa import db
from medusa.common import FAILED, SNATCHED, SUBTITLED
from medusa.schedulers.download_handler import ClientStatusEnum as ClientStatus
from medusa.show.history import History


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
            client_status = ClientStatus.SNATCHED.value

    main_db_con = db.DBConnection()
    main_db_con.action(
        'INSERT INTO history '
        '(action, date, indexer_id, showid, season, episode, quality, '
        'resource, provider, version, proper_tags, manually_searched, '
        'info_hash, size, provider_type, client_status, part_of_batch) '
        'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        [action, log_date, ep_obj.series.indexer, ep_obj.series.series_id,
         ep_obj.season, ep_obj.episode, ep_obj.quality, resource, provider,
         version, proper_tags, manually_searched, info_hash, size,
         provider_type, client_status, part_of_batch])


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
