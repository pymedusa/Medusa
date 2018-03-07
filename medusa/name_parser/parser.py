# coding=utf-8

"""Parser module which contains NameParser class."""
from __future__ import unicode_literals

import logging
import time
from builtins import object
from collections import OrderedDict

import guessit

from medusa import (
    common,
    db,
    helpers,
    scene_exceptions,
    scene_numbering,
)
from medusa.helper.common import episode_num
from medusa.indexers.indexer_api import indexerApi
from medusa.indexers.indexer_exceptions import (
    IndexerEpisodeNotFound,
    IndexerError,
    IndexerException,
)
from medusa.logger.adapters.style import BraceAdapter

from six import iteritems


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
        self.show_type = parse_method or ('anime' if series and series.is_anime else ('normal' if series else None))

    @staticmethod
    def _get_episodes_by_air_date(result):
        airdate = result.air_date.toordinal()
        main_db_con = db.DBConnection()
        sql_result = main_db_con.select(
            b'SELECT season, episode FROM tv_episodes WHERE indexer = ? AND showid = ? AND airdate = ?',
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
            season_number = int(episode_by_air_date[0][0])
            episode_numbers = [int(episode_by_air_date[0][1])]

            # Use the next query item if we have multiple results
            # and the current one is a special episode (season 0)
            if season_number == 0 and len(episode_by_air_date) > 1:
                season_number = int(episode_by_air_date[1][0])
                episode_numbers = [int(episode_by_air_date[1][1])]

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
                    'Unable to contact {indexer_api.name}: {error}',
                    {'indexer_api': indexer_api, 'error': error.message}
                )
                episode_numbers = []
            except IndexerException as error:
                log.warning(
                    'Indexer exception: {indexer_api.name}: {error}',
                    {'indexer_api': indexer_api, 'error': error.message}
                )
                episode_numbers = []

        for episode_number in episode_numbers:
            season = season_number
            episode = episode_number

            if result.series.is_scene:
                (season, episode) = scene_numbering.get_indexer_numbering(
                    result.series,
                    season_number,
                    episode_number,
                )
                log.debug(
                    'Scene numbering enabled series {name}, using indexer numbering: {ep}',
                    {'name': result.series.name, 'ep': episode_num(season, episode)}
                )
            new_episode_numbers.append(episode)
            new_season_numbers.append(season)

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
        log.debug('Scene numbering enabled series {name} is anime',
                  {'name': result.series.name})

        new_episode_numbers = []
        new_season_numbers = []
        new_absolute_numbers = []

        # Try to translate the scene series name to a scene number.
        # For example Jojo's bizarre Adventure - Diamond is unbreakable, will use xem, to translate the
        # "diamond is unbreakable" exception back to season 4 of it's "master" table. This will be used later
        # to translate it to an absolute number, which in turn can be translated to an indexer SxEx.
        # For example Diamond is unbreakable - 26 -> Season 4 -> Absolute number 100 -> tvdb S03E26
        scene_season = scene_exceptions.get_scene_exceptions_by_name(result.series_name)[0][1]

        if result.ab_episode_numbers:
            for absolute_episode in result.ab_episode_numbers:
                a = absolute_episode

                # Apparently we got a scene_season using the season scene exceptions. If we also do not have a season
                # parsed, guessit made a 'mistake' and it should have set the season with the value.
                # This is required for titles like: '[HorribleSubs].Kekkai.Sensen.&.Beyond.-.01.[1080p].mkv'
                #
                # Don't assume that scene_exceptions season is the same as indexer season.
                # E.g.: [HorribleSubs] Cardcaptor Sakura Clear Card - 08 [720p].mkv thetvdb s04, thexem s02
                if result.series.is_scene or (result.season_number is None and scene_season > 0):
                    a = scene_numbering.get_indexer_absolute_numbering(
                        result.series, absolute_episode, True, scene_season
                    )

                # Translate the absolute episode number, back to the indexers season and episode.
                (season, episode) = helpers.get_all_episodes_from_absolute_number(result.series, [a])

                if result.season_number is None and scene_season > 0:
                    log.debug(
                        'Detected a season scene exception [{series_name} -> {scene_season}] without a '
                        'season number in the title, '
                        'translating the episode absolute # [{scene_absolute}] to season #[{absolute_season}] and '
                        'episode #[{absolute_episode}].',
                        {'series_name': result.series_name, 'scene_season': scene_season, 'scene_absolute': a,
                         'absolute_season': season, 'absolute_episode': episode}
                    )
                else:
                    log.debug(
                        'Scene numbering enabled series {name} using indexer for absolute {absolute}: {ep}',
                        {'name': result.series.name, 'absolute': a, 'ep': episode_num(season, episode, 'absolute')}
                    )

                new_absolute_numbers.append(a)
                new_episode_numbers.extend(episode)
                new_season_numbers.append(season)

        # It's possible that we map a parsed result to an anime series,
        # but the result is not detected/parsed as an anime. In that case, we're using the result.episode_numbers.
        else:
            for episode_number in result.episode_numbers:
                season = result.season_number
                episode = episode_number
                a = helpers.get_absolute_number_from_season_and_episode(result.series, season, episode)
                if a:
                    new_absolute_numbers.append(a)
                    log.debug(
                        'Scene numbering enabled anime {name} using indexer with absolute {absolute}: {ep}',
                        {'name': result.series.name, 'absolute': a, 'ep': episode_num(season, episode, 'absolute')}
                    )

                new_episode_numbers.append(episode)
                new_season_numbers.append(season)

        return new_episode_numbers, new_season_numbers, new_absolute_numbers

    @staticmethod
    def _parse_series(result):
        new_episode_numbers = []
        new_season_numbers = []
        new_absolute_numbers = []

        for episode_number in result.episode_numbers:
            season = result.season_number
            episode = episode_number

            if result.series.is_scene:
                (season, episode) = scene_numbering.get_indexer_numbering(
                    result.series,
                    result.season_number,
                    episode_number
                )
                log.debug(
                    'Scene numbering enabled series {name} using indexer numbering: {ep}',
                    {'name': result.series.name, 'ep': episode_num(season, episode)}
                )

            new_episode_numbers.append(episode)
            new_season_numbers.append(season)

        return new_episode_numbers, new_season_numbers, new_absolute_numbers

    def _parse_string(self, name):
        guess = guessit.guessit(name, dict(show_type=self.show_type))
        result = self.to_parse_result(name, guess)

        search_series = helpers.get_show(result.series_name, self.try_indexers) if not self.naming_pattern else None

        # confirm passed in show object indexer id matches result show object indexer id
        series_obj = None if search_series and self.series and search_series.indexerid != self.series.indexerid else search_series
        result.series = series_obj or self.series

        # if this is a naming pattern test or result doesn't have a show object then return best result
        if not result.series or self.naming_pattern:
            return result

        new_episode_numbers = []
        new_season_numbers = []
        new_absolute_numbers = []

        # if we have an air-by-date show and the result is air-by-date,
        # then get the real season/episode numbers
        if result.series.air_by_date and result.is_air_by_date:
            new_episode_numbers, new_season_numbers = self._parse_air_by_date(result)

        elif result.series.is_anime or result.is_anime:
            new_episode_numbers, new_season_numbers, new_absolute_numbers = self._parse_anime(result)

        elif result.season_number and result.episode_numbers:
            new_episode_numbers, new_season_numbers, new_absolute_numbers = self._parse_series(result)

        # need to do a quick sanity check here ex. It's possible that we now have episodes
        # from more than one season (by tvdb numbering), and this is just too much
        # for the application, so we'd need to flag it.
        new_season_numbers = sorted(set(new_season_numbers))  # remove duplicates
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

        if new_season_numbers and new_episode_numbers:
            result.episode_numbers = new_episode_numbers
            result.season_number = new_season_numbers[0]

        # For anime that we still couldn't get a season, let's assume we should use 1.
        if result.series.is_anime and result.season_number is None and result.episode_numbers:
            result.season_number = 1
            log.warning(
                'Unable to parse season number for anime {name}, '
                'assuming absolute numbered anime with season 1',
                {'name': result.series.name}
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
        name_parser_cache.remove(indexer, indexer_id)

    def parse(self, name, cache_result=True):
        """Parse the name into a ParseResult.

        :param name:
        :type name: str
        :param cache_result:
        :type cache_result: bool
        :return:
        :rtype: ParseResult
        """
        name = helpers.unicodify(name)

        if self.naming_pattern:
            cache_result = False

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

        log.debug('Parsed {name} into {result}', {'name': name, 'result': result})
        return result

    @staticmethod
    def assert_supported(result):
        """Whether or not the result is supported.

        :param result:
        :type result: ParseResult
        """
        if not result.series:
            raise InvalidShowException('Unable to match {result.original_name} to a series in your database. '
                                       'Parser result: {result}'.format(result=result))

        log.debug(
            'Matched release {release} to a series in your database: {name}',
            {'release': result.original_name, 'name': result.series.name}
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
        season_numbers = helpers.ensure_list(guess.get('season'))
        if len(season_numbers) > 1 and not self.allow_multi_season:
            raise InvalidNameException("Discarding result. Multi-season detected for '{name}': {guess}".format(name=name, guess=guess))

        return ParseResult(guess, original_name=name, series_name=guess.get('alias') or guess.get('title'),
                           season_number=helpers.single_or_list(season_numbers, self.allow_multi_season),
                           episode_numbers=helpers.ensure_list(guess.get('episode'))
                           if guess.get('episode') != guess.get('absolute_episode') else [],
                           ab_episode_numbers=helpers.ensure_list(guess.get('absolute_episode')),
                           air_date=guess.get('date'), release_group=guess.get('release_group'),
                           proper_tags=helpers.ensure_list(guess.get('proper_tag')), version=guess.get('version', -1))


class ParseResult(object):
    """Represent the release information for a given name."""

    def __init__(self, guess, series_name=None, season_number=None, episode_numbers=None, ab_episode_numbers=None,
                 air_date=None, release_group=None, proper_tags=None, version=None, original_name=None):
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


class NameParserCache(object):
    """Name parser cache."""

    def __init__(self, max_size=1000):
        """Initialize the cache with a maximum size."""
        self.cache = OrderedDict()
        self.max_size = max_size

    def add(self, name, parse_result):
        """Add the result to the parser cache.

        :param name:
        :type name: str
        :param parse_result:
        :type parse_result: ParseResult
        """
        while len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)
        self.cache[name] = parse_result

    def get(self, name):
        """Return the cached parsed result.

        :param name:
        :type name: str
        :return:
        :rtype: ParseResult
        """
        if name in self.cache:
            log.debug('Using cached parse result for {name}', {'name': name})
            return self.cache[name]

    def remove(self, indexer, indexer_id):
        """Remove cache item given indexer and indexer_id."""
        if not indexer or not indexer_id:
            return
        to_remove = (cached_name for cached_name, cached_parsed_result in iteritems(self.cache) if
                     cached_parsed_result.series.indexer == indexer and cached_parsed_result.series.indexerid == indexer_id)
        for item in to_remove:
            self.cache.popitem(item)
            log.debug('Removed parsed cached result for release: {release}'.format(release=item))


name_parser_cache = NameParserCache()


class InvalidNameException(Exception):
    """The given release name is not valid."""


class InvalidShowException(Exception):
    """The given show name is not valid."""
