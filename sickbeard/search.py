# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>

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

import os
import re
import errno
import threading
import datetime
import traceback
import requests
from socket import timeout as SocketTimeout

import sickbeard

from sickbeard.common import SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, Quality, SEASON_RESULT, MULTI_EP_RESULT

from sickbeard import logger, db, show_name_helpers, helpers
from sickbeard import sab
from sickbeard import nzbget
from sickbeard import clients
from sickbeard import history
from sickbeard import notifiers
from sickbeard import nzbSplitter
from sickbeard import ui
from sickbeard import failed_history
from sickbeard import common
from sickrage.helper.encoding import ek
from sickrage.helper.exceptions import AuthException, ex
from sickrage.providers.GenericProvider import GenericProvider
from sickrage.helper.common import enabled_providers


def _downloadResult(result):
    """
    Downloads a result to the appropriate black hole folder.

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
        file_name = ek(os.path.join, sickbeard.NZB_DIR, result.name + ".nzb")

        logger.log(u"Saving NZB to " + file_name)

        new_result = True

        # save the data to disk
        try:
            with ek(open, file_name, 'w') as fileOut:
                fileOut.write(result.extraInfo[0])

            helpers.chmodAsParent(file_name)

        except EnvironmentError as e:
            logger.log(u"Error trying to save NZB to black hole: " + ex(e), logger.ERROR)
            new_result = False
    elif result.resultType == "torrent":
        new_result = res_provider.download_result(result)
    else:
        logger.log(u"Invalid provider type - this is a coding error, report it please", logger.ERROR)
        new_result = False

    return new_result


def snatchEpisode(result, end_status=SNATCHED):  # pylint: disable=too-many-branches, too-many-statements
    """
    Contains the internal logic necessary to actually "snatch" a result that
    has been found.

    :param result: SearchResult instance to be snatched.
    :param end_status: the episode status that should be used for the episode object once it's snatched.
    :return: boolean, True on success
    """

    if result is None:
        return False

    result.priority = 0  # -1 = low, 0 = normal, 1 = high
    if sickbeard.ALLOW_HIGH_PRIORITY:
        # if it aired recently make it high priority
        for cur_ep in result.episodes:
            if datetime.date.today() - cur_ep.airdate <= datetime.timedelta(days=7):
                result.priority = 1
    if re.search(r'(^|[\. _-])(proper|repack)([\. _-]|$)', result.name, re.I) is not None:
        end_status = SNATCHED_PROPER

    if result.url.startswith('magnet') or result.url.endswith('torrent'):
        result.resultType = 'torrent'

    # NZBs can be sent straight to SAB or saved to disk
    if result.resultType in ("nzb", "nzbdata"):
        if sickbeard.NZB_METHOD == "blackhole":
            dlResult = _downloadResult(result)
        elif sickbeard.NZB_METHOD == "sabnzbd":
            dlResult = sab.sendNZB(result)
        elif sickbeard.NZB_METHOD == "nzbget":
            is_proper = True if end_status == SNATCHED_PROPER else False
            dlResult = nzbget.sendNZB(result, is_proper)
        else:
            logger.log(u"Unknown NZB action specified in config: " + sickbeard.NZB_METHOD, logger.ERROR)
            dlResult = False

    # Torrents can be sent to clients or saved to disk
    elif result.resultType == "torrent":
        # torrents are saved to disk when blackhole mode
        if sickbeard.TORRENT_METHOD == "blackhole":
            dlResult = _downloadResult(result)
        else:
            if not result.content and not result.url.startswith('magnet'):
                if result.provider.login():
                    result.content = result.provider.get_url(result.url, returns='content')

            if result.content or result.url.startswith('magnet'):
                client = clients.getClientIstance(sickbeard.TORRENT_METHOD)()
                dlResult = client.sendTORRENT(result)
            else:
                logger.log(u"Torrent file content is empty", logger.WARNING)
                dlResult = False
    else:
        logger.log(u"Unknown result type, unable to download it (%r)" % result.resultType, logger.ERROR)
        dlResult = False

    if not dlResult:
        return False

    if sickbeard.USE_FAILED_DOWNLOADS:
        failed_history.logSnatch(result)

    ui.notifications.message('Episode snatched', result.name)

    history.logSnatch(result)

    # don't notify when we re-download an episode
    sql_l = []
    trakt_data = []
    for cur_ep_obj in result.episodes:
        with cur_ep_obj.lock:
            if isFirstBestMatch(result):
                cur_ep_obj.status = Quality.compositeStatus(SNATCHED_BEST, result.quality)
            else:
                cur_ep_obj.status = Quality.compositeStatus(end_status, result.quality)

            sql_l.append(cur_ep_obj.get_sql())

        if cur_ep_obj.status not in Quality.DOWNLOADED:
            try:
                notify_message = cur_ep_obj.formatted_filename('%SN - %Sx%0E - %EN - %QN')
                if all([sickbeard.SEEDERS_LEECHERS_IN_NOTIFY, result.seeders not in (-1, None), result.leechers not in (-1, None)]):
                    notifiers.notify_snatch(
                        "{0} with {1} seeders and {2} leechers from {3}".format(notify_message, result.seeders,
                                                                                result.leechers, result.provider.name))
                else:
                    notifiers.notify_snatch("{0} from {1}".format(notify_message, result.provider.name))
            except Exception:
                # Without this, when notification fail, it crashes the snatch thread and Medusa will
                # keep snatching until notification is sent
                logger.log(u"Failed to send snatch notification", logger.DEBUG)

            trakt_data.append((cur_ep_obj.season, cur_ep_obj.episode))

    data = notifiers.trakt_notifier.trakt_episode_data_generate(trakt_data)

    if sickbeard.USE_TRAKT and sickbeard.TRAKT_SYNC_WATCHLIST:
        logger.log(u"Add episodes, showid: indexerid " + str(result.show.indexerid) + ", Title " +
                   str(result.show.name) + " to Traktv Watchlist", logger.DEBUG)
        if data:
            notifiers.trakt_notifier.update_watchlist(result.show, data_episode=data, update="add")

    if sql_l:
        main_db_con = db.DBConnection()
        main_db_con.mass_action(sql_l)

    return True


def pickBestResult(results, show):  # pylint: disable=too-many-branches
    """
    Find the best result out of a list of search results for a show

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

        # build the black And white list
        if show.is_anime:
            if not show.release_groups.is_valid(cur_result):
                continue

        logger.log(u"Quality of " + cur_result.name + " is " + Quality.qualityStrings[cur_result.quality])

        any_qualities, best_qualities = Quality.splitQuality(show.quality)

        if cur_result.quality not in any_qualities + best_qualities:
            logger.log(cur_result.name + " is a quality we know we don't want, rejecting it", logger.DEBUG)
            continue

        if show.rls_ignore_words and show_name_helpers.containsAtLeastOneWord(cur_result.name, cur_result.show.rls_ignore_words):
            logger.log(u"Ignoring " + cur_result.name + " based on ignored words filter: " + show.rls_ignore_words,
                       logger.INFO)
            continue

        if show.rls_require_words and not show_name_helpers.containsAtLeastOneWord(cur_result.name, cur_result.show.rls_require_words):
            logger.log(u"Ignoring " + cur_result.name + " based on required words filter: " + show.rls_require_words,
                       logger.INFO)
            continue

        if not show_name_helpers.filterBadReleases(cur_result.name, parse=False, show=show):
            logger.log(u"Ignoring " + cur_result.name + " because its not a valid scene release that we want, ignoring it",
                       logger.INFO)
            continue

        if hasattr(cur_result, 'size'):
            if sickbeard.USE_FAILED_DOWNLOADS and failed_history.hasFailed(cur_result.name, cur_result.size,
                                                                           cur_result.provider.name):
                logger.log(cur_result.name + u" has previously failed, rejecting it")
                continue
        preferred_words = ''
        if sickbeard.PREFERRED_WORDS:
            preferred_words = sickbeard.PREFERRED_WORDS.lower().split(',')
        undesired_words = ''
        if sickbeard.UNDESIRED_WORDS:
            undesired_words = sickbeard.UNDESIRED_WORDS.lower().split(',')

        if not best_result:
            best_result = cur_result
        elif cur_result.quality in best_qualities and (best_result.quality < cur_result.quality or best_result.quality not in best_qualities):
            best_result = cur_result
        elif cur_result.quality in any_qualities and best_result.quality not in best_qualities and best_result.quality < cur_result.quality:
            best_result = cur_result
        elif best_result.quality == cur_result.quality:
            if any(ext in cur_result.name.lower() for ext in preferred_words):
                logger.log(u"Preferring " + cur_result.name + " (preferred words)")
                best_result = cur_result
            if "proper" in cur_result.name.lower() or "real" in cur_result.name.lower() or "repack" in cur_result.name.lower():
                logger.log(u"Preferring " + cur_result.name + " (repack/proper/real over nuked)")
                best_result = cur_result
            elif "internal" in best_result.name.lower() and "internal" not in cur_result.name.lower():
                logger.log(u"Preferring " + cur_result.name + " (normal instead of internal)")
                best_result = cur_result
            elif "xvid" in best_result.name.lower() and "x264" in cur_result.name.lower():
                logger.log(u"Preferring " + cur_result.name + " (x264 over xvid)")
                best_result = cur_result
            if any(ext in best_result.name.lower() and ext not in cur_result.name.lower() for ext in undesired_words):
                logger.log(u"Dont want this release " + cur_result.name + " (contains undesired word(s))")
                best_result = cur_result

    if best_result:
        logger.log(u"Picked " + best_result.name + " as the best", logger.DEBUG)
    else:
        logger.log(u"No result picked.", logger.DEBUG)

    return best_result


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
    Checks if the given result is a best quality match and if we want to stop searching providers here.

    :param result: to check
    :return: True if the result is the best quality match else False
    """

    logger.log(u"Checking if we should stop searching for a better quality for for episode " + result.name,
               logger.DEBUG)

    show_obj = result.episodes[0].show

    _, best_qualities = Quality.splitQuality(show_obj.quality)

    return result.quality in best_qualities if best_qualities else False


def wantedEpisodes(show, from_date):
    """
    Get a list of episodes that we want to download
    :param show: Show these episodes are from
    :param from_date: Search from a certain date
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
        [show.indexerid, from_date.toordinal()]
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

        ep_obj = show.getEpisode(result["season"], result["episode"])
        ep_obj.wantedQuality = [i for i in all_qualities if i > cur_quality and i != common.Quality.UNKNOWN]
        wanted.append(ep_obj)

    return wanted


