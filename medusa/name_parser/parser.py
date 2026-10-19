# coding=utf-8

"""Parser module which contains NameParser class."""
from __future__ import unicode_literals

import logging
import os
import re
import time
from collections import OrderedDict

import guessit

from medusa import (
    app,
    common,
    db,
    helpers,
    scene_exceptions,
    scene_numbering,
)
from medusa.helper.common import episode_num
from medusa.indexers.api import indexerApi
from medusa.indexers.exceptions import (
    IndexerEpisodeNotFound,
    IndexerError,
    IndexerException,
)
from medusa.logger.adapters.style import BraceAdapter
from medusa.name_parser.cache import BaseCache
from medusa.name_parser.series_name import normalize_series_name_for_comparison
from medusa.search.release_matcher import (
    MIN_EPISODE_TITLE_LENGTH,
    normalize_release_text,
)

from six import iteritems, text_type

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class NameParser(object):
    """Responsible to parse release names."""

    def __init__(self, series=None, try_indexers=False, naming_pattern=False, parse_method=None,
                 allow_multi_season=False):
        """Initialize the class.

        :param series:
        :type series: medusa.tv.Series
        :param try_indexers:
        :type try_indexers: bool
        :param naming_pattern:
        :type naming_pattern: bool
        :param parse_method: normal or anime
        :type parse_method: str or None
        :param allow_multi_season:
        :type allow_multi_season: bool
        """
        self.series = series
        self.try_indexers = try_indexers
        self.naming_pattern = naming_pattern
        self.allow_multi_season = allow_multi_season
        self.show_type = parse_method or ('anime' if series and series.is_anime else 'normal')

    @staticmethod
    def _get_episodes_by_air_date(result):
        airdate = result.air_date.toordinal()
        main_db_con = db.DBConnection()
        sql_result = main_db_con.select(
            'SELECT season, episode FROM tv_episodes WHERE indexer = ? AND showid = ? AND airdate = ?',
            [result.series.indexer, result.series.series_id, airdate])

        return sql_result

    def _parse_air_by_date(self, result):
        """
        Parse anime season episode results.

        Translate scene episode and season numbering to indexer numbering,
        using an air date to indexer season/episode translation.

        :param result: Guessit parse result object.
        :return: tuple of found indexer episode numbers and indexer season numbers
        """
        log.debug('Series {name} is air by date', {'name': result.series.name})

        new_episode_numbers = []
        new_season_numbers = []

        episode_by_air_date = self._get_episodes_by_air_date(result)

        season_number = None
        episode_numbers = []

        if episode_by_air_date:
            season_number = int(episode_by_air_date[0]['season'])
            episode_numbers = [int(episode_by_air_date[0]['episode'])]

            # Use the next query item if we have multiple results
            # and the current one is a special episode (season 0)
            if season_number == 0 and len(episode_by_air_date) > 1:
                season_number = int(episode_by_air_date[1]['season'])
                episode_numbers = [int(episode_by_air_date[1]['episode'])]

            log.debug(
                'Database info for series {name}: Season: {season} Episode(s): {episodes}', {
                    'name': result.series.name,
                    'season': season_number,
                    'episodes': episode_numbers
                }
            )

        if season_number is None or not episode_numbers:
            log.debug('Series {name} has no season or episodes, using indexer',
                      {'name': result.series.name})

            indexer_api_params = indexerApi(result.series.indexer).api_params.copy()
            indexer_api = indexerApi(result.series.indexer).indexer(**indexer_api_params)
            try:
                if result.series.lang:
                    indexer_api_params['language'] = result.series.lang

                tv_episode = indexer_api[result.series.indexerid].aired_on(result.air_date)[0]

                season_number = int(tv_episode['seasonnumber'])
                episode_numbers = [int(tv_episode['episodenumber'])]
                log.debug(
                    'Indexer info for series {name}: {ep}', {
                        'name': result.series.name,
                        'ep': episode_num(season_number, episode_numbers[0]),
                    }
                )
            except IndexerEpisodeNotFound:
                log.warning(
                    'Unable to find episode with date {date} for series {name}. Skipping',
                    {'date': result.air_date, 'name': result.series.name}
                )
                episode_numbers = []
            except IndexerError as error:
                log.warning(
                    'Unable to contact {indexer_api.name}: {error!r}',
                    {'indexer_api': indexer_api, 'error': error}
                )
                episode_numbers = []
            except IndexerException as error:
                log.warning(
                    'Indexer exception: {indexer_api.name}: {error!r}',
                    {'indexer_api': indexer_api, 'error': error}
                )
                episode_numbers = []

        for episode_number in episode_numbers:
            season = season_number
            episode = episode_number

            (idx_season, idx_episode) = scene_numbering.get_indexer_numbering(
                result.series,
                episode_number,
                season_number
            )

            if idx_season is not None:
                season = idx_season
            if idx_episode is not None:
                episode = idx_episode

            new_season_numbers.append(season)
            new_episode_numbers.append(episode)

        return new_episode_numbers, new_season_numbers

    @staticmethod
    def _parse_anime(result):
        """
        Parse anime season episode results.

        Translate scene episode and season numbering to indexer numbering,
        using anime scen episode/season translation tables to indexer episode/season.

        :param result: Guessit parse result object.
        :return: tuple of found indexer episode numbers and indexer season numbers
        """
        log.debug('Series {name} is anime', {'name': result.series.name})

        new_episode_numbers = []
        new_season_numbers = []
        new_absolute_numbers = []

        # Try to translate the scene series name to a scene number.
        # For example Jojo's bizarre Adventure - Diamond is unbreakable, will use xem, to translate the
        # "diamond is unbreakable" exception back to season 4 of it's "master" table. This will be used later
        # to translate it to an absolute number, which in turn can be translated to an indexer SxEx.
        # For example Diamond is unbreakable - 26 -> Season 4 -> Absolute number 100 -> tvdb S03E26
        season_exception = None
        if result.season_number is None:
            season_exception = scene_exceptions.get_season_from_name(result.series, result.series_name)

        if result.ab_episode_numbers:
            for absolute_episode in result.ab_episode_numbers:
                abs_ep = absolute_episode

                # Don't assume that scene_exceptions season is the same as indexer season.
                # E.g.: [HorribleSubs] Cardcaptor Sakura Clear Card - 08 [720p].mkv thetvdb s04, thexem s02
                if season_exception is not None or result.series.is_scene:
                    # Get absolute number from custom numbering (1), XEM (2) or indexer (3)
                    idx_abs_ep = scene_numbering.get_indexer_abs_numbering(
                        result.series, abs_ep, season=season_exception
                    )
                    if idx_abs_ep is not None:
                        abs_ep = idx_abs_ep

                new_absolute_numbers.append(abs_ep)

                # Translate the absolute episode number, back to the indexers season and episode.
                (season, episodes) = helpers.get_all_episodes_from_absolute_number(result.series, [abs_ep])
                if season and episodes:

                    new_episode_numbers.extend(episodes)
                    new_season_numbers.append(season)

                    if season_exception is not None:
                        log.debug(
                            'Detected a season scene exception [{series_name} -> {scene_season}] without a '
                            'season number in the title, '
                            'translating the episode #{abs} to indexer #{indexer_absolute}: {ep}',
                            {'series_name': result.series_name, 'scene_season': season_exception,
                             'abs': absolute_episode, 'indexer_absolute': abs_ep,
                             'ep': episode_num(season, episodes[0])}
                        )
                    elif result.series.is_scene:
                        log.debug(
                            'Scene numbering enabled anime series {name} using indexer numbering #{absolute}: {ep}',
                            {'name': result.series.name, 'season': season, 'absolute': abs_ep,
                             'ep': episode_num(season, episodes[0])}
                        )
                    else:
                        log.debug(
                            'Anime series {name} using indexer numbering #{absolute}: {ep}',
                            {'name': result.series.name, 'season': season, 'absolute': abs_ep,
                             'ep': episode_num(season, episodes[0])}
                        )

        # It's possible that we map a parsed result to an anime series,
        # but the result is not detected/parsed as an anime. In that case, we're using the result.episode_numbers.
        elif result.episode_numbers:
            for episode_number in result.episode_numbers:
                season = result.season_number
                episode = episode_number

                idx_abs_ep = scene_numbering.get_indexer_abs_numbering(result.series, episode, season=season)
                if idx_abs_ep is not None:
                    new_absolute_numbers.append(idx_abs_ep)

                (idx_season, idx_episode) = scene_numbering.get_indexer_numbering(
                    result.series,
                    episode_number,
                    result.season_number
                )

                if idx_season is not None:
                    season = idx_season
                if idx_episode is not None:
                    episode = idx_episode

                new_season_numbers.append(season)
                new_episode_numbers.append(episode)

                if result.series.is_scene:
                    log.debug(
                        'Scene numbering enabled anime {name} using indexer numbering: {ep}',
                        {'name': result.series.name, 'absolute': idx_abs_ep, 'ep': episode_num(season, episode)}
                    )
                else:
                    log.debug(
                        'Anime series {name} using using indexer numbering #{absolute}: {ep}',
                        {'name': result.series.name, 'absolute': idx_abs_ep, 'ep': episode_num(season, episode)}
                    )
        else:
            # Treat it as a season pack.
            new_season_numbers.append(season_exception or result.season_number)

        return new_episode_numbers, new_season_numbers, new_absolute_numbers

    @staticmethod
    def _parse_series(result):
        new_episode_numbers = []
        new_season_numbers = []
        new_absolute_numbers = []

        ex_season = scene_exceptions.get_season_from_name(result.series, result.series_name) or result.season_number
        # GuessIt may treat a release year as season (e.g. ``(1991)`` → season 1991).
        # Season ranges arrive as lists (e.g. S01-04 → [1, 2, 3, 4]); skip those.
        if ex_season is not None and not isinstance(ex_season, (list, tuple)):
            try:
                if int(ex_season) >= 1900:
                    ex_season = None
            except (TypeError, ValueError):
                ex_season = None
        if ex_season is None:
            ex_season = 1
            log.info(
                "For the show {name} we could not parse a season number. We did match the title, so we'll asume season 1",
                {'name': result.series.name}
            )

        # Prefer episode-title identification over parsed episode numbers.
        # A wrong release number must not win when the title uniquely identifies
        # the library episode (avoids inversions like ``05 - Episode Title`` -> E05).
        title_match, title_ambiguous = NameParser._match_episode_by_title(
            result.series,
            result.guess.get('episode_title'),
            preferred_season=ex_season,
            preferred_episodes=result.episode_numbers,
        )
        if title_match is not None:
            if result.episode_numbers and title_match.episode not in result.episode_numbers:
                log.info(
                    'Overriding parsed numbering {parsed} for {series} using episode '
                    'title {title!r} -> {ep}',
                    {
                        'parsed': result.episode_numbers,
                        'series': result.series.name,
                        'title': title_match.name,
                        'ep': episode_num(title_match.season, title_match.episode),
                    }
                )
            else:
                log.info(
                    'Resolved {series} by episode title {title!r} to {ep} '
                    '(episode title takes priority over parsed numbering {parsed})',
                    {
                        'series': result.series.name,
                        'title': title_match.name,
                        'ep': episode_num(title_match.season, title_match.episode),
                        'parsed': result.episode_numbers,
                    }
                )
            return [title_match.episode], [title_match.season], []

        if title_ambiguous:
            raise InvalidNameException(
                'Episode title {title!r} for {series} matched multiple library episodes '
                'and parsed numbering {parsed} could not safely disambiguate them. '
                'Refusing to trust the release number alone.'.format(
                    title=result.guess.get('episode_title'),
                    series=result.series.name,
                    parsed=result.episode_numbers,
                )
            )

        if result.episode_numbers:
            for episode_number in result.episode_numbers:
                season = ex_season
                episode = episode_number

                (idx_season, idx_episode) = scene_numbering.get_indexer_numbering(
                    result.series,
                    episode_number,
                    ex_season
                )

                if idx_season is not None:
                    season = idx_season
                if idx_episode is not None:
                    episode = idx_episode

                new_season_numbers.append(season)
                new_episode_numbers.append(episode)
        else:
            # No episode numbers. Treat it like a season pack.
            if isinstance(ex_season, (list, tuple)):
                new_season_numbers.extend(ex_season)
            else:
                new_season_numbers.append(ex_season)

        return new_episode_numbers, new_season_numbers, new_absolute_numbers

    @staticmethod
    def _normalize_episode_title(value):
        """Normalize an episode title for equality comparisons."""
        return normalize_release_text(value)

    @staticmethod
    def _match_episode_by_title(series, episode_title, preferred_season=None, preferred_episodes=None):
        """Match a library episode by title, optionally disambiguated by number.

        Episode titles take priority over parsed numbers when the match is unique.
        If several episodes share the same title, preferred season/episode numbers
        are used only to disambiguate among those title matches.

        :return: (episode_or_none, ambiguous)
        :rtype: tuple[object|None, bool]
        """
        if not series or not episode_title:
            return None, False

        if isinstance(episode_title, (list, tuple)):
            episode_title = ' '.join(text_type(part) for part in episode_title if part)

        normalized_title = NameParser._normalize_episode_title(episode_title)
        if len(normalized_title) < MIN_EPISODE_TITLE_LENGTH:
            return None, False

        try:
            candidates = series.get_all_episodes()
        except Exception as error:
            log.debug(
                'Unable to load episodes for title matching on {series}: {error}',
                {'series': series.name, 'error': error}
            )
            return None, False

        matches = [
            episode for episode in candidates
            if episode.season != 0
            and NameParser._normalize_episode_title(episode.name) == normalized_title
        ]
        if not matches:
            return None, False

        if len(matches) == 1:
            return matches[0], False

        preferred_episode_set = set(preferred_episodes or [])
        narrowed = matches
        if preferred_episode_set:
            narrowed = [episode for episode in narrowed if episode.episode in preferred_episode_set]
        if preferred_season is not None:
            season_narrowed = [episode for episode in narrowed if episode.season == preferred_season]
            if len(season_narrowed) == 1:
                return season_narrowed[0], False
            if season_narrowed:
                narrowed = season_narrowed

        if len(narrowed) == 1:
            return narrowed[0], False

        log.info(
            'Episode title {title!r} for {series} matched {count} episodes; '
            'parsed numbering {parsed} could not disambiguate safely',
            {
                'title': episode_title,
                'series': series.name,
                'count': len(matches),
                'parsed': list(preferred_episode_set) if preferred_episode_set else None,
            }
        )
        return None, True

    @staticmethod
    def _parse_special(result):
        new_episode_numbers = []
        new_season_numbers = []

        episode_title = result.guess.get('episode_title')
        if not episode_title:
            log.info(
                '{name}: This episode is marked as a special. We could not find an episode title. And we need that to map it to an episode in the library.',
                {'name': result.series.name}
            )
            return new_episode_numbers, new_season_numbers

        # Sanitize the episode title.
        episode_title = episode_title.lower()
        if episode_title.startswith('special'):
            episode_title = episode_title.split('special')[-1].strip()

        all_episodes = result.series.get_all_episodes(season=0)
        for special_episode in all_episodes:
            if special_episode.name.lower() == episode_title:
                new_season_numbers.append(0)
                new_episode_numbers.append(special_episode.episode)
                return new_episode_numbers, new_season_numbers

        return [], []

    @staticmethod
    def _display_series_name(name):
        """Return a single string for log/error output when GuessIt yields a list title."""
        if name is None:
            return None
        if isinstance(name, (list, tuple)):
            parts = [text_type(part) for part in name if part]
            return ', '.join(parts) if parts else None
        return text_type(name)

    @staticmethod
    def _prefer_longer_library_name(name, series_name, search_series):
        """Prefer a library show whose longer name is spelled out in the release.

        GuessIt truncates spin-off titles such as ``Show Name(s), Subtitle - 01 - Episode``
        to ``Show Name`` and the name cache then resolves the parent show. When the
        release basename contains the full name of a library show that starts with the
        parsed title, that longer name is the intended series.
        """
        if not series_name or not isinstance(series_name, text_type) or not app.showList:
            return search_series

        parsed = normalize_series_name_for_comparison(series_name)
        if not parsed:
            return search_series

        basename = os.path.basename(name.replace('\\', '/'))
        normalized_release = normalize_series_name_for_comparison(basename)
        if not normalized_release:
            return search_series

        best_series = search_series
        best_length = len(normalize_series_name_for_comparison(search_series.name)) if search_series else len(parsed)

        for candidate in app.showList:
            candidate_name = normalize_series_name_for_comparison(candidate.name)
            if len(candidate_name) <= best_length or not candidate_name.startswith(parsed + ' '):
                continue
            if not re.search(r'(?:^|\s)' + re.escape(candidate_name) + r'(?:\s|$)', normalized_release):
                continue
            best_series = candidate
            best_length = len(candidate_name)

        if best_series is not search_series:
            log.debug(
                'Series resolution preferring {longer!r} over {shorter!r}: '
                'full name found in release {release!r}',
                {
                    'longer': best_series.name,
                    'shorter': search_series.name if search_series else series_name,
                    'release': basename,
                }
            )
        return best_series

    def _parse_string(self, name):
        guess = guessit.guessit(name, dict(show_type=self.show_type))

        result = self.to_parse_result(name, guess)

        log.debug(
            'Series resolution input={input!r} series_name={series_name!r} title={title!r} '
            'season={season!r} episode={episode!r}',
            {
                'input': name,
                'series_name': result.series_name,
                'title': guess.get('title'),
                'season': result.season_number,
                'episode': result.episode_numbers,
            }
        )

        search_series = helpers.get_show(result.series_name, self.try_indexers) if not self.naming_pattern else None

        if not search_series and not self.naming_pattern:
            title = guess.get('title')
            alias = guess.get('alias')
            year = guess.get('year')

            # Only fall back for the exact year alias produced by CreateAliasWithCountryOrYear.
            if title and year and alias == '{title} {year}'.format(title=title, year=year):
                log.debug(
                    'Series resolution retrying get_show with title={title!r} after year alias miss',
                    {'title': title}
                )
                candidate = helpers.get_show(title, self.try_indexers)
                candidate_year = None
                candidate_has_year = False
                if candidate:
                    for raw_candidate_year in (candidate.imdb_year, candidate.start_year):
                        if raw_candidate_year in (None, ''):
                            continue
                        candidate_has_year = True
                        try:
                            candidate_year = int(raw_candidate_year)
                            break
                        except (TypeError, ValueError):
                            continue
                years_match = False
                if candidate and not candidate_has_year:
                    years_match = True
                elif candidate and candidate_year is not None:
                    years_match = candidate_year == int(year)
                if candidate and years_match:
                    search_series = candidate
                elif candidate:
                    # Parent-folder years (Show (2001)/...S17E01...) often disagree with the
                    # indexer start year. Enforce year equality only when the parsed year is
                    # part of the release basename (Show.Name.2026.S01E01).
                    basename = os.path.basename(name.replace('\\', '/'))
                    if str(year) not in basename:
                        log.debug(
                            'Series resolution accepting title={title!r} despite folder year '
                            'mismatch (parsed={parsed_year}, show={show_year})',
                            {
                                'title': title,
                                'parsed_year': year,
                                'show_year': candidate_year,
                            }
                        )
                        search_series = candidate

        if not self.naming_pattern:
            search_series = self._prefer_longer_library_name(name, result.series_name, search_series)

        # confirm passed in show object indexer id matches result show object indexer id
        series_obj = None if search_series and self.series and search_series.indexerid != self.series.indexerid else search_series
        result.series = series_obj or self.series

        log.debug(
            'Series resolution get_show result for {series_name!r}: {series}',
            {
                'series_name': result.series_name,
                'series': result.series.name if result.series else None,
            }
        )

        # if this is a naming pattern test or result doesn't have a show object then return best result
        if not result.series or self.naming_pattern:
            return result

        new_episode_numbers = []
        new_season_numbers = []
        new_absolute_numbers = []

        # Try to map special episodes without an episode number using the episode title.
        if result.is_episode_special and not result.episode_numbers:
            new_episode_numbers, new_season_numbers = self._parse_special(result)

        # Prefer episode-title identification when the release carries a title but no
        # SxEx: works for air-by-date shows whose filenames use the episode name
        # (and often a rebroadcast date that is not the indexer airdate).
        elif (
            result.guess.get('episode_title')
            and not result.episode_numbers
        ):
            new_episode_numbers, new_season_numbers, new_absolute_numbers = self._parse_series(result)
            if (
                not new_episode_numbers
                and result.series.air_by_date
                and result.is_air_by_date
            ):
                new_episode_numbers, new_season_numbers = self._parse_air_by_date(result)

        # Air-by-date shows still often carry SxxExx plus a rebroadcast date
        # (e.g. Fr5.2010-01-24). Prefer explicit numbering when present.
        elif result.series.air_by_date and result.is_air_by_date and not result.episode_numbers:
            new_episode_numbers, new_season_numbers = self._parse_air_by_date(result)

        # Only real anime shows use absolute numbering. GuessIt often sets
        # absolute_episode for bare `` - 01 - `` tokens on non-anime shows
        # (e.g. ``Show Name - 01 - Guest``); that must not force anime parsing.
        elif result.series.is_anime:
            new_episode_numbers, new_season_numbers, new_absolute_numbers = self._parse_anime(result)

        else:
            new_episode_numbers, new_season_numbers, new_absolute_numbers = self._parse_series(result)

        # Remove None from the list of seasons, as we can't sort on that
        new_season_numbers = sorted({season for season in new_season_numbers if season is not None})

        if not new_season_numbers and not new_absolute_numbers:
            raise InvalidNameException('The result that was found ({result_name}) is not yet supported by Medusa '
                                       'and will be skipped. Sorry.'.format(result_name=result.original_name))

        # need to do a quick sanity check here ex. It's possible that we now have episodes
        # from more than one season (by tvdb numbering), and this is just too much
        # for the application, so we'd need to flag it.
        if len(new_season_numbers) > 1:
            raise InvalidNameException('Scene numbering results episodes from seasons {seasons}, (i.e. more than one) '
                                       'and Medusa does not support this. Sorry.'.format(seasons=new_season_numbers))

        # If guess it's possible that we'd have duplicate episodes too,
        # so lets eliminate them
        new_episode_numbers = sorted(set(new_episode_numbers))

        # maybe even duplicate absolute numbers so why not do them as well
        new_absolute_numbers = sorted(set(new_absolute_numbers))

        if new_absolute_numbers:
            result.ab_episode_numbers = new_absolute_numbers

        if new_episode_numbers:
            result.episode_numbers = new_episode_numbers

        if new_season_numbers:
            result.season_number = new_season_numbers[0]

        # Bare episode numbers without a season (e.g. ``Show - 56 - Title``) are
        # common for single-season shows. GuessIt may also set absolute_episode;
        # that must not leave season unset for post-processing.
        if result.season_number is None and result.episode_numbers:
            result.season_number = 1
            log.info(
                'Unable to parse season number for {name}, '
                'assuming season 1 for episode(s) {episodes}',
                {'name': result.series.name, 'episodes': result.episode_numbers}
            )

        if result.series.is_scene:
            log.debug(
                'Converted parsed result {original} into {result}',
                {'original': result.original_name, 'result': result}
            )

        return result

    @staticmethod
    def erase_cached_parse(indexer, indexer_id):
        """Remove all names from given indexer and indexer_id."""
        name_parser_cache.remove_by_indexer(indexer, indexer_id)

    def parse(self, name, cache_result=True, use_cache=True):
        """Parse the name into a ParseResult.

        :param name:
        :type name: str
        :param cache_result:
        :type cache_result: bool
        :param use_cache:
        :type use_cache: bool
        :return:
        :rtype: ParseResult
        """
        name = helpers.unicodify(name)

        if self.naming_pattern:
            cache_result = False

        if use_cache:
            cached = name_parser_cache.get(name)
            if cached:
                return cached

        start_time = time.time()
        result = self._parse_string(name)
        if result:
            result.total_time = time.time() - start_time

        self.assert_supported(result)

        if cache_result:
            name_parser_cache.add(name, result)
            log.debug('Parsed {name} into {result} and added to cache', {'name': name, 'result': result})
        else:
            log.debug('Parsed {name} into {result}', {'name': name, 'result': result})

        return result

    @staticmethod
    def assert_supported(result):
        """Whether or not the result is supported.

        :param result:
        :type result: ParseResult
        """
        if not result.series:
            parsed_name = NameParser._display_series_name(
                result.series_name or (result.guess.get('title') if result.guess else None)
            )
            log.debug(
                'Series resolution failed for input={input!r} series_name={series_name!r} '
                'title={title!r} season={season!r} episodes={episodes!r} parser_result={result}',
                {
                    'input': result.original_name,
                    'series_name': result.series_name,
                    'title': result.guess.get('title') if result.guess else None,
                    'season': result.season_number,
                    'episodes': result.episode_numbers,
                    'result': result,
                }
            )
            if parsed_name:
                message = 'Unable to resolve parsed show "{0}" to a series in Medusa'.format(parsed_name)
            else:
                message = 'Unable to resolve release to a series in Medusa'
            raise InvalidShowException(
                message,
                series_name=parsed_name,
                input_name=result.original_name,
            )

        log.debug(
            'Matched release {release} to a series in your database: {name} using guessit title: {title}',
            {'release': result.original_name, 'name': result.series.name, 'title': result.guess.get('title')}
        )

        if result.season_number is None and not result.episode_numbers and \
                result.air_date is None and not result.ab_episode_numbers and not result.series_name:
            raise InvalidNameException('Unable to parse {result.original_name}. No episode numbering info. '
                                       'Parser result: {result}'.format(result=result))

        if result.season_number is not None and not result.episode_numbers and \
                not result.ab_episode_numbers and result.is_episode_special:
            raise InvalidNameException('Discarding {result.original_name}. Season special is not supported yet. '
                                       'Parser result: {result}'.format(result=result))

    def to_parse_result(self, name, guess):
        """Guess the episode information from a given release name.

        Uses guessit and returns a dictionary with keys and values according to ParseResult
        :param name:
        :type name: str
        :param guess:
        :type guess: dict
        :return:
        :rtype: ParseResult
        """
        if not self.allow_multi_season:
            season_numbers = helpers.ensure_list(guess.get('season'))
            if len(season_numbers) > 1:
                raise InvalidNameException(
                    "Discarding result. Multi-season detected for '{name}': {guess}"
                    .format(name=name, guess=guess))

            versions = helpers.ensure_list(guess.get('version'))
            if len(versions) > 1:
                raise InvalidNameException(
                    "Discarding result. Multi-version detected for '{name}': {guess}"
                    .format(name=name, guess=guess))

        return ParseResult(guess, original_name=name, series_name=guess.get('alias') or guess.get('title'),
                           season_number=helpers.single_or_list(season_numbers, self.allow_multi_season),
                           episode_numbers=helpers.ensure_list(guess.get('episode')),
                           ab_episode_numbers=helpers.ensure_list(guess.get('absolute_episode')),
                           air_date=guess.get('date'), release_group=guess.get('release_group'),
                           proper_tags=helpers.ensure_list(guess.get('proper_tag')), version=guess.get('version', -1),
                           episode_details=helpers.ensure_list(guess.get('episode_details')))


