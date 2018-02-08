# coding=utf-8

"""Proper finder module."""

from __future__ import unicode_literals

import datetime
import logging
import operator
import re
import threading
import time

from medusa import app, db, helpers
from medusa.common import Quality, cpu_presets
from medusa.helper.common import enabled_providers
from medusa.helper.exceptions import AuthException, ex
from medusa.logger.adapters.style import BraceAdapter
from medusa.name_parser.parser import InvalidNameException, InvalidShowException, NameParser
from medusa.search.core import pick_best_result, snatch_episode
from medusa.show.history import History

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class ProperFinder(object):  # pylint: disable=too-few-public-methods
    """Proper finder class."""

    def __init__(self):
        """Initialize the class."""
        self.amActive = False
        self.processed_propers = []
        self.ignore_processed_propers = False

    def run(self, force=False):  # pylint: disable=unused-argument
        """
        Start looking for new propers.

        :param force: Start even if already running (currently not used, defaults to False)
        """
        log.info('Beginning the search for new propers')

        if self.amActive:
            log.debug('Find propers is still running, not starting it again')
            return

        if app.forced_search_queue_scheduler.action.is_forced_search_in_progress():
            log.warning("Manual search is running. Can't start Find propers")
            return

        self.amActive = True

        # If force we should ignore existing processed propers
        self.ignore_processed_propers = False
        if force:
            self.ignore_processed_propers = True
            log.debug("Ignoring already processed propers as it's a forced search")

        log.info('Using proper search days: {search_days}', {'search_days': app.PROPERS_SEARCH_DAYS})

        propers = self._get_proper_results()

        if propers:
            self._download_propers(propers)

        self._set_last_proper_search(datetime.datetime.today().toordinal())

        run_at = ''
        if None is app.proper_finder_scheduler.start_time:
            run_in = app.proper_finder_scheduler.lastRun + \
                app.proper_finder_scheduler.cycleTime - datetime.datetime.now()
            hours, remainder = divmod(run_in.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            run_at = ', next check in approx. {0}'.format(
                '{0}h, {1}m'.format(hours, minutes) if 0 < hours else '{0}m, {1}s'.format(minutes, seconds))

        log.info('Completed the search for new propers{run_at}', {'run_at': run_at})

        self.amActive = False

    def _get_proper_results(self):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        """Retrieve a list of recently aired episodes, and search for these episodes in the different providers."""
        propers = {}

        # For each provider get the list of propers
        original_thread_name = threading.currentThread().name
        providers = enabled_providers('backlog')

        search_date = datetime.datetime.today() - datetime.timedelta(days=app.PROPERS_SEARCH_DAYS)
        main_db_con = db.DBConnection()
        if not app.POSTPONE_IF_NO_SUBS:
            # Get the recently aired (last 2 days) shows from DB
            search_q_params = ','.join('?' for _ in Quality.DOWNLOADED)
            recently_aired = main_db_con.select(
                b'SELECT indexer, showid, season, episode, status, airdate'
                b' FROM tv_episodes'
                b' WHERE airdate >= ?'
                b' AND status IN ({0})'.format(search_q_params),
                [search_date.toordinal()] + Quality.DOWNLOADED
            )
        else:
            # Get recently subtitled episodes (last 2 days) from DB
            # Episode status becomes downloaded only after found subtitles
            last_subtitled = search_date.strftime(History.date_format)
            recently_aired = main_db_con.select(b'SELECT indexer_id AS indexer, showid, season, episode FROM history '
                                                b"WHERE date >= ? AND action LIKE '%10'", [last_subtitled])

        if not recently_aired:
            log.info('No recently aired new episodes, nothing to search for')
            return []

        # Loop through the providers, and search for releases
        for cur_provider in providers:
            threading.currentThread().name = '{thread} :: [{provider}]'.format(thread=original_thread_name,
                                                                               provider=cur_provider.name)

            log.info('Searching for any new PROPER releases from {provider}', {'provider': cur_provider.name})

            try:
                cur_propers = cur_provider.find_propers(recently_aired)
            except AuthException as e:
                log.debug('Authentication error: {error}', {'error': ex(e)})
                continue

            # if they haven't been added by a different provider than add the proper to the list
            for proper in cur_propers:
                name = self._sanitize_name(proper.name)
                if name not in propers:
                    log.debug('Found new possible proper result: {name}', {'name': proper.name})
                    propers[name] = proper

        threading.currentThread().name = original_thread_name

        # take the list of unique propers and get it sorted by
        sorted_propers = sorted(propers.values(), key=operator.attrgetter('date'), reverse=True)
        final_propers = []

        # Keep only items from last PROPER_SEARCH_DAYS setting in processed propers:
        latest_proper = datetime.datetime.now() - datetime.timedelta(days=app.PROPERS_SEARCH_DAYS)
        self.processed_propers = [p for p in self.processed_propers if p.get('date') >= latest_proper]

        # Get proper names from processed propers
        processed_propers_names = [proper.get('name') for proper in self.processed_propers if proper.get('name')]

        for cur_proper in sorted_propers:

            if not self.ignore_processed_propers and cur_proper.name in processed_propers_names:
                log.debug(u'Proper already processed. Skipping: {proper_name}', {'proper_name': cur_proper.name})
                continue

            try:
                cur_proper.parse_result = NameParser().parse(cur_proper.name)
            except (InvalidNameException, InvalidShowException) as error:
                log.debug('{error}', {'error': error})
                continue

            if not cur_proper.parse_result.proper_tags:
                log.info('Skipping non-proper: {name}', {'name': cur_proper.name})
                continue

            if not cur_proper.series.episodes.get(cur_proper.parse_result.season_number) or \
                    any([ep for ep in cur_proper.parse_result.episode_numbers
                         if not cur_proper.series.episodes[cur_proper.parse_result.season_number].get(ep)]):
                log.info('Skipping proper for wrong season/episode: {name}', {'name': cur_proper.name})
                continue

            log.debug('Proper tags for {proper}: {tags}', {
                'proper': cur_proper.name,
                'tags': cur_proper.parse_result.proper_tags
            })

            if not cur_proper.parse_result.series_name:
                log.debug('Ignoring invalid show: {name}', {'name': cur_proper.name})
                if cur_proper.name not in processed_propers_names:
                    self.processed_propers.append({'name': cur_proper.name, 'date': cur_proper.date})
                continue

            if not cur_proper.parse_result.episode_numbers:
                log.debug('Ignoring full season instead of episode: {name}', {'name': cur_proper.name})
                if cur_proper.name not in processed_propers_names:
                    self.processed_propers.append({'name': cur_proper.name, 'date': cur_proper.date})
                continue

            log.debug('Successful match! Matched {original_name} to show {new_name}',
                      {'original_name': cur_proper.parse_result.original_name,
                       'new_name': cur_proper.parse_result.series.name
                       })

            # Map the indexerid in the db to the show's indexerid
            cur_proper.indexerid = cur_proper.parse_result.series.indexerid

            # Map the indexer in the db to the show's indexer
            cur_proper.indexer = cur_proper.parse_result.series.indexer

            # Map our Proper instance
            cur_proper.series = cur_proper.parse_result.series
            cur_proper.actual_season = cur_proper.parse_result.season_number \
                if cur_proper.parse_result.season_number is not None else 1
            cur_proper.actual_episodes = cur_proper.parse_result.episode_numbers
            cur_proper.release_group = cur_proper.parse_result.release_group
            cur_proper.version = cur_proper.parse_result.version
            cur_proper.quality = cur_proper.parse_result.quality
            cur_proper.content = None
            cur_proper.proper_tags = cur_proper.parse_result.proper_tags

            # filter release, in this case, it's just a quality gate. As we only send one result.
            best_result = pick_best_result(cur_proper)

            if not best_result:
                log.info('Rejected proper: {name}', {'name': cur_proper.name})
                if cur_proper.name not in processed_propers_names:
                    self.processed_propers.append({'name': cur_proper.name, 'date': cur_proper.date})
                continue

            # only get anime proper if it has release group and version
            if best_result.series.is_anime:
                if not best_result.release_group and best_result.version == -1:
                    log.info('Ignoring proper without release group and version: {name}', {'name': best_result.name})
                    if cur_proper.name not in processed_propers_names:
                        self.processed_propers.append({'name': cur_proper.name, 'date': cur_proper.date})
                    continue

            # check if we have the episode as DOWNLOADED
            main_db_con = db.DBConnection()
            sql_results = main_db_con.select(b"SELECT status, release_name "
                                             b"FROM tv_episodes WHERE indexer = ? "
                                             b"AND showid = ? AND season = ? "
                                             b"AND episode = ? AND status LIKE '%04'",
                                             [best_result.indexer,
                                              best_result.series.indexerid,
                                              best_result.actual_season,
                                              best_result.actual_episodes[0]])
            if not sql_results:
                log.info("Ignoring proper because this episode doesn't have 'DOWNLOADED' status: {name}", {
                    'name': best_result.name
                })
                continue

            # only keep the proper if we have already downloaded an episode with the same quality
            _, old_quality = Quality.split_composite_status(int(sql_results[0][b'status']))
            if old_quality != best_result.quality:
                log.info('Ignoring proper because quality is different: {name}', {'name': best_result.name})
                if cur_proper.name not in processed_propers_names:
                    self.processed_propers.append({'name': cur_proper.name, 'date': cur_proper.date})
                continue

            # only keep the proper if we have already downloaded an episode with the same codec
            release_name = sql_results[0][b'release_name']
            if release_name:
                release_name_guess = NameParser()._parse_string(release_name)
                current_codec = release_name_guess.video_codec
                # Ignore proper if codec differs from downloaded release codec
                if all([current_codec, best_result.parse_result.video_codec,
                        best_result.parse_result.video_codec != current_codec]):
                    log.info('Ignoring proper because codec is different: {name}', {'name': best_result.name})
                    if best_result.name not in processed_propers_names:
                        self.processed_propers.append({'name': best_result.name, 'date': best_result.date})
                    continue
                streaming_service = release_name_guess.guess.get(u'streaming_service')
                # Ignore proper if streaming service differs from downloaded release streaming service
                if best_result.parse_result.guess.get(u'streaming_service') != streaming_service:
                    log.info('Ignoring proper because streaming service is different: {name}',
                             {'name': best_result.name})
                    if best_result.name not in processed_propers_names:
                        self.processed_propers.append({'name': best_result.name, 'date': best_result.date})
                    continue
            else:
                log.debug("Coudn't find a release name in database. Skipping codec comparison for: {name}", {
                    'name': best_result.name
                })

            # check if we actually want this proper (if it's the right release group and a higher version)
            if best_result.series.is_anime:
                main_db_con = db.DBConnection()
                sql_results = main_db_con.select(
                    b'SELECT release_group, version '
                    b'FROM tv_episodes WHERE indexer = ? AND showid = ? '
                    b'AND season = ? AND episode = ?',
                    [best_result.indexer, best_result.series.indexerid, best_result.actual_season,
                     best_result.actual_episodes[0]])

                old_version = int(sql_results[0][b'version'])
                old_release_group = (sql_results[0][b'release_group'])

                if -1 < old_version < best_result.version:
                    log.info('Found new anime version {new} to replace existing version {old}: {name}',
                             {'old': old_version,
                              'new': best_result.version,
                              'name': best_result.name
                              })
                else:
                    log.info('Ignoring proper with the same or lower version: {name}', {'name': best_result.name})
                    if cur_proper.name not in processed_propers_names:
                        self.processed_propers.append({'name': best_result.name, 'date': best_result.date})
                    continue

                if old_release_group != best_result.release_group:
                    log.info('Ignoring proper from release group {new} instead of current group {old}',
                             {'new': best_result.release_group,
                              'old': old_release_group})
                    if best_result.name not in processed_propers_names:
                        self.processed_propers.append({'name': best_result.name, 'date': best_result.date})
                    continue

            # if the show is in our list and there hasn't been a proper already added for that particular episode
            # then add it to our list of propers
            if best_result.indexerid != -1 and (
                best_result.indexerid, best_result.actual_season, best_result.actual_episodes[0]
            ) not in map(operator.attrgetter('indexerid', 'actual_season', 'actual_episode'), final_propers):
                log.info('Found a desired proper: {name}', {'name': best_result.name})
                final_propers.append(best_result)

            if best_result.name not in processed_propers_names:
                self.processed_propers.append({'name': best_result.name, 'date': best_result.date})

        return final_propers

    def _download_propers(self, proper_list):
        """
        Download proper (snatch it).

        :param proper_list:
        """
        for cur_proper in proper_list:

            history_limit = datetime.datetime.today() - datetime.timedelta(days=30)

            main_db_con = db.DBConnection()
            history_results = main_db_con.select(
                b'SELECT resource FROM history '
                b'WHERE showid = ? '
                b'AND season = ? '
                b'AND episode = ? '
                b'AND quality = ? '
                b'AND date >= ? '
                b"AND (action LIKE '%02' OR action LIKE '%04' OR action LIKE '%09' OR action LIKE '%12')",
                [cur_proper.indexerid, cur_proper.actual_season, cur_proper.actual_episode, cur_proper.quality,
                 history_limit.strftime(History.date_format)])

            # make sure that none of the existing history downloads are the same proper we're trying to download
            # if the result exists in history already we need to skip it
            clean_proper_name = self._canonical_name(cur_proper.name, clear_extension=True)
            if any(clean_proper_name == self._canonical_name(cur_result[b'resource'], clear_extension=True)
                   for cur_result in history_results):
                log.debug('This proper {result!r} is already in history, skipping it', {'result': cur_proper.name})
                continue
            else:
                # make sure that none of the existing history downloads are the same proper we're trying to download
                clean_proper_name = self._canonical_name(cur_proper.name)
                if any(clean_proper_name == self._canonical_name(cur_result[b'resource'])
                       for cur_result in history_results):
                    log.debug('This proper {result!r} is already in history, skipping it', {'result': cur_proper.name})
                    continue

                cur_proper.create_episode_object()

                # snatch it
                snatch_episode(cur_proper)
                time.sleep(cpu_presets[app.CPU_PRESET])

    @staticmethod
    def _canonical_name(name, clear_extension=False):
        ignore_list = {'website', 'mimetype', 'parsing_time'} | {'container'} if clear_extension else {}
        return helpers.canonical_name(name, ignore_list=ignore_list).lower()

    @staticmethod
    def _sanitize_name(name):
        return re.sub(r'[._\-]', ' ', name).lower()

    @staticmethod
    def _set_last_proper_search(when):
        """Record last propersearch in DB.

        :param when: When was the last proper search
        """
        log.debug('Setting the last Proper search in the DB to {when}', {'when': when})

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(b'SELECT last_proper_search FROM info')

        if not sql_results:
            main_db_con.action(b'INSERT INTO info (last_backlog, last_indexer, last_proper_search) VALUES (?,?,?)',
                               [0, 0, str(when)])
        else:
            main_db_con.action(b'UPDATE info SET last_proper_search={0}'.format(when))

    @staticmethod
    def _get_last_proper_search():
        """Find last propersearch from DB."""
        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(b'SELECT last_proper_search FROM info')

        try:
            last_proper_search = datetime.date.fromordinal(int(sql_results[0][b'last_proper_search']))
        except Exception:
            return datetime.date.fromordinal(1)

        return last_proper_search
