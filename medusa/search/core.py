# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
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
"""Search core module."""
import datetime
import errno
import os
import threading
import traceback

from socket import timeout as socket_timeout

import requests

from .. import (
    app, clients, common, db, failed_history, helpers, history, logger,
    name_cache, notifiers, nzb_splitter, nzbget, sab, show_name_helpers, ui
)
from ..common import MULTI_EP_RESULT, Quality, SEASON_RESULT, SNATCHED, SNATCHED_BEST, SNATCHED_PROPER, UNKNOWN
from ..helper.common import enabled_providers, episode_num
from ..helper.exceptions import AuthException, ex
from ..providers import sorted_provider_list
from ..providers.generic_provider import GenericProvider


def _download_result(result):
    """
    Download a result to the appropriate black hole folder.

    :param result: SearchResult instance to download.
    :return: boolean, True on success
    """
    res_provider = result.provider
    if res_provider is None:
        logger.log(u"Invalid provider name - this is a coding error, report it please", logger.ERROR)
        return False

    # nzbs with an URL can just be downloaded from the provider
    if result.resultType == "nzb":
        new_result = res_provider.download_result(result)
    # if it's an nzb data result
    elif result.resultType == "nzbdata":

        # get the final file path to the nzb
        file_name = os.path.join(app.NZB_DIR, result.name + ".nzb")

        logger.log(u"Saving NZB to " + file_name)

        new_result = True

        # save the data to disk
        try:
            with open(file_name, 'w') as fileOut:
                fileOut.write(result.extraInfo[0])

            helpers.chmod_as_parent(file_name)

        except EnvironmentError as e:
            logger.log(u"Error trying to save NZB to black hole: " + ex(e), logger.ERROR)
            new_result = False
    elif result.resultType == "torrent":
        new_result = res_provider.download_result(result)
    else:
        logger.log(u"Invalid provider type - this is a coding error, report it please", logger.ERROR)
        new_result = False

    return new_result


