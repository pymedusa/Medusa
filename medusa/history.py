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

import datetime

import db
from .common import FAILED, Quality, SNATCHED, SUBTITLED
from .helper.encoding import ss
from .show.history import History


def _logHistoryItem(action, showid, season, episode, quality, resource,
                    provider, version=-1, proper_tags='', manually_searched=False, info_hash=None, resource_size=-1):
    """
    Insert a history item in DB

    :param action: action taken (snatch, download, etc)
    :param showid: showid this entry is about
    :param season: show season
    :param episode: show episode
    :param quality: media quality
    :param resource: resource used
    :param provider: provider used
    :param version: tracked version of file (defaults to -1)
    """
    logDate = datetime.datetime.today().strftime(History.date_format)
    resource = ss(resource)

    main_db_con = db.DBConnection()
    main_db_con.action(
        "INSERT INTO history "
        "(action, date, showid, season, episode, quality, "
        "resource, provider, version, proper_tags, manually_searched, info_hash, resource_size) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [action, logDate, showid, season, episode, quality,
         resource, provider, version, proper_tags, manually_searched, info_hash, resource_size])


def log_snatch(searchResult):
    """
    Log history of snatch

    :param searchResult: search result object
    """
    for curEpObj in searchResult.episodes:

        showid = int(curEpObj.show.indexerid)
        season = int(curEpObj.season)
        episode = int(curEpObj.episode)
        quality = searchResult.quality
        version = searchResult.version
        proper_tags = '|'.join(searchResult.proper_tags)
        manually_searched = searchResult.manually_searched
        info_hash = searchResult.hash.lower() if searchResult.hash else None
        resource_size = searchResult.size

        providerClass = searchResult.provider
        if providerClass is not None:
            provider = providerClass.name
        else:
            provider = "unknown"

        action = Quality.composite_status(SNATCHED, searchResult.quality)

        resource = searchResult.name

        _logHistoryItem(action, showid, season, episode, quality, resource,
                        provider, version, proper_tags, manually_searched, info_hash, resource_size)


def logDownload(episode, filename, new_ep_quality, release_group=None, version=-1):
    """
    Log history of download

    :param episode: episode of show
    :param filename: file on disk where the download is
    :param new_ep_quality: Quality of download
    :param release_group: Release group
    :param version: Version of file (defaults to -1)
    """
    showid = int(episode.show.indexerid)
    season = int(episode.season)
    ep_number = int(episode.episode)

    quality = new_ep_quality

    # store the release group as the provider if possible
    if release_group:
        provider = release_group
    else:
        provider = -1

    action = episode.status

    _logHistoryItem(action, showid, season, ep_number, quality, filename, provider, version)


def logSubtitle(showid, season, episode, status, subtitle_result):
    """
    Log download of subtitle

    :param showid: Showid of download
    :param season: Show season
    :param episode: Show episode
    :param status: Status of download
    :param subtitle_result: Result object
    """
    resource = subtitle_result.language.opensubtitles
    provider = subtitle_result.provider_name

    status, quality = Quality.split_composite_status(status)
    action = Quality.composite_status(SUBTITLED, quality)

    _logHistoryItem(action, showid, season, episode, quality, resource, provider)


def log_failed(ep_obj, release, provider=None):
    """
    Log a failed download

    :param ep_obj: Episode object
    :param release: Release group
    :param provider: Provider used for snatch
    """
    showid = int(ep_obj.show.indexerid)
    season = int(ep_obj.season)
    ep_number = int(ep_obj.episode)
    _, quality = Quality.split_composite_status(ep_obj.status)
    action = Quality.composite_status(FAILED, quality)

    _logHistoryItem(action, showid, season, ep_number, quality, release, provider)
