# coding=utf-8
# Author: p0psicles
#
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


import json
import threading
import time

from datetime import datetime
from dateutil import parser
from .queue import FORCED_SEARCH_HISTORY, ForcedSearchQueueItem
from .. import app, db, logger
from ..common import Overview, Quality, cpu_presets, statusStrings
from ..helper.common import enabled_providers, pretty_file_size
from ..sbdatetime import sbdatetime
from ..show.show import Show
from ..show_name_helpers import containsAtLeastOneWord, filterBadReleases

SEARCH_STATUS_FINISHED = "finished"
SEARCH_STATUS_QUEUED = "queued"
SEARCH_STATUS_SEARCHING = "searching"


def get_quality_class(ep_obj):
    """
    Find the quality class for the episode
    """

    _, ep_quality = Quality.split_composite_status(ep_obj.status)
    if ep_quality in Quality.cssClassStrings:
        quality_class = Quality.cssClassStrings[ep_quality]
    else:
        quality_class = Quality.cssClassStrings[Quality.UNKNOWN]

    return quality_class


def get_episode(show, season=None, episode=None, absolute=None):
    """ Get a specific episode object based on show, season and episode number

    :param show: Season number
    :param season: Season number
    :param episode: Episode number
    :param absolute: Optional if the episode number is a scene absolute number
    :return: episode object
    """
    if show is None:
        return "Invalid show parameters"

    show_obj = Show.find(app.showList, int(show))

    if show_obj is None:
        return "Invalid show paramaters"

    if absolute:
        ep_obj = show_obj.get_episode(absolute_number=absolute)
    elif season and episode:
        ep_obj = show_obj.get_episode(season, episode)
    else:
        return "Invalid paramaters"

    if ep_obj is None:
        return "Episode couldn't be retrieved"

    return ep_obj


def get_episodes(search_thread, searchstatus):
    """ Get all episodes located in a search thread with a specific status """

    results = []
    # NOTE!: Show.find called with just indexerid!
    show_obj = Show.find(app.showList, int(search_thread.show.indexerid))

    if not show_obj:
        if not search_thread.show.is_recently_deleted:
            logger.log(u'No Show Object found for show with indexerID: {0}'.
                       format(search_thread.show.indexerid), logger.ERROR)
        return results

    if not isinstance(search_thread.segment, list):
        search_thread.segment = [search_thread.segment]

    for ep_obj in search_thread.segment:
        ep = show_obj.get_episode(ep_obj.season, ep_obj.episode)
        results.append({
            'show': show_obj.indexerid,
            'episode': ep.episode,
            'episodeindexid': ep.indexerid,
            'season': ep.season,
            'searchstatus': searchstatus,
            'status': statusStrings[ep.status],
            'quality': get_quality_class(ep),
            'overview': Overview.overviewStrings[show_obj.get_overview(ep.status,
                                                                       manually_searched=ep.manually_searched)],
        })

    return results


def update_finished_search_queue_item(snatch_queue_item):
    """
    Updates the previous manual searched queue item with the correct status
    @param snatch_queue_item: A successful snatch queue item, send from pickManualSearch().
    @return: True if status update was successful, False if not.
    """
    # Finished Searches

    for search_thread in FORCED_SEARCH_HISTORY:
        if snatch_queue_item.show and not search_thread.show.indexerid == snatch_queue_item.show.indexerid:
            continue

        if isinstance(search_thread, ForcedSearchQueueItem):
            if not isinstance(search_thread.segment, list):
                search_thread.segment = [search_thread.segment]

            for ep_obj in snatch_queue_item.segment:
                if all([[search for search in search_thread.segment if search.indexerid == ep_obj.indexerid],
                        [search for search in search_thread.segment if search.season == ep_obj.season],
                        [search for search in search_thread.segment if search.episode == ep_obj.episode]]):
                    search_thread.segment = snatch_queue_item.segment
                    return True
    return False


