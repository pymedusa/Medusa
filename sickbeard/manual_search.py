# coding=utf-8
# Author: p0psicles
#
# Git: https://github.com/PyMedusa/SickRage.git
#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage. If not, see <http://www.gnu.org/licenses/>.


import time
import sickbeard
import threading
from sickbeard import search_queue
from sickbeard.common import Quality, Overview, statusStrings, cpu_presets
from sickbeard import logger, db
from sickrage.helper.common import try_int, enabled_providers
from sickrage.show.Show import Show

SEARCH_STATUS_FINISHED = "finished"
SEARCH_STATUS_QUEUED = "queued"
SEARCH_STATUS_SEARCHING = "searching"


def getQualityClass(ep_obj):
    """
    Find the quality class for the episode
    """

    _, ep_quality = Quality.splitCompositeStatus(ep_obj.status)
    if ep_quality in Quality.cssClassStrings:
        quality_class = Quality.cssClassStrings[ep_quality]
    else:
        quality_class = Quality.cssClassStrings[Quality.UNKNOWN]

    return quality_class


def getEpisode(show, season=None, episode=None, absolute=None):
    """ Get a specific episode object based on show, season and episode number

    :param show: Season number
    :param season: Season number
    :param season: Season number
    :param absolute: Optional if the episode number is a scene absolute number
    :return: episode object
    """
    if show is None:
        return "Invalid show parameters"

    show_obj = Show.find(sickbeard.showList, int(show))

    if show_obj is None:
        return "Invalid show paramaters"

    if absolute:
        ep_obj = show_obj.getEpisode(absolute_number=absolute)
    elif season and episode:
        ep_obj = show_obj.getEpisode(season, episode)
    else:
        return "Invalid paramaters"

    if ep_obj is None:
        return "Episode couldn't be retrieved"

    return ep_obj


def getEpisodes(search_thread, searchstatus):
    """ Get all episodes located in a search thread with a specific status """

    results = []
    # NOTE!: Show.find called with just indexerid!
    show_obj = Show.find(sickbeard.showList, int(search_thread.show.indexerid))

    if not show_obj:
        logger.log(u'No Show Object found for show with indexerID: {}'.format(search_thread.show.indexerid), logger.ERROR)
        return results

    if not isinstance(search_thread.segment, list):
            search_thread.segment = [search_thread.segment]

    for ep_obj in search_thread.segment:
        ep = show_obj.getEpisode(ep_obj.season, ep_obj.episode)
        results.append({
            'show': show_obj.indexerid,
            'episode': ep.episode,
            'episodeindexid': ep.indexerid,
            'season': ep.season,
            'searchstatus': searchstatus,
            'status': statusStrings[ep.status],
            'quality': getQualityClass(ep),
            'overview': Overview.overviewStrings[show_obj.getOverview(ep.status)],
        })

    return results


def update_finished_search_queue_item(snatch_queue_item):
    """
    Updates the previous manual searched queue item with the correct status
    @param snatch_queue_item: A successful snatch queue item, send from pickManualSearch().
    @return: True if status update was successful, False if not.
    """
    # Finished Searches

    for search_thread in sickbeard.search_queue.FORCED_SEARCH_HISTORY:
        if snatch_queue_item.show and not search_thread.show.indexerid == snatch_queue_item.show.indexerid:
            continue

        if isinstance(search_thread, sickbeard.search_queue.ForcedSearchQueueItem):
            if not isinstance(search_thread.segment, list):
                search_thread.segment = [search_thread.segment]

            for ep_obj in snatch_queue_item.segment:
                if all([[search for search in search_thread.segment if search.indexerid == ep_obj.indexerid],
                        [search for search in search_thread.segment if search.season == ep_obj.season],
                        [search for search in search_thread.segment if search.episode == ep_obj.episode]]):
                    search_thread.segment = snatch_queue_item.segment
                    return True
    return False


def collectEpisodesFromSearchThread(show):
    """
    Collects all episodes from from the forcedSearchQueueScheduler
    and looks for episodes that are in status queued or searching.
    If episodes are found in FORCED_SEARCH_HISTORY, these are set to status finished.
    """
    episodes = []

    # Queued Searches
    searchstatus = SEARCH_STATUS_QUEUED
    for search_thread in sickbeard.forcedSearchQueueScheduler.action.get_all_ep_from_queue(show):
        episodes += getEpisodes(search_thread, searchstatus)

    # Running Searches
    searchstatus = SEARCH_STATUS_SEARCHING
    if sickbeard.forcedSearchQueueScheduler.action.is_forced_search_in_progress():
        search_thread = sickbeard.forcedSearchQueueScheduler.action.currentItem

        if search_thread.success:
            searchstatus = SEARCH_STATUS_FINISHED

        episodes += getEpisodes(search_thread, searchstatus)

    # Finished Searches
    searchstatus = SEARCH_STATUS_FINISHED
    for search_thread in sickbeard.search_queue.FORCED_SEARCH_HISTORY:
        if show and not search_thread.show.indexerid == int(show):
            continue

        if isinstance(search_thread, sickbeard.search_queue.ForcedSearchQueueItem):
            if not [x for x in episodes if x['episodeindexid'] in [search.indexerid for search in search_thread.segment]]:
                episodes += getEpisodes(search_thread, searchstatus)
        else:
            # These are only Failed Downloads/Retry search thread items.. lets loop through the segment/episodes
            if not [i for i, j in zip(search_thread.segment, episodes) if i.indexerid == j['episodeindexid']]:
                episodes += getEpisodes(search_thread, searchstatus)

    return episodes


