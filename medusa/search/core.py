# coding=utf-8

"""Search core module."""
from __future__ import division
from __future__ import unicode_literals

import datetime
import itertools
import logging
import operator
import os
import threading
import time

from medusa import (
    app,
    common,
    db,
    failed_history,
    history,
    name_cache,
    notifiers,
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
from medusa.logger.adapters.style import CustomBraceAdapter
from medusa.network_timezones import app_timezone
from medusa.show import naming

from six import iteritems, itervalues

log = CustomBraceAdapter(logging.getLogger(__name__))
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
            with open(file_name, u'wb') as file_out:
                file_out.write(result.extra_info[0])

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
    for cur_ep_obj in result.episodes:
        with cur_ep_obj.lock:
            if is_first_best_match(result):
                cur_ep_obj.status = SNATCHED_BEST
                cur_ep_obj.quality = result.quality
            else:
                cur_ep_obj.status = end_status
                cur_ep_obj.quality = result.quality
            # Reset all others fields to the snatched status
            # New snatch by default doesn't have nfo/tbn
            cur_ep_obj.hasnfo = False
            cur_ep_obj.hastbn = False

            # We can't reset location because we need to know what we are replacing
            # cur_ep_obj.location = ''

            # Release name and group are parsed in PP
            cur_ep_obj.release_name = ''
            cur_ep_obj.release_group = ''

            # Need to reset subtitle settings because it's a different file
            cur_ep_obj.subtitles = list()
            cur_ep_obj.subtitles_searchcount = 0
            cur_ep_obj.subtitles_lastsearch = u'0001-01-01 00:00:00'

            # Need to store the correct is_proper. Not use the old one
            cur_ep_obj.is_proper = is_proper
            cur_ep_obj.version = 0

            cur_ep_obj.manually_searched = result.manually_searched

            sql_l.append(cur_ep_obj.get_sql())

        if cur_ep_obj.status != common.DOWNLOADED:
            notifiers.notify_snatch(cur_ep_obj, result)

            if app.USE_TRAKT and app.TRAKT_SYNC_WATCHLIST:
                trakt_data.append((cur_ep_obj.season, cur_ep_obj.episode))
                log.info(
                    u'Adding {0} {1} to Trakt watchlist',
                    result.series.name,
                    episode_num(cur_ep_obj.season, cur_ep_obj.episode),
                )

    if trakt_data:
        data_episode = notifiers.trakt_notifier.trakt_episode_data_generate(trakt_data)
        if data_episode:
            notifiers.trakt_notifier.update_watchlist(result.series, data_episode=data_episode, update=u'add')

    if sql_l:
        main_db_con = db.DBConnection()
        main_db_con.mass_action(sql_l)

    return True


def filter_results(results):
    """
    Filter wanted results out of a list of search results for a show.

    :param results: list of result objects
    :return: list of wanted result objects
    """
    results = results if isinstance(results, list) else [results]
    wanted_results = []

    # find the best result for the current episode
    for cur_result in results:
        assert cur_result.series, 'Every SearchResult object should have a series object available at this point.'

        # Skip the result if search delay is enabled for the provider
        if delay_search(cur_result):
            continue

        # Every SearchResult object should have a show attribute available at this point.
        series_obj = cur_result.series

        # build the black and white list
        if series_obj.is_anime and series_obj.release_groups:
            if not series_obj.release_groups.is_valid(cur_result):
                continue

        log.info('Quality of {0} is {1}', cur_result.name, Quality.qualityStrings[cur_result.quality])

        allowed_qualities, preferred_qualities = series_obj.current_qualities
        if cur_result.quality not in allowed_qualities + preferred_qualities:
            log.debug('{0} is an unwanted quality, rejecting it', cur_result.name)
            continue

        wanted_episodes = series_obj.want_episodes(
            cur_result.actual_season,
            cur_result.actual_episodes,
            cur_result.quality,
            download_current_quality=cur_result.download_current_quality,
            search_type=cur_result.search_type)

        if not wanted_episodes:
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

        wanted_results.append(cur_result)

    if wanted_results:
        log.debug(u'Found wanted results.')
    else:
        log.debug(u'No wanted results found.')

    return wanted_results


def sort_results(results):
    """Sort results based on show specific preferences."""
    wanted_results = []
    if not results:
        log.debug(u'No results to sort.')
        return wanted_results

    sorted_results = sorted(results, key=operator.attrgetter('quality'), reverse=True)
    log.debug(u'Sorting the following results: {0}', [x.name for x in sorted_results])

    preferred_words = []
    if app.PREFERRED_WORDS:
        preferred_words = [word.lower() for word in app.PREFERRED_WORDS]
    undesired_words = []
    if app.UNDESIRED_WORDS:
        undesired_words = [word.lower() for word in app.UNDESIRED_WORDS]

    def percentage(percent, whole):
        return (percent * whole) / 100.0

    initial_score = 100.0
    for result in sorted_results:
        score = initial_score

        if wanted_results:
            allowed_qualities, preferred_qualities = result.series.current_qualities
            if Quality.is_higher_quality(wanted_results[0][0].quality, result.quality,
                                         allowed_qualities, preferred_qualities):
                log.debug(u'Rewarding release {0} (higher quality)', result.name)
                score += percentage(10, score)
                initial_score = score

        if result.proper_tags and (not wanted_results or
                                   wanted_results[0][0].quality == result.quality):
            log.debug(u'Rewarding release {0} (repack/proper/real/rerip)', result.name)
            # Stop at max. 4 proper tags
            for _tag in result.proper_tags[:4]:
                score += percentage(2, score)

        if any(word in result.name.lower() for word in undesired_words):
            log.debug(u'Penalizing release {0} (contains undesired word(s))', result.name)
            score -= percentage(20, score)

        if any(word in result.name.lower() for word in preferred_words):
            log.debug(u'Rewarding release {0} (contains preferred word(s))', result.name)
            score += percentage(20, score)

        wanted_results.append((result, score))
        wanted_results.sort(key=operator.itemgetter(1), reverse=True)

    header = '{0:<6} {1}'.format('Score', 'Release')
    log.debug(
        u'Computed result scores:'
        u'\n{header}'
        u'\n{results}',
        {
            'header': header,
            'results': '\n'.join(
                '{score:<6.2f} {name}'.format(score=item[1], name=item[0].name)
                for item in wanted_results
            )
        }
    )

    return [result[0] for result in wanted_results]


def pick_result(wanted_results):
    """Pick the first result out of a list of wanted candidates."""
    candidates = sort_results(wanted_results)
    if not candidates:
        log.debug(u'No results to pick from.')
        return None

    best_result = candidates[0]
    log.info(u'Picked {0} as the best result.', best_result.name)

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
        'SELECT status, quality, season, episode, manually_searched '
        'FROM tv_episodes '
        'WHERE indexer = ? '
        ' AND showid = ?'
        ' AND season > 0'
        ' AND airdate > ?',
        [series_obj.indexer, series_obj.series_id, from_date.toordinal()]
    )

    # check through the list of statuses to see if we want any
    for episode in sql_results:
        cur_status, cur_quality = int(episode['status'] or UNSET), int(episode['quality'] or Quality.NA)
        should_search, should_search_reason = Quality.should_search(
            cur_status, cur_quality, series_obj, episode['manually_searched']
        )
        if not should_search:
            continue
        else:
            log.debug(
                u'Searching for {show} {ep}. Reason: {reason}', {
                    u'show': series_obj.name,
                    u'ep': episode_num(episode['season'], episode['episode']),
                    u'reason': should_search_reason,
                }
            )

        ep_obj = series_obj.get_episode(episode['season'], episode['episode'])
        ep_obj.wanted_quality = [
            quality
            for quality in all_qualities
            if Quality.is_higher_quality(
                cur_quality, quality, allowed_qualities, preferred_qualities
            )
        ]
        wanted.append(ep_obj)

    return wanted


