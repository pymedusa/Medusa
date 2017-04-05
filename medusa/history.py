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
"""Main database History module."""
import datetime

import db

from .common import FAILED, Quality, SNATCHED, SNATCHED_PROPER, SUBTITLED

from .helper.encoding import ss

from .show.history import History


def _log_history_item(action, showid, season, episode, quality, resource,
                      provider, version=-1, proper_tags='', manually_searched=False, info_hash=None, size=-1):
    """
    Insert a history item in DB.

    :param action: action taken (snatch, download, etc)
    :param showid: showid this entry is about
    :param season: show season
    :param episode: show episode
    :param quality: media quality
    :param resource: resource used
    :param provider: provider used
    :param version: tracked version of file (defaults to -1)
    """
    log_date = datetime.datetime.today().strftime(History.date_format)
    resource = ss(resource)

    main_db_con = db.DBConnection()
    main_db_con.action(
        "INSERT INTO history "
        "(action, date, showid, season, episode, quality, "
        "resource, provider, version, proper_tags, manually_searched, info_hash, size) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [action, log_date, showid, season, episode, quality,
         resource, provider, version, proper_tags, manually_searched, info_hash, size])


def log_snatch(search_result):
    """
    Log history of snatch.

    :param search_result: search result object
    """
    for cur_ep_obj in search_result.episodes:

        showid = int(cur_ep_obj.show.indexerid)
        season = int(cur_ep_obj.season)
        episode = int(cur_ep_obj.episode)
        quality = search_result.quality
        version = search_result.version
        proper_tags = '|'.join(search_result.proper_tags)
        manually_searched = search_result.manually_searched
        info_hash = search_result.hash.lower() if search_result.hash else None
        size = search_result.size

        provider_class = search_result.provider
        if provider_class is not None:
            provider = provider_class.name
        else:
            provider = "unknown"

        action = Quality.composite_status(SNATCHED_PROPER if cur_ep_obj.is_proper else SNATCHED, search_result.quality)

        resource = search_result.name

        _log_history_item(action, showid, season, episode, quality, resource,
                          provider, version, proper_tags, manually_searched, info_hash, size)


def log_download(episode, filename, new_ep_quality, release_group=None, version=-1):
    """
    Log history of download.

    :param episode: episode of show
    :param filename: file on disk where the download is
    :param new_ep_quality: Quality of download
    :param release_group: Release group
    :param version: Version of file (defaults to -1)
    """
    showid = int(episode.show.indexerid)
    season = int(episode.season)
    ep_number = int(episode.episode)
    size = int(episode.file_size)

    quality = new_ep_quality

    # store the release group as the provider if possible
    if release_group:
        provider = release_group
    else:
        provider = -1

    action = episode.status

    _log_history_item(action, showid, season, ep_number, quality, filename, provider, version, size=size)


def log_subtitle(showid, season, episode, status, subtitle_result):
    """
    Log download of subtitle.

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

    _log_history_item(action, showid, season, episode, quality, resource, provider)


def log_failed(ep_obj, release, provider=None):
    """
    Log a failed download.

    :param ep_obj: Episode object
    :param release: Release group
    :param provider: Provider used for snatch
    """
    showid = int(ep_obj.show.indexerid)
    season = int(ep_obj.season)
    ep_number = int(ep_obj.episode)
    _, quality = Quality.split_composite_status(ep_obj.status)
    action = Quality.composite_status(FAILED, quality)

    _log_history_item(action, showid, season, ep_number, quality, release, provider)