def snatch_episode(result):
    """
    Internal logic necessary to actually "snatch" a result that has been found.

    :param result: SearchResult instance to be snatched.
    :return: boolean, True on success
    """
    if result is None:
        return False

    result.priority = 0  # -1 = low, 0 = normal, 1 = high
    is_proper = False
    if app.ALLOW_HIGH_PRIORITY:
        # if it aired recently make it high priority
        for cur_ep in result.episodes:
            if datetime.date.today() - cur_ep.airdate <= datetime.timedelta(days=7):
                result.priority = 1
    if result.proper_tags:
        logger.log(u'Found proper tags for {0}. Snatching as PROPER'.format(result.name), logger.DEBUG)
        is_proper = True
        end_status = SNATCHED_PROPER
    else:
        end_status = SNATCHED

    if result.url.startswith('magnet') or result.url.endswith('torrent'):
        result.resultType = 'torrent'

    # NZBs can be sent straight to SAB or saved to disk
    if result.resultType in ("nzb", "nzbdata"):
        if app.NZB_METHOD == "blackhole":
            result_downloaded = _download_result(result)
        elif app.NZB_METHOD == "sabnzbd":
            result_downloaded = sab.sendNZB(result)
        elif app.NZB_METHOD == "nzbget":
            result_downloaded = nzbget.sendNZB(result, is_proper)
        else:
            logger.log(u"Unknown NZB action specified in config: " + app.NZB_METHOD, logger.ERROR)
            result_downloaded = False

    # Torrents can be sent to clients or saved to disk
    elif result.resultType == "torrent":
        # torrents are saved to disk when blackhole mode
        if app.TORRENT_METHOD == "blackhole":
            result_downloaded = _download_result(result)
        else:
            if not result.content and not result.url.startswith('magnet'):
                if result.provider.login():
                    result.content = result.provider.get_url(result.url, returns='content')

            if result.content or result.url.startswith('magnet'):
                client = clients.get_client_class(app.TORRENT_METHOD)()
                result_downloaded = client.send_torrent(result)
            else:
                logger.log(u"Torrent file content is empty", logger.WARNING)
                result_downloaded = False
    else:
        logger.log(u"Unknown result type, unable to download it (%r)" % result.resultType, logger.ERROR)
        result_downloaded = False

    if not result_downloaded:
        return False

    if app.USE_FAILED_DOWNLOADS:
        failed_history.log_snatch(result)

    ui.notifications.message('Episode snatched', result.name)

    history.log_snatch(result)

    # don't notify when we re-download an episode
    sql_l = []
    trakt_data = []
    for curEpObj in result.episodes:
        with curEpObj.lock:
            if is_first_best_match(result):
                curEpObj.status = Quality.composite_status(SNATCHED_BEST, result.quality)
            else:
                curEpObj.status = Quality.composite_status(end_status, result.quality)
            # Reset all others fields to the "snatched" status
            # New snatch by default doesn't have nfo/tbn
            curEpObj.hasnfo = False
            curEpObj.hastbn = False

            # We can't reset location because we need to know what we are replacing
            # curEpObj.location = ''

            # Size and release name are fetched in PP (only for downloaded status, not snatched)
            curEpObj.file_size = 0
            curEpObj.release_name = ''

            # Need to reset subtitle settings because it's a different file
            curEpObj.subtitles = list()
            curEpObj.subtitles_searchcount = 0
            curEpObj.subtitles_lastsearch = '0001-01-01 00:00:00'

            # Need to store the correct is_proper. Not use the old one
            curEpObj.is_proper = True if result.proper_tags else False
            curEpObj.version = 0

            # Release group is parsed in PP
            curEpObj.release_group = ''

            curEpObj.manually_searched = result.manually_searched

            sql_l.append(curEpObj.get_sql())

        if curEpObj.status not in Quality.DOWNLOADED:
            # TODO: Remove this broad catch when all notifiers handle exceptions
            try:
                notify_message = curEpObj.formatted_file_name('%SN - %Sx%0E - %EN - %QN')
                if all([app.SEEDERS_LEECHERS_IN_NOTIFY, result.seeders not in (-1, None),
                        result.leechers not in (-1, None)]):
                    notifiers.notify_snatch("{0} with {1} seeders and {2} leechers from {3}".format
                                            (notify_message, result.seeders,
                                             result.leechers, result.provider.name), is_proper)
                else:
                    notifiers.notify_snatch("{0} from {1}".format(notify_message, result.provider.name), is_proper)
            except Exception as e:
                # Without this, when notification fail, it crashes the snatch thread and Medusa will
                # keep snatching until notification is sent
                logger.log(u"Failed to send snatch notification. Error: {0}".format(e), logger.DEBUG)

            if app.USE_TRAKT and app.TRAKT_SYNC_WATCHLIST:
                trakt_data.append((curEpObj.season, curEpObj.episode))
                logger.log(u'Adding {0} {1} to Trakt watchlist'.format
                           (result.show.name, episode_num(curEpObj.season, curEpObj.episode)), logger.INFO)

    if trakt_data:
        data_episode = notifiers.trakt_notifier.trakt_episode_data_generate(trakt_data)
        if data_episode:
            notifiers.trakt_notifier.update_watchlist(result.show, data_episode=data_episode, update="add")

    if sql_l:
        main_db_con = db.DBConnection()
        main_db_con.mass_action(sql_l)

    return True