def search_for_needed_episodes(scheduler_start_time, force=False):
    """Search providers for needed episodes.

    :param force: run the search even if no episodes are needed
    :param scheduler_start_time: timestamp of the start of the search scheduler
    :return: list of found episodes
    """
    show_list = app.showList
    from_date = datetime.date.fromordinal(1)
    episodes = []

    for cur_show in show_list:
        if cur_show.paused:
            log.debug(
                u'Not checking for needed episodes of {0} because the show is paused',
                cur_show.name,
            )
            continue
        episodes.extend(wanted_episodes(cur_show, from_date))

    if not episodes and not force:
        # nothing wanted so early out, ie: avoid whatever arbitrarily
        # complex thing a provider cache update entails, for example,
        # reading rss feeds
        return []

    providers = enabled_providers(u'daily')
    if not providers:
        log.warning(
            u'No NZB/Torrent providers found or enabled in the application config for daily searches.'
            u' Please check your settings'
        )
        return []

    original_thread_name = threading.currentThread().name
    log.info(u'Using daily search providers')

    for cur_provider in providers:
        threading.currentThread().name = u'{thread} :: [{provider}]'.format(
            thread=original_thread_name, provider=cur_provider.name
        )
        cur_provider.cache.update_cache(scheduler_start_time)

    single_results = {}
    multi_results = []
    for cur_provider in providers:
        threading.currentThread().name = u'{thread} :: [{provider}]'.format(
            thread=original_thread_name, provider=cur_provider.name
        )
        try:
            found_results = cur_provider.cache.find_needed_episodes(episodes)
        except AuthException as error:
            log.error(u'Authentication error: {0}', ex(error))
            continue

        # pick a single result for each episode, respecting existing results
        for episode_no, results in iteritems(found_results):
            if results[0].series.paused:
                log.debug(u'Skipping {0} because the show is paused.', results[0].series.name)
                continue

            # if all results were rejected move on to the next episode
            wanted_results = filter_results(results)
            if not wanted_results:
                log.debug(u'All found results for {0} were rejected.', results[0].series.name)
                continue

            best_result = pick_result(wanted_results)

            if episode_no in (SEASON_RESULT, MULTI_EP_RESULT):
                multi_results.append(best_result)
            else:
                # if it's already in the list (from another provider) and
                # the newly found quality is no better then skip it
                if episode_no in single_results:
                    allowed_qualities, preferred_qualities = results[0].series.current_qualities
                    if not Quality.is_higher_quality(single_results[episode_no].quality,
                                                     best_result.quality, allowed_qualities,
                                                     preferred_qualities):
                        continue

                single_results[episode_no] = best_result

    threading.currentThread().name = original_thread_name

    return combine_results(multi_results, list(itervalues(single_results)))


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
                log.debug("DELAY: First result in cache doesn't have a valid date, skipping provider.")
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
    manual_search_results = []
    multi_results = []
    single_results = []

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
        threading.currentThread().name = '{original_thread_name} :: [{provider}]'.format(
            original_thread_name=original_thread_name, provider=cur_provider.name
        )

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
                search_results = []
                needed_eps = episodes

                if not manual_search:
                    cache_search_results = cur_provider.search_results_in_cache(episodes)
                    if cache_search_results:
                        cache_found_results = list_results_for_provider(cache_search_results, found_results, cur_provider)
                        multi_results, single_results = collect_candidates(
                            cache_found_results, cur_provider, multi_results, single_results
                        )
                        found_eps = itertools.chain(*(result.episodes for result in multi_results + single_results))
                        needed_eps = [ep for ep in episodes if ep not in found_eps]

                # We only search if we didn't get any useful results from cache
                if needed_eps:
                    log.debug(u'Could not find all candidates in cache, searching provider.')
                    search_results = cur_provider.find_search_results(series_obj, needed_eps, search_mode, forced_search,
                                                                      down_cur_quality, manual_search, manual_search_type)
                    # Update the list found_results
                    found_results = list_results_for_provider(search_results, found_results, cur_provider)
                    multi_results, single_results = collect_candidates(
                        found_results, cur_provider, multi_results, single_results
                    )
                    found_eps = itertools.chain(*(result.episodes for result in multi_results + single_results))
                    needed_eps = [ep for ep in episodes if ep not in found_eps]

            except AuthException as error:
                log.error(u'Authentication error: {0!r}', error)
                break

            if not needed_eps and found_results:
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
                log.debug(u'Fallback season pack search initiated')
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

    # Remove provider from thread name before return results
    threading.currentThread().name = original_thread_name

    if manual_search:
        # If results in manual search return True, else False
        return any(manual_search_results)
    else:
        return combine_results(multi_results, single_results)


