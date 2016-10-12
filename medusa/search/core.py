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

import datetime
import errno
import os
import threading
import traceback
from socket import timeout as SocketTimeout

import medusa as app
import requests
from .. import clients, common, db, failed_history, helpers, history, logger, notifiers, nzbSplitter, nzbget, sab, show_name_helpers, ui
from ..common import MULTI_EP_RESULT, Quality, SEASON_RESULT, SNATCHED, SNATCHED_BEST, SNATCHED_PROPER
from ..helper.common import enabled_providers, episode_num
from ..helper.exceptions import AuthException, ex
from ..providers.GenericProvider import GenericProvider


def _downloadResult(result):
    """
    Download a result to the appropriate black hole folder.

    :param result: SearchResult instance to download.
    :return: boolean, True on success
    """
    resProvider = result.provider
    if resProvider is None:
        logger.log(u"Invalid provider name - this is a coding error, report it please", logger.ERROR)
        return False

    # nzbs with an URL can just be downloaded from the provider
    if result.resultType == "nzb":
        newResult = resProvider.download_result(result)
    # if it's an nzb data result
    elif result.resultType == "nzbdata":

        # get the final file path to the nzb
        fileName = os.path.join(app.NZB_DIR, result.name + ".nzb")

        logger.log(u"Saving NZB to " + fileName)

        newResult = True

        # save the data to disk
        try:
            with open(fileName, 'w') as fileOut:
                fileOut.write(result.extraInfo[0])

            helpers.chmodAsParent(fileName)

        except EnvironmentError as e:
            logger.log(u"Error trying to save NZB to black hole: " + ex(e), logger.ERROR)
            newResult = False
    elif result.resultType == "torrent":
        newResult = resProvider.download_result(result)
    else:
        logger.log(u"Invalid provider type - this is a coding error, report it please", logger.ERROR)
        newResult = False

    return newResult


def snatchEpisode(result):  # pylint: disable=too-many-branches, too-many-statements
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
        for curEp in result.episodes:
            if datetime.date.today() - curEp.airdate <= datetime.timedelta(days=7):
                result.priority = 1
    if result.proper_tags:
        logger.log(u'Found proper tags for {0}. Snatching as PROPER'.format(result.name), logger.DEBUG)
        is_proper = True
        endStatus = SNATCHED_PROPER
    else:
        endStatus = SNATCHED

    if result.url.startswith('magnet') or result.url.endswith('torrent'):
        result.resultType = 'torrent'

    # NZBs can be sent straight to SAB or saved to disk
    if result.resultType in ("nzb", "nzbdata"):
        if app.NZB_METHOD == "blackhole":
            dlResult = _downloadResult(result)
        elif app.NZB_METHOD == "sabnzbd":
            dlResult = sab.sendNZB(result)
        elif app.NZB_METHOD == "nzbget":
            dlResult = nzbget.sendNZB(result, is_proper)
        else:
            logger.log(u"Unknown NZB action specified in config: " + app.NZB_METHOD, logger.ERROR)
            dlResult = False

    # Torrents can be sent to clients or saved to disk
    elif result.resultType == "torrent":
        # torrents are saved to disk when blackhole mode
        if app.TORRENT_METHOD == "blackhole":
            dlResult = _downloadResult(result)
        else:
            if not result.content and not result.url.startswith('magnet'):
                if result.provider.login():
                    result.content = result.provider.get_url(result.url, returns='content')

            if result.content or result.url.startswith('magnet'):
                client = clients.get_client_class(app.TORRENT_METHOD)()
                dlResult = client.send_torrent(result)
            else:
                logger.log(u"Torrent file content is empty", logger.WARNING)
                dlResult = False
    else:
        logger.log(u"Unknown result type, unable to download it (%r)" % result.resultType, logger.ERROR)
        dlResult = False

    if not dlResult:
        return False

    if app.USE_FAILED_DOWNLOADS:
        failed_history.logSnatch(result)

    ui.notifications.message('Episode snatched', result.name)

    history.logSnatch(result)

    # don't notify when we re-download an episode
    sql_l = []
    trakt_data = []
    for curEpObj in result.episodes:
        with curEpObj.lock:
            if isFirstBestMatch(result):
                curEpObj.status = Quality.compositeStatus(SNATCHED_BEST, result.quality)
            else:
                curEpObj.status = Quality.compositeStatus(endStatus, result.quality)
            # Reset all others fields to a "snatch" status
            curEpObj.hasnfo = False
            curEpObj.hastbn = False
            curEpObj.location = ''
            curEpObj.file_size = 0
            curEpObj.release_name = ''
            curEpObj.subtitles = list()
            curEpObj.subtitles_searchcount = 0
            curEpObj.subtitles_lastsearch = '0001-01-01 00:00:00'
            curEpObj.is_proper = True if result.proper_tags else False
            curEpObj.version = 0
            curEpObj.release_group = ''

            sql_l.append(curEpObj.get_sql())

        if curEpObj.status not in Quality.DOWNLOADED:
            # TODO: Remove this broad catch when all notifiers handle exceptions
            try:
                notify_message = curEpObj.formatted_filename('%SN - %Sx%0E - %EN - %QN')
                if all([app.SEEDERS_LEECHERS_IN_NOTIFY, result.seeders not in (-1, None),
                        result.leechers not in (-1, None)]):
                    notifiers.notify_snatch("{0} with {1} seeders and {2} leechers from {3}".format
                                            (notify_message, result.seeders, result.leechers, result.provider.name), is_proper)
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


