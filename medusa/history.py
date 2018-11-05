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
from medusa.show.history import History


def _log_history_item(action, ep_obj, resource, provider, version=-1, proper_tags='',
                      manually_searched=False, info_hash=None, size=-1):
    """
    Insert a history item in DB

    :param action: action taken (snatch, download, etc)
    :param ep_obj: episode object
    :param resource: resource used
    :param provider: provider used
    :param version: tracked version of file (defaults to -1)
    """
    log_date = datetime.datetime.today().strftime(History.date_format)

    main_db_con = db.DBConnection()
    main_db_con.action(
        'INSERT INTO history '
        '(action, date, indexer_id, showid, season, episode, quality, '
        'resource, provider, version, proper_tags, manually_searched, info_hash, size) '
        'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        [action, log_date, ep_obj.series.indexer, ep_obj.series.series_id, ep_obj.season, ep_obj.episode,
         ep_obj.quality, resource, provider, version, proper_tags, manually_searched, info_hash, size])


def log_snatch(search_result):
    """
    Log history of snatch

    :param search_result: search result object
    """
    for ep_obj in search_result.episodes:

        version = search_result.version
        proper_tags = '|'.join(search_result.proper_tags)
        manually_searched = search_result.manually_searched
        info_hash = search_result.hash.lower() if search_result.hash else None
        size = search_result.size

        providerClass = search_result.provider
        if providerClass is not None:
            provider = providerClass.name
        else:
            provider = 'unknown'

        action = SNATCHED
        ep_obj.quality = search_result.quality

        resource = search_result.name

        _log_history_item(action, ep_obj, resource,
                          provider, version, proper_tags, manually_searched, info_hash, size)


def log_download(ep_obj, filename, new_ep_quality, release_group=None, version=-1):
    """
    Log history of download

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

    _log_history_item(action, ep_obj, filename, provider, version, size=size)


def log_subtitle(ep_obj, subtitle_result):
    """
    Log download of subtitle

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
    Log a failed download

    :param ep_obj: Episode object
    :param release: Release group
    :param provider: Provider used for snatch
    """
    _log_history_item(FAILED, ep_obj, release, provider)