def collect_episodes_from_search_thread(show):
    """
    Collects all episodes from from the forcedSearchQueueScheduler
    and looks for episodes that are in status queued or searching.
    If episodes are found in FORCED_SEARCH_HISTORY, these are set to status finished.
    """
    episodes = []

    # Queued Searches
    searchstatus = SEARCH_STATUS_QUEUED
    for search_thread in app.forcedSearchQueueScheduler.action.get_all_ep_from_queue(show):
        episodes += get_episodes(search_thread, searchstatus)

    # Running Searches
    searchstatus = SEARCH_STATUS_SEARCHING
    if app.forcedSearchQueueScheduler.action.is_forced_search_in_progress():
        search_thread = app.forcedSearchQueueScheduler.action.currentItem

        if search_thread.success:
            searchstatus = SEARCH_STATUS_FINISHED

        episodes += get_episodes(search_thread, searchstatus)

    # Finished Searches
    searchstatus = SEARCH_STATUS_FINISHED
    for search_thread in FORCED_SEARCH_HISTORY:
        if show and not search_thread.show.indexerid == int(show):
            continue

        if isinstance(search_thread, ForcedSearchQueueItem):
            if not [x for x in episodes if x['episodeindexid'] in [search.indexerid for search in search_thread.segment]]:
                episodes += get_episodes(search_thread, searchstatus)
        else:
            # These are only Failed Downloads/Retry search thread items.. lets loop through the segment/episodes
            if not [i for i, j in zip(search_thread.segment, episodes) if i.indexerid == j['episodeindexid']]:
                episodes += get_episodes(search_thread, searchstatus)

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
    show_obj = Show.find(app.showList, int(show))
    preferred_words = show_obj.show_words().preferred_words.lower().split(',')
    undesired_words = show_obj.show_words().undesired_words.lower().split(',')
    ignored_words = show_obj.show_words().ignored_words.lower().split(',')
    required_words = show_obj.show_words().required_words.lower().split(',')

    main_db_con = db.DBConnection('cache.db')

    provider_results = {'last_prov_updates': {}, 'error': {}, 'found_items': []}
    original_thread_name = threading.currentThread().name

    sql_total = []
    combined_sql_q = []
    combined_sql_params = []

    for cur_provider in enabled_providers('manualsearch'):
        threading.currentThread().name = '{thread} :: [{provider}]'.format(thread=original_thread_name, provider=cur_provider.name)

        # Let's check if this provider table already exists
        table_exists = main_db_con.select(b"SELECT name FROM sqlite_master WHERE type='table' AND name=?", [cur_provider.get_id()])
        columns = [i[1] for i in main_db_con.select("PRAGMA table_info('{0}')".format(cur_provider.get_id()))] if table_exists else []
        minseed = int(cur_provider.minseed) if hasattr(cur_provider, 'minseed') else -1
        minleech = int(cur_provider.minleech) if hasattr(cur_provider, 'minleech') else -1

        # TODO: the implicit sqlite rowid is used, should be replaced with an explicit PK column
        # If table doesn't exist, start a search to create table and new columns seeders, leechers and size
        required_columns = ['seeders', 'leechers', 'size', 'proper_tags']
        if table_exists and all(required_column in columns for required_column in required_columns):
            # The default sql, that's executed for each providers cache table
            common_sql = b"SELECT rowid, ? AS 'provider_type', ? AS 'provider_image', \
                          ? AS 'provider', ? AS 'provider_id', ? 'provider_minseed', ? 'provider_minleech', \
                          name, season, episodes, indexerid, url, time, proper_tags, \
                          quality, release_group, version, seeders, leechers, size, time, pubdate \
                          FROM '{provider_id}' WHERE indexerid = ? AND quality > 0 ".format(provider_id=cur_provider.get_id())
            additional_sql = " AND episodes LIKE ? AND season = ? "

            # The params are always the same for both queries
            add_params = [cur_provider.provider_type.title(), cur_provider.image_name(),
                          cur_provider.name, cur_provider.get_id(), minseed, minleech, show]

            # If were not looking for all results, meaning don't do the filter on season + ep, add sql
            if not int(show_all_results):
                common_sql += additional_sql
                add_params += ["%|{0}|%".format(sql_episode), season]

            # Add the created sql, to lists, that are used down below to perform one big UNIONED query
            combined_sql_q.append(common_sql)
            combined_sql_params += add_params

            # Get the last updated cache items timestamp
            last_update = main_db_con.select(b"select max(time) AS lastupdate from '{provider_id}'".format(provider_id=cur_provider.get_id()))
            provider_results['last_prov_updates'][cur_provider.get_id()] = last_update[0]['lastupdate'] if last_update[0]['lastupdate'] else 0

    # Check if we have the combined sql strings
    if combined_sql_q:
        sql_prepend = b"SELECT * FROM ("
        sql_append = b") ORDER BY CASE quality WHEN '{quality_unknown}' THEN -1 ELSE CAST(quality AS DECIMAL) END DESC, " \
                     b" proper_tags DESC, seeders DESC".format(quality_unknown=Quality.UNKNOWN)

        # Add all results
        sql_total += main_db_con.select(b'{0} {1} {2}'.
                                        format(sql_prepend, ' UNION ALL '.join(combined_sql_q), sql_append),
                                        combined_sql_params)

    # Always start a search when no items found in cache
    if not sql_total or int(perform_search):
        # retrieve the episode object and fail if we can't get one
        ep_obj = get_episode(show, season, episode)
        if isinstance(ep_obj, str):
            # ui.notifications.error(u"Something went wrong when starting the manual search for show {0}, and episode: {1}x{2}".
            # format(show_obj.name, season, episode))
            provider_results['error'] = 'Something went wrong when starting the manual search for show {0}, \
            and episode: {1}x{2}'.format(show_obj.name, season, episode)

        # make a queue item for it and put it on the queue
        ep_queue_item = ForcedSearchQueueItem(ep_obj.show, [ep_obj], bool(int(down_cur_quality)), True, manual_search_type)  # pylint: disable=maybe-no-member

        app.forcedSearchQueueScheduler.action.add_item(ep_queue_item)

        # give the CPU a break and some time to start the queue
        time.sleep(cpu_presets[app.CPU_PRESET])
    else:
        cached_results = [dict(row) for row in sql_total]
        for i in cached_results:
            i['quality_name'] = Quality.split_quality(int(i['quality']))
            i['time'] = datetime.fromtimestamp(i['time']).strftime(app.DATE_PRESET + ' ' + app.TIME_PRESET)
            i['release_group'] = i['release_group'] or 'None'
            i['provider_img_link'] = 'images/providers/' + i['provider_image'] or 'missing.png'
            i['provider'] = i['provider'] if i['provider_image'] else 'missing provider'
            i['proper_tags'] = i['proper_tags'].replace('|', ', ')
            i['pretty_size'] = pretty_file_size(i['size']) if i['size'] > -1 else 'N/A'
            i['seeders'] = i['seeders'] if i['seeders'] >= 0 else '-'
            i['leechers'] = i['leechers'] if i['leechers'] >= 0 else '-'
            i['pubdate'] = sbdatetime.convert_to_setting(parser.parse(i['pubdate'])).strftime(
                app.DATE_PRESET + ' ' + app.TIME_PRESET) if i['pubdate'] else '-'
            release_group = i['release_group']
            if ignored_words and release_group in ignored_words:
                i['rg_highlight'] = 'ignored'
            elif required_words and release_group in required_words:
                i['rg_highlight'] = 'required'
            elif preferred_words and release_group in preferred_words:
                i['rg_highlight'] = 'preferred'
            elif undesired_words and release_group in undesired_words:
                i['rg_highlight'] = 'undesired'
            else:
                i['rg_highlight'] = ''
            if containsAtLeastOneWord(i['name'], required_words):
                i['name_highlight'] = 'required'
            elif containsAtLeastOneWord(i['name'], ignored_words) or not filterBadReleases(i['name'], parse=False):
                i['name_highlight'] = 'ignored'
            elif containsAtLeastOneWord(i['name'], undesired_words):
                i['name_highlight'] = 'undesired'
            elif containsAtLeastOneWord(i['name'], preferred_words):
                i['name_highlight'] = 'preferred'
            else:
                i['name_highlight'] = ''
            i['seed_highlight'] = 'ignored' if i.get('provider_minseed') > i.get('seeders', -1) >= 0 else ''
            i['leech_highlight'] = 'ignored' if i.get('provider_minleech') > i.get('leechers', -1) >= 0 else ''
        provider_results['found_items'] = cached_results

    # Remove provider from thread name before return results
    threading.currentThread().name = original_thread_name

    # Sanitize the last_prov_updates key
    provider_results['last_prov_updates'] = json.dumps(provider_results['last_prov_updates'])
    return provider_results