def pickBestResult(results, show):  # pylint: disable=too-many-branches
    """
    Find the best result out of a list of search results for a show.

    :param results: list of result objects
    :param show: Shows we check for
    :return: best result object
    """
    results = results if isinstance(results, list) else [results]

    logger.log(u"Picking the best result out of " + str([x.name for x in results]), logger.DEBUG)

    bestResult = None

    # find the best result for the current episode
    for cur_result in results:
        if show and cur_result.show is not show:
            continue

        # build the black and white list
        if show.is_anime:
            if not show.release_groups.is_valid(cur_result):
                continue

        logger.log(u"Quality of " + cur_result.name + u" is " + Quality.qualityStrings[cur_result.quality])

        anyQualities, bestQualities = Quality.splitQuality(show.quality)

        if cur_result.quality not in anyQualities + bestQualities:
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

        show_words = show_name_helpers.show_words(cur_result.show)
        ignore_words = show_words.ignore_words
        require_words = show_words.require_words
        found_ignore_word = show_name_helpers.containsAtLeastOneWord(cur_result.name, ignore_words)
        found_require_word = show_name_helpers.containsAtLeastOneWord(cur_result.name, require_words)

        if ignore_words and found_ignore_word:
            logger.log(u"Ignoring " + cur_result.name + u" based on ignored words filter: " + found_ignore_word,
                       logger.INFO)
            continue

        if require_words and not found_require_word:
            logger.log(u"Ignoring " + cur_result.name + u" based on required words filter: " + require_words,
                       logger.INFO)
            continue

        if not show_name_helpers.filterBadReleases(cur_result.name, parse=False):
            continue

        if hasattr(cur_result, 'size'):
            if app.USE_FAILED_DOWNLOADS and failed_history.hasFailed(cur_result.name, cur_result.size,
                                                                     cur_result.provider.name):
                logger.log(cur_result.name + u" has previously failed, rejecting it")
                continue
        preferred_words = ''
        if app.PREFERRED_WORDS:
            preferred_words = app.PREFERRED_WORDS.lower().split(',')
        undesired_words = ''
        if app.UNDESIRED_WORDS:
            undesired_words = app.UNDESIRED_WORDS.lower().split(',')

        if not bestResult:
            bestResult = cur_result
        elif cur_result.quality in bestQualities and (bestResult.quality < cur_result.quality or
                                                      bestResult.quality not in bestQualities):
            bestResult = cur_result
        elif cur_result.quality in anyQualities and bestResult.quality not in bestQualities and \
                bestResult.quality < cur_result.quality:
            bestResult = cur_result
        elif bestResult.quality == cur_result.quality:
            if any(ext in cur_result.name.lower() for ext in preferred_words):
                logger.log(u"Preferring " + cur_result.name + u" (preferred words)")
                bestResult = cur_result
            if cur_result.proper_tags:
                logger.log(u"Preferring " + cur_result.name + u" (repack/proper/real/rerip over nuked)")
                bestResult = cur_result
            elif "internal" in bestResult.name.lower() and "internal" not in cur_result.name.lower():
                logger.log(u"Preferring " + cur_result.name + u" (normal instead of internal)")
                bestResult = cur_result
            elif "xvid" in bestResult.name.lower() and "x264" in cur_result.name.lower():
                logger.log(u"Preferring " + cur_result.name + u" (x264 over xvid)")
                bestResult = cur_result
            if any(ext in bestResult.name.lower() and ext not in cur_result.name.lower() for ext in undesired_words):
                logger.log(u"Dont want this release " + cur_result.name + u" (contains undesired word(s))")
                bestResult = cur_result

    if bestResult:
        logger.log(u"Picked " + bestResult.name + u" as the best", logger.DEBUG)
    else:
        logger.log(u"No result picked.", logger.DEBUG)

    return bestResult


