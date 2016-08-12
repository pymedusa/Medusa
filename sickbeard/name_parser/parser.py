# coding=utf-8
#
# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
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
"""Parser module which contains NameParser class."""

from __future__ import unicode_literals

import logging
import time

try:
    from collections import OrderedDict
except ImportError:  # pragma: no-cover
    from ordereddict import OrderedDict

import guessit

import sickbeard
from .. import common, db, helpers, scene_exceptions, scene_numbering


logger = logging.getLogger(__name__)


class NameParser(object):
    """Responsible to parse release names."""

    def __init__(self, show=None, try_indexers=False, naming_pattern=False, parse_method=None,
                 allow_multi_season=False):
        """The NameParser constructor.

        :param show:
        :type show: sickbeard.tv.TVShow
        :param try_indexers:
        :type try_indexers: bool
        :param naming_pattern:
        :type naming_pattern: bool
        :param parse_method: normal or anime
        :type parse_method: str or None
        :param allow_multi_season:
        :type allow_multi_season: bool
        """
        self.show = show
        self.try_indexers = try_indexers
        self.naming_pattern = naming_pattern
        self.allow_multi_season = allow_multi_season
        self.show_type = parse_method or ('anime' if show and show.is_anime else ('normal' if show else None))

    def _parse_string(self, name):
        guess = guessit.guessit(name, dict(show_type=self.show_type))
        result = self.to_parse_result(name, guess)

        show = helpers.get_show(result.series_name, self.try_indexers) if not self.naming_pattern else None

        # confirm passed in show object indexer id matches result show object indexer id
        show = None if show and self.show and show.indexerid != self.show.indexerid else show
        result.show = show or self.show

        # if this is a naming pattern test or result doesn't have a show object then return best result
        if not result.show or self.naming_pattern:
            return result

        # get quality
        result.quality = common.Quality.nameQuality(name, result.show.is_anime)
        if result.quality == common.Quality.UNKNOWN:
            result.quality = common.Quality.from_guessit(guess)

        new_episode_numbers = []
        new_season_numbers = []
        new_absolute_numbers = []

        # if we have an air-by-date show and the result is air-by-date,
        # then get the real season/episode numbers
        if result.show.air_by_date and result.is_air_by_date:
            airdate = result.air_date.toordinal()
            main_db_con = db.DBConnection()
            sql_result = main_db_con.select(
                b'SELECT season, episode FROM tv_episodes WHERE showid = ? and indexer = ? and airdate = ?',
                [result.show.indexerid, result.show.indexer, airdate])

            season_number = None
            episode_numbers = []

            if sql_result:
                season_number = int(sql_result[0][0])
                episode_numbers = [int(sql_result[0][1])]

            if season_number is None or not episode_numbers:
                indexer_api = sickbeard.indexerApi(result.show.indexer)
                try:
                    indexer_api_params = indexer_api.api_params.copy()

                    if result.show.lang:
                        indexer_api_params['language'] = result.show.lang

                    t = sickbeard.indexerApi(result.show.indexer).indexer(**indexer_api_params)
                    tv_episode = t[result.show.indexerid].airedOn(result.air_date)[0]

                    season_number = int(tv_episode['seasonnumber'])
                    episode_numbers = [int(tv_episode['episodenumber'])]
                except sickbeard.indexer_episodenotfound:
                    logger.warn('Unable to find episode with date {date} for show {show.name} skipping',
                                date=result.air_date, show=show.name)
                    episode_numbers = []
                except sickbeard.indexer_error as e:
                    logger.warn('Unable to contact {indexer_api.name}: {ex!r}', indexer_api=indexer_api, ex=e)
                    episode_numbers = []

            for episode_number in episode_numbers:
                s = season_number
                e = episode_number

                if result.show.is_scene:
                    (s, e) = scene_numbering.get_indexer_numbering(result.show.indexerid,
                                                                   result.show.indexer,
                                                                   season_number,
                                                                   episode_number)
                new_episode_numbers.append(e)
                new_season_numbers.append(s)

        elif result.show.is_anime and result.is_anime:
            scene_season = scene_exceptions.get_scene_exception_by_name(result.series_name)[1]
            for absolute_episode in result.ab_episode_numbers:
                a = absolute_episode

                if result.show.is_scene:
                    a = scene_numbering.get_indexer_absolute_numbering(result.show.indexerid,
                                                                       result.show.indexer, absolute_episode,
                                                                       True, scene_season)

                (s, e) = helpers.get_all_episodes_from_absolute_number(result.show, [a])

                new_absolute_numbers.append(a)
                new_episode_numbers.extend(e)
                new_season_numbers.append(s)

        elif result.season_number and result.episode_numbers:
            for episode_number in result.episode_numbers:
                s = result.season_number
                e = episode_number

                if result.show.is_scene:
                    (s, e) = scene_numbering.get_indexer_numbering(result.show.indexerid,
                                                                   result.show.indexer,
                                                                   result.season_number,
                                                                   episode_number)
                if result.show.is_anime:
                    a = helpers.get_absolute_number_from_season_and_episode(result.show, s, e)
                    if a:
                        new_absolute_numbers.append(a)

                new_episode_numbers.append(e)
                new_season_numbers.append(s)

        # need to do a quick sanity check heregex.  It's possible that we now have episodes
        # from more than one season (by tvdb numbering), and this is just too much
        # for sickbeard, so we'd need to flag it.
        new_season_numbers = list(set(new_season_numbers))  # remove duplicates
        if len(new_season_numbers) > 1:
            raise InvalidNameException('Scene numbering results episodes from seasons {seasons}, (i.e. more than one) '
                                       'and Medusa does not support this. Sorry.'.format(seasons=new_season_numbers))

        # I guess it's possible that we'd have duplicate episodes too, so lets
        # eliminate them
        new_episode_numbers = list(set(new_episode_numbers))
        new_episode_numbers.sort()

        # maybe even duplicate absolute numbers so why not do them as well
        new_absolute_numbers = list(set(new_absolute_numbers))
        new_absolute_numbers.sort()

        if new_absolute_numbers:
            result.ab_episode_numbers = new_absolute_numbers

        if new_season_numbers and new_episode_numbers:
            result.episode_numbers = new_episode_numbers
            result.season_number = new_season_numbers[0]

        if result.show.is_scene:
            logger.debug('Converted parsed result {original} into {result}', original=result.original_name,
                         result=str(result).decode('utf-8', 'xmlcharrefreplace'))

        # CPU sleep
        time.sleep(0.02)

        return result

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

        result = self._parse_string(name)
        self.assert_supported(result)

        if cache_result:
            name_parser_cache.add(name, result)

        logger.debug('Parsed {name} into {result}', name=name, result=str(result).decode('utf-8', 'xmlcharrefreplace'))
        return result

    @staticmethod
    def assert_supported(result):
        """Whether or not the result is supported.

        :param result:
        :type result: ParseResult
        """
        if not result.show:
            raise InvalidShowException('Unable to match {result.original_name} to a show in your database. '
                                       'Parser result: {result}'.format(result=result))

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
        return ParseResult(guess, original_name=name, series_name=guess.get('alias') or guess.get('title'),
                           season_number=helpers.single_or_list(guess.get('season'), self.allow_multi_season),
                           episode_numbers=helpers.ensure_list(guess.get('episode'))
                           if guess.get('episode') != guess.get('absolute_episode') else [],
                           ab_episode_numbers=helpers.ensure_list(guess.get('absolute_episode')),
                           air_date=guess.get('date'), release_group=guess.get('release_group'),
                           proper_tags=helpers.ensure_list(guess.get('proper_tag')), version=guess.get('version', -1))


