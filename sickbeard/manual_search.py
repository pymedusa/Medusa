# coding=utf-8
# Author: p0psicles

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
#


import time

import sickbeard
from sickbeard import search_queue
from sickbeard.common import Quality, Overview, statusStrings, cpu_presets
from sickbeard import logger, db
from sickrage.helper.common import try_int

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

    showObj = Show.find(sickbeard.showList, int(show))

    if showObj is None:
        return "Invalid show paramaters"

    if absolute:
        epObj = showObj.getEpisode(absolute_number=absolute)
    elif season and episode:
        epObj = showObj.getEpisode(season, episode)
    else:
        return "Invalid paramaters"

    if epObj is None:
        return "Episode couldn't be retrieved"

    return epObj


def getEpisodes(searchThread, searchstatus):
    """ Get all episodes located in a searchThread with a specific status """

    results = []
    showObj = Show.find(sickbeard.showList, int(searchThread.show.indexerid))

    if not showObj:
        logger.log(u'No Show Object found for show with indexerID: ' + str(searchThread.show.indexerid), logger.ERROR)
        return results

    if isinstance(searchThread, (sickbeard.search_queue.ManualSearchQueueItem, sickbeard.search_queue.ManualSelectQueueItem)):
        results.append({
            'show': searchThread.show.indexerid,
            'episode': searchThread.segment.episode,
            'episodeindexid': searchThread.segment.indexerid,
            'season': searchThread.segment.season,
            'searchstatus': searchstatus,
            'status': statusStrings[searchThread.segment.status],
            'quality': getQualityClass(searchThread.segment),
            'overview': Overview.overviewStrings[showObj.getOverview(searchThread.segment.status)]
        })
    else:
        for epObj in searchThread.segment:
            results.append({'show': epObj.show.indexerid,
                            'episode': epObj.episode,
                            'episodeindexid': epObj.indexerid,
                            'season': epObj.season,
                            'searchstatus': searchstatus,
                            'status': statusStrings[epObj.status],
                            'quality': getQualityClass(epObj),
                            'overview': Overview.overviewStrings[showObj.getOverview(epObj.status)]
                            })

    return results


def collectEpisodesFromSearchThread(show):
    """
    Collects all episodes from from the searchQueueScheduler and looks for episodes that are in status queued or searching.
    If episodes are found in MANUAL_SEARCH_HISTORY, these are set to status finished.
    """
    episodes = []

    # Queued Searches
    searchstatus = SEARCH_STATUS_QUEUED
    for searchThread in sickbeard.searchQueueScheduler.action.get_all_ep_from_queue(show):
        episodes += getEpisodes(searchThread, searchstatus)

    # Running Searches
    searchstatus = SEARCH_STATUS_SEARCHING
    if sickbeard.searchQueueScheduler.action.is_manualsearch_in_progress():
        searchThread = sickbeard.searchQueueScheduler.action.currentItem

        if searchThread.success:
            searchstatus = SEARCH_STATUS_FINISHED

        episodes += getEpisodes(searchThread, searchstatus)

    # Finished Searches
    searchstatus = SEARCH_STATUS_FINISHED
    for searchThread in sickbeard.search_queue.MANUAL_SEARCH_HISTORY:
        if show is not None:
            if not str(searchThread.show.indexerid) == show:
                continue

        if isinstance(searchThread, (sickbeard.search_queue.ManualSearchQueueItem, sickbeard.search_queue.ManualSelectQueueItem)):
            if not [x for x in episodes if x['episodeindexid'] == searchThread.segment.indexerid]:
                episodes += getEpisodes(searchThread, searchstatus)
        else:
            # ## These are only Failed Downloads/Retry SearchThreadItems.. lets loop through the segment/episodes
            if not [i for i, j in zip(searchThread.segment, episodes) if i.indexerid == j['episodeindexid']]:
                episodes += getEpisodes(searchThread, searchstatus)

    return episodes


def get_provider_cache_results(indexer, show_all_results=None, perform_search=None, **search_show):
    """
    Check all provider cache tables for search results
    """

    show = search_show.get('show')
    season = search_show.get('season')
    episode = search_show.get('episode')

    down_cur_quality = 0
    showObj = Show.find(sickbeard.showList, int(show))

    main_db_con = db.DBConnection('cache.db')
    sql_return = {}
    provider_results = {'last_prov_updates': {}, 'error': {}, 'found_items': []}
    found_items = []
    last_prov_updates = {}

    providers = [x for x in sickbeard.providers.sortedProviderList(sickbeard.RANDOMIZE_PROVIDERS) if x.is_active() and x.enable_daily]
    for curProvider in providers:

        # Let's check if this provider table already exists
        table_exists = main_db_con.select("SELECT name FROM sqlite_master WHERE type='table' AND name=?", [curProvider.get_id()])
        if not table_exists:
            continue

        # TODO: the implicit sqlite rowid is used, should be replaced with an explicit PK column
        if not int(show_all_results):
            sql_return = main_db_con.select("SELECT rowid, ? as 'provider', ? as 'provider_id', name, season, \
                                            episodes, indexerid, url, time, (select max(time) from '%s') as lastupdate, \
                                            quality, release_group, version, seeders, leechers, size, time \
                                            FROM '%s' WHERE episodes LIKE ? AND season = ? AND indexerid = ?"
                                            % (curProvider.get_id(), curProvider.get_id()),
                                            [curProvider.name, curProvider.get_id(),
                                             "%|" + episode + "|%", season, show])

        else:
            sql_return = main_db_con.select("SELECT rowid, ? as 'provider', ? as 'provider_id', name, season, \
                                            episodes, indexerid, url, time, (select max(time) from '%s') as lastupdate, \
                                            quality, release_group, version, seeders, leechers, size, time \
                                            FROM '%s' WHERE indexerid = ?" % (curProvider.name, curProvider.get_id()),
                                            [curProvider.get_id(), show])

        if sql_return:
            for item in sql_return:
                found_items.append(dict(item))

            # Store the last table update, we'll need this to compare later
            provider_results['last_prov_updates'][curProvider.get_id()] = str(sql_return[0]['lastupdate'])
        else:
            provider_results['last_prov_updates'][curProvider.get_id()] = "0"

    # Always start a search when no items found in cache
    if not found_items or int(perform_search):
        # retrieve the episode object and fail if we can't get one
        ep_obj = getEpisode(show, season, episode)
        if isinstance(ep_obj, str):
            #ui.notifications.error(u"Something went wrong when starting the manual search for show {0}, and episode: {1}x{2}".
            #                       format(showObj.name, season, episode))
            provider_results['error'] = 'Something went wrong when starting the manual search for show {0}, and episode: {1}x{2}'.format(showObj.name, season, episode)

        # make a queue item for it and put it on the queue
        ep_queue_item = search_queue.ManualSearchQueueItem(ep_obj.show, ep_obj, bool(int(down_cur_quality)), True)

        sickbeard.searchQueueScheduler.action.add_item(ep_queue_item)

        # give the CPU a break and some time to start the queue
        time.sleep(cpu_presets[sickbeard.CPU_PRESET])
    else:
        # Sort the list of found items
        found_items = sorted(found_items, key=lambda k: (try_int(k['quality']), try_int(k['seeders'])), reverse=True)
        # Make unknown qualities at the botton
        found_items = [d for d in found_items if int(d['quality']) < 32768] + [d for d in found_items if int(d['quality']) == 32768]
        provider_results['found_items'] = found_items

    return provider_results