def isFinalResult(result):
    """
    Checks if the given result is good enough quality that we can stop searching for other ones.

    :param result: quality to check
    :return: True if the result is the highest quality in both the any/best quality lists else False
    """

    logger.log(u"Checking if we should keep searching after we've found " + result.name, logger.DEBUG)

    show_obj = result.episodes[0].show

    any_qualities, best_qualities = Quality.splitQuality(show_obj.quality)

    # if there is a re-download that's higher than this then we definitely need to keep looking
    if best_qualities and result.quality < max(best_qualities):
        return False

    # if it does not match the shows black and white list its no good
    elif show_obj.is_anime and show_obj.release_groups.is_valid(result):
        return False

    # if there's no re-download that's higher (above) and this is the highest initial download then we're good
    elif any_qualities and result.quality in any_qualities:
        return True

    elif best_qualities and result.quality == max(best_qualities):
        return True

    # if we got here than it's either not on the lists, they're empty, or it's lower than the highest required
    else:
        return False


def isFirstBestMatch(result):
    """
    Check if the given result is a best quality match and if we want to stop searching providers here.

    :param result: to check
    :return: True if the result is the best quality match else False
    """
    logger.log(u"Checking if we should stop searching for a better quality for for episode " + result.name,
               logger.DEBUG)

    show_obj = result.episodes[0].show

    _, best_qualities = Quality.splitQuality(show_obj.quality)

    return result.quality in best_qualities if best_qualities else False


def wantedEpisodes(show, fromDate):
    """
    Get a list of episodes that we want to download.

    :param show: Show these episodes are from
    :param fromDate: Search from a certain date
    :return: list of wanted episodes
    """
    wanted = []
    if show.paused:
        logger.log(u"Not checking for episodes of %s because the show is paused" % show.name, logger.DEBUG)
        return wanted

    allowed_qualities, preferred_qualities = common.Quality.splitQuality(show.quality)
    all_qualities = list(set(allowed_qualities + preferred_qualities))

    logger.log(u"Seeing if we need anything from " + show.name, logger.DEBUG)
    con = db.DBConnection()

    sql_results = con.select(
        "SELECT status, season, episode FROM tv_episodes WHERE showid = ? AND season > 0 and airdate > ?",
        [show.indexerid, fromDate.toordinal()]
    )

    # check through the list of statuses to see if we want any
    for result in sql_results:
        cur_status, cur_quality = common.Quality.splitCompositeStatus(int(result["status"] or -1))
        if cur_status not in {common.WANTED, common.DOWNLOADED, common.SNATCHED, common.SNATCHED_PROPER}:
            continue

        if cur_status != common.WANTED:
            if preferred_qualities:
                if cur_quality in preferred_qualities:
                    continue
            elif cur_quality in allowed_qualities:
                continue

        epObj = show.get_episode(result["season"], result["episode"])
        epObj.wanted_quality = [i for i in all_qualities if i > cur_quality and i != common.Quality.UNKNOWN]
        wanted.append(epObj)

    return wanted