class ParseResult(object):
    """Represent the release information for a given name."""

    def __init__(self, guess, series_name=None, season_number=None, episode_numbers=None, ab_episode_numbers=None,
                 air_date=None, release_group=None, proper_tags=None, version=None, original_name=None):
        """The ParseResult constructor.

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
        self.quality = common.Quality.UNKNOWN
        self.release_group = release_group
        self.air_date = air_date
        self.show = None
        self.version = version
        self.proper_tags = proper_tags
        self.guess = guess

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
            self.show == other.show,
            self.quality == other.quality,
            self.version == other.version,
            self.proper_tags == other.proper_tags,
            self.is_episode_special == other.is_episode_special
        ])

    def __str__(self):
        """String.

        :return:
        :rtype: str
        """
        return str(OrderedDict(self.guess, **dict(season=self.season_number,
                                                  episode=self.episode_numbers,
                                                  absolute_episode=self.ab_episode_numbers,
                                                  quality=self.quality)))

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


class NameParserCache(object):
    """Name parser cache."""

    _previous_parsed = {}
    _cache_size = 100

    def add(self, name, parse_result):
        """Add the result to the parser cache.

        :param name:
        :type name: str
        :param parse_result:
        :type parse_result: ParseResult
        """
        self._previous_parsed[name] = parse_result
        while len(self._previous_parsed) > self._cache_size:
            del self._previous_parsed[self._previous_parsed.keys()[0]]

    def get(self, name):
        """Return the cached parsed result.

        :param name:
        :type name: str
        :return:
        :rtype: ParseResult
        """
        if name in self._previous_parsed:
            logger.debug('Using cached parse result for {name}', name=name)
            return self._previous_parsed[name]


name_parser_cache = NameParserCache()


class InvalidNameException(Exception):
    """The given release name is not valid."""


class InvalidShowException(Exception):
    """The given show name is not valid."""