def collect_candidates(found_results, provider, multi_results, single_results):
    """Collect candidates for episode, multi-episode or season results."""
    # Collect candidates for multi-episode or season results
    multi_results = collect_multi_candidates(found_results[provider.name], multi_results)

    # Collect candidates for single-episode results
    single_results = collect_single_candidates(found_results[provider.name], single_results)

    return multi_results, single_results


def list_results_for_provider(search_results, found_results, provider):
    """
    Add results for this provider to the search_results dict.

    The structure is based on [provider_name][episode_number][search_result]
    :param search_results: New dictionary with search results for this provider
    :param found_results: Dictionary with existing per provider search results
    :param provider: Provider object
    :return: Updated dict found_results
    """
    for cur_ep in search_results:
        if cur_ep in found_results[provider.name]:
            found_results[provider.name][cur_ep] += search_results[cur_ep]
        else:
            found_results[provider.name][cur_ep] = search_results[cur_ep]

        # Sort the list by seeders if possible
        if provider.provider_type == u'torrent' or getattr(provider, u'torznab', None):
            found_results[provider.name][cur_ep].sort(key=lambda d: int(d.seeders), reverse=True)

    return found_results


def collect_multi_candidates(candidates, results):
    """Collect mutli-episode and season result candidates."""
    multi_results = list(results)
    new_candidates = []

    multi_candidates = (candidate for result, candidate in iteritems(candidates)
                        if result in (SEASON_RESULT, MULTI_EP_RESULT))
    multi_candidates = list(itertools.chain(*multi_candidates))
    if multi_candidates:
        new_candidates = filter_results(multi_candidates)

    return multi_results + new_candidates