def get_provider_cache_results(indexer, show_all_results=None, perform_search=None, **search_show):  # pylint: disable=too-many-locals,unused-argument
    """
    Check all provider cache tables for search results
    """

    show = search_show.get('show')
    season = search_show.get('season')
    episode = search_show.get('episode')
    manual_search_type = search_show.get('manual_search_type')
    sql_episode = '' if manual_search_type == 'season' else episode

    down_cur_quality = 0
    show_obj = Show.find(sickbeard.showList, int(show))

    main_db_con = db.DBConnection('cache.db')
    found_items = []
    provider_results = {'last_prov_updates': {}, 'error': {}, 'found_items': []}
    original_thread_name = threading.currentThread().name

    for cur_provider in enabled_providers('manualsearch'):
        threading.currentThread().name = '{thread} :: [{provider}]'.format(thread=original_thread_name, provider=cur_provider.name)
        sql_return = []
        # Let's check if this provider table already exists
        table_exists = main_db_con.select("SELECT name FROM sqlite_master WHERE type='table' AND name=?", [cur_provider.get_id()])
        columns = [i[1] for i in main_db_con.select("PRAGMA table_info('{0}')".format(cur_provider.get_id()))] if table_exists else []
        minseed = int(cur_provider.minseed) if hasattr(cur_provider, 'minseed') else -1
        minleech = int(cur_provider.minleech) if hasattr(cur_provider, 'minleech') else -1

        # TODO: the implicit sqlite rowid is used, should be replaced with an explicit PK column
        # If table doesn't exist, start a search to create table and new columns seeders, leechers and size
        if table_exists and 'seeders' in columns and 'leechers' in columns and 'size' in columns:

            common_sql = "SELECT rowid, ? as 'provider_type', ? as 'provider_image', \
                          ? as 'provider', ? as 'provider_id', ? 'provider_minseed', ? 'provider_minleech', \
                          name, season, episodes, indexerid, url, time, (select max(time) \
                          from '{provider_id}') as lastupdate, \
                          quality, release_group, version, seeders, leechers, size, time \
                          FROM '{provider_id}' WHERE indexerid = ?".format(provider_id=cur_provider.get_id())
            additional_sql = " AND episodes LIKE ? AND season = ?"

            if not int(show_all_results):
                sql_return = main_db_con.select(common_sql + additional_sql,
                                                (cur_provider.provider_type.title(), cur_provider.image_name(),
                                                 cur_provider.name, cur_provider.get_id(),
                                                 minseed, minleech, show, "%|{0}|%".format(sql_episode), season))
            else:
                sql_return = main_db_con.select(common_sql,
                                                (cur_provider.provider_type.title(), cur_provider.image_name(),
                                                 cur_provider.name, cur_provider.get_id(), minseed, minleech, show))

        if sql_return:
            for item in sql_return:
                found_items.append(dict(item))

            # Store the last table update, we'll need this to compare later
            provider_results['last_prov_updates'][cur_provider.get_id()] = str(sql_return[0]['lastupdate'])
        else:
            provider_results['last_prov_updates'][cur_provider.get_id()] = "0"

    # Always start a search when no items found in cache
    if not found_items or int(perform_search):
        # retrieve the episode object and fail if we can't get one
        ep_obj = getEpisode(show, season, episode)
        if isinstance(ep_obj, str):
            # ui.notifications.error(u"Something went wrong when starting the manual search for show {0}, and episode: {1}x{2}".
            # format(show_obj.name, season, episode))
            provider_results['error'] = 'Something went wrong when starting the manual search for show {0}, \
            and episode: {1}x{2}'.format(show_obj.name, season, episode)

        # make a queue item for it and put it on the queue
        ep_queue_item = search_queue.ForcedSearchQueueItem(ep_obj.show, [ep_obj], bool(int(down_cur_quality)), True, manual_search_type)  # pylint: disable=maybe-no-member

        sickbeard.forcedSearchQueueScheduler.action.add_item(ep_queue_item)

        # give the CPU a break and some time to start the queue
        time.sleep(cpu_presets[sickbeard.CPU_PRESET])
    else:
        # Sort the list of found items
        found_items = sorted(found_items, key=lambda k: (try_int(k['quality']), try_int(k['seeders'])), reverse=True)
        # Make unknown qualities at the botton
        found_items = [d for d in found_items if try_int(d['quality']) < 32768] + [d for d in found_items if try_int(d['quality']) == 32768]
        provider_results['found_items'] = found_items

    # Remove provider from thread name before return results
    threading.currentThread().name = original_thread_name

    return provider_results
