# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
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
"""Episode classes."""

from __future__ import unicode_literals

import datetime
import logging
import os.path
import re
import shutil
import time
from collections import (
    OrderedDict,
)

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
    NAMING_DUPLICATE,
    NAMING_EXTEND,
    NAMING_LIMITED_EXTEND,
    NAMING_LIMITED_EXTEND_E_PREFIXED,
    NAMING_SEPARATED_REPEAT,
    Quality,
    SKIPPED,
    UNAIRED,
    UNKNOWN,
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
from medusa.indexers.indexer_api import indexerApi
from medusa.indexers.indexer_config import indexerConfig
from medusa.indexers.indexer_exceptions import (
    IndexerEpisodeNotFound,
    IndexerError,
    IndexerSeasonNotFound,
)
from medusa.name_parser.parser import (
    InvalidNameException,
    InvalidShowException,
    NameParser,
)
from medusa.sbdatetime import sbdatetime
from medusa.scene_numbering import (
    get_scene_absolute_numbering,
    get_scene_numbering,
    xem_refresh,
)
from medusa.tv.base import TV

import shutil_custom

try:
    import xml.etree.cElementTree as ETree
except ImportError:
    import xml.etree.ElementTree as ETree

shutil.copyfile = shutil_custom.copyfile_custom

MILLIS_YEAR_1900 = datetime.datetime(year=1900, month=1, day=1).toordinal()

logger = logging.getLogger(__name__)