class ParseResult(object):
    """Represent the release information for a given name."""

    def __init__(self, guess, series_name=None, season_number=None, episode_numbers=None, ab_episode_numbers=None,
                 air_date=None, release_group=None, proper_tags=None, version=None, original_name=None, episode_details=None):
        """Initialize the class.

        :param guess:
        :type guess: dict
        :param series_name:
        :type series_name: str
        :param season_number:
        :type season_number: int
        :param episode_numbers:
        :type episode_numbers: list of int
        :param ab_episode_numbers:
        :type ab_episode_numbers: list of int
        :param air_date:
        :type air_date: date
        :param release_group:
        :type release_group: str
        :param proper_tags:
        :type proper_tags: list of str
        :param version:
        :type version: int
        :param original_name:
        :type original_name: str
        :param episode_details:
        :type episode_details: list of str
        """
        self.original_name = original_name
        self.series_name = series_name
        self.season_number = season_number
        self.episode_numbers = episode_numbers if episode_numbers else []
        self.ab_episode_numbers = ab_episode_numbers if ab_episode_numbers else []
        self.quality = self.get_quality(guess)
        self.release_group = release_group
        self.air_date = air_date
        self.series = None
        self.version = version
        self.proper_tags = proper_tags
        self.guess = guess
        self.total_time = None
        self.episode_details = episode_details

    def __eq__(self, other):
        """Equal implementation.

        :param other:
        :return:
        :rtype: bool
        """
        return other and all([
            self.series_name == other.series_name,
            self.season_number == other.season_number,
            self.episode_numbers == other.episode_numbers,
            self.release_group == other.release_group,
            self.air_date == other.air_date,
            self.ab_episode_numbers == other.ab_episode_numbers,
            self.series == other.series,
            self.quality == other.quality,
            self.version == other.version,
            self.proper_tags == other.proper_tags,
            self.is_episode_special == other.is_episode_special,
            self.video_codec == other.video_codec
        ])

    def __str__(self):
        """String.

        :return:
        :rtype: str
        """
        obj = OrderedDict(self.guess, **dict(season=self.season_number,
                                             episode=self.episode_numbers,
                                             absolute_episode=self.ab_episode_numbers,
                                             quality=common.Quality.qualityStrings[self.quality],
                                             total_time=self.total_time))
        return helpers.canonical_name(obj, fmt='{key}: {value}', separator=', ')

    def to_dict(self):
        """Return an dict representation."""
        return OrderedDict(self.guess, **dict(season=self.season_number,
                                              episode=self.episode_numbers,
                                              absolute_episode=self.ab_episode_numbers,
                                              quality=common.Quality.qualityStrings[self.quality],
                                              total_time=self.total_time))

    # Python 2 compatibility
    __unicode__ = __str__

    def get_quality(self, guess, extend=False):
        """Return video quality from guess or name.

        :return:
        :rtype: Quality
        """
        quality = common.Quality.from_guessit(guess)
        if quality != common.Quality.UNKNOWN:
            return quality
        return common.Quality.name_quality(self.original_name, self.is_anime, extend)

    @property
    def is_air_by_date(self):
        """Whether or not this episode has air date.

        :return:
        :rtype: bool
        """
        return bool(self.air_date)

    @property
    def is_anime(self):
        """Whether or not this episode is an anime.

        :return:
        :rtype: bool
        """
        return bool(self.ab_episode_numbers)

    @property
    def is_episode_special(self):
        """Whether or not it represents a special episode.

        :return:
        :rtype: bool
        """
        return self.guess.get('episode_details') == 'Special'

    @property
    def video_codec(self):
        """Return video codec.

        :return:
        :rtype: str
        """
        return self.guess.get('video_codec')


class NameParserCache(BaseCache):
    """Name parser cache."""

    def remove_by_indexer(self, indexer, indexer_id):
        """Remove cache item given indexer and indexer_id."""
        with self.lock:
            to_remove = [
                cached_name
                for cached_name, cached_parsed_result in iteritems(self.cache)
                if cached_parsed_result.series.indexer == indexer
                and cached_parsed_result.series.indexerid == indexer_id
            ]
            for item in to_remove:
                del self.cache[item]
                log.debug('Removed cached parse result for {name}', {'name': item})


name_parser_cache = NameParserCache()


class InvalidNameException(Exception):
    """The given release name is not valid."""


class InvalidShowException(Exception):
    """The given show name could not be resolved to a series in Medusa."""

    def __init__(self, message, series_name=None, input_name=None):
        """Keep structured lookup context for post-process diagnostics."""
        super(InvalidShowException, self).__init__(message)
        self.series_name = series_name
        self.input_name = input_name
