# coding=utf-8

"""Episode classes."""

from __future__ import unicode_literals

import logging
import os.path
import re
import time
import traceback
import warnings
from builtins import str
from datetime import date, datetime

import knowit

from medusa import (
    app,
    db,
    helpers,
    network_timezones,
    notifiers,
    post_processor,
    subtitles,
)
from medusa.common import (
    ARCHIVED,
    DOWNLOADED,
    NAMING_DUPLICATE,
    NAMING_EXTEND,
    NAMING_LIMITED_EXTEND,
    NAMING_LIMITED_EXTEND_E_LOWER_PREFIXED,
    NAMING_LIMITED_EXTEND_E_UPPER_PREFIXED,
    NAMING_SEPARATED_REPEAT,
    Quality,
    SKIPPED,
    SNATCHED,
    SNATCHED_BEST,
    SNATCHED_PROPER,
    UNAIRED,
    UNSET,
    WANTED,
    statusStrings,
)
from medusa.helper.common import (
    dateFormat,
    dateTimeFormat,
    episode_num,
    remove_extension,
    replace_extension,
    sanitize_filename,
    try_int,
)
from medusa.helper.exceptions import (
    EpisodeDeletedException,
    EpisodeNotFoundException,
    MultipleEpisodesInDatabaseException,
    NoNFOException,
    ex,
)
from medusa.indexers.api import indexerApi
from medusa.indexers.config import indexerConfig
from medusa.indexers.exceptions import (
    IndexerEpisodeNotFound,
    IndexerError,
    IndexerSeasonNotFound,
)
from medusa.logger.adapters.style import BraceAdapter
from medusa.name_parser.parser import (
    InvalidNameException,
    InvalidShowException,
    NameParser,
)
from medusa.sbdatetime import sbdatetime
from medusa.scene_numbering import (
    get_scene_absolute_numbering,
    get_scene_numbering,
)
from medusa.tv.base import Identifier, TV

from six import itervalues, viewitems

try:
    import xml.etree.cElementTree as ETree
except ImportError:
    import xml.etree.ElementTree as ETree

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class EpisodeNumber(Identifier):
    """Episode Number: season/episode, absolute or air by date."""

    date_fmt = '%Y-%m-%d'
    regex = re.compile(r'\b(?:(?P<air_date>\d{4}-\d{2}-\d{2})|'
                       r'(?:s(?P<season>\d{1,4}))(?:e(?P<episode>\d{1,4}))|'
                       r'(?:e(?P<abs_episode>\d{1,4})))\b', re.IGNORECASE)

    @classmethod
    def from_slug(cls, slug):
        """Create episode number from slug. E.g.: s01e02."""
        match = cls.regex.match(slug)
        if match:
            try:
                result = {k: int(v) if k != 'air_date' else datetime.strptime(v, cls.date_fmt)
                          for k, v in viewitems(match.groupdict()) if v is not None}
                if result:
                    if 'air_date' in result:
                        return AirByDateNumber(**result)
                    if 'season' in result and 'episode' in result:
                        return RelativeNumber(**result)
                    if 'abs_episode' in result:
                        return AbsoluteNumber(**result)
            except ValueError:
                pass


class RelativeNumber(Identifier):
    """Regular episode number: season and episode."""

    def __init__(self, season, episode):
        """Constructor.

        :param season:
        :type season: int
        :param episode:
        :type episode: int
        """
        self.season = season
        self.episode = episode

    def __bool__(self):
        """Magic method."""
        return self.season is not None and self.episode is not None

    def __repr__(self):
        """Magic method."""
        return '<RelativeNumber [s{0:02d}e{1:02d}]>'.format(self.season, self.episode)

    def __str__(self):
        """Magic method."""
        return 's{0:02d}e{1:02d}'.format(self.season, self.episode)

    def __hash__(self):
        """Magic method."""
        return hash((self.season, self.episode))

    def __eq__(self, other):
        """Magic method."""
        return isinstance(other, RelativeNumber) and (
            self.season == other.season and self.episode == other.episode)


class AbsoluteNumber(EpisodeNumber):
    """Episode number class that handles absolute episode numbers."""

    def __init__(self, abs_episode):
        """Constructor.

        :param abs_episode:
        :type abs_episode: int
        """
        self.episode = abs_episode

    def __bool__(self):
        """Magic method."""
        return self.episode is not None

    def __repr__(self):
        """Magic method."""
        return '<AbsoluteNumber [e{0:02d}]>'.format(self.episode)

    def __str__(self):
        """Magic method."""
        return 'e{0:02d}'.format(self.episode)

    def __hash__(self):
        """Magic method."""
        return hash(self.episode)

    def __eq__(self, other):
        """Magic method."""
        return isinstance(other, AbsoluteNumber) and self.episode == other.episode


class AirByDateNumber(EpisodeNumber):
    """Episode number class that handles air-by-date episode numbers."""

    def __init__(self, air_date):
        """Constructor.

        :param air_date:
        :type air_date: datetime
        """
        self.air_date = air_date

    def __bool__(self):
        """Magic method."""
        return self.air_date is not None

    def __repr__(self):
        """Magic method."""
        return '<AirByDateNumber [{0!r}]>'.format(self.air_date)

    def __str__(self):
        """Magic method."""
        return self.air_date.strftime(self.date_fmt)

    def __hash__(self):
        """Magic method."""
        return hash(self.air_date)

    def __eq__(self, other):
        """Magic method."""
        return isinstance(other, AirByDateNumber) and self.air_date == other.air_date


