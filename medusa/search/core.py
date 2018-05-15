# coding=utf-8

"""Search core module."""
from __future__ import division
from __future__ import unicode_literals

import datetime
import logging
import os
import threading
import time
from builtins import str

from medusa import (
    app,
    common,
    db,
    failed_history,
    history,
    name_cache,
    notifiers,
    nzb_splitter,
    ui,
)
from medusa.clients import torrent
from medusa.clients.nzb import (
    nzbget,
    sab,
)
from medusa.common import (
    MULTI_EP_RESULT,
    Quality,
    SEASON_RESULT,
    SNATCHED,
    SNATCHED_BEST,
    SNATCHED_PROPER,
    UNSET,
)
from medusa.helper.common import (
    enabled_providers,
    episode_num,
)
from medusa.helper.exceptions import (
    AuthException,
    ex,
)
from medusa.helpers import chmod_as_parent
from medusa.helpers.utils import to_timestamp
from medusa.logger.adapters.style import BraceAdapter
from medusa.network_timezones import app_timezone
from medusa.providers.generic_provider import GenericProvider
from medusa.show import naming

from six import itervalues

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


def _download_result(result):
    """
    Download a result to the appropriate black hole folder.

    :param result: SearchResult instance to download.
    :return: boolean, True on success
    """
    res_provider = result.provider
    if res_provider is None:
        log.error(u'Invalid provider name - this is a coding error, report it please')
        return False

    # nzbs with an URL can just be downloaded from the provider
    if result.result_type == u'nzb':
        new_result = res_provider.download_result(result)
    # if it's an nzb data result
    elif result.result_type == u'nzbdata':

        # get the final file path to the nzb
        file_name = os.path.join(app.NZB_DIR, result.name + u'.nzb')

        log.info(u'Saving NZB to {0}', file_name)

        new_result = True

        # save the data to disk
        try:
            with open(file_name, u'w') as fileOut:
                fileOut.write(result.extra_info[0])

            chmod_as_parent(file_name)

        except EnvironmentError as e:
            log.error(u'Error trying to save NZB to black hole: {0}', ex(e))
            new_result = False
    elif result.result_type == u'torrent':
        new_result = res_provider.download_result(result)
    else:
        log.error(u'Invalid provider type - this is a coding error, report it please')
        new_result = False

    return new_result