def searchForNeededEpisodes():
    """
    Check providers for details on wanted episodes.

    :return: episodes we have a search hit for
    """
    foundResults = {}

    didSearch = False

    show_list = app.showList
    fromDate = datetime.date.fromordinal(1)
    episodes = []

    for curShow in show_list:
        if not curShow.paused:
            episodes.extend(wantedEpisodes(curShow, fromDate))

    if not episodes:
        # nothing wanted so early out, ie: avoid whatever abritrarily
        # complex thing a provider cache update entails, for example,
        # reading rss feeds
        return foundResults.values()

    original_thread_name = threading.currentThread().name

    providers = enabled_providers('daily')
    for cur_provider in providers:
        threading.currentThread().name = '{thread} :: [{provider}]'.format(thread=original_thread_name,
                                                                           provider=cur_provider.name)
        cur_provider.cache.updateCache()

    for cur_provider in providers:
        threading.currentThread().name = '{thread} :: [{provider}]'.format(thread=original_thread_name,
                                                                           provider=cur_provider.name)
        curFoundResults = {}
        try:
            curFoundResults = cur_provider.search_rss(episodes)
        except AuthException as e:
            logger.log(u"Authentication error: " + ex(e), logger.ERROR)
            continue
        except Exception as e:
            logger.log(u"Error while searching " + cur_provider.name + u", skipping: " + ex(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)
            continue

        didSearch = True

        # pick a single result for each episode, respecting existing results
        for curEp in curFoundResults:
            if not curEp.show or curEp.show.paused:
                logger.log(u"Skipping %s because the show is paused " % curEp.pretty_name(), logger.DEBUG)
                continue

            bestResult = pickBestResult(curFoundResults[curEp], curEp.show)

            # if all results were rejected move on to the next episode
            if not bestResult:
                logger.log(u"All found results for " + curEp.pretty_name() + u" were rejected.", logger.DEBUG)
                continue

            # if it's already in the list (from another provider) and the newly found quality is no better then skip it
            if curEp in foundResults and bestResult.quality <= foundResults[curEp].quality:
                continue

            foundResults[curEp] = bestResult

    threading.currentThread().name = original_thread_name

    if not didSearch:
        logger.log(
            u"No NZB/Torrent providers found or enabled in the application config for daily searches. "
            u"Please check your settings.", logger.WARNING)

    return foundResults.values()


def searchProviders(show, episodes, forced_search=False, downCurQuality=False,
                    manual_search=False, manual_search_type='episode'):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
    """
    Walk providers for information on shows.

    :param show: Show we are looking for
    :param episodes: List, episodes we hope to find
    :param forced_search: Boolean, is this a forced search?
    :param downCurQuality: Boolean, should we re-download currently available quality file
    :param manual_search: Boolean, should we choose what to download?
    :return: results for search
    """
    foundResults = {}
    finalResults = []
    manual_search_results = []

    didSearch = False

    # build name cache for show
    app.name_cache.buildNameCache(show)

    original_thread_name = threading.currentThread().name

    if manual_search:
        logger.log("Using manual search providers")
        providers = [x for x in app.providers.sortedProviderList(app.RANDOMIZE_PROVIDERS)
                     if x.is_active() and x.enable_manualsearch]
    else:
        providers = [x for x in app.providers.sortedProviderList(app.RANDOMIZE_PROVIDERS)
                     if x.is_active() and x.enable_backlog]

    if not forced_search:
        for cur_provider in providers:
            threading.currentThread().name = '{thread} :: [{provider}]'.format(thread=original_thread_name,
                                                                               provider=cur_provider.name)
            cur_provider.cache.updateCache()

    threading.currentThread().name = original_thread_name

    for cur_provider in providers:
        threading.currentThread().name = original_thread_name + " :: [" + cur_provider.name + "]"

        if cur_provider.anime_only and not show.is_anime:
            logger.log(str(show.name) + u" is not an anime, skipping", logger.DEBUG)
            continue

        foundResults[cur_provider.name] = {}

        searchCount = 0
        search_mode = cur_provider.search_mode

        # Always search for episode when manually searching when in sponly
        if search_mode == 'sponly' and (forced_search or manual_search):
            search_mode = 'eponly'

        if manual_search and manual_search_type == 'season':
            search_mode = 'sponly'

        while True:
            searchCount += 1

            if search_mode == 'eponly':
                logger.log(u"Performing episode search for " + show.name)
            else:
                logger.log(u"Performing season pack search for " + show.name)

            try:
                searchResults = cur_provider.find_search_results(show, episodes, search_mode, forced_search,
                                                                 downCurQuality, manual_search, manual_search_type)
            except AuthException as e:
                logger.log(u"Authentication error: " + ex(e), logger.ERROR)
                break
            except SocketTimeout as e:
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
            except requests.exceptions.ContentDecodingError:
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

            didSearch = True

            if searchResults:
                # make a list of all the results for this provider
                for curEp in searchResults:
                    if curEp in foundResults[cur_provider.name]:
                        foundResults[cur_provider.name][curEp] += searchResults[curEp]
                    else:
                        foundResults[cur_provider.name][curEp] = searchResults[curEp]

                    # Sort the list by seeders if possible
                    if cur_provider.provider_type == 'torrent' or getattr(cur_provider, 'torznab', None):
                        foundResults[cur_provider.name][curEp].sort(key=lambda d: int(d.seeders), reverse=True)

                break
            elif not cur_provider.search_fallback or searchCount == 2:
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
        if not foundResults[cur_provider.name]:
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
                if (searched_episode in searchResults and
                        cur_provider.cache.update_cache_manual_search(searchResults[searched_episode])):
                    # If we have at least a result from one provider, it's good enough to be marked as result
                    manual_search_results.append(True)
            # Continue because we don't want to pick best results as we are running a manual search by user
            continue

        # pick the best season NZB
        bestSeasonResult = None
        if SEASON_RESULT in foundResults[cur_provider.name]:
            bestSeasonResult = pickBestResult(foundResults[cur_provider.name][SEASON_RESULT], show)

        highest_quality_overall = 0
        for cur_episode in foundResults[cur_provider.name]:
            for cur_result in foundResults[cur_provider.name][cur_episode]:
                if cur_result.quality != Quality.UNKNOWN and cur_result.quality > highest_quality_overall:
                    highest_quality_overall = cur_result.quality
        logger.log(u"The highest quality of any match is " + Quality.qualityStrings[highest_quality_overall],
                   logger.DEBUG)

        # see if every episode is wanted
        if bestSeasonResult:
            searchedSeasons = {str(x.season) for x in episodes}

            # get the quality of the season nzb
            seasonQual = bestSeasonResult.quality
            logger.log(
                u"The quality of the season " + bestSeasonResult.provider.provider_type + " is " +
                Quality.qualityStrings[seasonQual], logger.DEBUG)

            main_db_con = db.DBConnection()
            allEps = [int(x["episode"])
                      for x in main_db_con.select("SELECT episode FROM tv_episodes WHERE showid = ? AND "
                      "( season IN ( " + ','.join(searchedSeasons) + " ) )", [show.indexerid])]

            logger.log(u"Executed query: [SELECT episode FROM tv_episodes WHERE showid = %s AND season in  %s]" %
                       (show.indexerid, ','.join(searchedSeasons)))
            logger.log(u"Episode list: " + str(allEps), logger.DEBUG)

            allWanted = True
            anyWanted = False
            for curEpNum in allEps:
                for season in {x.season for x in episodes}:
                    if not show.want_episode(season, curEpNum, seasonQual, downCurQuality):
                        allWanted = False
                    else:
                        anyWanted = True

            # if we need every ep in the season and there's nothing better then
            # just download this and be done with it (unless single episodes are preferred)
            if allWanted and bestSeasonResult.quality == highest_quality_overall:
                logger.log(
                    u"Every ep in this season is needed, downloading the whole " +
                    bestSeasonResult.provider.provider_type + " " + bestSeasonResult.name)
                epObjs = []
                for curEpNum in allEps:
                    for season in {x.season for x in episodes}:
                        epObjs.append(show.get_episode(season, curEpNum))
                bestSeasonResult.episodes = epObjs

                # Remove provider from thread name before return results
                threading.currentThread().name = original_thread_name

                return [bestSeasonResult]

            elif not anyWanted:
                logger.log(
                    u"No eps from this season are wanted at this quality, ignoring the result of " +
                    bestSeasonResult.name, logger.DEBUG)

            else:

                if bestSeasonResult.provider.provider_type == GenericProvider.NZB:
                    logger.log(u"Breaking apart the NZB and adding the individual ones to our results", logger.DEBUG)

                    # if not, break it apart and add them as the lowest priority results
                    individualResults = nzbSplitter.split_result(bestSeasonResult)
                    for curResult in individualResults:
                        if len(curResult.episodes) == 1:
                            epNum = curResult.episodes[0].episode
                        elif len(curResult.episodes) > 1:
                            epNum = MULTI_EP_RESULT

                        if epNum in foundResults[cur_provider.name]:
                            foundResults[cur_provider.name][epNum].append(curResult)
                        else:
                            foundResults[cur_provider.name][epNum] = [curResult]

                # If this is a torrent all we can do is leech the entire torrent,
                # user will have to select which eps not do download in his torrent client
                else:

                    # Season result from Torrent Provider must be a full-season torrent,
                    # creating multi-ep result for it.
                    logger.log(
                        u"Adding multi-ep result for full-season torrent. "
                        u"Set the episodes you don't want to 'don't download' in your torrent client if desired!")
                    epObjs = []
                    for curEpNum in allEps:
                        for season in {x.season for x in episodes}:
                            epObjs.append(show.get_episode(season, curEpNum))
                    bestSeasonResult.episodes = epObjs

                    if MULTI_EP_RESULT in foundResults[cur_provider.name]:
                        foundResults[cur_provider.name][MULTI_EP_RESULT].append(bestSeasonResult)
                    else:
                        foundResults[cur_provider.name][MULTI_EP_RESULT] = [bestSeasonResult]

        # go through multi-ep results and see if we really want them or not, get rid of the rest
        multiResults = {}
        if MULTI_EP_RESULT in foundResults[cur_provider.name]:
            for _multiResult in foundResults[cur_provider.name][MULTI_EP_RESULT]:

                logger.log(u"Seeing if we want to bother with multi-episode result " +
                           _multiResult.name, logger.DEBUG)

                # Filter result by ignore/required/whitelist/blacklist/quality, etc
                multiResult = pickBestResult(_multiResult, show)
                if not multiResult:
                    continue

                # see how many of the eps that this result covers aren't covered by single results
                neededEps = []
                notNeededEps = []
                for epObj in multiResult.episodes:
                    # if we have results for the episode
                    if epObj.episode in foundResults[cur_provider.name] and \
                            len(foundResults[cur_provider.name][epObj.episode]) > 0:
                        notNeededEps.append(epObj.episode)
                    else:
                        neededEps.append(epObj.episode)

                logger.log(
                    u"Single-ep check result is neededEps: " + str(neededEps) + u", notNeededEps: " +
                    str(notNeededEps), logger.DEBUG)

                if not neededEps:
                    logger.log(u"All of these episodes were covered by single episode results, "
                               u"ignoring this multi-episode result", logger.DEBUG)
                    continue

                # check if these eps are already covered by another multi-result
                multiNeededEps = []
                multiNotNeededEps = []
                for epObj in multiResult.episodes:
                    if epObj.episode in multiResults:
                        multiNotNeededEps.append(epObj.episode)
                    else:
                        multiNeededEps.append(epObj.episode)

                logger.log(u"Multi-ep check result is multiNeededEps: " + str(multiNeededEps) +
                           u", multiNotNeededEps: " + str(multiNotNeededEps), logger.DEBUG)

                if not multiNeededEps:
                    logger.log(
                        u"All of these episodes were covered by another multi-episode nzbs, "
                        u"ignoring this multi-ep result", logger.DEBUG)
                    continue

                # don't bother with the single result if we're going to get it with a multi result
                for epObj in multiResult.episodes:
                    multiResults[epObj.episode] = multiResult
                    if epObj.episode in foundResults[cur_provider.name]:
                        logger.log(
                            u"A needed multi-episode result overlaps with a single-episode result for ep #" +
                            str(epObj.episode) + u", removing the single-episode results from the list", logger.DEBUG)
                        del foundResults[cur_provider.name][epObj.episode]

        # of all the single ep results narrow it down to the best one for each episode
        finalResults += set(multiResults.values())
        for curEp in foundResults[cur_provider.name]:
            if curEp in (MULTI_EP_RESULT, SEASON_RESULT):
                continue

            if not foundResults[cur_provider.name][curEp]:
                continue

            # if all results were rejected move on to the next episode
            bestResult = pickBestResult(foundResults[cur_provider.name][curEp], show)
            if not bestResult:
                continue

            # add result if its not a duplicate and
            found = False
            for i, result in enumerate(finalResults):
                for bestResultEp in bestResult.episodes:
                    if bestResultEp in result.episodes:
                        if result.quality < bestResult.quality:
                            finalResults.pop(i)
                        else:
                            found = True
            if not found:
                finalResults += [bestResult]

        # check that we got all the episodes we wanted first before doing a match and snatch
        wantedEpCount = 0
        for wantedEp in episodes:
            for result in finalResults:
                if wantedEp in result.episodes and isFinalResult(result):
                    wantedEpCount += 1

        # make sure we search every provider for results unless we found everything we wanted
        if wantedEpCount == len(episodes):
            break

    if not didSearch:
        logger.log(u"No NZB/Torrent providers found or enabled in the application config for backlog searches. "
                   u"Please check your settings.", logger.WARNING)

    # Remove provider from thread name before return results
    threading.currentThread().name = original_thread_name

    if manual_search:
        # If results in manual search return True, else False
        return any(manual_search_results)
    else:
        return finalResults