def pick_best_result(results, show):  # pylint: disable=too-many-branches
    """
    Find the best result out of a list of search results for a show.

    :param results: list of result objects
    :param show: Shows we check for
    :return: best result object
    """
    results = results if isinstance(results, list) else [results]

    logger.log(u"Picking the best result out of " + str([x.name for x in results]), logger.DEBUG)

    best_result = None

    # find the best result for the current episode
    for cur_result in results:
        if show and cur_result.show is not show:
            continue

        # build the black and white list
        if show.is_anime:
            if not show.release_groups.is_valid(cur_result):
                continue

        logger.log(u"Quality of " + cur_result.name + u" is " + Quality.qualityStrings[cur_result.quality])

        allowed_qualities, preferred_qualities = show.current_qualities

        if cur_result.quality not in allowed_qualities + preferred_qualities:
            logger.log(cur_result.name + u" is a quality we know we don't want, rejecting it", logger.DEBUG)
            continue

        # If doesnt have min seeders OR min leechers then discard it
        if cur_result.seeders not in (-1, None) and cur_result.leechers not in (-1, None) \
            and hasattr(cur_result.provider, 'minseed') and hasattr(cur_result.provider, 'minleech') \
            and (int(cur_result.seeders) < int(cur_result.provider.minseed) or
                 int(cur_result.leechers) < int(cur_result.provider.minleech)):
            logger.log(u"Discarding torrent because it doesn't meet the minimum provider setting "
                       u"S:{0} L:{1}. Result has S:{2} L:{3}".format
                       (cur_result.provider.minseed, cur_result.provider.minleech,
                        cur_result.seeders, cur_result.leechers))
            continue

        ignored_words = show.show_words().ignored_words
        required_words = show.show_words().required_words
        found_ignored_word = show_name_helpers.containsAtLeastOneWord(cur_result.name, ignored_words)
        found_required_word = show_name_helpers.containsAtLeastOneWord(cur_result.name, required_words)

        if ignored_words and found_ignored_word:
            logger.log(u"Ignoring " + cur_result.name + u" based on ignored words filter: " + found_ignored_word,
                       logger.INFO)
            continue

        if required_words and not found_required_word:
            logger.log(u"Ignoring " + cur_result.name + u" based on required words filter: " + required_words,
                       logger.INFO)
            continue

        if not show_name_helpers.filterBadReleases(cur_result.name, parse=False):
            continue

        if hasattr(cur_result, 'size'):
            if app.USE_FAILED_DOWNLOADS and failed_history.has_failed(cur_result.name, cur_result.size,
                                                                      cur_result.provider.name):
                logger.log(cur_result.name + u" has previously failed, rejecting it")
                continue
        preferred_words = ''
        if app.PREFERRED_WORDS:
            preferred_words = app.PREFERRED_WORDS.lower().split(',')
        undesired_words = ''
        if app.UNDESIRED_WORDS:
            undesired_words = app.UNDESIRED_WORDS.lower().split(',')

        if not best_result:
            best_result = cur_result
        if Quality.is_higher_quality(best_result.quality, cur_result.quality, allowed_qualities, preferred_qualities):
            best_result = cur_result
        elif best_result.quality == cur_result.quality:
            if any(ext in cur_result.name.lower() for ext in preferred_words):
                logger.log(u"Preferring " + cur_result.name + u" (preferred words)")
                best_result = cur_result
            if cur_result.proper_tags:
                logger.log(u"Preferring " + cur_result.name + u" (repack/proper/real/rerip over nuked)")
                best_result = cur_result
            elif "internal" in best_result.name.lower() and "internal" not in cur_result.name.lower():
                logger.log(u"Preferring " + cur_result.name + u" (normal instead of internal)")
                best_result = cur_result
            elif "xvid" in best_result.name.lower() and "x264" in cur_result.name.lower():
                logger.log(u"Preferring " + cur_result.name + u" (x264 over xvid)")
                best_result = cur_result
            if any(ext in best_result.name.lower() and ext not in cur_result.name.lower() for ext in undesired_words):
                logger.log(u"Dont want this release " + cur_result.name + u" (contains undesired word(s))")
                best_result = cur_result

    if best_result:
        logger.log(u"Picked " + best_result.name + u" as the best", logger.DEBUG)
    else:
        logger.log(u"No result picked.", logger.DEBUG)

    return best_result


def is_first_best_match(result):
    """
    Check if the given result is a best quality match and if we want to stop searching providers here.

    :param result: to check
    :return: True if the result is the best quality match else False
    """
    logger.log(u"Checking if we should stop searching for a better quality for for episode " + result.name,
               logger.DEBUG)

    show_obj = result.episodes[0].show

    _, preferred_qualities = show_obj.current_qualities
    # Don't pass allowed because we only want to check if this quality is wanted preferred.
    return Quality.wanted_quality(result.quality, [], preferred_qualities)