def snatch_episode(result):
    """
    Snatch a result that has been found.

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
        log.debug(u'Found proper tags for {0}. Snatching as PROPER', result.name)
        is_proper = True
        end_status = SNATCHED_PROPER
    else:
        end_status = SNATCHED

    # Binsearch.info requires you to download the nzb through a post.
    if result.provider.kind() == 'BinSearchProvider':
        result.result_type = 'nzbdata'
        nzb_data = result.provider.download_nzb_for_post(result)
        result.extra_info.append(nzb_data)

        if not nzb_data:
            log.warning('Error trying to get the nzb data from provider binsearch, no data returned')
            return False

    # NZBs can be sent straight to SAB or saved to disk
    if result.result_type in (u'nzb', u'nzbdata'):
        if app.NZB_METHOD == u'blackhole':
            result_downloaded = _download_result(result)
        elif app.NZB_METHOD == u'sabnzbd':
            result_downloaded = sab.send_nzb(result)
        elif app.NZB_METHOD == u'nzbget':
            result_downloaded = nzbget.sendNZB(result, is_proper)
        else:
            log.error(u'Unknown NZB action specified in config: {0}', app.NZB_METHOD)
            result_downloaded = False

    # Torrents can be sent to clients or saved to disk
    elif result.result_type == u'torrent':
        # torrents are saved to disk when blackhole mode
        if app.TORRENT_METHOD == u'blackhole':
            result_downloaded = _download_result(result)
        else:
            if not result.content and not result.url.startswith(u'magnet:'):
                if result.provider.login():
                    if result.provider.kind() == 'TorznabProvider':
                        result.url = result.provider.get_redirect_url(result.url)

                    if not result.url.startswith(u'magnet:'):
                        result.content = result.provider.get_content(result.url)

            if result.content or result.url.startswith(u'magnet:'):
                client = torrent.get_client_class(app.TORRENT_METHOD)()
                result_downloaded = client.send_torrent(result)
            else:
                log.warning(u'Torrent file content is empty: {0}', result.name)
                result_downloaded = False
    else:
        log.error(u'Unknown result type, unable to download it: {0!r}', result.result_type)
        result_downloaded = False

    if not result_downloaded:
        return False

    if app.USE_FAILED_DOWNLOADS:
        failed_history.log_snatch(result)

    ui.notifications.message(u'Episode snatched', result.name)

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
            # Reset all others fields to the snatched status
            # New snatch by default doesn't have nfo/tbn
            curEpObj.hasnfo = False
            curEpObj.hastbn = False

            # We can't reset location because we need to know what we are replacing
            # curEpObj.location = ''

            # Release name and group are parsed in PP
            curEpObj.release_name = ''
            curEpObj.release_group = ''

            # Need to reset subtitle settings because it's a different file
            curEpObj.subtitles = list()
            curEpObj.subtitles_searchcount = 0
            curEpObj.subtitles_lastsearch = u'0001-01-01 00:00:00'

            # Need to store the correct is_proper. Not use the old one
            curEpObj.is_proper = True if result.proper_tags else False
            curEpObj.version = 0

            curEpObj.manually_searched = result.manually_searched

            sql_l.append(curEpObj.get_sql())

        if curEpObj.splitted_status_status != common.DOWNLOADED:
            notify_message = curEpObj.formatted_filename(u'%SN - %Sx%0E - %EN - %QN')
            if all([app.SEEDERS_LEECHERS_IN_NOTIFY, result.seeders not in (-1, None),
                    result.leechers not in (-1, None)]):
                notifiers.notify_snatch(u'{0} with {1} seeders and {2} leechers from {3}'.format
                                        (notify_message, result.seeders,
                                         result.leechers, result.provider.name), is_proper)
            else:
                notifiers.notify_snatch(u'{0} from {1}'.format(notify_message, result.provider.name), is_proper)

            if app.USE_TRAKT and app.TRAKT_SYNC_WATCHLIST:
                trakt_data.append((curEpObj.season, curEpObj.episode))
                log.info(
                    u'Adding {0} {1} to Trakt watchlist',
                    result.series.name,
                    episode_num(curEpObj.season, curEpObj.episode),
                )

    if trakt_data:
        data_episode = notifiers.trakt_notifier.trakt_episode_data_generate(trakt_data)
        if data_episode:
            notifiers.trakt_notifier.update_watchlist(result.series, data_episode=data_episode, update=u'add')

    if sql_l:
        main_db_con = db.DBConnection()
        main_db_con.mass_action(sql_l)

    return True


def pick_best_result(results):  # pylint: disable=too-many-branches
    """
    Find the best result out of a list of search results for a show.

    :param results: list of result objects
    :return: best result object
    """
    results = results if isinstance(results, list) else [results]

    log.debug(u'Picking the best result out of {0}', [x.name for x in results])

    best_result = None

    # find the best result for the current episode
    for cur_result in results:
        assert cur_result.series, 'Every SearchResult object should have a series object available at this point.'

        # Every SearchResult object should have a show attribute available at this point.
        series_obj = cur_result.series

        # build the black and white list
        if series_obj.is_anime:
            if not series_obj.release_groups.is_valid(cur_result):
                continue

        log.info(u'Quality of {0} is {1}', cur_result.name, Quality.qualityStrings[cur_result.quality])

        allowed_qualities, preferred_qualities = series_obj.current_qualities

        if cur_result.quality not in allowed_qualities + preferred_qualities:
            log.debug(u'{0} is an unwanted quality, rejecting it', cur_result.name)
            continue

        wanted_ep = True

        if cur_result.actual_episodes:
            wanted_ep = False
            for episode in cur_result.actual_episodes:
                if series_obj.want_episode(cur_result.actual_season, episode, cur_result.quality,
                                           cur_result.forced_search, cur_result.download_current_quality,
                                           search_type=cur_result.search_type):
                    wanted_ep = True

        if not wanted_ep:
            continue

        # If doesnt have min seeders OR min leechers then discard it
        if cur_result.seeders not in (-1, None) and cur_result.leechers not in (-1, None) \
            and hasattr(cur_result.provider, u'minseed') and hasattr(cur_result.provider, u'minleech') \
            and (int(cur_result.seeders) < int(cur_result.provider.minseed) or
                 int(cur_result.leechers) < int(cur_result.provider.minleech)):
            log.info(
                u'Discarding torrent because it does not meet the minimum provider setting '
                u'S:{0} L:{1}. Result has S:{2} L:{3}',
                cur_result.provider.minseed,
                cur_result.provider.minleech,
                cur_result.seeders,
                cur_result.leechers,
            )
            continue

        ignored_words = series_obj.show_words().ignored_words
        required_words = series_obj.show_words().required_words
        found_ignored_word = naming.contains_at_least_one_word(cur_result.name, ignored_words)
        found_required_word = naming.contains_at_least_one_word(cur_result.name, required_words)

        if ignored_words and found_ignored_word:
            log.info(u'Ignoring {0} based on ignored words filter: {1}', cur_result.name, found_ignored_word)
            continue

        if required_words and not found_required_word:
            log.info(u'Ignoring {0} based on required words filter: {1}', cur_result.name, required_words)
            continue

        if not naming.filter_bad_releases(cur_result.name, parse=False):
            continue

        if hasattr(cur_result, u'size'):
            if app.USE_FAILED_DOWNLOADS and failed_history.has_failed(cur_result.name, cur_result.size,
                                                                      cur_result.provider.name):
                log.info(u'{0} has previously failed, rejecting it', cur_result.name)
                continue

        preferred_words = []
        if app.PREFERRED_WORDS:
            preferred_words = [_.lower() for _ in app.PREFERRED_WORDS]
        undesired_words = []
        if app.UNDESIRED_WORDS:
            undesired_words = [_.lower() for _ in app.UNDESIRED_WORDS]

        if not best_result:
            best_result = cur_result
        if Quality.is_higher_quality(best_result.quality, cur_result.quality, allowed_qualities, preferred_qualities):
            best_result = cur_result
        elif best_result.quality == cur_result.quality:
            if any(ext in cur_result.name.lower() for ext in preferred_words):
                log.info(u'Preferring {0} (preferred words)', cur_result.name)
                best_result = cur_result
            if cur_result.proper_tags:
                log.info(u'Preferring {0} (repack/proper/real/rerip over nuked)', cur_result.name)
                best_result = cur_result
            if any(ext in best_result.name.lower() for ext in undesired_words) and not any(ext in cur_result.name.lower() for ext in undesired_words):
                log.info(u'Unwanted release {0} (contains undesired word(s))', cur_result.name)
                best_result = cur_result

    if best_result:
        log.debug(u'Picked {0} as the best', best_result.name)
    else:
        log.debug(u'No result picked.')

    return best_result


def is_first_best_match(result):
    """
    Check if the given result is a best quality match and if we want to stop searching providers here.

    :param result: to check
    :return: True if the result is the best quality match else False
    """
    log.debug(u'Checking if we should stop searching for a better quality for for episode {0}', result.name)

    series_obj = result.episodes[0].series

    _, preferred_qualities = series_obj.current_qualities
    # Don't pass allowed because we only want to check if this quality is wanted preferred.
    return Quality.wanted_quality(result.quality, [], preferred_qualities)


def wanted_episodes(series_obj, from_date):
    """
    Get a list of episodes that we want to download.

    :param series_obj: Series these episodes are from
    :param from_date: Search from a certain date
    :return: list of wanted episodes
    """
    wanted = []
    allowed_qualities, preferred_qualities = series_obj.current_qualities
    all_qualities = list(set(allowed_qualities + preferred_qualities))

    log.debug(u'Seeing if we need anything from {0}', series_obj.name)
    con = db.DBConnection()

    sql_results = con.select(
        'SELECT status, season, episode, manually_searched '
        'FROM tv_episodes '
        'WHERE indexer = ? '
        ' AND showid = ?'
        ' AND season > 0'
        ' and airdate > ?',
        [series_obj.indexer, series_obj.series_id, from_date.toordinal()]
    )

    # check through the list of statuses to see if we want any
    for result in sql_results:
        _, cur_quality = common.Quality.split_composite_status(int(result[b'status'] or UNSET))
        should_search, should_search_reason = Quality.should_search(result[b'status'], series_obj, result[b'manually_searched'])
        if not should_search:
            continue
        else:
            log.debug(
                u'Searching for {show} {ep}. Reason: {reason}', {
                    u'show': series_obj.name,
                    u'ep': episode_num(result[b'season'], result[b'episode']),
                    u'reason': should_search_reason,
                }
            )
        ep_obj = series_obj.get_episode(result[b'season'], result[b'episode'])
        ep_obj.wanted_quality = [i for i in all_qualities if i > cur_quality and i != Quality.UNKNOWN]
        wanted.append(ep_obj)

    return wanted


def search_for_needed_episodes(force=False):
    """
    Check providers for details on wanted episodes.

    :return: episodes we have a search hit for
    """
    found_results = {}

    show_list = app.showList
    from_date = datetime.date.fromordinal(1)
    episodes = []

    for cur_show in show_list:
        if cur_show.paused:
            log.debug(u'Not checking for needed episodes of {0} because the show is paused', cur_show.name)
            continue
        episodes.extend(wanted_episodes(cur_show, from_date))

    if not episodes and not force:
        # nothing wanted so early out, ie: avoid whatever arbitrarily
        # complex thing a provider cache update entails, for example,
        # reading rss feeds
        return list(itervalues(found_results))

    original_thread_name = threading.currentThread().name

    providers = enabled_providers(u'daily')

    if not providers:
        log.warning(u'No NZB/Torrent providers found or enabled in the application config for daily searches.'
                    u' Please check your settings')
        return list(itervalues(found_results))

    log.info(u'Using daily search providers')
    for cur_provider in providers:
        threading.currentThread().name = u'{thread} :: [{provider}]'.format(thread=original_thread_name,
                                                                            provider=cur_provider.name)
        cur_provider.cache.update_cache()

    for cur_provider in providers:
        threading.currentThread().name = u'{thread} :: [{provider}]'.format(thread=original_thread_name,
                                                                            provider=cur_provider.name)
        try:
            cur_found_results = cur_provider.search_rss(episodes)
        except AuthException as error:
            log.error(u'Authentication error: {0}', ex(error))
            continue

        # pick a single result for each episode, respecting existing results
        for cur_ep in cur_found_results:
            if not cur_ep.series or cur_ep.series.paused:
                log.debug(u'Skipping {0} because the show is paused ', cur_ep.pretty_name())
                continue

            best_result = pick_best_result(cur_found_results[cur_ep])

            # if all results were rejected move on to the next episode
            if not best_result:
                log.debug(u'All found results for {0} were rejected.', cur_ep.pretty_name())
                continue

            # if it's already in the list (from another provider) and the newly found quality is no better then skip it
            if cur_ep in found_results and best_result.quality <= found_results[cur_ep].quality:
                continue

            # Skip the result if search delay is enabled for the provider.
            if delay_search(best_result):
                continue

            found_results[cur_ep] = best_result

    threading.currentThread().name = original_thread_name

    return list(itervalues(found_results))


def delay_search(best_result):
    """Delay the search by ignoring the best result, when search delay is enabled for this provider.

    If the providers attribute enable_search_delay is enabled for this provider and it's younger then then it's
    search_delay time (minutes) skip it. For this we need to check if the result has already been
    stored in the provider cache db, and if it's still younger then the providers attribute search_delay.
    :param best_result: SearchResult object.
    :return: True if we want to skipp this result.
    """
    cur_provider = best_result.provider
    if cur_provider.enable_search_delay and cur_provider.search_delay:  # In minutes
        cur_ep = best_result.episodes[0]
        log.debug('DELAY: Provider {provider} delay enabled, with an expiration of {delay} hours',
                  {'provider': cur_provider.name, 'delay': round(cur_provider.search_delay / 60, 1)})

        from medusa.search.manual import get_provider_cache_results
        results = get_provider_cache_results(
            cur_ep.series, show_all_results=False, perform_search=False,
            season=cur_ep.season, episode=cur_ep.episode, manual_search_type='episode'
        )

        if results.get('found_items'):
            # If date_added is missing we put it at the end of the list
            results['found_items'].sort(key=lambda d: d['date_added'] or datetime.datetime.now(app_timezone))

            first_result = results['found_items'][0]
            date_added = first_result['date_added']
            # Some results in cache have date_added as 0
            if not date_added:
                log.debug('DELAY: First result in cache doesn\'t have a valid date, skipping provider.')
                return False

            timestamp = to_timestamp(date_added)
            if timestamp + cur_provider.search_delay * 60 > time.time():
                # The provider's delay cooldown time hasn't expired yet. We're holding back the snatch.
                log.debug(
                    'DELAY: Holding back best result {best_result} over {first_result} for provider {provider}.'
                    ' The provider is waiting {search_delay_minutes} hours, before accepting the release.'
                    ' Still {hours_left} to go.', {
                        'best_result': best_result.name,
                        'first_result': first_result['name'],
                        'provider': cur_provider.name,
                        'search_delay_minutes': round(cur_provider.search_delay / 60, 1),
                        'hours_left': round((cur_provider.search_delay - (time.time() - timestamp) / 60) / 60, 1)
                    }
                )
                return True
            else:
                log.debug('DELAY: Provider {provider}, found a result in cache, and the delay has expired. '
                          'Time of first result: {first_result}',
                          {'provider': cur_provider.name, 'first_result': date_added})
        else:
            # This should never happen.
            log.debug(
                'DELAY: Provider {provider}, searched cache but could not get any results for: {series} {season_ep}',
                {'provider': cur_provider.name, 'series': best_result.series.name,
                 'season_ep': episode_num(cur_ep.season, cur_ep.episode)})
    return False


def search_providers(series_obj, episodes, forced_search=False, down_cur_quality=False,
                     manual_search=False, manual_search_type=u'episode'):
    """
    Walk providers for information on shows.

    :param series_obj: Show we are looking for
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

    # build name cache for show
    name_cache.build_name_cache(series_obj)

    original_thread_name = threading.currentThread().name

    if manual_search:
        log.info(u'Using manual search providers')
        providers = enabled_providers(u'manualsearch')
    else:
        log.info(u'Using backlog search providers')
        providers = enabled_providers(u'backlog')

    if not providers:
        log.warning(u'No NZB/Torrent providers found or enabled in the application config for {0} searches.'
                    u' Please check your settings', 'manual' if manual_search else 'backlog')

    threading.currentThread().name = original_thread_name

    for cur_provider in providers:
        threading.currentThread().name = original_thread_name + u' :: [' + cur_provider.name + u']'

        if cur_provider.anime_only and not series_obj.is_anime:
            log.debug(u'{0} is not an anime, skipping', series_obj.name)
            continue

        found_results[cur_provider.name] = {}

        search_count = 0
        search_mode = cur_provider.search_mode

        # Always search for episode when manually searching when in sponly
        if search_mode == u'sponly' and (forced_search or manual_search):
            search_mode = u'eponly'

        if manual_search and manual_search_type == u'season':
            search_mode = u'sponly'

        while True:
            search_count += 1

            if search_mode == u'eponly':
                log.info(u'Performing episode search for {0}', series_obj.name)
            else:
                log.info(u'Performing season pack search for {0}', series_obj.name)

            try:
                search_results = cur_provider.find_search_results(series_obj, episodes, search_mode, forced_search,
                                                                  down_cur_quality, manual_search, manual_search_type)
            except AuthException as error:
                log.error(u'Authentication error: {0}', ex(error))
                break

            if search_results:
                # make a list of all the results for this provider
                for cur_ep in search_results:
                    if cur_ep in found_results[cur_provider.name]:
                        found_results[cur_provider.name][cur_ep] += search_results[cur_ep]
                    else:
                        found_results[cur_provider.name][cur_ep] = search_results[cur_ep]

                    # Sort the list by seeders if possible
                    if cur_provider.provider_type == u'torrent' or getattr(cur_provider, u'torznab', None):
                        found_results[cur_provider.name][cur_ep].sort(key=lambda d: int(d.seeders), reverse=True)

                break
            elif not cur_provider.search_fallback or search_count == 2:
                break

            # Don't fallback when doing manual season search
            if manual_search_type == u'season':
                break

            if search_mode == u'sponly':
                log.debug(u'Fallback episode search initiated')
                search_mode = u'eponly'
            else:
                log.debug(u'Fallback season pack search initiate')
                search_mode = u'sponly'

        # skip to next provider if we have no results to process
        if not found_results[cur_provider.name]:
            continue

        # Update the cache if a manual search is being run
        if manual_search:
            # Let's create a list with episodes that we where looking for
            if manual_search_type == u'season':
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
            best_season_result = pick_best_result(found_results[cur_provider.name][SEASON_RESULT])

        highest_quality_overall = 0
        for cur_episode in found_results[cur_provider.name]:
            for cur_result in found_results[cur_provider.name][cur_episode]:
                if cur_result.quality != Quality.UNKNOWN and cur_result.quality > highest_quality_overall:
                    highest_quality_overall = cur_result.quality
        log.debug(u'The highest quality of any match is {0}', Quality.qualityStrings[highest_quality_overall])

        # see if every episode is wanted
        if best_season_result:
            searched_seasons = {str(x.season) for x in episodes}

            # get the quality of the season nzb
            season_quality = best_season_result.quality
            log.debug(u'The quality of the season {0} is {1}',
                      best_season_result.provider.provider_type,
                      Quality.qualityStrings[season_quality])
            main_db_con = db.DBConnection()
            selection = main_db_con.select(
                'SELECT episode '
                'FROM tv_episodes '
                'WHERE indexer = ?'
                ' AND showid = ?'
                ' AND ( season IN ( {0} ) )'.format(','.join(searched_seasons)),
                [series_obj.indexer, series_obj.series_id]
            )
            all_eps = [int(x[b'episode']) for x in selection]
            log.debug(u'Episode list: {0}', all_eps)

            all_wanted = True
            any_wanted = False
            for cur_ep_num in all_eps:
                for season in {x.season for x in episodes}:
                    if not series_obj.want_episode(season, cur_ep_num, season_quality, down_cur_quality):
                        all_wanted = False
                    else:
                        any_wanted = True

            # if we need every ep in the season and there's nothing better then
            # just download this and be done with it (unless single episodes are preferred)
            if all_wanted and best_season_result.quality == highest_quality_overall:
                log.info(u'All episodes in this season are needed, downloading {0} {1}',
                         best_season_result.provider.provider_type,
                         best_season_result.name)
                ep_objs = []
                for cur_ep_num in all_eps:
                    for season in {x.season for x in episodes}:
                        ep_objs.append(series_obj.get_episode(season, cur_ep_num))
                best_season_result.episodes = ep_objs

                # Remove provider from thread name before return results
                threading.currentThread().name = original_thread_name

                return [best_season_result]

            elif not any_wanted:
                log.debug(u'No episodes in this season are needed at this quality, ignoring {0} {1}',
                          best_season_result.provider.provider_type,
                          best_season_result.name)
            else:
                # Some NZB providers (e.g. Jackett) can also download torrents, but torrents cannot be split like NZB
                if (best_season_result.provider.provider_type == GenericProvider.NZB and
                        not best_season_result.url.endswith(GenericProvider.TORRENT)):
                    log.debug(u'Breaking apart the NZB and adding the individual ones to our results')

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
                    log.info(u'Adding multi-ep result for full-season torrent.'
                             u' Undesired episodes can be skipped in torrent client if desired!')
                    ep_objs = []
                    for cur_ep_num in all_eps:
                        for season in {x.season for x in episodes}:
                            ep_objs.append(series_obj.get_episode(season, cur_ep_num))
                    best_season_result.episodes = ep_objs

                    if MULTI_EP_RESULT in found_results[cur_provider.name]:
                        found_results[cur_provider.name][MULTI_EP_RESULT].append(best_season_result)
                    else:
                        found_results[cur_provider.name][MULTI_EP_RESULT] = [best_season_result]

        # go through multi-ep results and see if we really want them or not, get rid of the rest
        multi_results = {}
        if MULTI_EP_RESULT in found_results[cur_provider.name]:
            for _multi_result in found_results[cur_provider.name][MULTI_EP_RESULT]:
                log.debug(u'Seeing if we want to bother with multi-episode result {0}', _multi_result.name)

                # Filter result by ignore/required/whitelist/blacklist/quality, etc
                multi_result = pick_best_result(_multi_result)
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

                log.debug(u'Single-ep check result is needed_eps: {0}, not_needed_eps: {1}',
                          needed_eps, not_needed_eps)

                if not needed_eps:
                    log.debug(u'All of these episodes were covered by single episode results,'
                              u' ignoring this multi-episode result')
                    continue

                # check if these eps are already covered by another multi-result
                multi_needed_eps = []
                multi_not_needed_eps = []
                for ep_obj in multi_result.episodes:
                    if ep_obj.episode in multi_results:
                        multi_not_needed_eps.append(ep_obj.episode)
                    else:
                        multi_needed_eps.append(ep_obj.episode)

                log.debug(u'Multi-ep check result is multi_needed_eps: {0}, multi_not_needed_eps: {1}',
                          multi_needed_eps,
                          multi_not_needed_eps)

                if not multi_needed_eps:
                    log.debug(
                        u'All of these episodes were covered by another multi-episode nzb, '
                        u'ignoring this multi-ep result'
                    )
                    continue

                # don't bother with the single result if we're going to get it with a multi result
                for ep_obj in multi_result.episodes:
                    multi_results[ep_obj.episode] = multi_result
                    if ep_obj.episode in found_results[cur_provider.name]:
                        log.debug(
                            u'A needed multi-episode result overlaps with a single-episode result for episode {0},'
                            u' removing the single-episode results from the list',
                            ep_obj.episode,
                        )
                        del found_results[cur_provider.name][ep_obj.episode]

        # of all the single ep results narrow it down to the best one for each episode
        final_results += set(multi_results.values())
        for cur_ep in found_results[cur_provider.name]:
            if cur_ep in (MULTI_EP_RESULT, SEASON_RESULT):
                continue

            if not found_results[cur_provider.name][cur_ep]:
                continue

            # if all results were rejected move on to the next episode
            best_result = pick_best_result(found_results[cur_provider.name][cur_ep])
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
                # Skip the result if search delay is enabled for the provider.
                if not delay_search(best_result):
                    final_results += [best_result]

    # Remove provider from thread name before return results
    threading.currentThread().name = original_thread_name

    if manual_search:
        # If results in manual search return True, else False
        return any(manual_search_results)
    else:
        return final_results
