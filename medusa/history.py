import datetime

import db
from medusa.common import FAILED, Quality, SNATCHED, SUBTITLED
from medusa.helper.encoding import ss
from medusa.show.history import History


def _log_history_item(action, ep_obj, quality, resource,
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
    logDate = datetime.datetime.today().strftime(History.date_format)
    resource = ss(resource)

    main_db_con = db.DBConnection()
    main_db_con.action(
        "INSERT INTO history "
        "(action, date, indexer_id, showid, season, episode, quality, "
        "resource, provider, version, proper_tags, manually_searched, info_hash, size) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [action, logDate, ep_obj.series.indexer, ep_obj.series.series_id, ep_obj.season, ep_obj.episode, quality,
         resource, provider, version, proper_tags, manually_searched, info_hash, size])


def log_snatch(searchResult):
    """
    Log history of snatch.

    :param searchResult: search result object
    """
    for ep_obj in searchResult.episodes:

        quality = searchResult.quality
        version = searchResult.version
        proper_tags = '|'.join(searchResult.proper_tags)
        manually_searched = searchResult.manually_searched
        info_hash = searchResult.hash.lower() if searchResult.hash else None
        size = searchResult.size

        providerClass = searchResult.provider
        if providerClass is not None:
            provider = providerClass.name
        else:
            provider = "unknown"

        action = Quality.composite_status(SNATCHED, searchResult.quality)

        resource = searchResult.name

        _log_history_item(action, ep_obj, quality, resource,
                          provider, version, proper_tags, manually_searched, info_hash, size)


def log_download(ep_obj, filename, new_ep_quality, release_group=None, version=-1):
    """
    Log history of download.

    :param ep_obj: episode object of show
    :param filename: file on disk where the download is
    :param new_ep_quality: Quality of download
    :param release_group: Release group
    :param version: Version of file (defaults to -1)
    """
    size = int(ep_obj.file_size)

    quality = new_ep_quality

    # store the release group as the provider if possible
    if release_group:
        provider = release_group
    else:
        provider = -1

    action = ep_obj.status

    _log_history_item(action, ep_obj, quality, filename, provider, version, size=size)


def log_subtitle(ep_obj, status, subtitle_result):
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

    status, quality = Quality.split_composite_status(status)
    action = Quality.composite_status(SUBTITLED, quality)

    _log_history_item(action, ep_obj, quality, resource, provider)


def log_failed(ep_obj, release, provider=None):
    """
    Log a failed download.

    :param ep_obj: Episode object
    :param release: Release group
    :param provider: Provider used for snatch
    """
    _, quality = Quality.split_composite_status(ep_obj.status)
    action = Quality.composite_status(FAILED, quality)

    _log_history_item(action, ep_obj, quality, release, provider)