def wanted_episodes(show, from_date):
    """
    Get a list of episodes that we want to download.

    :param show: Show these episodes are from
    :param from_date: Search from a certain date
    :return: list of wanted episodes
    """
    wanted = []
    allowed_qualities, preferred_qualities = show.current_qualities
    all_qualities = list(set(allowed_qualities + preferred_qualities))

    logger.log(u"Seeing if we need anything from " + show.name, logger.DEBUG)
    con = db.DBConnection()

    sql_results = con.select(
        "SELECT status, season, episode, manually_searched "
        "FROM tv_episodes "
        "WHERE showid = ? AND season > 0 and airdate > ?",
        [show.indexerid, from_date.toordinal()]
    )

    # check through the list of statuses to see if we want any
    for result in sql_results:
        _, cur_quality = common.Quality.split_composite_status(int(result['status'] or UNKNOWN))
        if not Quality.should_search(result['status'], show, result['manually_searched']):
            continue

        ep_obj = show.get_episode(result['season'], result['episode'])
        ep_obj.wanted_quality = [i for i in all_qualities if i > cur_quality and i != common.Quality.UNKNOWN]
        wanted.append(ep_obj)

    return wanted


def search_for_needed_episodes():
    """
    Check providers for details on wanted episodes.

    :return: episodes we have a search hit for
    """
    found_results = {}

    did_search = False

    show_list = app.showList
    from_date = datetime.date.fromordinal(1)
    episodes = []

    for cur_show in show_list:
        if cur_show.paused:
            logger.log(u"Not checking for needed episodes of %s because the show is paused" % cur_show.name,
                       logger.DEBUG)
            continue
        episodes.extend(wanted_episodes(cur_show, from_date))

    if not episodes:
        # nothing wanted so early out, ie: avoid whatever abritrarily
        # complex thing a provider cache update entails, for example,
        # reading rss feeds
        return found_results.values()

    original_thread_name = threading.currentThread().name

    providers = enabled_providers('daily')
    logger.log("Using daily search providers")
    for cur_provider in providers:
        threading.currentThread().name = '{thread} :: [{provider}]'.format(thread=original_thread_name,
                                                                           provider=cur_provider.name)
        cur_provider.cache.update_cache()

    for cur_provider in providers:
        threading.currentThread().name = '{thread} :: [{provider}]'.format(thread=original_thread_name,
                                                                           provider=cur_provider.name)
        try:
            cur_found_results = cur_provider.search_rss(episodes)
        except AuthException as e:
            logger.log(u"Authentication error: " + ex(e), logger.ERROR)
            continue
        except Exception as e:
            logger.log(u"Error while searching " + cur_provider.name + u", skipping: " + ex(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)
            continue

        did_search = True

        # pick a single result for each episode, respecting existing results
        for cur_ep in cur_found_results:
            if not cur_ep.show or cur_ep.show.paused:
                logger.log(u"Skipping %s because the show is paused " % cur_ep.pretty_name(), logger.DEBUG)
                continue

            best_result = pick_best_result(cur_found_results[cur_ep], cur_ep.show)

            # if all results were rejected move on to the next episode
            if not best_result:
                logger.log(u"All found results for " + cur_ep.pretty_name() + u" were rejected.", logger.DEBUG)
                continue

            # if it's already in the list (from another provider) and the newly found quality is no better then skip it
            if cur_ep in found_results and best_result.quality <= found_results[cur_ep].quality:
                continue

            found_results[cur_ep] = best_result

    threading.currentThread().name = original_thread_name

    if not did_search:
        logger.log(
            u"No NZB/Torrent providers found or enabled in the application config for daily searches. "
            u"Please check your settings.", logger.WARNING)

    return found_results.values()


def search_providers(show, episodes, forced_search=False, down_cur_quality=False,
                     manual_search=False, manual_search_type='episode'):
    """
    Walk providers for information on shows.

    :param show: Show we are looking for
    :param episodes: List, episodes we hope to find
    :param forced_search: Boolean, is this a forced search?
    :param down_cur_quality: Boolean, should we re-download currently available quality file
    :param manual_search: Boolean, should we choose what to download?
    :param manual_search_type: Episode or Season search
    :return: results for search
    """
    found_results = {}
    final_results = []
    manual_search_results = []

    did_search = False

    # build name cache for show
    name_cache.build_name_cache(show)

    original_thread_name = threading.currentThread().name

    if manual_search:
        logger.log("Using manual search providers")
        providers = [x for x in sorted_provider_list(app.RANDOMIZE_PROVIDERS)
                     if x.is_active() and x.enable_manualsearch]
    else:
        logger.log("Using backlog search providers")
        providers = [x for x in sorted_provider_list(app.RANDOMIZE_PROVIDERS)
                     if x.is_active() and x.enable_backlog]

    threading.currentThread().name = original_thread_name

    for cur_provider in providers:
        threading.currentThread().name = original_thread_name + " :: [" + cur_provider.name + "]"

        if cur_provider.anime_only and not show.is_anime:
            logger.log(str(show.name) + u" is not an anime, skipping", logger.DEBUG)
            continue

        found_results[cur_provider.name] = {}

        search_count = 0
        search_mode = cur_provider.search_mode

        # Always search for episode when manually searching when in sponly
        if search_mode == 'sponly' and (forced_search or manual_search):
            search_mode = 'eponly'

        if manual_search and manual_search_type == 'season':
            search_mode = 'sponly'

        while True:
            search_count += 1

            if search_mode == 'eponly':
                logger.log(u"Performing episode search for " + show.name)
            else:
                logger.log(u"Performing season pack search for " + show.name)

            try:
                search_results = cur_provider.find_search_results(show, episodes, search_mode, forced_search,
                                                                  down_cur_quality, manual_search, manual_search_type)
            except AuthException as e:
                logger.log(u"Authentication error: " + ex(e), logger.ERROR)
                break
            except socket_timeout as e:
                logger.log(u"Connection timed out (sockets) while searching %s. Error: %r" %
                           (cur_provider.name, ex(e)), logger.DEBUG)
                break
            except (requests.exceptions.HTTPError, requests.exceptions.TooManyRedirects) as e:
                logger.log(u"HTTP error while searching %s. Error: %r" %
                           (cur_provider.name, ex(e)), logger.DEBUG)
                break
            except requests.exceptions.ConnectionError as e:
                logger.log(u"Connection error while searching %s. Error: %r" %
                           (cur_provider.name, ex(e)), logger.DEBUG)
                break
            except requests.exceptions.Timeout as e:
                logger.log(u"Connection timed out while searching %s. Error: %r" %
                           (cur_provider.name, ex(e)), logger.DEBUG)
                break
            except requests.exceptions.ContentDecodingError as e:
                logger.log(u"Content-Encoding was gzip, but content was not compressed while searching %s. "
                           u"Error: %r" % (cur_provider.name, ex(e)), logger.DEBUG)
                break
            except Exception as e:
                if 'ECONNRESET' in e or (hasattr(e, 'errno') and e.errno == errno.ECONNRESET):
                    logger.log(u"Connection reseted by peer while searching %s. Error: %r" %
                               (cur_provider.name, ex(e)), logger.WARNING)
                else:
                    logger.log(u"Unknown exception while searching %s. Error: %r" %
                               (cur_provider.name, ex(e)), logger.ERROR)
                    logger.log(traceback.format_exc(), logger.DEBUG)
                break

            did_search = True

            if search_results:
                # make a list of all the results for this provider
                for cur_ep in search_results:
                    if cur_ep in found_results[cur_provider.name]:
                        found_results[cur_provider.name][cur_ep] += search_results[cur_ep]
                    else:
                        found_results[cur_provider.name][cur_ep] = search_results[cur_ep]

                    # Sort the list by seeders if possible
                    if cur_provider.provider_type == 'torrent' or getattr(cur_provider, 'torznab', None):
                        found_results[cur_provider.name][cur_ep].sort(key=lambda d: int(d.seeders), reverse=True)

                break
            elif not cur_provider.search_fallback or search_count == 2:
                break

            # Dont fallback when doing manual season search
            if manual_search_type == 'season':
                break

            if search_mode == 'sponly':
                logger.log(u"Fallback episode search initiated", logger.DEBUG)
                search_mode = 'eponly'
            else:
                logger.log(u"Fallback season pack search initiate", logger.DEBUG)
                search_mode = 'sponly'

        # skip to next provider if we have no results to process
        if not found_results[cur_provider.name]:
            continue

        # Update the cache if a manual search is being runned
        if manual_search:
            # Let's create a list with episodes that we where looking for
            if manual_search_type == 'season':
                # If season search type, we only want season packs
                searched_episode_list = [SEASON_RESULT]
            else:
                searched_episode_list = [episode_obj.episode for episode_obj in episodes] + [MULTI_EP_RESULT]
            for searched_episode in searched_episode_list:
                if (searched_episode in search_results and
                        cur_provider.cache.update_cache_manual_search(search_results[searched_episode])):
                    # If we have at least a result from one provider, it's good enough to be marked as result
                    manual_search_results.append(True)
            # Continue because we don't want to pick best results as we are running a manual search by user
            continue

        # pick the best season NZB
        best_season_result = None
        if SEASON_RESULT in found_results[cur_provider.name]:
            best_season_result = pick_best_result(found_results[cur_provider.name][SEASON_RESULT], show)

        highest_quality_overall = 0
        for cur_episode in found_results[cur_provider.name]:
            for cur_result in found_results[cur_provider.name][cur_episode]:
                if cur_result.quality != Quality.UNKNOWN and cur_result.quality > highest_quality_overall:
                    highest_quality_overall = cur_result.quality
        logger.log(u"The highest quality of any match is " + Quality.qualityStrings[highest_quality_overall],
                   logger.DEBUG)

        # see if every episode is wanted
        if best_season_result:
            searched_seasons = {str(x.season) for x in episodes}

            # get the quality of the season nzb
            season_quality = best_season_result.quality
            logger.log(
                u"The quality of the season " + best_season_result.provider.provider_type + " is " +
                Quality.qualityStrings[season_quality], logger.DEBUG)

            main_db_con = db.DBConnection()
            all_eps = [int(x["episode"])
                       for x in main_db_con.select("SELECT episode FROM tv_episodes WHERE showid = ? AND "
                       "( season IN ( " + ','.join(searched_seasons) + " ) )", [show.indexerid])]

            logger.log(u"Executed query: [SELECT episode FROM tv_episodes WHERE showid = %s AND season in  %s]" %
                       (show.indexerid, ','.join(searched_seasons)))
            logger.log(u"Episode list: " + str(all_eps), logger.DEBUG)

            all_wanted = True
            any_wanted = False
            for cur_ep_num in all_eps:
                for season in {x.season for x in episodes}:
                    if not show.want_episode(season, cur_ep_num, season_quality, down_cur_quality):
                        all_wanted = False
                    else:
                        any_wanted = True

            # if we need every ep in the season and there's nothing better then
            # just download this and be done with it (unless single episodes are preferred)
            if all_wanted and best_season_result.quality == highest_quality_overall:
                logger.log(
                    u"Every ep in this season is needed, downloading the whole " +
                    best_season_result.provider.provider_type + " " + best_season_result.name)
                ep_objs = []
                for cur_ep_num in all_eps:
                    for season in {x.season for x in episodes}:
                        ep_objs.append(show.get_episode(season, cur_ep_num))
                best_season_result.episodes = ep_objs

                # Remove provider from thread name before return results
                threading.currentThread().name = original_thread_name

                return [best_season_result]

            elif not any_wanted:
                logger.log(
                    u"No eps from this season are wanted at this quality, ignoring the result of " +
                    best_season_result.name, logger.DEBUG)

            else:

                if best_season_result.provider.provider_type == GenericProvider.NZB:
                    logger.log(u"Breaking apart the NZB and adding the individual ones to our results", logger.DEBUG)

                    # if not, break it apart and add them as the lowest priority results
                    individual_results = nzb_splitter.split_result(best_season_result)
                    for cur_result in individual_results:
                        if len(cur_result.episodes) == 1:
                            ep_number = cur_result.episodes[0].episode
                        elif len(cur_result.episodes) > 1:
                            ep_number = MULTI_EP_RESULT

                        if ep_number in found_results[cur_provider.name]:
                            found_results[cur_provider.name][ep_number].append(cur_result)
                        else:
                            found_results[cur_provider.name][ep_number] = [cur_result]

                # If this is a torrent all we can do is leech the entire torrent,
                # user will have to select which eps not do download in his torrent client
                else:

                    # Season result from Torrent Provider must be a full-season torrent,
                    # creating multi-ep result for it.
                    logger.log(
                        u"Adding multi-ep result for full-season torrent. "
                        u"Set the episodes you don't want to 'don't download' in your torrent client if desired!")
                    ep_objs = []
                    for cur_ep_num in all_eps:
                        for season in {x.season for x in episodes}:
                            ep_objs.append(show.get_episode(season, cur_ep_num))
                    best_season_result.episodes = ep_objs

                    if MULTI_EP_RESULT in found_results[cur_provider.name]:
                        found_results[cur_provider.name][MULTI_EP_RESULT].append(best_season_result)
                    else:
                        found_results[cur_provider.name][MULTI_EP_RESULT] = [best_season_result]

        # go through multi-ep results and see if we really want them or not, get rid of the rest
        multi_results = {}
        if MULTI_EP_RESULT in found_results[cur_provider.name]:
            for _multi_result in found_results[cur_provider.name][MULTI_EP_RESULT]:

                logger.log(u"Seeing if we want to bother with multi-episode result " +
                           _multi_result.name, logger.DEBUG)

                # Filter result by ignore/required/whitelist/blacklist/quality, etc
                multi_result = pick_best_result(_multi_result, show)
                if not multi_result:
                    continue

                # see how many of the eps that this result covers aren't covered by single results
                needed_eps = []
                not_needed_eps = []
                for ep_obj in multi_result.episodes:
                    # if we have results for the episode
                    if ep_obj.episode in found_results[cur_provider.name] and \
                            len(found_results[cur_provider.name][ep_obj.episode]) > 0:
                        not_needed_eps.append(ep_obj.episode)
                    else:
                        needed_eps.append(ep_obj.episode)

                logger.log(
                    u"Single-ep check result is needed_eps: " + str(needed_eps) + u", not_needed_eps: " +
                    str(not_needed_eps), logger.DEBUG)

                if not needed_eps:
                    logger.log(u"All of these episodes were covered by single episode results, "
                               u"ignoring this multi-episode result", logger.DEBUG)
                    continue

                # check if these eps are already covered by another multi-result
                multi_needed_eps = []
                multi_not_needed_eps = []
                for ep_obj in multi_result.episodes:
                    if ep_obj.episode in multi_results:
                        multi_not_needed_eps.append(ep_obj.episode)
                    else:
                        multi_needed_eps.append(ep_obj.episode)

                logger.log(u"Multi-ep check result is multi_needed_eps: " + str(multi_needed_eps) +
                           u", multi_not_needed_eps: " + str(multi_not_needed_eps), logger.DEBUG)

                if not multi_needed_eps:
                    logger.log(
                        u"All of these episodes were covered by another multi-episode nzbs, "
                        u"ignoring this multi-ep result", logger.DEBUG)
                    continue

                # don't bother with the single result if we're going to get it with a multi result
                for ep_obj in multi_result.episodes:
                    multi_results[ep_obj.episode] = multi_result
                    if ep_obj.episode in found_results[cur_provider.name]:
                        logger.log(
                            u"A needed multi-episode result overlaps with a single-episode result for ep #" +
                            str(ep_obj.episode) + u", removing the single-episode results from the list", logger.DEBUG)
                        del found_results[cur_provider.name][ep_obj.episode]

        # of all the single ep results narrow it down to the best one for each episode
        final_results += set(multi_results.values())
        for cur_ep in found_results[cur_provider.name]:
            if cur_ep in (MULTI_EP_RESULT, SEASON_RESULT):
                continue

            if not found_results[cur_provider.name][cur_ep]:
                continue

            # if all results were rejected move on to the next episode
            best_result = pick_best_result(found_results[cur_provider.name][cur_ep], show)
            if not best_result:
                continue

            # add result if its not a duplicate and
            found = False
            for i, result in enumerate(final_results):
                for best_resultEp in best_result.episodes:
                    if best_resultEp in result.episodes:
                        if result.quality < best_result.quality:
                            final_results.pop(i)
                        else:
                            found = True
            if not found:
                final_results += [best_result]

    if not did_search:
        logger.log(u"No NZB/Torrent providers found or enabled in the application config for backlog searches. "
                   u"Please check your settings.", logger.WARNING)

    # Remove provider from thread name before return results
    threading.currentThread().name = original_thread_name

    if manual_search:
        # If results in manual search return True, else False
        return any(manual_search_results)
    else:
        return final_results