def collect_single_candidates(candidates, results):
    """
    Collect single-episode result candidates.

    :param candidates: A list of SearchResult objects we just parsed, which we want to evaluate against the already
    collected list of results.
    :param results: The existing list of valid results.
    """
    single_results = list(results)
    new_candidates = []

    # of all the single-ep results narrow it down to the best one for each episode
    for episode in candidates:
        if episode in (MULTI_EP_RESULT, SEASON_RESULT):
            continue

        # if all results were rejected move on to the next episode
        wanted_results = filter_results(candidates[episode])
        if not wanted_results:
            continue

        result_candidates = []
        for i, candidate in enumerate(single_results):
            if episode in candidate.actual_episodes:
                result_candidates.append(candidate)
                del single_results[i]

        best_result = pick_result(result_candidates + wanted_results)
        new_candidates.append(best_result)

    return single_results + new_candidates


def combine_results(multi_results, single_results):
    """Combine single and multi-episode results, filtering out overlapping results."""
    log.debug(u'Combining single and multi-episode results')
    result_candidates = []

    multi_results = sort_results(multi_results)
    for candidate in multi_results:
        if result_candidates:
            # check if these eps are already covered by another multi-result
            multi_needed_eps = []
            multi_not_needed_eps = []
            for ep_obj in candidate.episodes:
                for result in result_candidates:
                    if ep_obj in result.episodes:
                        multi_not_needed_eps.append(ep_obj.episode)
                    else:
                        multi_needed_eps.append(ep_obj.episode)

            log.debug(u'Multi-ep check result is multi_needed_eps: {0}, multi_not_needed_eps: {1}',
                      multi_needed_eps,
                      multi_not_needed_eps)

            if not multi_needed_eps:
                log.debug(
                    u'All of these episodes were covered by another multi-episode result,'
                    u' ignoring this multi-episode result'
                )
                continue

        log.debug(u'Adding {0} to multi-episode result candidates', candidate.name)
        result_candidates.append(candidate)

    # If there aren't any single results we can return early
    if not single_results:
        return result_candidates

    for multi_result in result_candidates:
        # remove the single result if we're going to get it with a multi-result
        for ep_obj in multi_result.episodes:
            for i, result in enumerate(single_results):
                if ep_obj in result.episodes:
                    log.debug(
                        u'A needed multi-episode result overlaps with a single-episode result'
                        u' for episode {0}, removing the single-episode results from the list',
                        ep_obj.episode,
                    )
                    del single_results[i]

    return single_results + result_candidates