def searchForNeededEpisodes():
    """
    Check providers for details on wanted episodes

    :return: episodes we have a search hit for
    """
    found_results = {}

    did_search = False

    show_list = sickbeard.showList
    from_date = datetime.date.fromordinal(1)
    episodes = []

    for cur_show in show_list:
        if not cur_show.paused:
            sickbeard.name_cache.buildNameCache(cur_show)
            episodes.extend(wantedEpisodes(cur_show, from_date))

    if not episodes:
        # nothing wanted so early out, ie: avoid whatever abritrarily
        # complex thing a provider cache update entails, for example,
        # reading rss feeds
        logger.log(u"No episodes needed.", logger.INFO)
        return found_results.values()

    original_thread_name = threading.currentThread().name

    providers = enabled_providers('daily')
    for cur_provider in providers:
        threading.currentThread().name = '{thread} :: [{provider}]'.format(thread=original_thread_name, provider=cur_provider.name)
        cur_provider.cache.updateCache()

    for cur_provider in providers:
        threading.currentThread().name = '{thread} :: [{provider}]'.format(thread=original_thread_name, provider=cur_provider.name)
        cur_found_results = {}
        try:
            cur_found_results = cur_provider.search_rss(episodes)
        except AuthException as e:
            logger.log(u"Authentication error: " + ex(e), logger.ERROR)
            continue
        except Exception as e:
            logger.log(u"Error while searching " + cur_provider.name + ", skipping: " + ex(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)
            continue

        did_search = True

        # pick a single result for each episode, respecting existing results
        for cur_ep in cur_found_results:
            if not cur_ep.show or cur_ep.show.paused:
                logger.log(u"Skipping %s because the show is paused " % cur_ep.prettyName(), logger.DEBUG)
                continue

            best_result = pickBestResult(cur_found_results[cur_ep], cur_ep.show)

            # if all results were rejected move on to the next episode
            if not best_result:
                logger.log(u"All found results for " + cur_ep.prettyName() + " were rejected.", logger.DEBUG)
                continue

            # if it's already in the list (from another provider) and the newly found quality is no better then skip it
            if cur_ep in found_results and best_result.quality <= found_results[cur_ep].quality:
                continue

            found_results[cur_ep] = best_result

    threading.currentThread().name = original_thread_name

    if not did_search:
        logger.log(
            u"No NZB/Torrent providers found or enabled in the sickrage config for daily searches. Please check your settings.",
            logger.WARNING)

    return found_results.values()


class Search(object):
    """Search Class"""
    def __init__(self, manual_search=False, force_stop=None):
        """Initialize Search object
        This Class has been created to keep an external reference to the self.force_stop attribute.
        The attribute can be used to gracefully halt the searchProvider() method

        :param manual_search: Pass as True or False to mark the searchProvider as a manual search,
        which will not automatically snatch the best result, but update the providers cache table instead
        :param force_stop: A mutable attribute pass as [True] or [False]. The list is used to keep an external
        reference. The force_stop attribute will gracefully stop the search_providers() method.
        """
        self.manual_search = manual_search
        self.force_stop = force_stop

    def search_providers(self, show, episodes, forced_search=False, down_cur_quality=False):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        """
        Walk providers for information on shows

        :param show: Show we are looking for
        :param episodes: Episodes we hope to find
        :param forced_search: Boolean, is this a forced search?
        :param down_cur_quality: Boolean, should we re-download currently available quality file
        :return: results for search
        """
        found_results = {}
        final_results = []
        manual_search_results = []

        did_search = False

        # build name cache for show
        sickbeard.name_cache.buildNameCache(show)

        original_thread_name = threading.currentThread().name

        if self.manual_search:
            logger.log("Using manual search providers")
            providers = [x for x in sickbeard.providers.sortedProviderList(sickbeard.RANDOMIZE_PROVIDERS)
                         if x.is_active() and x.enable_manualsearch]
        else:
            providers = [x for x in sickbeard.providers.sortedProviderList(sickbeard.RANDOMIZE_PROVIDERS)
                         if x.is_active() and x.enable_backlog]

        if not forced_search:
            for cur_provider in providers:
                if self.force_stop[0]:
                    logger.log(u"A forced stop was detected, skipping cache update for provider [{0}]".format(cur_provider.name), logger.DEBUG)
                    continue
                threading.currentThread().name = '{thread} :: [{provider}]'.format(thread=original_thread_name, provider=cur_provider.name)
                cur_provider.cache.updateCache()

        threading.currentThread().name = original_thread_name

        for cur_provider in providers:
            # If force_stop is toggled, lets skip all remaining providers, but process the results we have
            if self.force_stop[0]:
                logger.log(u"A forced stop was detected, skipping search for provider [{0}]".format(cur_provider.name), logger.DEBUG)
                continue

            threading.currentThread().name = original_thread_name + " :: [" + cur_provider.name + "]"

            if cur_provider.anime_only and not show.is_anime:
                logger.log(u"" + str(show.name) + " is not an anime, skipping", logger.DEBUG)
                continue

            found_results[cur_provider.name] = {}

            search_count = 0
            search_mode = cur_provider.search_mode

            # Always search for episode when manually searching when in sponly
            if search_mode == 'sponly' and (forced_search or self.manual_search):
                search_mode = 'eponly'

            while True:
                search_count += 1

                if search_mode == 'eponly':
                    logger.log(u"Performing episode search for " + show.name)
                else:
                    logger.log(u"Performing season pack search for " + show.name)

                try:
                    search_results = cur_provider.find_search_results(show, episodes, search_mode,
                                                                      forced_search, down_cur_quality, self.manual_search)
                except AuthException as e:
                    logger.log(u"Authentication error: " + ex(e), logger.ERROR)
                    break
                except (SocketTimeout, TypeError) as e:
                    logger.log(u"Connection timed out (sockets) while searching %s. Error: %r" %
                               (cur_provider.name, ex(e)), logger.DEBUG)
                    break
                except (requests.exceptions.HTTPError, requests.exceptions.TooManyRedirects) as e:
                    logger.log(u"HTTP error while searching %s. Error: %r" % (cur_provider.name, ex(e)), logger.DEBUG)
                    break
                except requests.exceptions.ConnectionError as e:
                    logger.log(u"Connection error while searching %s. Error: %r" % (cur_provider.name, ex(e)), logger.DEBUG)
                    break
                except requests.exceptions.Timeout as e:
                    logger.log(u"Connection timed out while searching %s. Error: %r" % (cur_provider.name, ex(e)), logger.DEBUG)
                    break
                except requests.exceptions.ContentDecodingError:
                    logger.log(u"Content-Encoding was gzip, but content was not compressed while searching %s. Error: %r" %
                               (cur_provider.name, ex(e)), logger.DEBUG)
                    break
                except Exception as e:
                    if 'ECONNRESET' in e or (hasattr(e, 'errno') and e.errno == errno.ECONNRESET):
                        logger.log(u"Connection reseted by peer while searching %s. Error: %r" %
                                   (cur_provider.name, ex(e)), logger.WARNING)
                    else:
                        logger.log(u"Unknown exception while searching %s. Error: %r" % (cur_provider.name, ex(e)), logger.ERROR)
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

                    break
                elif not cur_provider.search_fallback or search_count == 2:
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
            if self.manual_search:
                # Let's create a list with episodes that we where looking for
                searched_episode_list = [episode_obj.episode for episode_obj in episodes]
                # Add the -1 to also match season pack results
                searched_episode_list.append(-1)
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
                best_season_result = pickBestResult(found_results[cur_provider.name][SEASON_RESULT], show)

            highest_quality_overall = 0
            for cur_episode in found_results[cur_provider.name]:
                for cur_result in found_results[cur_provider.name][cur_episode]:
                    if cur_result.quality != Quality.UNKNOWN and cur_result.quality > highest_quality_overall:
                        highest_quality_overall = cur_result.quality
            logger.log(u"The highest quality of any match is " + Quality.qualityStrings[highest_quality_overall],
                       logger.DEBUG)

            # see if every episode is wanted
            if best_season_result:
                searched_seasons = [str(x.season) for x in episodes]

                # get the quality of the season nzb
                season_qual = best_season_result.quality
                logger.log(
                    u"The quality of the season " + best_season_result.provider.provider_type + " is " + Quality.qualityStrings[
                        season_qual], logger.DEBUG)

                main_db_con = db.DBConnection()
                all_eps = [int(x["episode"])
                          for x in main_db_con.select("SELECT episode FROM tv_episodes WHERE showid = ? AND \
                          ( season IN ( " + ','.join(searched_seasons) + " ) )",
                                                        [show.indexerid])]

                logger.log(u"Executed query: [SELECT episode FROM tv_episodes WHERE showid = %s AND season in  %s]" %
                           (show.indexerid, ','.join(searched_seasons)))
                logger.log(u"Episode list: " + str(all_eps), logger.DEBUG)

                all_wanted = True
                any_wanted = False
                for cur_ep_num in all_eps:
                    for season in {x.season for x in episodes}:
                        if not show.wantEpisode(season, cur_ep_num, season_qual, down_cur_quality):
                            all_wanted = False
                        else:
                            any_wanted = True

                # if we need every ep in the season and there's nothing better then just download this and be done with it
                # (unless single episodes are preferred)
                if all_wanted and best_season_result.quality == highest_quality_overall:
                    logger.log(
                        u"Every ep in this season is needed, downloading the whole " +
                        best_season_result.provider.provider_type + " " + best_season_result.name)
                    ep_objs = []
                    for cur_ep_num in all_eps:
                        for season in {x.season for x in episodes}:
                            ep_objs.append(show.getEpisode(season, cur_ep_num))
                    best_season_result.episodes = ep_objs

                    # Remove provider from thread name before return results
                    threading.currentThread().name = original_thread_name

                    return [best_season_result]

                elif not any_wanted:
                    logger.log(
                        u"No eps from this season are wanted at this quality, ignoring the result of " + best_season_result.name,
                        logger.DEBUG)

                else:

                    if best_season_result.provider.provider_type == GenericProvider.NZB:
                        logger.log(u"Breaking apart the NZB and adding the individual ones to our results", logger.DEBUG)

                        # if not, break it apart and add them as the lowest priority results
                        individual_results = nzbSplitter.split_result(best_season_result)
                        for cur_result in individual_results:
                            if len(cur_result.episodes) == 1:
                                ep_num = cur_result.episodes[0].episode
                            elif len(cur_result.episodes) > 1:
                                ep_num = MULTI_EP_RESULT

                            if ep_num in found_results[cur_provider.name]:
                                found_results[cur_provider.name][ep_num].append(cur_result)
                            else:
                                found_results[cur_provider.name][ep_num] = [cur_result]

                    # If this is a torrent all we can do is leech the entire torrent, user will have to select which eps not do download in his torrent client
                    else:

                        # Season result from Torrent Provider must be a full-season torrent, creating multi-ep result for it.
                        logger.log(
                            u"Adding multi-ep result for full-season torrent. \
                            Set the episodes you don't want to 'don't download' in your torrent client if desired!")
                        ep_obj = []
                        for cur_ep_num in all_eps:
                            for season in {x.season for x in episodes}:
                                ep_obj.append(show.getEpisode(season, cur_ep_num))
                        best_season_result.episodes = ep_obj

                        if MULTI_EP_RESULT in found_results[cur_provider.name]:
                            found_results[cur_provider.name][MULTI_EP_RESULT].append(best_season_result)
                        else:
                            found_results[cur_provider.name][MULTI_EP_RESULT] = [best_season_result]

            # go through multi-ep results and see if we really want them or not, get rid of the rest
            multi_results = {}
            if MULTI_EP_RESULT in found_results[cur_provider.name]:
                for _multi_results in found_results[cur_provider.name][MULTI_EP_RESULT]:

                    logger.log(u"Seeing if we want to bother with multi-episode result " + _multi_results.name, logger.DEBUG)

                    # Filter result by ignore/required/whitelist/blacklist/quality, etc
                    multi_results = pickBestResult(_multi_results, show)
                    if not multi_results:
                        continue

                    # see how many of the eps that this result covers aren't covered by single results
                    needed_eps = []
                    not_needed_eps = []
                    for ep_obj in multi_results.episodes:
                        # if we have results for the episode
                        if ep_obj.episode in found_results[cur_provider.name] and len(found_results[cur_provider.name][ep_obj.episode]) > 0:
                            not_needed_eps.append(ep_obj.episode)
                        else:
                            needed_eps.append(ep_obj.episode)

                    logger.log(
                        u"Single-ep check result is needed_eps: " + str(needed_eps) + ", not_needed_eps: " + str(not_needed_eps),
                        logger.DEBUG)

                    if not needed_eps:
                        logger.log(u"All of these episodes were covered by single episode results, \
                        ignoring this multi-episode result", logger.DEBUG)
                        continue

                    # check if these eps are already covered by another multi-result
                    multi_needed_eps = []
                    multi_not_needed_eps = []
                    for ep_obj in multi_results.episodes:
                        if ep_obj.episode in multi_results:
                            multi_not_needed_eps.append(ep_obj.episode)
                        else:
                            multi_needed_eps.append(ep_obj.episode)

                    logger.log(
                        u"Multi-ep check result is multi_needed_eps: " + str(multi_needed_eps) + ", multi_not_needed_eps: " + str(
                            multi_not_needed_eps), logger.DEBUG)

                    if not multi_needed_eps:
                        logger.log(
                            u"All of these episodes were covered by another multi-episode nzbs, ignoring this multi-ep result",
                            logger.DEBUG)
                        continue

                    # don't bother with the single result if we're going to get it with a multi result
                    for ep_obj in multi_results.episodes:
                        multi_results[ep_obj.episode] = multi_results
                        if ep_obj.episode in found_results[cur_provider.name]:
                            logger.log(
                                u"A needed multi-episode result overlaps with a single-episode result for ep #" + str(
                                    ep_obj.episode) + ", removing the single-episode results from the list", logger.DEBUG)
                            del found_results[cur_provider.name][ep_obj.episode]

            # of all the single ep results narrow it down to the best one for each episode
            final_results += set(multi_results.values())
            for cur_ep in found_results[cur_provider.name]:
                if cur_ep in (MULTI_EP_RESULT, SEASON_RESULT):
                    continue

                if not found_results[cur_provider.name][cur_ep]:
                    continue

                # if all results were rejected move on to the next episode
                best_result = pickBestResult(found_results[cur_provider.name][cur_ep], show)
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

            # check that we got all the episodes we wanted first before doing a match and snatch
            wanted_ep_count = 0
            for wanted_ep in episodes:
                for result in final_results:
                    if wanted_ep in result.episodes and isFinalResult(result):
                        wanted_ep_count += 1

            # make sure we search every provider for results unless we found everything we wanted
            if wanted_ep_count == len(episodes):
                break

        if not did_search:
            logger.log(u"No NZB/Torrent providers found or enabled in the sickrage config for backlog searches. \
            Please check your settings.",
                       logger.WARNING)

        # Remove provider from thread name before return results
        threading.currentThread().name = original_thread_name

        if self.manual_search:
            # If results in manual search return True, else False
            return any(manual_search_results)
        else:
            return final_results