class Episode(TV):
    """Represent a TV Show episode."""

    __refactored = {
        'show': 'series',
    }

    def __init__(self, series, season, episode, filepath=''):
        """Instantiate a Episode with database information."""
        super(Episode, self).__init__(
            int(series.indexer) if series else 0,
            0,
            {'series',
             'scene_season',
             'scene_episode',
             'scene_absolute_number',
             'related_episodes',
             'wanted_quality',
             'loaded'
             }
        )
        self.series = series
        self.name = ''
        self.season = season
        self.episode = episode
        self.slug = 's{season:02d}e{episode:02d}'.format(season=self.season, episode=self.episode)
        self.absolute_number = 0
        self.description = ''
        self.subtitles = []
        self.subtitles_searchcount = 0
        self.subtitles_lastsearch = str(datetime.min)
        self.airdate = date.fromordinal(1)
        self.hasnfo = False
        self.hastbn = False
        self.status = UNSET
        self.quality = Quality.NA
        self.file_size = 0
        self.release_name = ''
        self.is_proper = False
        self.version = 0
        self.release_group = ''
        self._location = filepath
        self.scene_season = 0
        self.scene_episode = 0
        self.scene_absolute_number = 0
        self.manually_searched = False
        self.related_episodes = []
        self.wanted_quality = []
        self.loaded = False
        self.watched = False
        if series:
            self._specify_episode(self.season, self.episode)
            self.check_for_meta_files()

    def __setattr__(self, key, value):
        """Set attribute values for deprecated attributes."""
        try:
            refactor = self.__refactored[key]
        except KeyError:
            super(Episode, self).__setattr__(key, value)
        else:
            warnings.warn(
                '{item} is deprecated, use {refactor} instead \n{trace}'.format(
                    item=key, refactor=refactor, trace=traceback.print_stack(),
                ),
                DeprecationWarning
            )
            super(Episode, self).__setattr__(refactor, value)

    def __getattr__(self, item):
        """Get attribute values for deprecated attributes."""
        try:
            return super(Episode, self).__getattribute__(item)
        except AttributeError as error:
            try:
                refactor = self.__refactored[item]
            except KeyError:
                raise error
            else:
                warnings.warn(
                    '{item} is deprecated, use {refactor} instead \n{trace}'.format(
                        item=item, refactor=refactor, trace=traceback.print_stack(),
                    ),
                    DeprecationWarning
                )
                return super(Episode, self).__getattribute__(refactor)

    def __eq__(self, other):
        """Override default equalize implementation."""
        return all([self.series.identifier == other.series.identifier,
                    self.season == other.season,
                    self.episode == other.episode])

    @classmethod
    def find_by_series_and_episode(cls, series, episode_number):
        """Find Episode based on series and episode number.

        :param series:
        :type series: medusa.tv.series.Series
        :param episode_number:
        :type episode_number: EpisodeNumber
        :return:
        :rtype: medusa.tv.Episode
        """
        if isinstance(episode_number, RelativeNumber):
            episode = series.get_episode(season=episode_number.season, episode=episode_number.episode)
        elif isinstance(episode_number, AbsoluteNumber):
            episode = series.get_episode(absolute_number=episode_number.episode)

        elif isinstance(episode_number, AirByDateNumber):
            episode = series.get_episode(air_date=episode_number.air_date)
        else:
            # if this happens then it's a bug!
            raise ValueError

        if episode:
            if episode.loaded or episode.load_from_db(episode.season, episode.episode):
                return episode

    @staticmethod
    def from_filepath(filepath):
        """Return an Episode for the given filepath.

        IMPORTANT: The filepath is not kept in the Episode.location
        Episode.location should only be set after it's post-processed and it's in the correct location.
        As of now, Episode is also not cached in Series.episodes since this method is only used during postpone PP.
        Goal here is to slowly move to use this method to create TVEpisodes. New parameters might be introduced.

        :param filepath:
        :type filepath: str
        :return:
        :rtype: Episode
        """
        try:
            parse_result = NameParser(try_indexers=True).parse(filepath, cache_result=True)
            results = []
            if parse_result.series.is_anime and parse_result.ab_episode_numbers:
                results = [parse_result.series.get_episode(absolute_number=episode_number, should_cache=False)
                           for episode_number in parse_result.ab_episode_numbers]

            if not parse_result.series.is_anime and parse_result.episode_numbers:
                results = [parse_result.series.get_episode(season=parse_result.season_number,
                                                           episode=episode_number, should_cache=False)
                           for episode_number in parse_result.episode_numbers]

            for episode in results:
                episode.related_episodes = list(results[1:])
                return episode  # only root episode has related_episodes

        except (InvalidNameException, InvalidShowException):
            log.warning('Cannot create Episode from path {path}',
                        {'path': filepath})

    @property
    def identifier(self):
        """Return the episode identifier.

        :return:
        :rtype: string
        """
        if self.series.air_by_date and self.airdate != date.fromordinal(1):
            return self.airdate.strftime(dateFormat)
        if self.series.is_anime and self.absolute_number is not None:
            return 'e{0:02d}'.format(self.absolute_number)

        return 's{0:02d}e{1:02d}'.format(self.season, self.episode)

    @property
    def location(self):
        """Return the location.

        :return:
        :rtype: location
        """
        return self._location

    @location.setter
    def location(self, value):
        log.debug('{id}: Setter sets location to {location}',
                  {'id': self.series.series_id, 'location': value})
        self._location = value
        self.file_size = os.path.getsize(value) if value and self.is_location_valid(value) else 0

    @property
    def indexer_name(self):
        """Return the indexer name identifier. Example: tvdb."""
        return indexerConfig[self.indexer].get('identifier')

    @property
    def air_date(self):
        """Return air date from the episode."""
        if self.airdate == date.min:
            return None

        date_parsed = sbdatetime.convert_to_setting(
            network_timezones.parse_date_time(
                date.toordinal(self.airdate),
                self.series.airs,
                self.series.network)
        )

        return date_parsed.isoformat()

    @property
    def status_name(self):
        """Return the status name."""
        return statusStrings[self.status]

    @property
    def quality_name(self):
        """Return the status name."""
        return Quality.qualityStrings[self.quality]

    def is_location_valid(self, location=None):
        """Whether the location is a valid file.

        :param location:
        :type location: str
        :return:
        :rtype: bool
        """
        return os.path.isfile(location or self._location)

    def metadata(self):
        """Return the video metadata."""
        try:
            return knowit.know(self.location)
        except knowit.KnowitException as error:
            log.warning(
                'An error occurred while parsing: {path}\n'
                'KnowIt reported:\n{report}', {
                    'path': self.location,
                    'report': error,
                })
            return {}

    def refresh_subtitles(self):
        """Look for subtitles files and refresh the subtitles property."""
        current_subtitles = subtitles.get_current_subtitles(self)
        ep_num = (episode_num(self.season, self.episode) or
                  episode_num(self.season, self.episode, numbering='absolute'))
        if self.subtitles == current_subtitles:
            log.debug(
                '{id}: No changed subtitles for {series} {ep}. Current subtitles: {subs}', {
                    'id': self.series.series_id,
                    'series': self.series.name,
                    'ep': ep_num,
                    'subs': current_subtitles
                }
            )
        else:
            log.debug(
                '{id}: Subtitle changes detected for {series} {ep}.'
                ' Current subtitles: {subs}', {
                    'id': self.series.series_id,
                    'series': self.series.name,
                    'ep': ep_num,
                    'subs': current_subtitles
                }
            )
            self.subtitles = current_subtitles if current_subtitles else []
            log.debug('{id}: Saving subtitles changes to database',
                      {'id': self.series.series_id})
            self.save_to_db()

    def download_subtitles(self, lang=None):
        """Download subtitles.

        :param lang:
        :type lang: string
        """
        if not self.is_location_valid():
            log.debug(
                '{id}: {series} {ep} does not exist, unable to download subtitles', {
                    'id': self.series.series_id,
                    'series': self.series.name,
                    'ep': (episode_num(self.season, self.episode) or
                           episode_num(self.season, self.episode, numbering='absolute')),
                }
            )
            return

        new_subtitles = subtitles.download_subtitles(self, lang=lang)
        if new_subtitles:
            self.subtitles = subtitles.merge_subtitles(self.subtitles, new_subtitles)

        self.subtitles_searchcount += 1 if self.subtitles_searchcount else 1
        self.subtitles_lastsearch = datetime.now().strftime(dateTimeFormat)
        log.debug('{id}: Saving last subtitles search to database',
                  {'id': self.series.series_id})
        self.save_to_db()

        if new_subtitles:
            subtitle_list = ', '.join([subtitles.name_from_code(code) for code in new_subtitles])
            log.info(
                '{id}: Downloaded {subs} subtitles for {series} {ep}', {
                    'id': self.series.series_id,
                    'subs': subtitle_list,
                    'series': self.series.name,
                    'ep': (episode_num(self.season, self.episode) or
                           episode_num(self.season, self.episode, numbering='absolute')),
                }
            )
            notifiers.notify_subtitle_download(self, subtitle_list)
        else:
            log.info(
                '{id}: No subtitles found for {series} {ep}', {
                    'id': self.series.series_id,
                    'series': self.series.name,
                    'ep': (episode_num(self.season, self.episode) or
                           episode_num(self.season, self.episode, numbering='absolute')),
                }
            )
        return new_subtitles

    def check_for_meta_files(self):
        """Check Whether metadata files has changed. And write the current set self.hasnfo and set.hastbn.

        :return: Whether a database update should be done on the episode.
        :rtype: bool
        """
        oldhasnfo = self.hasnfo
        oldhastbn = self.hastbn

        all_nfos = []
        all_tbns = []

        # check for nfo and tbn
        if not self.is_location_valid():
            return False

        for metadata_provider in itervalues(app.metadata_provider_dict):
            if metadata_provider.episode_metadata:
                new_result = metadata_provider.has_episode_metadata(self)
            else:
                new_result = False
            all_nfos.append(new_result)

            if metadata_provider.episode_thumbnails:
                new_result = metadata_provider.has_episode_thumb(self)
            else:
                new_result = False
            all_tbns.append(new_result)

        self.hasnfo = any(all_nfos)
        self.hastbn = any(all_tbns)

        return oldhasnfo != self.hasnfo or oldhastbn != self.hastbn

    def _specify_episode(self, season, episode):

        sql_results = self.load_from_db(season, episode)

        if not sql_results:
            # only load from NFO if we didn't load from DB
            if self.is_location_valid():
                try:
                    self.__load_from_nfo(self.location)
                except NoNFOException:
                    log.error(
                        '{id}: There was an error loading the NFO for {series} {ep}', {
                            'id': self.series.series_id,
                            'series': self.series.name,
                            'ep': episode_num(season, episode),
                        }
                    )

                # if we tried loading it from NFO and didn't find the NFO, try the Indexers
                if not self.hasnfo:
                    try:
                        result = self.load_from_indexer(season, episode)
                    except EpisodeDeletedException:
                        result = False

                    # if we failed SQL *and* NFO, Indexers then fail
                    if not result:
                        raise EpisodeNotFoundException('{id}: Unable to find {series} {ep}'.format
                                                       (id=self.series.series_id, series=self.series.name,
                                                        ep=episode_num(season, episode)))

    def load_from_db(self, season, episode):
        """Load episode information from database.

        :param season:
        :type season: int
        :param episode:
        :type episode: int
        :return:
        :rtype: bool
        """
        if self.loaded:
            return True

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(
            'SELECT '
            '  * '
            'FROM '
            '  tv_episodes '
            'WHERE '
            '  indexer = ? '
            '  AND showid = ? '
            '  AND season = ? '
            '  AND episode = ?', [self.series.indexer, self.series.series_id, season, episode])

        if len(sql_results) > 1:
            raise MultipleEpisodesInDatabaseException('Your DB has two records for the same series somehow.')
        elif not sql_results:
            log.debug(
                '{id}: {series} {ep} not found in the database', {
                    'id': self.series.series_id,
                    'series': self.series.name,
                    'ep': episode_num(self.season, self.episode),
                }
            )
            return False
        else:
            if sql_results[0]['name']:
                self.name = sql_results[0]['name']

            self.season = season
            self.episode = episode
            self.absolute_number = sql_results[0]['absolute_number']
            self.description = sql_results[0]['description']
            if not self.description:
                self.description = ''
            if sql_results[0]['subtitles'] and sql_results[0]['subtitles']:
                self.subtitles = sql_results[0]['subtitles'].split(',')
            self.subtitles_searchcount = sql_results[0]['subtitles_searchcount']
            self.subtitles_lastsearch = sql_results[0]['subtitles_lastsearch']
            self.airdate = date.fromordinal(int(sql_results[0]['airdate']))
            self.status = int(sql_results[0]['status'] or UNSET)
            self.quality = int(sql_results[0]['quality'] or Quality.NA)
            self.watched = bool(sql_results[0]['watched'])

            # don't overwrite my location
            if sql_results[0]['location']:
                self._location = os.path.normpath(sql_results[0]['location'])
            if sql_results[0]['file_size']:
                self.file_size = int(sql_results[0]['file_size'])
            else:
                self.file_size = 0

            self.indexerid = int(sql_results[0]['indexerid'])
            self.indexer = int(sql_results[0]['indexer'])

            self.scene_season = try_int(sql_results[0]['scene_season'], 0)
            self.scene_episode = try_int(sql_results[0]['scene_episode'], 0)
            self.scene_absolute_number = try_int(sql_results[0]['scene_absolute_number'], 0)

            if self.scene_absolute_number == 0:
                self.scene_absolute_number = get_scene_absolute_numbering(
                    self.series,
                    self.absolute_number
                )

            if self.scene_season == 0 or self.scene_episode == 0:
                self.scene_season, self.scene_episode = get_scene_numbering(
                    self.series, self.episode, self.season
                )

            if sql_results[0]['release_name'] is not None:
                self.release_name = sql_results[0]['release_name']

            if sql_results[0]['is_proper']:
                self.is_proper = int(sql_results[0]['is_proper'])

            if sql_results[0]['version']:
                self.version = int(sql_results[0]['version'])

            if sql_results[0]['release_group'] is not None:
                self.release_group = sql_results[0]['release_group']

            self.loaded = True
            self.reset_dirty()
            return True

    def set_indexer_data(self, season=None, indexer_api=None):
        """Set episode information from indexer.

        :param season:
        :param indexer_api:
        :rtype: bool
        """
        if season is None:
            season = self.season

        if indexer_api is None or indexer_api.indexer != self.series.indexer_api.indexer:
            api = self.series.indexer_api
        else:
            api = indexer_api

        try:
            api._get_episodes(self.series.series_id, aired_season=season)
        except IndexerError as error:
            log.warning(
                '{id}: {indexer} threw up an error: {error_msg}', {
                    'id': self.series.series_id,
                    'indexer': indexerApi(self.indexer).name,
                    'error_msg': ex(error),
                }
            )
            return False

        return True

    def load_from_indexer(self, season=None, episode=None, tvapi=None, cached_season=None):
        """Load episode information from indexer.

        :param season:
        :type season: int
        :param episode:
        :type episode: int
        :param tvapi:
        :param cached_season:
        :return:
        :rtype: bool
        """
        if season is None:
            season = self.season
        if episode is None:
            episode = self.episode

        try:
            if cached_season:
                my_ep = cached_season[episode]
            else:
                series = self.series.indexer_api[self.series.series_id]
                my_ep = series[season][episode]

        except (IndexerError, IOError) as error:
            log.warning(
                '{id}: {indexer} threw up an error: {error_msg}', {
                    'id': self.series.series_id,
                    'indexer': indexerApi(self.indexer).name,
                    'error_msg': ex(error),
                }
            )

            # if the episode is already valid just log it, if not throw it up
            if self.name:
                log.debug(
                    '{id}: {indexer} timed out but we have enough info from other sources, allowing the error', {
                        'id': self.series.series_id,
                        'indexer': indexerApi(self.indexer).name,
                    }
                )
                return
            else:
                log.warning(
                    '{id}: {indexer} timed out, unable to create the episode', {
                        'id': self.series.series_id,
                        'indexer': indexerApi(self.indexer).name,
                    }
                )
                return False
        except (IndexerEpisodeNotFound, IndexerSeasonNotFound):
            log.debug(
                '{id}: Unable to find the episode on {indexer}. Deleting it from db', {
                    'id': self.series.series_id,
                    'indexer': indexerApi(self.indexer).name,
                }
            )
            # if I'm no longer on the Indexers but I once was then delete myself from the DB
            if self.indexerid != -1:
                self.delete_episode()
            return

        if getattr(my_ep, 'episodename', None) is None:
            log.info(
                '{id}: {series} {ep} has no name on {indexer}. Setting to an empty string', {
                    'id': self.series.series_id,
                    'series': self.series.name,
                    'ep': episode_num(season, episode),
                    'indexer': indexerApi(self.indexer).name,
                }
            )
            setattr(my_ep, 'episodename', '')

        if getattr(my_ep, 'absolute_number', None) is None:
            log.debug(
                '{id}: {series} {ep} has no absolute number on {indexer}', {
                    'id': self.series.series_id,
                    'series': self.series.name,
                    'ep': episode_num(season, episode),
                    'indexer': indexerApi(self.indexer).name,
                }
            )
        else:
            self.absolute_number = int(my_ep['absolute_number'])
            log.debug(
                '{id}: {series} {ep} has absolute number: {absolute} ', {
                    'id': self.series.series_id,
                    'series': self.series.name,
                    'ep': episode_num(season, episode),
                    'absolute': self.absolute_number,
                }
            )

        self.name = getattr(my_ep, 'episodename', '')
        self.season = season
        self.episode = episode

        self.scene_absolute_number = get_scene_absolute_numbering(
            self.series,
            self.absolute_number
        )

        self.scene_season, self.scene_episode = get_scene_numbering(
            self.series, self.episode, self.season
        )

        self.description = getattr(my_ep, 'overview', '')

        firstaired = getattr(my_ep, 'firstaired', None)
        if not firstaired or firstaired == '0000-00-00':
            firstaired = str(date.fromordinal(1))
        raw_airdate = [int(x) for x in firstaired.split('-')]

        try:
            self.airdate = date(raw_airdate[0], raw_airdate[1], raw_airdate[2])
        except (ValueError, IndexError):
            log.warning(
                '{id}: Malformed air date of {aired} retrieved from {indexer} for {series} {ep}', {
                    'id': self.series.series_id,
                    'aired': firstaired,
                    'indexer': indexerApi(self.indexer).name,
                    'series': self.series.name,
                    'ep': episode_num(season, episode),
                }
            )

            # if I'm incomplete on the indexer but I once was complete then just delete myself from the DB for now
            if self.indexerid != -1:
                self.delete_episode()
            return False

        # early conversion to int so that episode doesn't get marked dirty
        self.indexerid = getattr(my_ep, 'id', None)
        if self.indexerid is None:
            log.error(
                '{id}: Failed to retrieve ID from {indexer}', {
                    'id': self.series.series_id,
                    'aired': firstaired,
                    'indexer': indexerApi(self.indexer).name,
                }
            )
            if self.indexerid != -1:
                self.delete_episode()
            return False

        # don't update series status if series directory is missing, unless it's missing on purpose
        if all([not self.series.is_location_valid(),
                not app.CREATE_MISSING_SHOW_DIRS,
                not app.ADD_SHOWS_WO_DIR]):
            log.warning(
                '{id}: {series} episode statuses unchanged. Location is missing: {location}', {
                    'id': self.series.series_id,
                    'series': self.series.name,
                    'location': self.series.location,
                }
            )
            return

        if self.location:
            log.debug(
                '{id}: {series} {ep} status is {status!r}. Location: {location}', {
                    'id': self.series.series_id,
                    'series': self.series.name,
                    'ep': episode_num(season, episode),
                    'status': statusStrings[self.status],
                    'location': self.location,
                }
            )

        if not os.path.isfile(self.location):
            if (self.airdate >= date.today() or self.airdate == date.fromordinal(1)) and \
                    self.status in (UNSET, UNAIRED, WANTED):
                # Need to check if is UNAIRED otherwise code will step into second 'IF'
                # and make episode as default_ep_status
                # If is a leaked episode and user manually snatched, it will respect status
                # If is a fake (manually snatched), when user set as FAILED, status will be WANTED
                # and code below will make it UNAIRED again
                self.status = UNAIRED
                log.debug(
                    '{id}: {series} {ep} airs in the future or has no air date, marking it {status}', {
                        'id': self.series.series_id,
                        'series': self.series.name,
                        'ep': episode_num(season, episode),
                        'status': statusStrings[self.status],
                    }
                )
            elif self.status in (UNSET, UNAIRED):
                # Only do UNAIRED/UNSET, it could already be snatched/ignored/skipped,
                # or downloaded/archived to disconnected media
                self.status = self.series.default_ep_status if self.season > 0 else SKIPPED  # auto-skip specials
                log.debug(
                    '{id}: {series} {ep} has already aired, marking it {status}', {
                        'id': self.series.series_id,
                        'series': self.series.name,
                        'ep': episode_num(season, episode),
                        'status': statusStrings[self.status],
                    }
                )
            else:
                log.debug(
                    '{id}: {series} {ep} status untouched: {status}', {
                        'id': self.series.series_id,
                        'series': self.series.name,
                        'ep': episode_num(season, episode),
                        'status': statusStrings[self.status],
                    }
                )
        # Update the episode's status/quality if a file exists and the status is not SNATCHED|DOWNLOADED|ARCHIVED
        elif helpers.is_media_file(self.location):
            if self.status not in [SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, DOWNLOADED, ARCHIVED]:
                self.update_status_quality(self.location)
            else:
                log.debug(
                    '{id}: {series} {ep} status untouched: {status}', {
                        'id': self.series.series_id,
                        'series': self.series.name,
                        'ep': episode_num(season, episode),
                        'status': statusStrings[self.status],
                    }
                )
        # shouldn't get here probably
        else:
            log.warning(
                '{id}: {series} {ep} status changed from {old_status} to UNSET', {
                    'id': self.series.series_id,
                    'series': self.series.name,
                    'ep': episode_num(season, episode),
                    'old_status': statusStrings[self.status],
                }
            )
            self.status = UNSET

        self.save_to_db()

    def __load_from_nfo(self, location):

        if not self.series.is_location_valid():
            log.warning('{id}: The series location {location} is missing, unable to load metadata',
                        {'id': self.series.series_id, 'location': location})
            return

        log.debug('{id}: Loading episode details from the NFO file associated with {location}',
                  {'id': self.series.series_id, 'location': location})

        self.location = location

        if self.location != '':

            if self.status == UNSET and helpers.is_media_file(self.location):
                self.update_status_quality(self.location)

            nfo_file = replace_extension(self.location, 'nfo')
            log.debug('{id}: Using NFO name {nfo}',
                      {'id': self.series.series_id, 'nfo': nfo_file})

            if os.path.isfile(nfo_file):
                try:
                    series_xml = ETree.ElementTree(file=nfo_file)
                except (SyntaxError, ValueError) as error:
                    log.error('{id}: Error loading the NFO, backing up the NFO and skipping for now: {error_msg}',
                              {'id': self.series.series_id, 'error_msg': ex(error)})
                    try:
                        os.rename(nfo_file, nfo_file + '.old')
                    except Exception as error:
                        log.warning('{id}: Error renaming the NFO. Delete it or fix it: {error_msg}',
                                    {'id': self.series.series_id, 'error_msg': ex(error)})
                    raise NoNFOException('Error in NFO format')

                for ep_details in list(series_xml.iter('episodedetails')):
                    if (ep_details.findtext('season') is None or int(ep_details.findtext('season')) != self.season or
                            ep_details.findtext('episode') is None or
                            int(ep_details.findtext('episode')) != self.episode):
                        log.debug(
                            '{id}: NFO has an <episodedetails> block for a different episode -'
                            ' wanted {ep_wanted} but got {ep_found}', {
                                'id': self.series.series_id,
                                'ep_wanted': episode_num(self.season, self.episode),
                                'ep_found': episode_num(ep_details.findtext('season'),
                                                        ep_details.findtext('episode')),
                            }
                        )
                        continue

                    if ep_details.findtext('title') is None or ep_details.findtext('aired') is None:
                        raise NoNFOException('Error in NFO format (missing episode title or airdate)')

                    self.name = ep_details.findtext('title')
                    self.episode = int(ep_details.findtext('episode'))
                    self.season = int(ep_details.findtext('season'))

                    self.scene_absolute_number = get_scene_absolute_numbering(
                        self.series,
                        self.absolute_number
                    )

                    self.scene_season, self.scene_episode = get_scene_numbering(
                        self.series, self.episode, self.season
                    )

                    self.description = ep_details.findtext('plot')
                    if self.description is None:
                        self.description = ''

                    if ep_details.findtext('aired'):
                        raw_airdate = [int(x) for x in ep_details.findtext('aired').split('-')]
                        self.airdate = date(raw_airdate[0], raw_airdate[1], raw_airdate[2])
                    else:
                        self.airdate = date.fromordinal(1)

                    self.hasnfo = True
            else:
                self.hasnfo = False

            self.hastbn = bool(os.path.isfile(replace_extension(nfo_file, 'tbn')))

        self.save_to_db()

    def __str__(self):
        """Represent a string.

        :return:
        :rtype: unicode
        """
        result = ''
        result += '%r - %r - %r\n' % (self.series.name, episode_num(self.season, self.episode), self.name)
        result += 'location: %r\n' % self.location
        result += 'description: %r\n' % self.description
        result += 'subtitles: %r\n' % ','.join(self.subtitles)
        result += 'subtitles_searchcount: %r\n' % self.subtitles_searchcount
        result += 'subtitles_lastsearch: %r\n' % self.subtitles_lastsearch
        result += 'airdate: %r (%r)\n' % (self.airdate.toordinal(), self.airdate)
        result += 'hasnfo: %r\n' % self.hasnfo
        result += 'hastbn: %r\n' % self.hastbn
        result += 'status: %r\n' % self.status
        result += 'quality: %r\n' % self.quality
        return result

    def to_json(self, detailed=True):
        """Return the json representation."""
        data = {}
        data['identifier'] = self.identifier
        data['id'] = {self.indexer_name: self.indexerid}
        data['slug'] = self.slug
        data['season'] = self.season
        data['episode'] = self.episode

        if self.absolute_number:
            data['absoluteNumber'] = self.absolute_number

        data['airDate'] = self.air_date
        data['title'] = self.name
        data['description'] = self.description
        data['title'] = self.name
        data['subtitles'] = self.subtitles
        data['status'] = self.status_name
        data['watched'] = bool(self.watched)
        data['quality'] = self.quality
        data['release'] = {}
        data['release']['name'] = self.release_name
        data['release']['group'] = self.release_group
        data['release']['proper'] = self.is_proper
        data['release']['version'] = self.version
        data['scene'] = {}
        data['scene']['season'] = self.scene_season
        data['scene']['episode'] = self.scene_episode

        if self.scene_absolute_number:
            data['scene']['absoluteNumber'] = self.scene_absolute_number

        data['file'] = {}
        data['file']['location'] = self.location
        data['file']['name'] = os.path.basename(self.location)
        if self.file_size:
            data['file']['size'] = self.file_size

        data['content'] = {}
        data['content']['hasNfo'] = self.hasnfo
        data['content']['hasTbn'] = self.hastbn

        if detailed:
            data['statistics'] = {}
            data['statistics']['subtitleSearch'] = {}
            data['statistics']['subtitleSearch']['last'] = self.subtitles_lastsearch
            data['statistics']['subtitleSearch']['count'] = self.subtitles_searchcount
            data['wantedQualities'] = self.wanted_quality
            data['wantedQualities'] = [ep.identifier for ep in self.related_episodes]

        return data

    def create_meta_files(self):
        """Create episode metadata files."""
        if not self.series.is_location_valid():
            log.warning('{id}: The series directory is missing, unable to create metadata',
                        {'id': self.series.series_id})
            return

        for metadata_provider in itervalues(app.metadata_provider_dict):
            self.__create_nfo(metadata_provider)
            self.__create_thumbnail(metadata_provider)

        if self.check_for_meta_files():
            log.debug('{id}: Saving metadata changes to database',
                      {'id': self.series.series_id})
            self.save_to_db()

    def __create_nfo(self, metadata_provider):

        result = False

        # You may only call .values() on metadata_provider_dict! As on values() call the indexer_api attribute
        # is reset. This will prevent errors, when using multiple indexers and caching.
        result = metadata_provider.create_episode_metadata(self) or result

        return result

    def __create_thumbnail(self, metadata_provider):

        result = False

        # You may only call .values() on metadata_provider_dict! As on values() call the indexer_api attribute
        # is reset. This will prevent errors, when using multiple indexers and caching.
        result = metadata_provider.create_episode_thumb(self) or result

        return result

    def delete_episode(self):
        """Delete episode from database."""
        log.debug(
            '{id}: Deleting {series} {ep} from the DB', {
                'id': self.series.series_id,
                'series': self.series.name,
                'ep': episode_num(self.season, self.episode),
            }
        )

        # remove myself from the series dictionary
        if self.series.get_episode(self.season, self.episode, no_create=True) == self:
            log.debug('{id}: Removing episode from series',
                      {'id': self.series.series_id})
            del self.series.episodes[self.season][self.episode]

        # delete myself from the DB
        log.debug('{id}: Deleting episode from the database',
                  {'id': self.series.series_id})
        main_db_con = db.DBConnection()
        main_db_con.action(
            'DELETE FROM tv_episodes '
            'WHERE showid = ?'
            ' AND season = ?'
            ' AND episode = ?',
            [self.series.series_id, self.season, self.episode]
        )
        raise EpisodeDeletedException()

    def get_sql(self):
        """Create SQL queue for this episode if any of its data has been changed since the last save."""
        if not self.dirty:
            log.debug('{id}: Not creating SQL query - record is not dirty',
                      {'id': self.series.series_id})
            return

        try:
            main_db_con = db.DBConnection()
            rows = main_db_con.select(
                'SELECT '
                '  episode_id, '
                '  subtitles '
                'FROM '
                '  tv_episodes '
                'WHERE '
                '  indexer = ?'
                '  AND showid = ? '
                '  AND season = ? '
                '  AND episode = ?',
                [self.series.indexer, self.series.series_id, self.season, self.episode])

            ep_id = None
            if rows:
                ep_id = int(rows[0]['episode_id'])

            if ep_id:
                # use a custom update method to get the data into the DB for existing records.
                # Multi or added subtitle or removed subtitles
                if app.SUBTITLES_MULTI or not rows[0]['subtitles'] or not self.subtitles:
                    sql_query = [
                        'UPDATE '
                        '  tv_episodes '
                        'SET '
                        '  indexerid = ?, '
                        '  indexer = ?, '
                        '  name = ?, '
                        '  description = ?, '
                        '  subtitles = ?, '
                        '  subtitles_searchcount = ?, '
                        '  subtitles_lastsearch = ?, '
                        '  airdate = ?, '
                        '  hasnfo = ?, '
                        '  hastbn = ?, '
                        '  status = ?, '
                        '  quality = ?, '
                        '  location = ?, '
                        '  file_size = ?, '
                        '  release_name = ?, '
                        '  is_proper = ?, '
                        '  showid = ?, '
                        '  season = ?, '
                        '  episode = ?, '
                        '  absolute_number = ?, '
                        '  version = ?, '
                        '  release_group = ?, '
                        '  manually_searched = ?, '
                        '  watched = ? '
                        'WHERE '
                        '  episode_id = ?',
                        [self.indexerid, self.indexer, self.name, self.description, ','.join(self.subtitles),
                         self.subtitles_searchcount, self.subtitles_lastsearch, self.airdate.toordinal(), self.hasnfo,
                         self.hastbn, self.status, self.quality, self.location, self.file_size, self.release_name,
                         self.is_proper, self.series.series_id, self.season, self.episode, self.absolute_number,
                         self.version, self.release_group, self.manually_searched, self.watched, ep_id]]
                else:
                    # Don't update the subtitle language when the srt file doesn't contain the
                    # alpha2 code, keep value from subliminal
                    sql_query = [
                        'UPDATE '
                        '  tv_episodes '
                        'SET '
                        '  indexerid = ?, '
                        '  indexer = ?, '
                        '  name = ?, '
                        '  description = ?, '
                        '  subtitles_searchcount = ?, '
                        '  subtitles_lastsearch = ?, '
                        '  airdate = ?, '
                        '  hasnfo = ?, '
                        '  hastbn = ?, '
                        '  status = ?, '
                        '  quality = ?, '
                        '  location = ?, '
                        '  file_size = ?, '
                        '  release_name = ?, '
                        '  is_proper = ?, '
                        '  showid = ?, '
                        '  season = ?, '
                        '  episode = ?, '
                        '  absolute_number = ?, '
                        '  version = ?, '
                        '  release_group = ?, '
                        '  manually_searched = ?, '
                        '  watched = ? '
                        'WHERE '
                        '  episode_id = ?',
                        [self.indexerid, self.indexer, self.name, self.description,
                         self.subtitles_searchcount, self.subtitles_lastsearch, self.airdate.toordinal(), self.hasnfo,
                         self.hastbn, self.status, self.quality, self.location, self.file_size, self.release_name,
                         self.is_proper, self.series.series_id, self.season, self.episode, self.absolute_number,
                         self.version, self.release_group, self.manually_searched, self.watched, ep_id]]
            else:
                # use a custom insert method to get the data into the DB.
                sql_query = [
                    'INSERT OR IGNORE INTO '
                    '  tv_episodes '
                    '  (episode_id, '
                    '  indexerid, '
                    '  indexer, '
                    '  name, '
                    '  description, '
                    '  subtitles, '
                    '  subtitles_searchcount, '
                    '  subtitles_lastsearch, '
                    '  airdate, '
                    '  hasnfo, '
                    '  hastbn, '
                    '  status, '
                    '  quality, '
                    '  location, '
                    '  file_size, '
                    '  release_name, '
                    '  is_proper, '
                    '  showid, '
                    '  season, '
                    '  episode, '
                    '  absolute_number, '
                    '  version, '
                    '  release_group, '
                    '  manually_searched, '
                    '  watched) '
                    'VALUES '
                    '  ((SELECT episode_id FROM tv_episodes WHERE indexer = ? AND showid = ? AND season = ? AND episode = ?), '
                    '  ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);',
                    [self.series.indexer, self.series.series_id, self.season, self.episode, self.indexerid, self.series.indexer, self.name,
                     self.description, ','.join(self.subtitles), self.subtitles_searchcount, self.subtitles_lastsearch,
                     self.airdate.toordinal(), self.hasnfo, self.hastbn, self.status, self.quality, self.location,
                     self.file_size, self.release_name, self.is_proper, self.series.series_id, self.season, self.episode,
                     self.absolute_number, self.version, self.release_group, self.manually_searched, self.watched]]
        except Exception as error:
            log.error('{id}: Error while updating database: {error_msg!r}',
                      {'id': self.series.series_id, 'error_msg': error})
            self.reset_dirty()
            return

        self.loaded = False
        self.reset_dirty()

        return sql_query

    def save_to_db(self):
        """Save this episode to the database if any of its data has been changed since the last save."""
        if not self.dirty:
            return

        log.debug('{id}: Saving episode to database: {show} {ep}',
                  {'id': self.series.series_id,
                   'show': self.series.name,
                   'ep': episode_num(self.season, self.episode)})

        new_value_dict = {
            'indexerid': self.indexerid,
            'name': self.name,
            'description': self.description,
            'subtitles': ','.join(self.subtitles),
            'subtitles_searchcount': self.subtitles_searchcount,
            'subtitles_lastsearch': self.subtitles_lastsearch,
            'airdate': self.airdate.toordinal(),
            'hasnfo': self.hasnfo,
            'hastbn': self.hastbn,
            'status': self.status,
            'quality': self.quality,
            'location': self.location,
            'file_size': self.file_size,
            'release_name': self.release_name,
            'is_proper': self.is_proper,
            'absolute_number': self.absolute_number,
            'version': self.version,
            'release_group': self.release_group,
            'manually_searched': self.manually_searched,
            'watched': self.watched,
        }

        control_value_dict = {
            'indexer': self.series.indexer,
            'showid': self.series.series_id,
            'season': self.season,
            'episode': self.episode,
        }

        # use a custom update/insert method to get the data into the DB
        main_db_con = db.DBConnection()
        main_db_con.upsert('tv_episodes', new_value_dict, control_value_dict)

        self.loaded = False
        self.reset_dirty()

    def full_path(self):
        """Return episode full path.

        :return:
        :rtype: str
        """
        if self.location is None or self.location == '':
            return None
        else:
            return os.path.join(self.series.location, self.location)

    def pretty_name(self):
        """Return the name of this episode in a "pretty" human-readable format.

        Used for logging and notifications and such.

        :return: A string representing the episode's name and season/ep numbers
        :rtype: str
        """
        if self.series.anime and not self.series.scene:
            return self._format_pattern('%SN - %AB - %EN')
        elif self.series.air_by_date:
            return self._format_pattern('%SN - %AD - %EN')

        return self._format_pattern('%SN - S%0SE%0E - %EN')

    def pretty_name_with_quality(self):
        """Return the name of this episode in a "pretty" human-readable format, with quality information.

        Used for notifications.

        :return: A string representing the episode's name, season/ep numbers and quality
        :rtype: str
        """
        if self.series.anime and not self.series.scene:
            return self._format_pattern('%SN - %AB - %EN - %QN')
        elif self.series.air_by_date:
            return self._format_pattern('%SN - %AD - %EN - %QN')

        return self._format_pattern('%SN - %Sx%0E - %EN - %QN')

    def __ep_name(self):
        """Return the name of the episode to use during renaming.

        Combines the names of related episodes.
        Eg. "Ep Name (1)" and "Ep Name (2)" becomes "Ep Name"
            "Ep Name" and "Other Ep Name" becomes "Ep Name & Other Ep Name"
        :return:
        :rtype: str
        """
        multi_name_regex = r'(.*) \(\d{1,2}\)'

        self.related_episodes = sorted(self.related_episodes, key=lambda rel: rel.episode)

        if not self.related_episodes:
            good_name = self.name
        else:
            single_name = True
            cur_good_name = None

            for cur_name in [self.name] + [x.name for x in self.related_episodes]:
                match = re.match(multi_name_regex, cur_name)
                if not match:
                    single_name = False
                    break

                if cur_good_name is None:
                    cur_good_name = match.group(1)
                elif cur_good_name != match.group(1):
                    single_name = False
                    break

            if single_name:
                good_name = cur_good_name
            else:
                good_name = self.name
                for rel_ep in self.related_episodes:
                    good_name += ' & ' + rel_ep.name

        return good_name

    def __replace_map(self):
        """Generate a replacement map for this episode.

        Maps all possible custom naming patterns to the correct value for this episode.

        :return: A dict with patterns as the keys and their replacement values as the values.
        :rtype: dict (str -> str)
        """
        ep_name = self.__ep_name()

        def dot(name):
            return helpers.sanitize_scene_name(name)

        def us(name):
            return re.sub('[ -]', '_', name)

        def release_name(name):
            if name:
                name = remove_extension(name)
            return name

        def release_group(series, name):
            if name:
                name = remove_extension(name)
            else:
                return ''

            try:
                parse_result = NameParser(series=series, naming_pattern=True).parse(name)
            except (InvalidNameException, InvalidShowException) as error:
                log.debug('Unable to parse release_group: {error_msg}',
                          {'error_msg': ex(error)})
                return ''

            if not parse_result.release_group:
                return ''
            return parse_result.release_group.strip('.- []{}')

        if app.NAMING_STRIP_YEAR:
            series_name = re.sub(r'\(\d+\)$', '', self.series.name).rstrip()
        else:
            series_name = self.series.name

        # try to get the release group
        rel_grp = {
            app.UNKNOWN_RELEASE_GROUP: app.UNKNOWN_RELEASE_GROUP
        }
        if hasattr(self, 'location'):  # from the location name
            rel_grp['location'] = release_group(self.series, self.location)
            if not rel_grp['location']:
                del rel_grp['location']
        if hasattr(self, 'release_group'):  # from the release group field in db
            rel_grp['database'] = self.release_group.strip('.- []{}')
            if not rel_grp['database']:
                del rel_grp['database']
        if hasattr(self, 'release_name'):  # from the release name field in db
            rel_grp['release_name'] = release_group(self.series, self.release_name)
            if not rel_grp['release_name']:
                del rel_grp['release_name']

        # use release_group, release_name, location in that order
        if 'database' in rel_grp:
            relgrp = 'database'
        elif 'release_name' in rel_grp:
            relgrp = 'release_name'
        elif 'location' in rel_grp:
            relgrp = 'location'
        else:
            relgrp = app.UNKNOWN_RELEASE_GROUP

        # try to get the release encoder to comply with scene naming standards
        encoder = Quality.scene_quality_from_name(self.release_name.replace(rel_grp[relgrp], ''), self.quality)
        if encoder:
            log.debug('Found codec for {series} {ep}',
                      {'series': series_name, 'ep': ep_name})

        return {
            '%SN': series_name,
            '%S.N': dot(series_name),
            '%S_N': us(series_name),
            '%EN': ep_name,
            '%E.N': dot(ep_name),
            '%E_N': us(ep_name),
            '%QN': Quality.qualityStrings[self.quality],
            '%Q.N': dot(Quality.qualityStrings[self.quality]),
            '%Q_N': us(Quality.qualityStrings[self.quality]),
            '%SQN': Quality.scene_quality_strings[self.quality] + encoder,
            '%SQ.N': dot(Quality.scene_quality_strings[self.quality] + encoder),
            '%SQ_N': us(Quality.scene_quality_strings[self.quality] + encoder),
            '%S': str(self.season),
            '%0S': '%02d' % self.season,
            '%E': str(self.episode),
            '%0E': '%02d' % self.episode,
            '%XS': str(self.scene_season),
            '%0XS': '%02d' % try_int(self.scene_season, self.season),
            '%XE': str(self.scene_episode),
            '%0XE': '%02d' % try_int(self.scene_episode, self.episode),
            '%AB': '%(#)03d' % {'#': self.absolute_number},
            '%XAB': '%(#)03d' % {'#': self.scene_absolute_number},
            '%RN': release_name(self.release_name),
            '%RG': rel_grp[relgrp],
            '%CRG': rel_grp[relgrp].upper(),
            '%AD': str(self.airdate).replace('-', ' '),
            '%A.D': str(self.airdate).replace('-', '.'),
            '%A_D': us(str(self.airdate)),
            '%A-D': str(self.airdate),
            '%Y': str(self.airdate.year),
            '%M': str(self.airdate.month),
            '%D': str(self.airdate.day),
            '%CY': str(date.today().year),
            '%CM': str(date.today().month),
            '%CD': str(date.today().day),
            '%0M': '%02d' % self.airdate.month,
            '%0D': '%02d' % self.airdate.day,
            '%RT': 'PROPER' if self.is_proper else '',
        }

    @staticmethod
    def __format_string(pattern, replace_map):
        """Replace all template strings with the correct value.

        :param pattern:
        :type pattern: str
        :param replace_map:
        :type replace_map: dict (str -> str)
        :return:
        :rtype: str
        """
        result_name = pattern

        # do the replacements
        for cur_replacement in sorted(list(replace_map), reverse=True):
            result_name = result_name.replace(cur_replacement, sanitize_filename(replace_map[cur_replacement]))
            result_name = result_name.replace(cur_replacement.lower(),
                                              sanitize_filename(replace_map[cur_replacement].lower()))

        return result_name

    def _format_pattern(self, pattern=None, multi=None, anime_type=None):
        """Manipulate an episode naming pattern and then fills the template in.

        :param pattern:
        :type pattern: str
        :param multi:
        :type multi: bool
        :param anime_type:
        :type anime_type: int
        :return:
        :rtype: str
        """
        if pattern is None:
            pattern = app.NAMING_PATTERN

        if multi is None:
            multi = app.NAMING_MULTI_EP

        if app.NAMING_CUSTOM_ANIME:
            if anime_type is None:
                anime_type = app.NAMING_ANIME
        else:
            anime_type = 3

        replace_map = self.__replace_map()

        result_name = pattern

        # if there's no release group in the db, let the user know we replaced it
        if replace_map['%RG'] and replace_map['%RG'] != app.UNKNOWN_RELEASE_GROUP:
            if not hasattr(self, 'release_group') or not self.release_group:
                log.debug('{id}: Episode has no release group, replacing it with {rg}',
                          {'id': self.series.series_id, 'rg': replace_map['%RG']})
                self.release_group = replace_map['%RG']  # if release_group is not in the db, put it there

        # if there's no release name then replace it with a reasonable facsimile
        if not replace_map['%RN']:

            if self.series.air_by_date or self.series.sports:
                result_name = result_name.replace('%RN', '%S.N.%A.D.%E.N-' + replace_map['%RG'])
                result_name = result_name.replace('%rn', '%s.n.%A.D.%e.n-' + replace_map['%RG'].lower())

            elif anime_type != 3:
                result_name = result_name.replace('%RN', '%S.N.%AB.%E.N-' + replace_map['%RG'])
                result_name = result_name.replace('%rn', '%s.n.%ab.%e.n-' + replace_map['%RG'].lower())

            else:
                result_name = result_name.replace('%RN', '%S.N.S%0SE%0E.%E.N-' + replace_map['%RG'])
                result_name = result_name.replace('%rn', '%s.n.s%0se%0e.%e.n-' + replace_map['%RG'].lower())

        if not replace_map['%RT']:
            result_name = re.sub('([ _.-]*)%RT([ _.-]*)', r'\2', result_name)

        # split off ep name part only
        name_groups = re.split(r'[\\/]', result_name)

        # figure out the double-ep numbering style for each group, if applicable
        for cur_name_group in name_groups:

            season_ep_regex = r"""
                                (?P<pre_sep>[ _.-]*)
                                ((?:s(?:eason|eries)?\s*)?%0?S(?![._]?N))
                                (.*?)
                                (%0?E(?![._]?N))
                                (?P<post_sep>[ _.-]*)
                              """
            ep_only_regex = r'(E?%0?E(?![._]?N))'

            # try the normal way
            season_ep_match = re.search(season_ep_regex, cur_name_group, re.I | re.X)
            ep_only_match = re.search(ep_only_regex, cur_name_group, re.I | re.X)

            # if we have a season and episode then collect the necessary data
            if season_ep_match:
                season_format = season_ep_match.group(2)
                ep_sep = season_ep_match.group(3)
                ep_format = season_ep_match.group(4)
                sep = season_ep_match.group('pre_sep')
                if not sep:
                    sep = season_ep_match.group('post_sep')
                if not sep:
                    sep = ' '

                # force 2-3-4 format if they chose to extend
                if multi in (NAMING_EXTEND, NAMING_LIMITED_EXTEND, NAMING_LIMITED_EXTEND_E_UPPER_PREFIXED, NAMING_LIMITED_EXTEND_E_LOWER_PREFIXED):
                    ep_sep = '-'

                regex_used = season_ep_regex

            # if there's no season then there's not much choice so we'll just force them to use 03-04-05 style
            elif ep_only_match:
                season_format = ''
                ep_sep = '-'
                ep_format = ep_only_match.group(1)
                sep = ''
                regex_used = ep_only_regex

            else:
                continue

            # we need at least this much info to continue
            if not ep_sep or not ep_format:
                continue

            # start with the ep string, eg. E03
            ep_string = self.__format_string(ep_format.upper(), replace_map)
            for other_ep in self.related_episodes:

                # for limited extend we only append the last ep
                if multi in (NAMING_LIMITED_EXTEND, NAMING_LIMITED_EXTEND_E_UPPER_PREFIXED, NAMING_LIMITED_EXTEND_E_LOWER_PREFIXED) and \
                        other_ep != self.related_episodes[-1]:
                    continue

                elif multi == NAMING_DUPLICATE:
                    # add " - S01"
                    ep_string += sep + season_format

                elif multi == NAMING_SEPARATED_REPEAT:
                    ep_string += sep

                # add "E04"
                ep_string += ep_sep

                if multi == NAMING_LIMITED_EXTEND_E_UPPER_PREFIXED:
                    ep_string += 'E'

                elif multi == NAMING_LIMITED_EXTEND_E_LOWER_PREFIXED:
                    ep_string += 'e'

                ep_string += other_ep.__format_string(ep_format.upper(), other_ep.__replace_map())

            if anime_type != 3:
                if self.absolute_number == 0:
                    cur_absolute_number = self.episode
                else:
                    cur_absolute_number = self.absolute_number

                if self.season != 0:  # don't set absolute numbers if we are on specials !
                    if anime_type == 1:  # this crazy person wants both ! (note: +=)
                        ep_string += sep + '%(#)03d' % {
                            '#': cur_absolute_number}
                    elif anime_type == 2:  # total anime freak only need the absolute number ! (note: =)
                        ep_string = '%(#)03d' % {'#': cur_absolute_number}

                    for rel_ep in self.related_episodes:
                        if rel_ep.absolute_number != 0:
                            ep_string += '-' + '%(#)03d' % {'#': rel_ep.absolute_number}
                        else:
                            ep_string += '-' + '%(#)03d' % {'#': rel_ep.episode}

            regex_replacement = None
            if anime_type == 2 and regex_used != ep_only_regex:
                regex_replacement = r'\g<pre_sep>' + ep_string + r'\g<post_sep>'
            elif season_ep_match:
                regex_replacement = r'\g<pre_sep>\g<2>\g<3>' + ep_string + r'\g<post_sep>'
            elif ep_only_match:
                regex_replacement = ep_string

            if regex_replacement:
                # fill out the template for this piece and then insert this piece into the actual pattern
                cur_name_group_result = re.sub('(?i)(?x)' + regex_used, regex_replacement, cur_name_group)
                # cur_name_group_result = cur_name_group.replace(ep_format, ep_string)
                result_name = result_name.replace(cur_name_group, cur_name_group_result)

        parsed_result_name = self.__format_string(result_name, replace_map)

        # With the episode name filenames tend to grow very large. Worst case scenario we even need to add `-thumb.jpg`
        # to the filename. To make sure we stay under the 255 character limit, we're working with 244 chars, taking into
        # account the thumbnail.
        if len(parsed_result_name) > 244 and any(['%E.N' in result_name, '%EN' in result_name, '%E_N' in result_name]):
            for remove_pattern in ('%E.N', '%EN', '%E_N'):
                result_name = result_name.replace(remove_pattern, '')
            # The Episode name can be appended with a - or . in between. Therefor we're removing it.
            # Creating a clean filename.
            result_name = result_name.strip('-. ')
            parsed_result_name = self.__format_string(result_name, replace_map)
            log.debug('{id}: Cutting off the episode name, as the total filename is too long. > 255 chars.',
                      {'id': self.series.series_id})

        log.debug('{id}: Formatting pattern: {pattern} -> {result}',
                  {'id': self.series.series_id, 'pattern': result_name, 'result': parsed_result_name})

        return parsed_result_name

    def proper_path(self):
        """Figure out the path where this episode SHOULD be according to the renaming rules, relative from the series dir.

        :return:
        :rtype: str
        """
        anime_type = app.NAMING_ANIME
        if not self.series.is_anime:
            anime_type = 3

        result = self.formatted_filename(anime_type=anime_type)

        # if they want us to flatten it and we're allowed to flatten it then we will
        if not self.series.season_folders and not app.NAMING_FORCE_FOLDERS:
            return result

        # if not we append the folder on and use that
        else:
            result = os.path.join(self.formatted_dir(), result)

        return result

    def formatted_dir(self, pattern=None, multi=None):
        """Just the folder name of the episode.

        :param pattern:
        :type pattern: str
        :param multi:
        :type multi: bool
        :return:
        :rtype: str
        """
        if pattern is None:
            # we only use ABD if it's enabled, this is an ABD series, AND this is not a multi-ep
            if self.series.air_by_date and app.NAMING_CUSTOM_ABD and not self.related_episodes:
                pattern = app.NAMING_ABD_PATTERN
            elif self.series.sports and app.NAMING_CUSTOM_SPORTS and not self.related_episodes:
                pattern = app.NAMING_SPORTS_PATTERN
            elif self.series.anime and app.NAMING_CUSTOM_ANIME:
                pattern = app.NAMING_ANIME_PATTERN
            else:
                pattern = app.NAMING_PATTERN

        # split off the dirs only, if they exist
        name_groups = re.split(r'[\\/]', pattern)

        if len(name_groups) == 1:
            return ''
        else:
            return self._format_pattern(os.sep.join(name_groups[:-1]), multi)

    def formatted_filename(self, pattern=None, multi=None, anime_type=None):
        """Just the filename of the episode, formatted based on the naming settings.

        :param pattern:
        :type pattern: str
        :param multi:
        :type multi: bool
        :param anime_type:
        :type anime_type: int
        :return:
        :rtype: str
        """
        if pattern is None:
            # we only use ABD if it's enabled, this is an ABD series, AND this is not a multi-ep
            if self.series.air_by_date and app.NAMING_CUSTOM_ABD and not self.related_episodes:
                pattern = app.NAMING_ABD_PATTERN
            elif self.series.sports and app.NAMING_CUSTOM_SPORTS and not self.related_episodes:
                pattern = app.NAMING_SPORTS_PATTERN
            elif self.series.anime and app.NAMING_CUSTOM_ANIME:
                pattern = app.NAMING_ANIME_PATTERN
            else:
                pattern = app.NAMING_PATTERN

        # split off the dirs only, if they exist
        name_groups = re.split(r'[\\/]', pattern)

        return sanitize_filename(self._format_pattern(name_groups[-1], multi, anime_type))

    def rename(self):
        """Rename an episode file and all related files to the location and filename as specified in naming settings."""
        if not self.is_location_valid():
            log.warning('{id} Skipping rename, location does not exist: {location}',
                        {'id': self.indexerid, 'location': self.location})
            return

        proper_path = self.proper_path()
        absolute_proper_path = os.path.join(self.series.location, proper_path)
        absolute_current_path_no_ext, file_ext = os.path.splitext(self.location)
        absolute_current_path_no_ext_length = len(absolute_current_path_no_ext)

        related_subs = []

        current_path = absolute_current_path_no_ext

        if absolute_current_path_no_ext.startswith(self.series.location):
            current_path = absolute_current_path_no_ext[len(self.series.location):]

        log.debug(
            '{id}: Renaming/moving episode from the base path {location} to {new_location}', {
                'id': self.indexerid,
                'location': self.location,
                'new_location': absolute_proper_path,
            }
        )

        # if it's already named correctly then don't do anything
        if proper_path == current_path:
            log.debug(
                '{id}: File {location} is already named correctly, skipping', {
                    'id': self.indexerid,
                    'location': self.location,
                    'new_location': absolute_proper_path,
                }
            )
            return

        related_files = post_processor.PostProcessor(self.location).list_associated_files(
            self.location, subfolders=True)

        # This is wrong. Cause of pp not moving subs.
        if self.series.subtitles and app.SUBTITLES_DIR != '':
            related_subs = post_processor.PostProcessor(
                self.location).list_associated_files(app.SUBTITLES_DIR, subfolders=True, subtitles_only=True)

        log.debug(
            '{id} Files associated to {location}: {related_files}', {
                'id': self.indexerid,
                'location': self.location,
                'related_files': related_files
            }
        )

        # move the ep file
        result = helpers.rename_ep_file(self.location, absolute_proper_path, absolute_current_path_no_ext_length)

        # move related files
        for cur_related_file in related_files:
            # We need to fix something here because related files can be in subfolders
            # and the original code doesn't handle this (at all)
            cur_related_dir = os.path.dirname(os.path.abspath(cur_related_file))
            subfolder = cur_related_dir.replace(os.path.dirname(os.path.abspath(self.location)), '')
            # We now have a subfolder. We need to add that to the absolute_proper_path.
            # First get the absolute proper-path dir
            proper_related_dir = os.path.dirname(os.path.abspath(absolute_proper_path + file_ext))
            proper_related_path = absolute_proper_path.replace(proper_related_dir, proper_related_dir + subfolder)

            cur_result = helpers.rename_ep_file(cur_related_file, proper_related_path,
                                                absolute_current_path_no_ext_length + len(subfolder))
            if not cur_result:
                log.warning('{id}: Unable to rename file {cur_file}',
                            {'id': self.indexerid, 'cur_file': cur_related_file})

        for cur_related_sub in related_subs:
            absolute_proper_subs_path = os.path.join(app.SUBTITLES_DIR, self.formatted_filename())
            cur_result = helpers.rename_ep_file(cur_related_sub, absolute_proper_subs_path,
                                                absolute_current_path_no_ext_length)
            if not cur_result:
                log.warning('{id}: Unable to rename file {cur_file}',
                            {'id': self.indexerid, 'cur_file': cur_related_sub})

        # save the ep
        with self.lock:
            if result:
                self.location = absolute_proper_path + file_ext
                for rel_ep in self.related_episodes:
                    rel_ep.location = absolute_proper_path + file_ext

        # in case something changed with the metadata just do a quick check
        for cur_ep in [self] + self.related_episodes:
            cur_ep.check_for_meta_files()

        # save any changes to the database
        sql_l = []
        with self.lock:
            for rel_ep in [self] + self.related_episodes:
                sql_l.append(rel_ep.get_sql())

        if sql_l:
            main_db_con = db.DBConnection()
            main_db_con.mass_action(sql_l)

    def airdate_modify_stamp(self):
        """Make the modify date and time of a file reflect the series air date and time.

        Note: Also called from post_processor
        """
        if not all([app.AIRDATE_EPISODES, self.airdate, self.location,
                    self.series, self.series.airs, self.series.network]):
            return

        try:
            airdate_ordinal = self.airdate.toordinal()
            if airdate_ordinal < 1:
                return

            airdatetime = network_timezones.parse_date_time(airdate_ordinal, self.series.airs, self.series.network)

            if app.FILE_TIMESTAMP_TIMEZONE == 'local':
                airdatetime = airdatetime.astimezone(network_timezones.app_timezone)

            filemtime = datetime.fromtimestamp(
                os.path.getmtime(self.location)).replace(tzinfo=network_timezones.app_timezone)

            if filemtime != airdatetime:
                airdatetime = airdatetime.timetuple()
                log.debug(
                    '{id}: About to modify date of {location} to series air date {air_date}', {
                        'id': self.series.series_id,
                        'location': self.location,
                        'air_date': time.strftime('%b %d,%Y (%H:%M)', airdatetime),
                    }
                )
                try:
                    if helpers.touch_file(self.location, time.mktime(airdatetime)):
                        log.info(
                            '{id}: Changed modify date of {location} to series air date {air_date}', {
                                'id': self.series.series_id,
                                'location': os.path.basename(self.location),
                                'air_date': time.strftime('%b %d,%Y (%H:%M)', airdatetime),
                            }
                        )
                    else:
                        log.warning(
                            '{id}: Unable to modify date of {location} to series air date {air_date}', {
                                'id': self.series.series_id,
                                'location': os.path.basename(self.location),
                                'air_date': time.strftime('%b %d,%Y (%H:%M)', airdatetime),
                            }
                        )
                except Exception:
                    log.warning(
                        '{id}: Failed to modify date of {location} to series air date {air_date}', {
                            'id': self.series.series_id,
                            'location': os.path.basename(self.location),
                            'air_date': time.strftime('%b %d,%Y (%H:%M)', airdatetime),
                        }
                    )
        except Exception:
            log.warning(
                '{id}: Failed to modify date of {location}', {
                    'id': self.series.series_id,
                    'location': os.path.basename(self.location),
                }
            )

    def update_status_quality(self, filepath):
        """Update the episode status and quality according to the file information.

        The status should only be changed if either the size or the filename changed.
        :param filepath: Path to the new episode file.
        """
        old_status, old_quality = self.status, self.quality

        old_location = self.location
        # Changing the name of the file might also change its quality
        same_name = old_location and os.path.normpath(old_location) == os.path.normpath(filepath)

        old_size = self.file_size
        # Setting a location to episode, will get the size of the filepath
        with self.lock:
            self.location = filepath
        # If size from given filepath is 0 it means we couldn't determine file size
        same_size = old_size > 0 and self.file_size > 0 and self.file_size == old_size

        if not same_size or not same_name:
            log.debug(
                '{name}: The old episode had a different file associated with it, '
                're-checking the quality using the new filename {filepath}',
                {'name': self.series.name, 'filepath': filepath}
            )

            new_quality = Quality.name_quality(filepath, self.series.is_anime)

            if old_status in (SNATCHED, SNATCHED_PROPER, SNATCHED_BEST) or (
                    old_status == DOWNLOADED and old_location) or (
                    old_status == WANTED and not old_location):
                new_status = DOWNLOADED
            else:
                new_status = ARCHIVED

            with self.lock:
                self.status = new_status
                self.quality = new_quality

                if not same_name:
                    # Reset release name as the name changed
                    self.release_name = ''

            log.debug(
                "{name}: Setting the status from '{status_old}' to '{status_new}' and"
                " quality '{quality_old}' to '{quality_new}' based on file: {filepath}", {
                    'name': self.series.name,
                    'status_old': statusStrings[old_status],
                    'status_new': statusStrings[new_status],
                    'quality_old': Quality.qualityStrings[old_quality],
                    'quality_new': Quality.qualityStrings[new_quality],
                    'filepath': filepath,
                }
            )
        else:
            log.debug(
                "{name}: Not changing current status '{status_old}' or"
                " quality '{quality_old}' based on file: {filepath}", {
                    'name': self.series.name,
                    'status_old': statusStrings[old_status],
                    'quality_old': Quality.qualityStrings[old_quality],
                    'filepath': filepath,
                }
            )