class Episode(TV):
    """Represent a TV Show episode."""

    def __init__(self, show, season, episode, filepath='', status=UNKNOWN):
        """Instantiate a Episode with database information."""
        super(Episode, self).__init__(
            int(show.indexer) if show else 0,
            0,
            {'show',
             'scene_season',
             'scene_episode',
             'scene_absolute_number',
             'related_episodes',
             'wanted_quality'}
        )
        self.show = show
        self.name = ''
        self.season = season
        self.episode = episode
        self.absolute_number = 0
        self.description = ''
        self.subtitles = list()
        self.subtitles_searchcount = 0
        self.subtitles_lastsearch = str(datetime.datetime.min)
        self.airdate = datetime.date.fromordinal(1)
        self.hasnfo = False
        self.hastbn = False
        self.status = status
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
        if show:
            self._specify_episode(self.season, self.episode)
            self.check_for_meta_files()

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
            if parse_result.show.is_anime and parse_result.ab_episode_numbers:
                results = [parse_result.show.get_episode(absolute_number=episode_number, should_cache=False)
                           for episode_number in parse_result.ab_episode_numbers]

            if not parse_result.show.is_anime and parse_result.episode_numbers:
                results = [parse_result.show.get_episode(season=parse_result.season_number,
                                                         episode=episode_number, should_cache=False)
                           for episode_number in parse_result.episode_numbers]

            for episode in results:
                episode.related_episodes = list(results[1:])
                return episode  # only root episode has related_episodes

        except (InvalidNameException, InvalidShowException):
            logger.warning('Cannot create Episode from path {path}', path=filepath)

    @property
    def identifier(self):
        """Return the episode identifier.

        :return:
        :rtype: string
        """
        if self.show.air_by_date and self.airdate is not None:
            return self.airdate.strftime(dateFormat)
        if self.show.is_anime and self.absolute_number is not None:
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
        logger.debug('{id}: Setter sets location to {location}',
                     id=self.show.indexerid, location=value)
        self._location = value
        self.file_size = os.path.getsize(value) if value and self.is_location_valid(value) else 0

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
        return knowit.know(self.location)

    def refresh_subtitles(self):
        """Look for subtitles files and refresh the subtitles property."""
        current_subtitles = subtitles.get_current_subtitles(self)
        ep_num = (episode_num(self.season, self.episode) or
                  episode_num(self.season, self.episode, numbering='absolute'))
        if self.subtitles == current_subtitles:
            logger.debug('{id}: No changed subtitles for {show} {ep}. Current subtitles: {subs}',
                         id=self.show.indexerid, show=self.show.name, ep=ep_num, subs=current_subtitles)
        else:
            logger.debug('{id}: Subtitle changes detected for this show {show} {ep}. Current subtitles: {subs}',
                         id=self.show.indexerid, show=self.show.name, ep=ep_num, subs=current_subtitles)
            self.subtitles = current_subtitles if current_subtitles else []
            logger.debug('{id}: Saving subtitles changes to database', id=self.show.indexerid)
            self.save_to_db()

    def download_subtitles(self, lang=None):
        """Download subtitles.

        :param lang:
        :type lang: string
        """
        if not self.is_location_valid():
            logger.debug("{id}: {show} {ep} file doesn't exist, can't download subtitles",
                         id=self.show.indexerid, show=self.show.name,
                         ep=(episode_num(self.season, self.episode) or episode_num(self.season, self.episode,
                                                                                   numbering='absolute')))
            return

        new_subtitles = subtitles.download_subtitles(self, lang=lang)
        if new_subtitles:
            self.subtitles = subtitles.merge_subtitles(self.subtitles, new_subtitles)

        self.subtitles_searchcount += 1 if self.subtitles_searchcount else 1
        self.subtitles_lastsearch = datetime.datetime.now().strftime(dateTimeFormat)
        logger.debug('{id}: Saving last subtitles search to database', id=self.show.indexerid)
        self.save_to_db()

        if new_subtitles:
            subtitle_list = ', '.join([subtitles.name_from_code(code) for code in new_subtitles])
            logger.info('{id}: Downloaded {subs} subtitles for {show} {ep}',
                        id=self.show.indexerid, subs=subtitle_list, show=self.show.name,
                        ep=(episode_num(self.season, self.episode) or
                            episode_num(self.season, self.episode, numbering='absolute')))

            notifiers.notify_subtitle_download(self.pretty_name(), subtitle_list)
        else:
            logger.info('{id}: No subtitles found for {show} {ep}',
                        id=self.show.indexerid, show=self.show.name,
                        ep=(episode_num(self.season, self.episode) or
                            episode_num(self.season, self.episode, numbering='absolute')))

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

        for metadata_provider in app.metadata_provider_dict.values():
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
                    logger.error('{id}: There was an error loading the NFO for episode {show} {ep}',
                                 id=self.show.indexerid, show=self.show.name, ep=episode_num(season, episode))

                # if we tried loading it from NFO and didn't find the NFO, try the Indexers
                if not self.hasnfo:
                    try:
                        result = self.load_from_indexer(season, episode)
                    except EpisodeDeletedException:
                        result = False

                    # if we failed SQL *and* NFO, Indexers then fail
                    if not result:
                        raise EpisodeNotFoundException("{id}: Couldn't find episode {show} {ep}".format
                                                       (id=self.show.indexerid, show=self.show.name,
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
            b'SELECT '
            b'  * '
            b'FROM '
            b'  tv_episodes '
            b'WHERE '
            b'  showid = ? '
            b'  AND season = ? '
            b'  AND episode = ?', [self.show.indexerid, season, episode])

        if len(sql_results) > 1:
            raise MultipleEpisodesInDatabaseException('Your DB has two records for the same show somehow.')
        elif not sql_results:
            logger.debug('{id}: {show} {ep} not found in the database',
                         id=self.show.indexerid, show=self.show.name, ep=episode_num(self.season, self.episode))
            return False
        else:
            if sql_results[0][b'name']:
                self.name = sql_results[0][b'name']

            self.season = season
            self.episode = episode
            self.absolute_number = sql_results[0][b'absolute_number']
            self.description = sql_results[0][b'description']
            if not self.description:
                self.description = ''
            if sql_results[0][b'subtitles'] and sql_results[0][b'subtitles']:
                self.subtitles = sql_results[0][b'subtitles'].split(',')
            self.subtitles_searchcount = sql_results[0][b'subtitles_searchcount']
            self.subtitles_lastsearch = sql_results[0][b'subtitles_lastsearch']
            self.airdate = datetime.date.fromordinal(int(sql_results[0][b'airdate']))
            self.status = int(sql_results[0][b'status'] or -1)

            # don't overwrite my location
            if sql_results[0][b'location']:
                self.location = os.path.normpath(sql_results[0][b'location'])
            if sql_results[0][b'file_size']:
                self.file_size = int(sql_results[0][b'file_size'])
            else:
                self.file_size = 0

            self.indexerid = int(sql_results[0][b'indexerid'])
            self.indexer = int(sql_results[0][b'indexer'])

            xem_refresh(self.show.indexerid, self.show.indexer)

            self.scene_season = try_int(sql_results[0][b'scene_season'], 0)
            self.scene_episode = try_int(sql_results[0][b'scene_episode'], 0)
            self.scene_absolute_number = try_int(sql_results[0][b'scene_absolute_number'], 0)

            if self.scene_absolute_number == 0:
                self.scene_absolute_number = get_scene_absolute_numbering(
                    self.show.indexerid,
                    self.show.indexer,
                    self.absolute_number
                )

            if self.scene_season == 0 or self.scene_episode == 0:
                self.scene_season, self.scene_episode = get_scene_numbering(
                    self.show.indexerid,
                    self.show.indexer,
                    self.season, self.episode
                )

            if sql_results[0][b'release_name'] is not None:
                self.release_name = sql_results[0][b'release_name']

            if sql_results[0][b'is_proper']:
                self.is_proper = int(sql_results[0][b'is_proper'])

            if sql_results[0][b'version']:
                self.version = int(sql_results[0][b'version'])

            if sql_results[0][b'release_group'] is not None:
                self.release_group = sql_results[0][b'release_group']

            self.loaded = True
            self.reset_dirty()
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
                show = self.show.indexer_api[self.show.indexerid]
                my_ep = show[season][episode]

        except (IndexerError, IOError) as e:
            logger.warning('{id}: {indexer} threw up an error: {error_msg}',
                           id=self.show.indexerid, indexer=indexerApi(self.indexer).name, error_msg=ex(e))

            # if the episode is already valid just log it, if not throw it up
            if self.name:
                logger.debug(
                    '{id}: {indexer} timed out but we have enough info from other sources, allowing the error',
                    id=self.show.indexerid, indexer=indexerApi(self.indexer).name)
                return
            else:
                logger.warning('{id}: {indexer} timed out, unable to create the episode',
                               id=self.show.indexerid, indexer=indexerApi(self.indexer).name)
                return False
        except (IndexerEpisodeNotFound, IndexerSeasonNotFound):
            logger.debug('{id}: Unable to find the episode on {indexer}. Deleting it from db',
                         id=self.show.indexerid, indexer=indexerApi(self.indexer).name)
            # if I'm no longer on the Indexers but I once was then delete myself from the DB
            if self.indexerid != -1:
                self.delete_episode()
            return

        if getattr(my_ep, 'episodename', None) is None:
            logger.info('{id}: {show} {ep} has no name on {indexer}. Setting to an empty string',
                        id=self.show.indexerid, show=self.show.name, ep=episode_num(season, episode),
                        indexer=indexerApi(self.indexer).name)
            setattr(my_ep, 'episodename', '')

        if getattr(my_ep, 'absolute_number', None) is None:
            logger.debug('{id}: {show} {ep} has no absolute number on {indexer}',
                         id=self.show.indexerid, show=self.show.name, ep=episode_num(season, episode),
                         indexer=indexerApi(self.indexer).name)
        else:
            logger.debug('{id}: {show} {ep} has absolute number: {absolute} ',
                         id=self.show.indexerid, show=self.show.name, ep=episode_num(season, episode),
                         absolute=my_ep['absolute_number'])
            self.absolute_number = int(my_ep['absolute_number'])

        self.name = getattr(my_ep, 'episodename', '')
        self.season = season
        self.episode = episode

        xem_refresh(self.show.indexerid, self.show.indexer)

        self.scene_absolute_number = get_scene_absolute_numbering(
            self.show.indexerid,
            self.show.indexer,
            self.absolute_number
        )

        self.scene_season, self.scene_episode = get_scene_numbering(
            self.show.indexerid,
            self.show.indexer,
            self.season, self.episode
        )

        self.description = getattr(my_ep, 'overview', '')

        firstaired = getattr(my_ep, 'firstaired', None)
        if not firstaired or firstaired == '0000-00-00':
            firstaired = str(datetime.date.fromordinal(1))
        raw_airdate = [int(x) for x in firstaired.split('-')]

        try:
            self.airdate = datetime.date(raw_airdate[0], raw_airdate[1], raw_airdate[2])
        except (ValueError, IndexError):
            logger.warning('{id}: Malformed air date of {aired} retrieved from {indexer} for {show} {ep}',
                           id=self.show.indexerid, aired=firstaired, indexer=indexerApi(self.indexer).name,
                           show=self.show.name, ep=episode_num(season, episode))
            # if I'm incomplete on the indexer but I once was complete then just delete myself from the DB for now
            if self.indexerid != -1:
                self.delete_episode()
            return False

        # early conversion to int so that episode doesn't get marked dirty
        self.indexerid = getattr(my_ep, 'id', None)
        if self.indexerid is None:
            logger.error('{id}: Failed to retrieve ID from {indexer}',
                         id=self.show.indexerid, indexer=indexerApi(self.indexer).name)
            if self.indexerid != -1:
                self.delete_episode()
            return False

        # don't update show status if show dir is missing, unless it's missing on purpose
        if all([not self.show.is_location_valid(),
                not app.CREATE_MISSING_SHOW_DIRS,
                not app.ADD_SHOWS_WO_DIR]):
            logger.warning("{id}: Show {show} location '{location}' is missing. Keeping current episode statuses",
                           id=self.show.indexerid, show=self.show.name, location=self.show.raw_location)
            return

        if self.location:
            logger.debug("{id}: {show} {ep} has status '{status}' and location {location}",
                         id=self.show.indexerid, show=self.show.name, ep=episode_num(season, episode),
                         status=statusStrings[self.status].upper(), location=self.location)

        if not os.path.isfile(self.location):
            if (self.airdate >= datetime.date.today() or self.airdate == datetime.date.fromordinal(1)) and \
                    self.status in (UNAIRED, UNKNOWN, WANTED):
                # Need to check if is UNAIRED otherwise code will step into second 'IF'
                # and make episode as default_ep_status
                # If is a leaked episode and user manually snatched, it will respect status
                # If is a fake (manually snatched), when user set as FAILED, status will be WANTED
                # and code below will make it UNAIRED again
                logger.debug("{id}: {show} {ep} airs in the future or has no airdate, marking it '{status}'",
                             id=self.show.indexerid, show=self.show.name, ep=episode_num(season, episode),
                             status=statusStrings[UNAIRED].upper())
                self.status = UNAIRED
            elif self.status in (UNAIRED, UNKNOWN):
                # Only do UNAIRED/UNKNOWN, it could already be snatched/ignored/skipped,
                # or downloaded/archived to disconnected media
                new_status = self.show.default_ep_status if self.season > 0 else SKIPPED  # auto-skip specials
                logger.debug("{id}: {show} {ep} has already aired, marking it '{status}'",
                             id=self.show.indexerid, show=self.show.name, ep=episode_num(season, episode),
                             status=statusStrings[new_status].upper())
                self.status = new_status
            else:
                logger.debug("{id}: {show} {ep} status untouched: '{status}'",
                             id=self.show.indexerid, show=self.show.name,
                             ep=episode_num(season, episode), status=statusStrings[self.status].upper())

        #  We only change the episode's status if a file exists and the status is not SNATCHED|DOWNLOADED|ARCHIVED
        elif helpers.is_media_file(self.location):
            if self.status not in Quality.SNATCHED_PROPER + Quality.DOWNLOADED + Quality.SNATCHED + \
                    Quality.ARCHIVED + Quality.SNATCHED_BEST:
                old_status = self.status
                self.status = Quality.status_from_name(self.location, anime=self.show.is_anime)
                logger.debug("{id}: {show} {ep} status changed from '{old_status}' to '{new_status}' "
                             "as current status is not SNATCHED|DOWNLOADED|ARCHIVED",
                             id=self.show.indexerid, show=self.show.name, ep=episode_num(season, episode),
                             old_status=statusStrings[old_status].upper(),
                             new_status=statusStrings[self.status].upper())

            else:
                logger.debug("{id}: {show} {ep} status untouched: '{status}'",
                             id=self.show.indexerid, show=self.show.name,
                             ep=episode_num(season, episode), status=statusStrings[self.status].upper())

        # shouldn't get here probably
        else:
            logger.warning("{id}: {show} {ep} status changed from '{old_status}' to 'UNKNOWN'",
                           id=self.show.indexerid, show=self.show.name, ep=episode_num(season, episode),
                           old_status=statusStrings[self.status].upper())
            self.status = UNKNOWN

    def __load_from_nfo(self, location):

        if not self.show.is_location_valid():
            logger.warning('{id}: The show location {location} is missing, unable to load metadata',
                           id=self.show.indexerid, location=location)
            return

        logger.debug('{id}: Loading episode details from the NFO file associated with {location}',
                     id=self.show.indexerid, location=location)

        self.location = location

        if self.location != '':

            if self.status == UNKNOWN and helpers.is_media_file(self.location):
                self.status = Quality.status_from_name(self.location, anime=self.show.is_anime)
                logger.debug("{id}: {show} {ep} status changed from 'UNKNOWN' to '{new_status}'",
                             id=self.show.indexerid, show=self.show.name, ep=episode_num(self.season, self.episode),
                             new_status=self.status)

            nfo_file = replace_extension(self.location, 'nfo')
            logger.debug('{id}: Using NFO name {nfo}', id=self.show.indexerid, nfo=nfo_file)

            if os.path.isfile(nfo_file):
                try:
                    show_xml = ETree.ElementTree(file=nfo_file)
                except (SyntaxError, ValueError) as e:
                    logger.error('{id}: Error loading the NFO, backing up the NFO and skipping for now: {error_msg}',
                                 id=self.show.indexerid, error_msg=ex(e))
                    try:
                        os.rename(nfo_file, nfo_file + '.old')
                    except Exception as e:
                        logger.warning("{id}: Failed to rename your episode's NFO file. "
                                       'You need to delete it or fix it: {error_msg}',
                                       id=self.show.indexerid, error_msg=ex(e))
                    raise NoNFOException('Error in NFO format')

                for ep_details in list(show_xml.iter('episodedetails')):
                    if (ep_details.findtext('season') is None or int(ep_details.findtext('season')) != self.season or
                            ep_details.findtext('episode') is None or
                            int(ep_details.findtext('episode')) != self.episode):
                        logger.debug('{id}: NFO has an <episodedetails> block for a different episode - '
                                     'wanted {ep_wanted} but got {ep_found}',
                                     id=self.show.indexerid, ep_wanted=episode_num(self.season, self.episode),
                                     ep_found=episode_num(ep_details.findtext('season'),
                                                          ep_details.findtext('episode')))
                        continue

                    if ep_details.findtext('title') is None or ep_details.findtext('aired') is None:
                        raise NoNFOException('Error in NFO format (missing episode title or airdate)')

                    self.name = ep_details.findtext('title')
                    self.episode = int(ep_details.findtext('episode'))
                    self.season = int(ep_details.findtext('season'))

                    self.scene_absolute_number = get_scene_absolute_numbering(
                        self.show.indexerid,
                        self.show.indexer,
                        self.absolute_number
                    )

                    self.scene_season, self.scene_episode = get_scene_numbering(
                        self.show.indexerid,
                        self.show.indexer,
                        self.season, self.episode
                    )

                    self.description = ep_details.findtext('plot')
                    if self.description is None:
                        self.description = ''

                    if ep_details.findtext('aired'):
                        raw_airdate = [int(x) for x in ep_details.findtext('aired').split('-')]
                        self.airdate = datetime.date(raw_airdate[0], raw_airdate[1], raw_airdate[2])
                    else:
                        self.airdate = datetime.date.fromordinal(1)

                    self.hasnfo = True
            else:
                self.hasnfo = False

            self.hastbn = bool(os.path.isfile(replace_extension(nfo_file, 'tbn')))

    def __str__(self):
        """String representation.

        :return:
        :rtype: unicode
        """
        result = ''
        result += '%r - %r - %r\n' % (self.show.name, episode_num(self.season, self.episode), self.name)
        result += 'location: %r\n' % self.location
        result += 'description: %r\n' % self.description
        result += 'subtitles: %r\n' % ','.join(self.subtitles)
        result += 'subtitles_searchcount: %r\n' % self.subtitles_searchcount
        result += 'subtitles_lastsearch: %r\n' % self.subtitles_lastsearch
        result += 'airdate: %r (%r)\n' % (self.airdate.toordinal(), self.airdate)
        result += 'hasnfo: %r\n' % self.hasnfo
        result += 'hastbn: %r\n' % self.hastbn
        result += 'status: %r\n' % self.status
        return result

    def to_json(self, detailed=True):
        """Return the json representation."""
        indexer_name = indexerConfig[self.indexer]['identifier']
        parsed_airdate = sbdatetime.convert_to_setting(
            network_timezones.parse_date_time(
                datetime.datetime.toordinal(self.airdate),
                self.show.airs,
                self.show.network
            )
        ).isoformat('T')
        data = OrderedDict([
            ('identifier', self.identifier),
            ('id', OrderedDict([
                (indexer_name, self.indexerid),
            ])),
            ('season', self.season),
            ('episode', self.episode),
            ('absoluteNumber', self.absolute_number),
            ('airDate', parsed_airdate),
            ('title', self.name),
            ('description', self.description),
            ('hasNfo', self.hasnfo),
            ('hasTbn', self.hastbn),
            ('subtitles', self.subtitles),
            ('status', statusStrings[Quality.split_composite_status(self.status).status]),
            ('releaseName', self.release_name),
            ('isProper', self.is_proper),
            ('version', self.version),
            ('scene', OrderedDict([
                ('season', self.scene_season),
                ('episode', self.scene_episode),
                ('absoluteNumber', self.scene_absolute_number),
            ])),
            ('location', self.location),
            ('fileSize', self.file_size),
        ])
        if detailed:
            data.update(OrderedDict([
                ('releaseGroup', self.release_group),
                ('subtitlesSearchCount', self.subtitles_searchcount),
                ('subtitlesLastSearched', self.subtitles_lastsearch),
                ('wantedQualities', self.wanted_quality),
                ('relatedEpisodes', [ep.identifier() for ep in self.related_episodes]),
            ]))
        return data

    def create_meta_files(self):
        """Create episode metadata files."""
        if not self.show.is_location_valid():
            logger.warning('{id}: The show dir is missing, unable to create metadata', id=self.show.indexerid)
            return

        for metadata_provider in app.metadata_provider_dict.values():
            self.__create_nfo(metadata_provider)
            self.__create_thumbnail(metadata_provider)

        if self.check_for_meta_files():
            logger.debug('{id}: Saving metadata changes to database', id=self.show.indexerid)
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
        logger.debug('{id}: Deleting {show} {ep} from the DB',
                     id=self.show.indexerid, show=self.show.name,
                     ep=episode_num(self.season, self.episode))

        # remove myself from the show dictionary
        if self.show.get_episode(self.season, self.episode, no_create=True) == self:
            logger.debug("{id}: Removing myself from my show's list",
                         id=self.show.indexerid)
            del self.show.episodes[self.season][self.episode]

        # delete myself from the DB
        logger.debug('{id}: Deleting myself from the database',
                     id=self.show.indexerid)
        main_db_con = db.DBConnection()
        sql = b'DELETE FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ?'
        main_db_con.action(sql, [self.show.indexerid, self.season, self.episode])

        raise EpisodeDeletedException()

    def get_sql(self):
        """Create SQL queue for this episode if any of its data has been changed since the last save."""
        try:
            if not self.dirty:
                logger.debug('{id}: Not creating SQL queue - record is not dirty',
                             id=self.show.indexerid)
                return

            main_db_con = db.DBConnection()
            rows = main_db_con.select(
                b'SELECT '
                b'  episode_id, '
                b'  subtitles '
                b'FROM '
                b'  tv_episodes '
                b'WHERE '
                b'  showid = ? '
                b'  AND season = ? '
                b'  AND episode = ?',
                [self.show.indexerid, self.season, self.episode])

            ep_id = None
            if rows:
                ep_id = int(rows[0][b'episode_id'])

            if ep_id:
                # use a custom update method to get the data into the DB for existing records.
                # Multi or added subtitle or removed subtitles
                if app.SUBTITLES_MULTI or not rows[0][b'subtitles'] or not self.subtitles:
                    return [
                        b'UPDATE '
                        b'  tv_episodes '
                        b'SET '
                        b'  indexerid = ?, '
                        b'  indexer = ?, '
                        b'  name = ?, '
                        b'  description = ?, '
                        b'  subtitles = ?, '
                        b'  subtitles_searchcount = ?, '
                        b'  subtitles_lastsearch = ?, '
                        b'  airdate = ?, '
                        b'  hasnfo = ?, '
                        b'  hastbn = ?, '
                        b'  status = ?, '
                        b'  location = ?, '
                        b'  file_size = ?, '
                        b'  release_name = ?, '
                        b'  is_proper = ?, '
                        b'  showid = ?, '
                        b'  season = ?, '
                        b'  episode = ?, '
                        b'  absolute_number = ?, '
                        b'  version = ?, '
                        b'  release_group = ?, '
                        b'  manually_searched = ? '
                        b'WHERE '
                        b'  episode_id = ?',
                        [self.indexerid, self.indexer, self.name, self.description, ','.join(self.subtitles),
                         self.subtitles_searchcount, self.subtitles_lastsearch, self.airdate.toordinal(), self.hasnfo,
                         self.hastbn, self.status, self.location, self.file_size, self.release_name, self.is_proper,
                         self.show.indexerid, self.season, self.episode, self.absolute_number, self.version,
                         self.release_group, self.manually_searched, ep_id]]
                else:
                    # Don't update the subtitle language when the srt file doesn't contain the
                    # alpha2 code, keep value from subliminal
                    return [
                        b'UPDATE '
                        b'  tv_episodes '
                        b'SET '
                        b'  indexerid = ?, '
                        b'  indexer = ?, '
                        b'  name = ?, '
                        b'  description = ?, '
                        b'  subtitles_searchcount = ?, '
                        b'  subtitles_lastsearch = ?, '
                        b'  airdate = ?, '
                        b'  hasnfo = ?, '
                        b'  hastbn = ?, '
                        b'  status = ?, '
                        b'  location = ?, '
                        b'  file_size = ?, '
                        b'  release_name = ?, '
                        b'  is_proper = ?, '
                        b'  showid = ?, '
                        b'  season = ?, '
                        b'  episode = ?, '
                        b'  absolute_number = ?, '
                        b'  version = ?, '
                        b'  release_group = ?, '
                        b'  manually_searched = ? '
                        b'WHERE '
                        b'  episode_id = ?',
                        [self.indexerid, self.indexer, self.name, self.description,
                         self.subtitles_searchcount, self.subtitles_lastsearch, self.airdate.toordinal(), self.hasnfo,
                         self.hastbn, self.status, self.location, self.file_size, self.release_name, self.is_proper,
                         self.show.indexerid, self.season, self.episode, self.absolute_number, self.version,
                         self.release_group, self.manually_searched, ep_id]]
            else:
                # use a custom insert method to get the data into the DB.
                return [
                    b'INSERT OR IGNORE INTO '
                    b'  tv_episodes '
                    b'  (episode_id, '
                    b'  indexerid, '
                    b'  indexer, '
                    b'  name, '
                    b'  description, '
                    b'  subtitles, '
                    b'  subtitles_searchcount, '
                    b'  subtitles_lastsearch, '
                    b'  airdate, '
                    b'  hasnfo, '
                    b'  hastbn, '
                    b'  status, '
                    b'  location, '
                    b'  file_size, '
                    b'  release_name, '
                    b'  is_proper, '
                    b'  showid, '
                    b'  season, '
                    b'  episode, '
                    b'  absolute_number, '
                    b'  version, '
                    b'  release_group) '
                    b'VALUES '
                    b'  ((SELECT episode_id FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ?), '
                    b'  ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);',
                    [self.show.indexerid, self.season, self.episode, self.indexerid, self.indexer, self.name,
                     self.description, ','.join(self.subtitles), self.subtitles_searchcount, self.subtitles_lastsearch,
                     self.airdate.toordinal(), self.hasnfo, self.hastbn, self.status, self.location, self.file_size,
                     self.release_name, self.is_proper, self.show.indexerid, self.season, self.episode,
                     self.absolute_number, self.version, self.release_group]]
        except Exception as e:
            logger.error('{id}: Error while updating database: {error_msg}', id=self.show.indexerid, error_msg=repr(e))

    def save_to_db(self):
        """Save this episode to the database if any of its data has been changed since the last save."""
        if not self.dirty:
            return

        new_value_dict = {b'indexerid': self.indexerid,
                          b'indexer': self.indexer,
                          b'name': self.name,
                          b'description': self.description,
                          b'subtitles': ','.join(self.subtitles),
                          b'subtitles_searchcount': self.subtitles_searchcount,
                          b'subtitles_lastsearch': self.subtitles_lastsearch,
                          b'airdate': self.airdate.toordinal(),
                          b'hasnfo': self.hasnfo,
                          b'hastbn': self.hastbn,
                          b'status': self.status,
                          b'location': self.location,
                          b'file_size': self.file_size,
                          b'release_name': self.release_name,
                          b'is_proper': self.is_proper,
                          b'absolute_number': self.absolute_number,
                          b'version': self.version,
                          b'release_group': self.release_group}

        control_value_dict = {b'showid': self.show.indexerid,
                              b'season': self.season,
                              b'episode': self.episode}

        # use a custom update/insert method to get the data into the DB
        main_db_con = db.DBConnection()
        main_db_con.upsert(b'tv_episodes', new_value_dict, control_value_dict)
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
            return os.path.join(self.show.location, self.location)

    def pretty_name(self):
        """Return the name of this episode in a "pretty" human-readable format.

        Used for logging and notifications and such.

        :return: A string representing the episode's name and season/ep numbers
        :rtype: str
        """
        if self.show.anime and not self.show.scene:
            return self._format_pattern('%SN - %AB - %EN')
        elif self.show.air_by_date:
            return self._format_pattern('%SN - %AD - %EN')

        return self._format_pattern('%SN - S%0SE%0E - %EN')

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

        def release_group(show, name):
            if name:
                name = remove_extension(name)
            else:
                return ''

            try:
                parse_result = NameParser(show=show, naming_pattern=True).parse(name)
            except (InvalidNameException, InvalidShowException) as e:
                logger.debug('Unable to parse release_group: {error_msg}', error_msg=ex(e))
                return ''

            if not parse_result.release_group:
                return ''
            return parse_result.release_group.strip('.- []{}')

        _, ep_qual = Quality.split_composite_status(self.status)  # @UnusedVariable

        if app.NAMING_STRIP_YEAR:
            show_name = re.sub(r'\(\d+\)$', '', self.show.name).rstrip()
        else:
            show_name = self.show.name

        # try to get the release group
        rel_grp = {
            app.UNKNOWN_RELEASE_GROUP: app.UNKNOWN_RELEASE_GROUP
        }
        if hasattr(self, 'location'):  # from the location name
            rel_grp['location'] = release_group(self.show, self.location)
            if not rel_grp['location']:
                del rel_grp['location']
        if hasattr(self, 'release_group'):  # from the release group field in db
            rel_grp['database'] = self.release_group.strip('.- []{}')
            if not rel_grp['database']:
                del rel_grp['database']
        if hasattr(self, 'release_name'):  # from the release name field in db
            rel_grp['release_name'] = release_group(self.show, self.release_name)
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
        encoder = Quality.scene_quality_from_name(self.release_name.replace(rel_grp[relgrp], ''), ep_qual)
        if encoder:
            logger.debug('Found codec for {show} {ep}', show=show_name, ep=ep_name)

        return {
            '%SN': show_name,
            '%S.N': dot(show_name),
            '%S_N': us(show_name),
            '%EN': ep_name,
            '%E.N': dot(ep_name),
            '%E_N': us(ep_name),
            '%QN': Quality.qualityStrings[ep_qual],
            '%Q.N': dot(Quality.qualityStrings[ep_qual]),
            '%Q_N': us(Quality.qualityStrings[ep_qual]),
            '%SQN': Quality.sceneQualityStrings[ep_qual] + encoder,
            '%SQ.N': dot(Quality.sceneQualityStrings[ep_qual] + encoder),
            '%SQ_N': us(Quality.sceneQualityStrings[ep_qual] + encoder),
            '%S': str(self.season),
            '%0S': '%02d' % self.season,
            '%E': str(self.episode),
            '%0E': '%02d' % self.episode,
            '%XS': str(self.scene_season),
            '%0XS': '%02d' % self.scene_season,
            '%XE': str(self.scene_episode),
            '%0XE': '%02d' % self.scene_episode,
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
            '%CY': str(datetime.date.today().year),
            '%CM': str(datetime.date.today().month),
            '%CD': str(datetime.date.today().day),
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
        for cur_replacement in sorted(replace_map.keys(), reverse=True):
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
                logger.debug('{id}: Episode has no release group, replacing it with {rg}',
                             id=self.show.indexerid, rg=replace_map['%RG'])
                self.release_group = replace_map['%RG']  # if release_group is not in the db, put it there

        # if there's no release name then replace it with a reasonable facsimile
        if not replace_map['%RN']:

            if self.show.air_by_date or self.show.sports:
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
                if multi in (NAMING_EXTEND, NAMING_LIMITED_EXTEND, NAMING_LIMITED_EXTEND_E_PREFIXED):
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
                if multi in (NAMING_LIMITED_EXTEND, NAMING_LIMITED_EXTEND_E_PREFIXED) and \
                        other_ep != self.related_episodes[-1]:
                    continue

                elif multi == NAMING_DUPLICATE:
                    # add " - S01"
                    ep_string += sep + season_format

                elif multi == NAMING_SEPARATED_REPEAT:
                    ep_string += sep

                # add "E04"
                ep_string += ep_sep

                if multi == NAMING_LIMITED_EXTEND_E_PREFIXED:
                    ep_string += 'E'

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
            if anime_type == 2:
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

        result_name = self.__format_string(result_name, replace_map)

        logger.debug('{id}: Formatting pattern: {pattern} -> {result_name}',
                     id=self.show.indexerid, pattern=pattern, result_name=result_name)

        return result_name

    def proper_path(self):
        """Figure out the path where this episode SHOULD be according to the renaming rules, relative from the show dir.

        :return:
        :rtype: str
        """
        anime_type = app.NAMING_ANIME
        if not self.show.is_anime:
            anime_type = 3

        result = self.formatted_filename(anime_type=anime_type)

        # if they want us to flatten it and we're allowed to flatten it then we will
        if self.show.flatten_folders and not app.NAMING_FORCE_FOLDERS:
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
            # we only use ABD if it's enabled, this is an ABD show, AND this is not a multi-ep
            if self.show.air_by_date and app.NAMING_CUSTOM_ABD and not self.related_episodes:
                pattern = app.NAMING_ABD_PATTERN
            elif self.show.sports and app.NAMING_CUSTOM_SPORTS and not self.related_episodes:
                pattern = app.NAMING_SPORTS_PATTERN
            elif self.show.anime and app.NAMING_CUSTOM_ANIME:
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
            # we only use ABD if it's enabled, this is an ABD show, AND this is not a multi-ep
            if self.show.air_by_date and app.NAMING_CUSTOM_ABD and not self.related_episodes:
                pattern = app.NAMING_ABD_PATTERN
            elif self.show.sports and app.NAMING_CUSTOM_SPORTS and not self.related_episodes:
                pattern = app.NAMING_SPORTS_PATTERN
            elif self.show.anime and app.NAMING_CUSTOM_ANIME:
                pattern = app.NAMING_ANIME_PATTERN
            else:
                pattern = app.NAMING_PATTERN

        # split off the dirs only, if they exist
        name_groups = re.split(r'[\\/]', pattern)

        return sanitize_filename(self._format_pattern(name_groups[-1], multi, anime_type))

    def rename(self):
        """Rename an episode file and all related files to the location and filename as specified in naming settings."""
        if not self.is_location_valid():
            logger.warning("{id} Can't perform rename on {location} when it doesn't exist, skipping",
                           id=self.indexerid, location=self.location)
            return

        proper_path = self.proper_path()
        absolute_proper_path = os.path.join(self.show.location, proper_path)
        absolute_current_path_no_ext, file_ext = os.path.splitext(self.location)
        absolute_current_path_no_ext_length = len(absolute_current_path_no_ext)

        related_subs = []

        current_path = absolute_current_path_no_ext

        if absolute_current_path_no_ext.startswith(self.show.location):
            current_path = absolute_current_path_no_ext[len(self.show.location):]

        logger.debug('{id}: Renaming/moving episode from the base path {location} to {new_location}',
                     id=self.indexerid, location=self.location, new_location=absolute_proper_path)

        # if it's already named correctly then don't do anything
        if proper_path == current_path:
            logger.debug('{id}: File {location} is already named correctly, skipping',
                         id=self.indexerid, location=self.location)
            return

        related_files = post_processor.PostProcessor(self.location).list_associated_files(
            self.location, base_name_only=True, subfolders=True)

        # This is wrong. Cause of pp not moving subs.
        if self.show.subtitles and app.SUBTITLES_DIR != '':
            related_subs = post_processor.PostProcessor(
                self.location).list_associated_files(app.SUBTITLES_DIR, subtitles_only=True, subfolders=True)

        logger.debug('{id} Files associated to {location}: {related_files}',
                     id=self.indexerid, location=self.location, related_files=related_files)

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
                logger.warning('{id}: Unable to rename file {cur_file}',
                               id=self.indexerid, cur_file=cur_related_file)

        for cur_related_sub in related_subs:
            absolute_proper_subs_path = os.path.join(app.SUBTITLES_DIR, self.formatted_filename())
            cur_result = helpers.rename_ep_file(cur_related_sub, absolute_proper_subs_path,
                                                absolute_current_path_no_ext_length)
            if not cur_result:
                logger.warning('{id}: Unable to rename file {cur_file}',
                               id=self.indexerid, cur_file=cur_related_sub)

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
        """Make the modify date and time of a file reflect the show air date and time.

        Note: Also called from post_processor
        """
        if not all([app.AIRDATE_EPISODES, self.airdate, self.location,
                    self.show, self.show.airs, self.show.network]):
            return

        try:
            airdate_ordinal = self.airdate.toordinal()
            if airdate_ordinal < 1:
                return

            airdatetime = network_timezones.parse_date_time(airdate_ordinal, self.show.airs, self.show.network)

            if app.FILE_TIMESTAMP_TIMEZONE == 'local':
                airdatetime = airdatetime.astimezone(network_timezones.app_timezone)

            filemtime = datetime.datetime.fromtimestamp(
                os.path.getmtime(self.location)).replace(tzinfo=network_timezones.app_timezone)

            if filemtime != airdatetime:
                airdatetime = airdatetime.timetuple()
                logger.debug("{id}: About to modify date of '{location}' to show air date {air_date}",
                             id=self.show.indexerid, location=self.location,
                             air_date=time.strftime('%b %d,%Y (%H:%M)', airdatetime))
                try:
                    if helpers.touch_file(self.location, time.mktime(airdatetime)):
                        logger.info("{id}: Changed modify date of '{location}' to show air date {air_date}",
                                    id=self.show.indexerid, location=os.path.basename(self.location),
                                    air_date=time.strftime('%b %d,%Y (%H:%M)', airdatetime))
                    else:
                        logger.warning("{id}: Unable to modify date of '{location}' to show air date {air_date}",
                                       id=self.show.indexerid, location=os.path.basename(self.location),
                                       air_date=time.strftime('%b %d,%Y (%H:%M)', airdatetime))
                except Exception:
                    logger.warning("{id}: Failed to modify date of '{location}' to show air date {air_date}",
                                   id=self.show.indexerid, location=os.path.basename(self.location),
                                   air_date=time.strftime('%b %d,%Y (%H:%M)', airdatetime))
        except Exception:
            logger.warning("{id}: Failed to modify date of '{location}'",
                           id=self.show.indexerid, location=os.path.basename(self.location))
