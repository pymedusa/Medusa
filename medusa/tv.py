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
"""TVShow and TVEpisode classes."""

import datetime
import glob
import os.path
import re
import shutil
import stat
import threading
import time
import traceback

from collections import OrderedDict, namedtuple
from itertools import groupby

from imdb import imdb
from imdb._exceptions import IMDbDataAccessError, IMDbParserError

import knowit

import shutil_custom

from six import text_type

from . import app, db, helpers, image_cache, logger, network_timezones, notifiers, post_processor, subtitles
from .black_and_white_list import BlackAndWhiteList
from .common import (
    ARCHIVED, DOWNLOADED, IGNORED, NAMING_DUPLICATE, NAMING_EXTEND, NAMING_LIMITED_EXTEND,
    NAMING_LIMITED_EXTEND_E_PREFIXED, NAMING_SEPARATED_REPEAT, Overview, Quality, SKIPPED,
    SNATCHED, SNATCHED_PROPER, UNAIRED, UNKNOWN, WANTED, qualityPresets, statusStrings
)
from .helper.common import (
    dateFormat, dateTimeFormat, episode_num, pretty_file_size, remove_extension, replace_extension, sanitize_filename,
    try_int
)
from .helper.exceptions import (
    EpisodeDeletedException, EpisodeNotFoundException, MultipleEpisodesInDatabaseException,
    MultipleShowObjectsException, MultipleShowsInDatabaseException, NoNFOException, ShowDirectoryNotFoundException,
    ShowNotFoundException, ex
)
from .helper.externals import get_externals
from .indexers.indexer_api import indexerApi
from .indexers.indexer_config import INDEXER_TVDBV2, INDEXER_TVRAGE, indexerConfig, mappings, reverse_mappings
from .indexers.indexer_exceptions import (IndexerAttributeNotFound, IndexerEpisodeNotFound, IndexerError,
                                          IndexerSeasonNotFound)
from .name_parser.parser import InvalidNameException, InvalidShowException, NameParser
from .sbdatetime import sbdatetime
from .scene_exceptions import get_scene_exceptions
from .scene_numbering import get_scene_absolute_numbering, get_scene_numbering, xem_refresh
from .show.show import Show

try:
    import xml.etree.cElementTree as ETree
except ImportError:
    import xml.etree.ElementTree as ETree

try:
    from send2trash import send2trash
except ImportError:
    app.TRASH_REMOVE_SHOW = 0


shutil.copyfile = shutil_custom.copyfile_custom

MILLIS_YEAR_1900 = datetime.datetime(year=1900, month=1, day=1).toordinal()


class TVObject(object):
    """Base class for TVShow and TVEpisode."""

    def __init__(self, indexer, indexerid, ignored_properties):
        """Constructor with ignore_properties.

        :param indexer:
        :type indexer: int
        :param indexerid:
        :type indexerid: int
        :param ignored_properties:
        :type ignored_properties: set(str)
        """
        self.__dirty = True
        self.__ignored_properties = ignored_properties | {'lock'}
        self.indexer = int(indexer)
        self.indexerid = int(indexerid)
        self.lock = threading.Lock()

    def __setattr__(self, key, value):
        """Set the corresponding attribute and use the dirty flag if the new value is different from the old value.

        :param key:
        :type key: str
        :param value:
        """
        if key == '_location' or (not key.startswith('_') and key not in self.__ignored_properties):
            self.__dirty |= self.__dict__.get(key) != value

        super(TVObject, self).__setattr__(key, value)

    @property
    def dirty(self):
        """Return the dirty flag.

        :return:
        :rtype: bool
        """
        return self.__dirty

    def reset_dirty(self):
        """Reset the dirty flag."""
        self.__dirty = False

    @property
    def tvdb_id(self):
        """Return the tvdb_id.

        :return:
        :rtype: int
        """
        return self.indexerid if self.indexerid and self.indexer == INDEXER_TVDBV2 else None

    def __getstate__(self):
        """Get threading lock state.

        :return:
        :rtype: dict(str -> threading.Lock)
        """
        d = dict(self.__dict__)
        del d['lock']
        return d

    def __setstate__(self, d):
        """Set threading lock state."""
        d['lock'] = threading.Lock()
        self.__dict__.update(d)


class TVShow(TVObject):
    """Represent a TV Show."""

    def __init__(self, indexer, indexerid, lang='', quality=None, flatten_folders=None, enabled_subtitles=None):
        """Instantiate a TVShow with database information based on indexerid.

        :param indexer:
        :type indexer: int
        :param indexerid:
        :type indexerid: int
        :param lang:
        :type lang: str
        """
        super(TVShow, self).__init__(indexer, indexerid, {'episodes', 'nextaired', 'release_groups'})
        self.name = ''
        self.imdbid = ''
        self.network = ''
        self.genre = ''
        self.classification = ''
        self.runtime = 0
        self.imdb_info = {}
        self.quality = quality or int(app.QUALITY_DEFAULT)
        self.flatten_folders = flatten_folders or int(app.FLATTEN_FOLDERS_DEFAULT)
        self.status = 'Unknown'
        self.airs = ''
        self.startyear = 0
        self.paused = 0
        self.air_by_date = 0
        self.subtitles = enabled_subtitles or int(app.SUBTITLES_DEFAULT)
        self.dvdorder = 0
        self.lang = lang
        self.last_update_indexer = 1
        self.sports = 0
        self.anime = 0
        self.scene = 0
        self.rls_ignore_words = ''
        self.rls_require_words = ''
        self.default_ep_status = SKIPPED
        self._location = ''
        self.episodes = {}
        self.nextaired = ''
        self.release_groups = None
        self.exceptions = []
        self.externals = {}

        other_show = Show.find(app.showList, self.indexerid)
        if other_show is not None:
            raise MultipleShowObjectsException("Can't create a show if it already exists")

        self._load_from_db()

    @property
    def is_anime(self):
        """Whether this show is an anime or not.

        :return:
        :rtype: bool
        """
        return int(self.anime) > 0

    @property
    def is_sports(self):
        """Whether this is a sport show or not.

        :return:
        :rtype: bool
        """
        return int(self.sports) > 0

    @property
    def is_scene(self):
        """Whether this is a scene show or not.

        :return:
        :rtype: bool
        """
        return int(self.scene) > 0

    @property
    def network_logo_name(self):
        """Return the network logo name.

        :return:
        :rtype: str
        """
        return self.network.replace(u'\u00C9', 'e').replace(u'\u00E9', 'e').lower()

    @property
    def is_recently_deleted(self):
        """Whether the show was recently deleted.

        A property that checks if this show has been recently deleted, or was attempted to be deleted.
        Can be used to suppress some error messages, when the TVShow was used, just after a removal.

        :return:
        :rtype: bool
        """
        return self.indexerid in app.RECENTLY_DELETED

    @property
    def raw_location(self):
        """Return the raw location without executing any validation.

        :return:
        :rtype: str
        """
        return self._location

    @property
    def location(self):
        """Return the location.

        :return:
        :rtype: str
        """
        # no dir check needed if missing show dirs are created during post-processing
        if app.CREATE_MISSING_SHOW_DIRS or self.is_location_valid():
            return self._location

        raise ShowDirectoryNotFoundException("Show folder doesn't exist, you shouldn't be using it")

    @location.setter
    def location(self, value):
        logger.log(u'{id}: Setter sets location to {location}'.format
                   (id=self.indexerid, location=value), logger.DEBUG)
        # Don't validate dir if user wants to add shows without creating a dir
        if app.ADD_SHOWS_WO_DIR or self.is_location_valid(value):
            self._location = value
        else:
            raise ShowDirectoryNotFoundException('Invalid folder for the show!')

    def is_location_valid(self, location=None):
        """Return whether the location is valid.

        :param location:
        :type location: str
        :return:
        :rtype: bool
        """
        return os.path.isdir(location or self._location)

    @property
    def current_qualities(self):
        """Current qualities."""
        allowed_qualities, preferred_qualities = Quality.split_quality(int(self.quality))
        return (allowed_qualities, preferred_qualities)

    @property
    def using_preset_quality(self):
        """Whether preset is used."""
        return self.quality in qualityPresets

    @property
    def default_ep_status_name(self):
        """Default episode status name."""
        return statusStrings[self.default_ep_status]

    def show_size(self, pretty=False):
        """Show size."""
        show_size = helpers.get_size(self.raw_location)
        return pretty_file_size(show_size) if pretty else show_size

    @property
    def subtitle_flag(self):
        """Subtitle flag."""
        return subtitles.code_from_code(self.lang) if self.lang else ''

    def flush_episodes(self):
        """Delete references to anything that's not in the internal lists."""
        for cur_season in self.episodes:
            for cur_ep in self.episodes[cur_season]:
                my_ep = self.episodes[cur_season][cur_ep]
                self.episodes[cur_season][cur_ep] = None
                del my_ep

    def get_all_seasons(self, last_airdate=False):
        """Retrieve a dictionary of seasons with the number of episodes, using the episodes table.

        :param last_airdate: Option to pass the airdate of the last aired episode for the season in stead of the number
        of episodes
        :type last_airdate: bool
        :return:
        :rtype: dictionary of seasons (int) and count(episodes) (int)
        """
        sql_selection = b'SELECT season, {0} AS number_of_episodes FROM tv_episodes ' \
                        b'WHERE showid = ? GROUP BY season'.format(b'count(*)' if not last_airdate else b'max(airdate)')
        main_db_con = db.DBConnection()
        results = main_db_con.select(sql_selection, [self.indexerid])

        return {int(x['season']): int(x['number_of_episodes']) for x in results}

    def get_all_episodes(self, season=None, has_location=False):
        """Retrieve all episodes for this show given the specified filter.

        :param season:
        :type season: int
        :param has_location:
        :type has_location: bool
        :return:
        :rtype: list of TVEpisode
        """
        sql_selection = b'SELECT season, episode, '

        # subselection to detect multi-episodes early, share_location > 0
        sql_selection += (b'(SELECT '
                          b'  COUNT (*) '
                          b'FROM '
                          b'  tv_episodes '
                          b'WHERE '
                          b'  showid = tve.showid '
                          b'  AND season = tve.season '
                          b"  AND location != '' "
                          b'  AND location = tve.location '
                          b'  AND episode != tve.episode) AS share_location ')

        sql_selection = sql_selection + b' FROM tv_episodes tve WHERE showid = ' + str(self.indexerid)

        if season is not None:
            sql_selection = sql_selection + b' AND season = ' + str(season)

        if has_location:
            sql_selection += b" AND location != '' "

        # need ORDER episode ASC to rename multi-episodes in order S01E01-02
        sql_selection += b' ORDER BY season ASC, episode ASC'

        main_db_con = db.DBConnection()
        results = main_db_con.select(sql_selection)

        ep_list = []
        for cur_result in results:
            cur_ep = self.get_episode(cur_result[b'season'], cur_result[b'episode'])
            if not cur_ep:
                continue

            cur_ep.related_episodes = []
            if cur_ep.location:
                # if there is a location, check if it's a multi-episode (share_location > 0)
                # and put them in related_episodes
                if cur_result[b'share_location'] > 0:
                    related_eps_result = main_db_con.select(
                        b'SELECT '
                        b'  season, episode '
                        b'FROM '
                        b'  tv_episodes '
                        b'WHERE '
                        b'  showid = ? '
                        b'  AND season = ? '
                        b'  AND location = ? '
                        b'  AND episode != ? '
                        b'ORDER BY episode ASC',
                        [self.indexerid, cur_ep.season, cur_ep.location, cur_ep.episode])
                    for cur_related_ep in related_eps_result:
                        related_ep = self.get_episode(cur_related_ep[b'season'], cur_related_ep[b'episode'])
                        if related_ep and related_ep not in cur_ep.related_episodes:
                            cur_ep.related_episodes.append(related_ep)
            ep_list.append(cur_ep)

        return ep_list

    def get_episode(self, season=None, episode=None, filepath=None, no_create=False, absolute_number=None,
                    air_date=None, should_cache=True):
        """Return TVEpisode given the specified filter.

        :param season:
        :type season: int
        :param episode:
        :type episode: int
        :param filepath:
        :type filepath: str
        :param no_create:
        :type no_create: bool
        :param absolute_number:
        :type absolute_number: int
        :param air_date:
        :type air_date: datetime.datetime
        :param should_cache:
        :type should_cache: bool
        :return:
        :rtype: TVEpisode
        """
        season = try_int(season, None)
        episode = try_int(episode, None)
        absolute_number = try_int(absolute_number, None)

        # if we get an anime get the real season and episode
        if not season and not episode:
            main_db_con = db.DBConnection()
            sql = None
            sql_args = None
            if self.is_anime and absolute_number:
                sql = b'SELECT season, episode ' \
                      b'FROM tv_episodes ' \
                      b'WHERE showid = ? AND absolute_number = ? AND season != 0'
                sql_args = [self.indexerid, absolute_number]
                logger.log(u'{id}: Season and episode lookup for {show} using absolute number {absolute}'.
                           format(id=self.indexerid, absolute=absolute_number, show=self.name), logger.DEBUG)
            elif air_date:
                sql = b'SELECT season, episode FROM tv_episodes WHERE showid = ? AND airdate = ?'
                sql_args = [self.indexerid, air_date.toordinal()]
                logger.log(u'{id}: Season and episode lookup for {show} using air date {air_date}'.
                           format(id=self.indexerid, air_date=air_date, show=self.name), logger.DEBUG)

            sql_results = main_db_con.select(sql, sql_args) if sql else []
            if len(sql_results) == 1:
                episode = int(sql_results[0][b'episode'])
                season = int(sql_results[0][b'season'])
                logger.log(u'{id}: Found season and episode which is {show} {ep}'.format
                           (id=self.indexerid, show=self.name, ep=episode_num(season, episode)), logger.DEBUG)
            elif len(sql_results) > 1:
                logger.log(u'{id}: Multiple entries found in show: {show} '.format
                           (id=self.indexerid, show=self.name), logger.ERROR)

                return None
            else:
                logger.log(u'{id}: No entries found in show: {show}'.format
                           (id=self.indexerid, show=self.name), logger.DEBUG)
                return None

        if season not in self.episodes:
            self.episodes[season] = {}

        if episode in self.episodes[season] and self.episodes[season][episode] is not None:
            return self.episodes[season][episode]
        elif no_create:
            return None

        if filepath:
            ep = TVEpisode(self, season, episode, filepath)
        else:
            ep = TVEpisode(self, season, episode)

        if ep is not None and should_cache:
            self.episodes[season][episode] = ep

        return ep

    def create_next_season_update(self, for_season=None):
        """Update the cache indexer_update table.

        :param for_season: Optional limit to only update the next update date for this season.
        :type for_season: int
        """
        seasons = self.get_all_seasons(last_airdate=True)
        for season in seasons:
            if for_season and for_season != season:
                continue

            # Get last airdate for this season and calculate the next_update
            if seasons[season] < 719163:
                if season < max(seasons):
                    # Before epoch and not last season
                    next_update = time.time() + 3153600
                else:
                    # This is the last season, we don't know if this is an old show, or airdate not yet known
                    next_update = time.time() + 3600
            else:
                last_airdate = int(time.mktime(datetime.date.fromordinal(seasons[season]).timetuple()))
                if last_airdate > time.time():
                    next_update = time.time() + 3600
                else:
                    next_update = int(time.time() + ((time.time() - last_airdate) / 100))

            cache_db = db.DBConnection('cache.db')
            cache_db.upsert('indexer_update',
                            {'next_update': int(next_update)},
                            {'indexer': self.indexer, 'indexer_id': self.indexerid, 'season': season})

    def cleanup_season_updates(self, season):
        """Remove the season from the season update table.

        This could happen when the indexer adds a new season/episode, but later decides to remove it.
        """
        sql_episodes_left_in_season = b'SELECT season FROM tv_episodes WHERE showid = ? AND season = ?'
        main_db_con = db.DBConnection()
        if not main_db_con.select(sql_episodes_left_in_season, [self.indexerid, season]):
            logger.log(u'{id}: Cleaning up indexer_update table for {show} {season} from the DB'.format
                       (id=self.indexerid, show=self.name,
                        season=season), logger.DEBUG)

            cache_db = db.DBConnection('cache.db')
            sql = b'DELETE FROM indexer_update WHERE indexer = ? AND indexer_id = ? AND season = ?'
            cache_db.action(sql, [self.indexer, self.indexerid, season])

    def should_update(self, update_date=datetime.date.today()):
        """Whether the show information should be updated.

        :param update_date:
        :type update_date: datetime.date
        :return:
        :rtype: bool
        """
        # if show is 'paused' do not update_date
        if self.paused:
            logger.log(u'{id}: Show {show} is paused. Update skipped'.format
                       (id=self.indexerid, show=self.name), logger.INFO)
            return False

        # if show is not 'Ended' always update (status 'Continuing')
        if self.status == 'Continuing':
            return True

        # run logic against the current show latest aired and next unaired data to
        # see if we should bypass 'Ended' status

        graceperiod = datetime.timedelta(days=30)

        last_airdate = datetime.date.fromordinal(1)

        # get latest aired episode to compare against today - graceperiod and today + graceperiod
        main_db_con = db.DBConnection()
        sql_result = main_db_con.select(
            b'SELECT '
            b'  IFNULL(MAX(airdate), 0) as last_aired '
            b'FROM '
            b'  tv_episodes '
            b'WHERE '
            b'  showid = ? '
            b'  AND season > 0 '
            b'  AND airdate > 1 '
            b'  AND status > 1',
            [self.indexerid])

        if sql_result and sql_result[0][b'last_aired'] != 0:
            last_airdate = datetime.date.fromordinal(sql_result[0][b'last_aired'])
            if (update_date - graceperiod) <= last_airdate <= (update_date + graceperiod):
                return True

        # get next upcoming UNAIRED episode to compare against today + graceperiod
        sql_result = main_db_con.select(
            b'SELECT '
            b'  IFNULL(MIN(airdate), 0) as airing_next '
            b'FROM '
            b'  tv_episodes '
            b'WHERE '
            b'  showid = ? '
            b'  AND season > 0 '
            b'  AND airdate > 1 '
            b'  AND status = 1',
            [self.indexerid])

        if sql_result and sql_result[0][b'airing_next'] != 0:
            next_airdate = datetime.date.fromordinal(sql_result[0][b'airing_next'])
            if next_airdate <= (update_date + graceperiod):
                return True

        last_update_indexer = datetime.date.fromordinal(self.last_update_indexer)

        # in the first year after ended (last airdate), update every 30 days
        if (update_date - last_airdate) < datetime.timedelta(days=450) and (
                (update_date - last_update_indexer) > datetime.timedelta(days=30)):
            return True

        return False

    def show_words(self):
        """Return all related words to show: preferred, undesired, ignore, require."""
        words = namedtuple('show_words', ['preferred_words', 'undesired_words', 'ignored_words', 'required_words'])

        preferred_words = ','.join(app.PREFERRED_WORDS.split(',')) if app.PREFERRED_WORDS.split(',') else ''
        undesired_words = ','.join(app.UNDESIRED_WORDS.split(',')) if app.UNDESIRED_WORDS.split(',') else ''

        global_ignore = app.IGNORE_WORDS.split(',') if app.IGNORE_WORDS else []
        global_require = app.REQUIRE_WORDS.split(',') if app.REQUIRE_WORDS else []
        show_ignore = self.rls_ignore_words.split(',') if self.rls_ignore_words else []
        show_require = self.rls_require_words.split(',') if self.rls_require_words else []

        # If word is in global ignore and also in show require, then remove it from global ignore
        # Join new global ignore with show ignore
        final_ignore = show_ignore + [i for i in global_ignore if i.lower() not in [r.lower() for r in show_require]]
        # If word is in global require and also in show ignore, then remove it from global require
        # Join new global required with show require
        final_require = show_require + [i for i in global_require if i.lower() not in [r.lower() for r in show_ignore]]

        ignored_words = ','.join(final_ignore)
        required_words = ','.join(final_require)

        return words(preferred_words, undesired_words, ignored_words, required_words)

    def __write_show_nfo(self):

        result = False

        logger.log(u'{id}: Writing NFOs for show'.format(id=self.indexerid), logger.DEBUG)
        for cur_provider in app.metadata_provider_dict.values():
            result = cur_provider.create_show_metadata(self) or result

        return result

    def write_metadata(self, show_only=False):
        """Write show metadata files.

        :param show_only:
        :type show_only: bool
        """
        if not self.is_location_valid():
            logger.log(u"{id}: Show dir doesn't exist, skipping NFO generation".format(id=self.indexerid),
                       logger.WARNING)
            return

        self.__get_images()

        self.__write_show_nfo()

        if not show_only:
            self.__write_episode_nfos()

    def __write_episode_nfos(self):

        logger.log(u"{id}: Writing NFOs for all episodes".format(id=self.indexerid), logger.DEBUG)

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(
            b'SELECT '
            b'  season, '
            b'  episode '
            b'FROM '
            b'  tv_episodes '
            b'WHERE '
            b'  showid = ? '
            b"  AND location != ''", [self.indexerid])

        for ep_result in sql_results:
            logger.log(u'{id}: Retrieving/creating episode {ep}'.format
                       (id=self.indexerid, ep=episode_num(ep_result[b'season'], ep_result[b'episode'])),
                       logger.DEBUG)
            cur_ep = self.get_episode(ep_result[b'season'], ep_result[b'episode'])
            if not cur_ep:
                continue

            cur_ep.create_meta_files()

    def update_metadata(self):
        """Update show metadata files."""
        if not self.is_location_valid():
            logger.log(u"{id}: Show dir doesn't exist, skipping NFO generation".format(id=self.indexerid),
                       logger.WARNING)
            return

        self.__update_show_nfo()

    def __update_show_nfo(self):

        result = False

        logger.log(u"{id}: Updating NFOs for show with new indexer info".format(id=self.indexerid), logger.INFO)
        for cur_provider in app.metadata_provider_dict.values():
            result = cur_provider.update_show_indexer_metadata(self) or result

        return result

    def load_episodes_from_dir(self):
        """Find all media files in the show folder and create episodes for as many as possible."""
        if not self.is_location_valid():
            logger.log(u"{id}: Show dir doesn't exist, not loading episodes from disk".format(id=self.indexerid),
                       logger.WARNING)
            return

        logger.log(u"{id}: Loading all episodes from the show directory: {location}".format
                   (id=self.indexerid, location=self.location), logger.DEBUG)

        # get file list
        media_files = helpers.list_media_files(self.location)
        logger.log(u'{id}: Found files: {media_files}'.format
                   (id=self.indexerid, media_files=media_files), logger.DEBUG)

        # create TVEpisodes from each media file (if possible)
        sql_l = []
        for media_file in media_files:
            cur_episode = None

            logger.log(u"{id}: Creating episode from: {location}".format
                       (id=self.indexerid, location=media_file), logger.DEBUG)
            try:
                cur_episode = self.make_ep_from_file(os.path.join(self.location, media_file))
            except (ShowNotFoundException, EpisodeNotFoundException) as e:
                logger.log(u"{id}: Episode {location} returned an exception {error_msg}".format
                           (id=self.indexerid, location=media_file, error_msg=ex(e)), logger.WARNING)
                continue
            except EpisodeDeletedException:
                logger.log(u'{id}: The episode deleted itself when I tried making an object for it'.format
                           (id=self.indexerid), logger.DEBUG)

            if cur_episode is None:
                continue

            # see if we should save the release name in the db
            ep_file_name = os.path.basename(cur_episode.location)
            ep_file_name = os.path.splitext(ep_file_name)[0]

            try:
                parse_result = NameParser(show=self, try_indexers=True).parse(ep_file_name)
            except (InvalidNameException, InvalidShowException):
                parse_result = None

            if ' ' not in ep_file_name and parse_result and parse_result.release_group:
                logger.log(u'{id}: Filename {file_name} gave release group of {rg}, seems valid'.format
                           (id=self.indexerid, file_name=ep_file_name, rg=parse_result.release_group), logger.DEBUG)
                cur_episode.release_name = ep_file_name

            # store the reference in the show
            if cur_episode is not None:
                if self.subtitles:
                    try:
                        cur_episode.refresh_subtitles()
                    except Exception:
                        logger.log(u'{id}: Could not refresh subtitles'.format(id=self.indexerid), logger.ERROR)
                        logger.log(traceback.format_exc(), logger.DEBUG)

                sql_l.append(cur_episode.get_sql())

        if sql_l:
            main_db_con = db.DBConnection()
            main_db_con.mass_action(sql_l)

    def load_episodes_from_db(self, seasons=None):
        """Load episodes from database.

        :param: seasons: list of seasons ([int])
        :return:
        :rtype: dict(int -> dict(int -> bool))
        """
        scanned_eps = {}

        try:
            main_db_con = db.DBConnection()
            sql = (b'SELECT '
                   b'  season, episode, showid, show_name '
                   b'FROM '
                   b'  tv_episodes '
                   b'JOIN '
                   b'  tv_shows '
                   b'WHERE '
                   b'  showid = indexer_id AND showid = ?')
            if seasons:
                sql += b' AND season IN (%s)' % ','.join('?' * len(seasons))
                sql_results = main_db_con.select(sql, [self.indexerid] + seasons)
                logger.log(u'{id}: Loading all episodes of season(s) {seasons} from the DB'.format
                           (id=self.indexerid, seasons=seasons), logger.DEBUG)
            else:
                sql_results = main_db_con.select(sql, [self.indexerid])
                logger.log(u'{id}: Loading all episodes of all seasons from the DB'.format
                           (id=self.indexerid), logger.DEBUG)
        except Exception as error:
            logger.log(u'{id}: Could not load episodes from the DB. Error: {error_msg}'.format
                       (id=self.indexerid, error_msg=error), logger.ERROR)
            return scanned_eps

        indexer_api_params = indexerApi(self.indexer).api_params.copy()

        if self.lang:
            indexer_api_params[b'language'] = self.lang
            logger.log(u'{id}: Using language from show settings: {lang}'.format
                       (id=self.indexerid, lang=self.lang), logger.DEBUG)

        if self.dvdorder != 0:
            indexer_api_params[b'dvdorder'] = True

        t = indexerApi(self.indexer).indexer(**indexer_api_params)

        cached_show = t[self.indexerid]
        cached_seasons = {}
        cur_show_name = ''
        cur_show_id = ''

        for cur_result in sql_results:

            cur_season = int(cur_result[b'season'])
            cur_episode = int(cur_result[b'episode'])
            cur_show_id = int(cur_result[b'showid'])
            cur_show_name = text_type(cur_result[b'show_name'])

            delete_ep = False

            logger.log(u'{id}: Loading {show} {ep} from the DB'.format
                       (id=cur_show_id, show=cur_show_name, ep=episode_num(cur_season, cur_episode)),
                       logger.DEBUG)

            if cur_season not in cached_seasons:
                try:
                    cached_seasons[cur_season] = cached_show[cur_season]
                except IndexerSeasonNotFound as error:
                    logger.log(u'{id}: {error_msg} (unaired/deleted) in the indexer {indexer} for {show}. '
                               u'Removing existing records from database'.format
                               (id=cur_show_id, error_msg=error.message, indexer=indexerApi(self.indexer).name,
                                show=cur_show_name), logger.DEBUG)
                    delete_ep = True

            if cur_season not in scanned_eps:
                scanned_eps[cur_season] = {}

            try:
                cur_ep = self.get_episode(cur_season, cur_episode)
                if not cur_ep:
                    raise EpisodeNotFoundException

                # if we found out that the ep is no longer on TVDB then delete it from our database too
                if delete_ep:
                    cur_ep.delete_episode()

                cur_ep.load_from_db(cur_season, cur_episode)
                scanned_eps[cur_season][cur_episode] = True
            except EpisodeDeletedException:
                logger.log(u'{id}: Tried loading {show} {ep} from the DB that should have been deleted, '
                           u'skipping it'.format(id=cur_show_id, show=cur_show_name,
                                                 ep=episode_num(cur_season, cur_episode)), logger.DEBUG)
                continue

        logger.log(u'{id}: Finished loading all episodes for {show} from the DB'.format
                   (show=cur_show_name, id=cur_show_id), logger.DEBUG)

        return scanned_eps

    def load_episodes_from_indexer(self, seasons=None, tvapi=None):
        """Load episodes from indexer.

        :param seasons: Only load episodes for these seasons (only if supported by the indexer)
        :type seasons: list of integers or integer
        :param tvapi: indexer_object
        :type tvapi: indexer object
        :return:
        :rtype: dict(int -> dict(int -> bool))
        """
        if tvapi:
            t = tvapi
            show_obj = t[self.indexerid]
        else:
            indexer_api_params = indexerApi(self.indexer).api_params.copy()

            indexer_api_params['cache'] = False

            if self.lang:
                indexer_api_params['language'] = self.lang

            if self.dvdorder != 0:
                indexer_api_params['dvdorder'] = True

            try:
                t = indexerApi(self.indexer).indexer(**indexer_api_params)
                show_obj = t.get_episodes_for_season(self.indexerid, specials=False, aired_season=seasons)
            except IndexerError:
                logger.log(u'{id}: {indexer} timed out, unable to update episodes'.format
                           (id=self.indexerid, indexer=indexerApi(self.indexer).name), logger.WARNING)
                return None

        logger.log(u'{id}: Loading all episodes from {indexer}'.format
                   (id=self.indexerid, indexer=indexerApi(self.indexer).name), logger.DEBUG)

        scanned_eps = {}

        sql_l = []
        for season in show_obj:
            scanned_eps[season] = {}
            for episode in show_obj[season]:
                # need some examples of wtf episode 0 means to decide if we want it or not
                if episode == 0:
                    continue
                try:
                    ep = self.get_episode(season, episode)
                    if not ep:
                        raise EpisodeNotFoundException
                except EpisodeNotFoundException:
                    logger.log(u'{id}: {indexer} object for {ep} is incomplete, skipping this episode'.format
                               (id=self.indexerid, indexer=indexerApi(self.indexer).name,
                                ep=episode_num(season, episode)))
                    continue
                else:
                    try:
                        ep.load_from_indexer(tvapi=t)
                    except EpisodeDeletedException:
                        logger.log(u'{id}: The episode {ep} was deleted, skipping the rest of the load'.format
                                   (id=self.indexerid, ep=episode_num(season, episode)), logger.DEBUG)
                        continue

                with ep.lock:
                    sql_l.append(ep.get_sql())

                scanned_eps[season][episode] = True

        if sql_l:
            main_db_con = db.DBConnection()
            main_db_con.mass_action(sql_l)

        # Done updating save last update date
        self.last_update_indexer = datetime.date.today().toordinal()
        logger.log(u'{id}: Saving indexer changes to database'.format(id=self.indexerid), logger.DEBUG)
        self.save_to_db()

        return scanned_eps

    def _load_externals_from_db(self, indexer=None, indexer_id=None):
        """Load and recreate the indexers external id's.

        :param indexer: Optional pass indexer id, else use the current shows indexer.
        :type indexer: int
        :param indexer_id: Optional pass indexer id, else use the current shows indexer.
        :type indexer_id: int
        """
        indexer = indexer or self.indexer
        indexer_id = indexer_id or self.indexerid

        main_db_con = db.DBConnection()
        sql = (b'SELECT indexer, indexer_id, mindexer, mindexer_id '
               b'FROM indexer_mapping '
               b'WHERE (indexer = ? AND indexer_id = ?) '
               b'OR (mindexer = ? AND mindexer_id = ?)')

        results = main_db_con.select(sql, [indexer, indexer_id, indexer, indexer_id])

        for result in results:
            if result[0] == self.indexer:
                self.externals[mappings[result[2]]] = result[3]
            else:
                self.externals[mappings[result[0]]] = result[1]

        return self.externals

    def _save_externals_to_db(self):
        """Save the indexers external id's to the db."""
        sql_l = []

        for external in self.externals:
            if external in reverse_mappings and self.externals[external]:
                sql_l.append([b'INSERT OR IGNORE '
                              'INTO indexer_mapping (indexer_id, indexer, mindexer_id, mindexer) '
                              'VALUES (?,?,?,?)',
                              [self.indexerid,
                               self.indexer,
                               self.externals[external],
                               int(reverse_mappings[external])
                               ]])

        if sql_l:
            main_db_con = db.DBConnection()
            main_db_con.mass_action(sql_l)

    def __get_images(self):
        fanart_result = poster_result = banner_result = False
        season_posters_result = season_banners_result = season_all_poster_result = season_all_banner_result = False

        for cur_provider in app.metadata_provider_dict.values():
            fanart_result = cur_provider.create_fanart(self) or fanart_result
            poster_result = cur_provider.create_poster(self) or poster_result
            banner_result = cur_provider.create_banner(self) or banner_result

            season_posters_result = cur_provider.create_season_posters(self) or season_posters_result
            season_banners_result = cur_provider.create_season_banners(self) or season_banners_result
            season_all_poster_result = cur_provider.create_season_all_poster(self) or season_all_poster_result
            season_all_banner_result = cur_provider.create_season_all_banner(self) or season_all_banner_result
            cur_provider.indexer_api = None  # Let's cleanup the stored indexerApi objects.

        return (fanart_result or poster_result or banner_result or season_posters_result or
                season_banners_result or season_all_poster_result or season_all_banner_result)

    def make_ep_from_file(self, filepath):
        """Make a TVEpisode object from a media file.

        :param filepath:
        :type filepath: str
        :return:
        :rtype: TVEpisode
        """
        if not os.path.isfile(filepath):
            logger.log(u"{0}: That isn't even a real file dude... {1}".format
                       (self.indexerid, filepath))
            return None

        logger.log(u'{0}: Creating episode object from {1}'.format
                   (self.indexerid, filepath), logger.DEBUG)

        try:
            parse_result = NameParser(show=self, try_indexers=True, parse_method=(
                'normal', 'anime')[self.is_anime]).parse(filepath)
        except (InvalidNameException, InvalidShowException) as error:
            logger.log(u'{0}: {1}'.format(self.indexerid, error), logger.DEBUG)
            return None

        episodes = [ep for ep in parse_result.episode_numbers if ep is not None]
        if not episodes:
            logger.log(u'{0}: parse_result: {1}'.format(self.indexerid, parse_result))
            logger.log(u'{0}: No episode number found in {1}, ignoring it'.format
                       (self.indexerid, filepath), logger.WARNING)
            return None

        # for now lets assume that any episode in the show dir belongs to that show
        season = parse_result.season_number if parse_result.season_number is not None else 1
        root_ep = None

        sql_l = []
        for current_ep in episodes:
            logger.log(u'{0}: {1} parsed to {2} {3}'.format
                       (self.indexerid, filepath, self.name, episode_num(season, current_ep)), logger.DEBUG)

            check_quality_again = False
            same_file = False

            cur_ep = self.get_episode(season, current_ep)
            if not cur_ep:
                try:
                    cur_ep = self.get_episode(season, current_ep, filepath)
                    if not cur_ep:
                        raise EpisodeNotFoundException
                except EpisodeNotFoundException:
                    logger.log(u'{0}: Unable to figure out what this file is, skipping {1}'.format
                               (self.indexerid, filepath), logger.ERROR)
                    continue

            else:
                # if there is a new file associated with this ep then re-check the quality
                if not cur_ep.location or os.path.normpath(cur_ep.location) != os.path.normpath(filepath):
                    logger.log(
                        u'{0}: The old episode had a different file associated with it, '
                        u're-checking the quality using the new filename {1}'.format(self.indexerid, filepath),
                        logger.DEBUG)
                    check_quality_again = True

                with cur_ep.lock:
                    old_size = cur_ep.file_size
                    cur_ep.location = filepath
                    # if the sizes are the same then it's probably the same file
                    same_file = old_size and cur_ep.file_size == old_size
                    cur_ep.check_for_meta_files()

            if root_ep is None:
                root_ep = cur_ep
            else:
                if cur_ep not in root_ep.related_episodes:
                    with root_ep.lock:
                        root_ep.related_episodes.append(cur_ep)

            # if it's a new file then
            if not same_file:
                with cur_ep.lock:
                    cur_ep.release_name = ''

            # if they replace a file on me I'll make some attempt at re-checking the
            # quality unless I know it's the same file
            if check_quality_again and not same_file:
                new_quality = Quality.name_quality(filepath, self.is_anime)
                logger.log(u'{0}: Since this file has been renamed, I checked {1} and found quality {2}'.format
                           (self.indexerid, filepath, Quality.qualityStrings[new_quality]), logger.DEBUG)
                if new_quality != Quality.UNKNOWN:
                    with cur_ep.lock:
                        cur_ep.status = Quality.composite_status(DOWNLOADED, new_quality)

            # check for status/quality changes as long as it's a new file
            elif not same_file and helpers.is_media_file(filepath) and (
                    cur_ep.status not in Quality.DOWNLOADED + Quality.ARCHIVED + [IGNORED]):
                old_status, old_quality = Quality.split_composite_status(cur_ep.status)
                new_quality = Quality.name_quality(filepath, self.is_anime)
                new_status = None

                # if it was snatched and now exists then set the status correctly
                if old_status == SNATCHED and old_quality <= new_quality:
                    logger.log(
                        u"{0}: This ep used to be snatched with quality '{1}' but a file exists with quality '{2}' "
                        u"so setting the status to 'DOWNLOADED'".format
                        (self.indexerid, Quality.qualityStrings[old_quality],
                         Quality.qualityStrings[new_quality]), logger.DEBUG)
                    new_status = DOWNLOADED

                # if it was snatched proper and we found a higher quality one then allow the status change
                elif old_status == SNATCHED_PROPER and old_quality < new_quality:
                    logger.log(u"{0}: This ep used to be snatched proper with quality '{1}' "
                               u"but a file exists with quality '{2}' so setting the status to 'DOWNLOADED'".format
                               (self.indexerid, Quality.qualityStrings[old_quality],
                                Quality.qualityStrings[new_quality]), logger.DEBUG)
                    new_status = DOWNLOADED

                elif old_status not in (SNATCHED, SNATCHED_PROPER):
                    new_status = DOWNLOADED

                if new_status is not None:
                    with cur_ep.lock:
                        old_ep_status = cur_ep.status
                        cur_ep.status = Quality.composite_status(new_status, new_quality)
                        logger.log(u'{0}: We have an associated file, '
                                   u'so setting the status from {1} to DOWNLOADED/{2}'.format
                                   (self.indexerid, old_ep_status, cur_ep.status), logger.DEBUG)

            with cur_ep.lock:
                sql_l.append(cur_ep.get_sql())

        if sql_l:
            main_db_con = db.DBConnection()
            main_db_con.mass_action(sql_l)

        # creating metafiles on the root should be good enough
        if root_ep:
            with root_ep.lock:
                root_ep.create_meta_files()

        return root_ep

    def _load_from_db(self):

        logger.log(u'{id}: Loading show info from database'.format(id=self.indexerid), logger.DEBUG)

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(b'SELECT * FROM tv_shows WHERE indexer_id = ?', [self.indexerid])

        if len(sql_results) > 1:
            raise MultipleShowsInDatabaseException()
        elif not sql_results:
            logger.log(u'{0}: Unable to find the show in the database'.format(self.indexerid))
            return
        else:
            self.indexer = int(sql_results[0][b'indexer'] or 0)

            if not self.name:
                self.name = sql_results[0][b'show_name']
            if not self.network:
                self.network = sql_results[0][b'network']
            if not self.genre:
                self.genre = sql_results[0][b'genre']
            if not self.classification:
                self.classification = sql_results[0][b'classification']

            self.runtime = sql_results[0][b'runtime']

            self.status = sql_results[0][b'status']
            if self.status is None:
                self.status = 'Unknown'

            self.airs = sql_results[0]['airs']
            if self.airs is None or not network_timezones.test_timeformat(self.airs):
                self.airs = ''

            self.startyear = int(sql_results[0][b'startyear'] or 0)
            self.air_by_date = int(sql_results[0][b'air_by_date'] or 0)
            self.anime = int(sql_results[0][b'anime'] or 0)
            self.sports = int(sql_results[0][b'sports'] or 0)
            self.scene = int(sql_results[0][b'scene'] or 0)
            self.subtitles = int(sql_results[0][b'subtitles'] or 0)
            self.dvdorder = int(sql_results[0][b'dvdorder'] or 0)
            self.quality = int(sql_results[0][b'quality'] or UNKNOWN)
            self.flatten_folders = int(sql_results[0][b'flatten_folders'] or 0)
            self.paused = int(sql_results[0][b'paused'] or 0)
            self._location = sql_results[0][b'location']  # skip location validation

            if not self.lang:
                self.lang = sql_results[0][b'lang']

            self.last_update_indexer = sql_results[0][b'last_update_indexer']

            self.rls_ignore_words = sql_results[0][b'rls_ignore_words']
            self.rls_require_words = sql_results[0][b'rls_require_words']

            self.default_ep_status = int(sql_results[0][b'default_ep_status'] or SKIPPED)

            if not self.imdbid:
                self.imdbid = sql_results[0][b'imdb_id']

            if self.is_anime:
                self.release_groups = BlackAndWhiteList(self.indexerid)

            # Load external id's from indexer_mappings table.
            self._load_externals_from_db()

        # Get IMDb_info from database
        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(b'SELECT * FROM imdb_info WHERE indexer_id = ?', [self.indexerid])

        if not sql_results:
            logger.log(u'{id}: Unable to find the following IMDb show info in the database: {show}'.format
                       (id=self.indexerid, show=self.name))
            return
        else:
            self.imdb_info = dict(zip(sql_results[0].keys(), sql_results[0]))

        self.reset_dirty()
        return True

    def load_from_indexer(self, tvapi=None):
        """Load show from indexer.

        :param tvapi:
        """
        if self.indexer == INDEXER_TVRAGE:
            return

        logger.log(u'{0}: Loading show info from {1}'.format(
            self.indexerid, indexerApi(self.indexer).name), logger.DEBUG)

        # There's gotta be a better way of doing this but we don't wanna
        # change the cache value elsewhere
        if tvapi:
            t = tvapi
        else:
            indexer_api_params = indexerApi(self.indexer).api_params.copy()

            indexer_api_params['cache'] = False

            if self.lang:
                indexer_api_params['language'] = self.lang

            if self.dvdorder != 0:
                indexer_api_params['dvdorder'] = True

            t = indexerApi(self.indexer).indexer(**indexer_api_params)

        indexed_show = t[self.indexerid]

        try:
            self.name = indexed_show['seriesname'].strip()
        except AttributeError:
            raise IndexerAttributeNotFound(
                "Found {id}, but attribute 'seriesname' was empty.".format(id=self.indexerid))

        self.classification = getattr(indexed_show, 'classification', 'Scripted')
        self.genre = getattr(indexed_show, 'genre', '')
        self.network = getattr(indexed_show, 'network', '')
        self.runtime = getattr(indexed_show, 'runtime', '')

        # set the externals, using the result from the indexer.
        self.externals = {k: v for k, v in getattr(indexed_show, 'externals', {}).items() if v}

        # Add myself (indexer) as an external
        self.externals[mappings[self.indexer]] = self.indexerid

        # Enrich the externals, using reverse lookup.
        self.externals.update(get_externals(self))

        self.imdbid = self.externals.get('imdb_id') or getattr(indexed_show, 'imdb_id', '')

        if getattr(indexed_show, 'airs_dayofweek', '') and getattr(indexed_show, 'airs_time', ''):
            self.airs = '{airs_day_of_week} {airs_time}'.format(airs_day_of_week=indexed_show['airs_dayofweek'],
                                                                airs_time=indexed_show['airs_time'])

        if getattr(indexed_show, 'firstaired', ''):
            self.startyear = int(str(indexed_show['firstaired']).split('-')[0])

        self.status = getattr(indexed_show, 'status', 'Unknown')

        self._save_externals_to_db()

    def load_imdb_info(self):
        """Load all required show information from IMDb with IMDbPY."""
        imdb_api = imdb.IMDb()

        try:
            if not self.imdbid:
                # Somewhere title2imdbID started to return without 'tt'
                self.imdbid = imdb_api.title2imdbID(self.name, kind='tv series')

            if not self.imdbid:
                logger.log(u'{0}: Not loading show info from IMDb, '
                           u"because we don't know its ID".format(self.indexerid))
                return

            # Make sure we only use one ID, and sanitize the imdb to include the tt.
            self.imdbid = self.imdbid.split(',')[0]
            if 'tt' not in self.imdbid:
                self.imdbid = 'tt{imdb_id}'.format(imdb_id=self.imdbid)

            logger.log(u'{0}: Loading show info from IMDb with ID: {1}'.format(
                self.indexerid, self.imdbid), logger.DEBUG)

            # Remove first two chars from ID
            imdb_obj = imdb_api.get_movie(self.imdbid[2:])

            # IMDb returned something we don't want
            if not imdb_obj.get('year'):
                logger.log(u'{0}: IMDb returned invalid info for {1}, skipping update.'.format(
                    self.indexerid, self.imdbid), logger.DEBUG)
                return

        except IMDbDataAccessError:
            logger.log(u'{0}: Failed to obtain info from IMDb for: {1}'.format(
                self.indexerid, self.name), logger.DEBUG)
            return

        except IMDbParserError:
            logger.log(u'{0}: Failed to parse info from IMDb for: {1}'.format(
                self.indexerid, self.name), logger.ERROR)
            return

        self.imdb_info = {
            'imdb_id': self.imdbid,
            'title': imdb_obj.get('title', ''),
            'year': imdb_obj.get('year', ''),
            'akas': '|'.join(imdb_obj.get('akas', '')),
            'genres': '|'.join(imdb_obj.get('genres', '')),
            'countries': '|'.join(imdb_obj.get('countries', '')),
            'country_codes': '|'.join(imdb_obj.get('country codes', '')),
            'rating': imdb_obj.get('rating', ''),
            'votes': imdb_obj.get('votes', ''),
            'last_update': datetime.date.today().toordinal()
        }

        self.externals['imdb_id'] = self.imdbid

        if imdb_obj.get('runtimes'):
            self.imdb_info['runtimes'] = re.search(r'\d+', imdb_obj['runtimes'][0]).group(0)

        # Get only the production country certificate if any
        if imdb_obj.get('certificates') and imdb_obj.get('countries'):
            for certificate in imdb_obj['certificates']:
                if certificate.split(':')[0] in imdb_obj['countries']:
                    self.imdb_info['certificates'] = certificate.split(':')[1]
                    break

        logger.log(u'{0}: Obtained info from IMDb: {1}'.format(
            self.indexerid, self.imdb_info), logger.DEBUG)

    def next_episode(self):
        """Return the next episode air date.

        :return:
        :rtype: datetime.date
        """
        logger.log(u'{0}: Finding the episode which airs next'.format(self.indexerid), logger.DEBUG)

        cur_date = datetime.date.today().toordinal()
        if not self.nextaired or self.nextaired and cur_date > self.nextaired:
            main_db_con = db.DBConnection()
            sql_results = main_db_con.select(
                b'SELECT '
                b'  airdate,'
                b'  season,'
                b'  episode '
                b'FROM '
                b'  tv_episodes '
                b'WHERE '
                b'  showid = ? '
                b'  AND airdate >= ? '
                b'  AND status IN (?,?) '
                b'ORDER BY'
                b'  airdate '
                b'ASC LIMIT 1',
                [self.indexerid, datetime.date.today().toordinal(), UNAIRED, WANTED])

            if sql_results is None or len(sql_results) == 0:
                logger.log(u'{id}: No episode found... need to implement a show status'.format
                           (id=self.indexerid), logger.DEBUG)
                self.nextaired = u''
            else:
                logger.log(u'{id}: Found episode {ep}'.format
                           (id=self.indexerid, ep=episode_num(sql_results[0][b'season'], sql_results[0][b'episode'])),
                           logger.DEBUG)
                self.nextaired = sql_results[0][b'airdate']

        return self.nextaired

    def delete_show(self, full=False):
        """Delete the tv show from the database.

        :param full:
        :type full: bool
        """
        sql_l = [[b'DELETE FROM tv_episodes WHERE showid = ?', [self.indexerid]],
                 [b'DELETE FROM tv_shows WHERE indexer_id = ?', [self.indexerid]],
                 [b'DELETE FROM imdb_info WHERE indexer_id = ?', [self.indexerid]],
                 [b'DELETE FROM xem_refresh WHERE indexer_id = ?', [self.indexerid]],
                 [b'DELETE FROM scene_numbering WHERE indexer_id = ?', [self.indexerid]]]

        main_db_con = db.DBConnection()
        main_db_con.mass_action(sql_l)

        # Clean up the indexer_update table,
        # making sure we're not trying to update this show in near future.
        cache_db_con = db.DBConnection('cache.db')
        cache_db_con.action(b'DELETE FROM indexer_update '
                            b'WHERE indexer = ? AND indexer_id = ?',
                            [self.indexer, self.indexerid])

        action = ('delete', 'trash')[app.TRASH_REMOVE_SHOW]

        # remove self from show list
        app.showList = [x for x in app.showList if int(x.indexerid) != self.indexerid]

        # clear the cache
        image_cache_dir = os.path.join(app.CACHE_DIR, 'images')
        for cache_file in glob.glob(os.path.join(image_cache_dir, str(self.indexerid) + '.*')):
            logger.log(u'{id}: Attempt to {action} cache file {cache_file}'.format
                       (id=self.indexerid, action=action, cache_file=cache_file))
            try:
                if app.TRASH_REMOVE_SHOW:
                    send2trash(cache_file)
                else:
                    os.remove(cache_file)

            except OSError as e:
                logger.log(u'{id}: Unable to {action} {cache_file}: {error_msg}'.format
                           (id=self.indexerid, action=action, cache_file=cache_file, error_msg=ex(e)), logger.WARNING)

        # remove entire show folder
        if full:
            try:
                logger.log(u'{id}: Attempt to {action} show folder {location}'.format
                           (id=self.indexerid, action=action, location=self.location))
                # check first the read-only attribute
                file_attribute = os.stat(self.location)[0]
                if not file_attribute & stat.S_IWRITE:
                    # File is read-only, so make it writeable
                    logger.log(u'{id}: Attempting to make writeable the read only folder {location}'.format
                               (id=self.indexerid, location=self.location), logger.DEBUG)
                    try:
                        os.chmod(self.location, stat.S_IWRITE)
                    except OSError:
                        logger.log(u'{id}: Unable to change permissions of {location}'.format
                                   (id=self.indexerid, location=self.location), logger.WARNING)

                if app.TRASH_REMOVE_SHOW:
                    send2trash(self.location)
                else:
                    shutil.rmtree(self.location)

                logger.log(u'{id}: {action} show folder {location}'.format
                           (id=self.indexerid, action=action, location=self.raw_location))

            except ShowDirectoryNotFoundException:
                logger.log(u'{id}: Show folder {location} does not exist. No need to {action}'.format
                           (id=self.indexerid, location=self.raw_location, action=action), logger.WARNING)
            except OSError as e:
                logger.log(u'{id}: Unable to {action} {location}. Error: {error_msg}'.format
                           (id=self.indexerid, action=action, location=self.raw_location, error_msg=ex(e)),
                           logger.WARNING)

        if app.USE_TRAKT and app.TRAKT_SYNC_WATCHLIST:
            logger.log(u'{id}: Removing show {show} from Trakt watchlist'.format
                       (id=self.indexerid, show=self.name), logger.DEBUG)
            notifiers.trakt_notifier.update_watchlist(self, update='remove')

    def populate_cache(self):
        """Populate image caching."""
        cache_inst = image_cache.ImageCache()

        logger.log(u'{id}: Checking & filling cache for show {show}'.format
                   (id=self.indexerid, show=self.name), logger.DEBUG)
        cache_inst.fill_cache(self)

    def refresh_dir(self):
        """Refresh show using its location.

        :return:
        :rtype: bool
        """
        # make sure the show dir is where we think it is unless dirs are created on the fly
        if not app.CREATE_MISSING_SHOW_DIRS and not self.is_location_valid():
            return False

        # load from dir
        self.load_episodes_from_dir()

        # run through all locations from DB, check that they exist
        logger.log(u'{id}: Loading all episodes from {show} with a location from the database'.format
                   (id=self.indexerid, show=self.name), logger.DEBUG)

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(
            b'SELECT '
            b'  season, episode, location '
            b'FROM '
            b'  tv_episodes '
            b'WHERE '
            b'  showid = ? '
            b"  AND location != ''", [self.indexerid])

        sql_l = []
        for ep in sql_results:
            cur_loc = os.path.normpath(ep[b'location'])
            season = int(ep[b'season'])
            episode = int(ep[b'episode'])

            try:
                cur_ep = self.get_episode(season, episode)
                if not cur_ep:
                    raise EpisodeDeletedException
            except EpisodeDeletedException:
                logger.log(u'{id:} Episode {show} {ep} was deleted while we were refreshing it, '
                           u'moving on to the next one'.format
                           (id=self.indexerid, show=self.name, ep=episode_num(season, episode)), logger.DEBUG)
                continue

            # if the path doesn't exist or if it's not in our show dir
            if (not os.path.isfile(cur_loc) or
                    not os.path.normpath(cur_loc).startswith(os.path.normpath(self.location))):

                # check if downloaded files still exist, update our data if this has changed
                if not app.SKIP_REMOVED_FILES:
                    with cur_ep.lock:
                        # if it used to have a file associated with it and it doesn't anymore then
                        # set it to app.EP_DEFAULT_DELETED_STATUS
                        if cur_ep.location and cur_ep.status in Quality.DOWNLOADED:

                            if app.EP_DEFAULT_DELETED_STATUS == ARCHIVED:
                                _, old_quality = Quality.split_composite_status(cur_ep.status)
                                new_status = Quality.composite_status(ARCHIVED, old_quality)
                            else:
                                new_status = app.EP_DEFAULT_DELETED_STATUS

                            logger.log(u"{id}: Location for {show} {ep} doesn't exist, "
                                       u"removing it and changing our status to '{status}'".format
                                       (id=self.indexerid, show=self.name, ep=episode_num(season, episode),
                                        status=statusStrings[new_status]), logger.DEBUG)
                            cur_ep.status = new_status
                            cur_ep.subtitles = ''
                            cur_ep.subtitles_searchcount = 0
                            cur_ep.subtitles_lastsearch = ''
                        cur_ep.location = ''
                        cur_ep.hasnfo = False
                        cur_ep.hastbn = False
                        cur_ep.release_name = ''

                        sql_l.append(cur_ep.get_sql())

                    logger.log('{id}: Looking for hanging associated files for: {show} {ep} in: {location}'.format
                               (id=self.indexerid, show=self.name, ep=episode_num(season, episode), location=cur_loc))
                    related_files = post_processor.PostProcessor(cur_loc).list_associated_files(
                        cur_loc, base_name_only=False, subfolders=True)

                    if related_files:
                        logger.log(u'{id}: Found hanging associated files for {show} {ep}, deleting: {files}'.format
                                   (id=self.indexerid, show=self.name, ep=episode_num(season, episode),
                                    files=related_files),
                                   logger.WARNING)
                        for related_file in related_files:
                            try:
                                os.remove(related_file)
                            except Exception as e:
                                logger.log(
                                    u'{id}: Could not delete associated file: {related_file}. Error: {error_msg}'.format
                                    (id=self.indexerid, related_file=related_file, error_msg=e), logger.WARNING)

        # clean up any empty season folders after deletion of associated files
        if os.path.isdir(self.location):
            for sub_dir in os.listdir(self.location):
                helpers.delete_empty_folders(os.path.join(self.location, sub_dir), self.location)

        if sql_l:
            main_db_con = db.DBConnection()
            main_db_con.mass_action(sql_l)

    def download_subtitles(self):
        """Download subtitles."""
        if not self.is_location_valid():
            logger.log(u"{id}: Show {show} location doesn't exist, can't download subtitles".format
                       (id=self.indexerid, show=self.name), logger.WARNING)
            return

        logger.log(u'{id}: Downloading subtitles for {show}'.format(id=self.indexerid, show=self.name), logger.DEBUG)

        try:
            episodes = self.get_all_episodes(has_location=True)
            if not episodes:
                logger.log(u'{id}: No episodes to download subtitles for {show}'.format
                           (id=self.indexerid, show=self.name), logger.DEBUG)
                return

            for episode in episodes:
                episode.download_subtitles()

        except Exception:
            logger.log(u'{id}: Error occurred when downloading subtitles for show {show}'.format
                       (id=self.indexerid, show=self.name), logger.WARNING)
            logger.log(traceback.format_exc(), logger.ERROR)

    def save_to_db(self):
        """Save to database."""
        if not self.dirty:
            return

        logger.log(u'{id}: Saving to database: {show}'.format(id=self.indexerid, show=self.name), logger.DEBUG)

        control_value_dict = {'indexer_id': self.indexerid}
        new_value_dict = {'indexer': self.indexer,
                          'show_name': self.name,
                          'location': self.raw_location,  # skip location validation
                          'network': self.network,
                          'genre': self.genre,
                          'classification': self.classification,
                          'runtime': self.runtime,
                          'quality': self.quality,
                          'airs': self.airs,
                          'status': self.status,
                          'flatten_folders': self.flatten_folders,
                          'paused': self.paused,
                          'air_by_date': self.air_by_date,
                          'anime': self.anime,
                          'scene': self.scene,
                          'sports': self.sports,
                          'subtitles': self.subtitles,
                          'dvdorder': self.dvdorder,
                          'startyear': self.startyear,
                          'lang': self.lang,
                          'imdb_id': self.imdbid,
                          'last_update_indexer': self.last_update_indexer,
                          'rls_ignore_words': self.rls_ignore_words,
                          'rls_require_words': self.rls_require_words,
                          'default_ep_status': self.default_ep_status}

        main_db_con = db.DBConnection()
        main_db_con.upsert('tv_shows', new_value_dict, control_value_dict)

        helpers.update_anime_support()

        if self.imdbid and self.imdb_info.get('year'):
            control_value_dict = {'indexer_id': self.indexerid}
            new_value_dict = self.imdb_info

            main_db_con = db.DBConnection()
            main_db_con.upsert('imdb_info', new_value_dict, control_value_dict)

        self.reset_dirty()

    def __str__(self):
        """String representation.

        :return:
        :rtype: str
        """
        to_return = ''
        to_return += 'indexerid: ' + str(self.indexerid) + '\n'
        to_return += 'indexer: ' + str(self.indexer) + '\n'
        to_return += 'name: ' + self.name + '\n'
        to_return += 'location: ' + self.raw_location + '\n'  # skip location validation
        if self.network:
            to_return += 'network: ' + self.network + '\n'
        if self.airs:
            to_return += 'airs: ' + self.airs + '\n'
        to_return += 'status: ' + self.status + '\n'
        to_return += 'startyear: ' + str(self.startyear) + '\n'
        if self.genre:
            to_return += 'genre: ' + self.genre + '\n'
        to_return += 'classification: ' + self.classification + '\n'
        to_return += 'runtime: ' + str(self.runtime) + '\n'
        to_return += 'quality: ' + str(self.quality) + '\n'
        to_return += 'scene: ' + str(self.is_scene) + '\n'
        to_return += 'sports: ' + str(self.is_sports) + '\n'
        to_return += 'anime: ' + str(self.is_anime) + '\n'
        return to_return

    def __unicode__(self):
        """Unicode representation.

        :return:
        :rtype: unicode
        """
        to_return = u''
        to_return += u'indexerid: {0}\n'.format(self.indexerid)
        to_return += u'indexer: {0}\n'.format(self.indexer)
        to_return += u'name: {0}\n'.format(self.name)
        to_return += u'location: {0}\n'.format(self.raw_location)  # skip location validation
        if self.network:
            to_return += u'network: {0}\n'.format(self.network)
        if self.airs:
            to_return += u'airs: {0}\n'.format(self.airs)
        to_return += u'status: {0}\n'.format(self.status)
        to_return += u'startyear: {0}\n'.format(self.startyear)
        if self.genre:
            to_return += u'genre: {0}\n'.format(self.genre)
        to_return += u'classification: {0}\n'.format(self.classification)
        to_return += u'runtime: {0}\n'.format(self.runtime)
        to_return += u'quality: {0}\n'.format(self.quality)
        to_return += u'scene: {0}\n'.format(self.is_scene)
        to_return += u'sports: {0}\n'.format(self.is_sports)
        to_return += u'anime: {0}\n'.format(self.is_anime)
        return to_return

    def to_json(self, detailed=True):
        """Return JSON representation."""
        indexer_name = indexerConfig[self.indexer]['identifier']
        bw_list = self.release_groups or BlackAndWhiteList(self.indexerid)
        result = OrderedDict([
            ('id', OrderedDict([
                (indexer_name, self.indexerid),
                ('imdb', str(self.imdbid))
            ])),
            ('title', self.name),
            ('indexer', indexer_name),  # e.g. tvdb
            ('network', self.network),  # e.g. CBS
            ('type', self.classification),  # e.g. Scripted
            ('status', self.status),  # e.g. Continuing
            ('airs', text_type(self.airs).replace('am', ' AM').replace('pm', ' PM').replace('  ', ' ').strip()),
            # e.g Thursday 8:00 PM
            ('language', self.lang),
            ('showType', 'sports' if self.is_sports else ('anime' if self.is_anime else 'series')),
            ('akas', self.get_akas()),
            ('year', OrderedDict([
                ('start', self.imdb_info.get('year') or self.startyear),
            ])),
            ('nextAirDate', self.get_next_airdate()),
            ('runtime', self.imdb_info.get('runtimes') or self.runtime),
            ('genres', self.get_genres()),
            ('rating', OrderedDict([])),
            ('classification', self.imdb_info.get('certificates')),
            ('cache', OrderedDict([])),
            ('countries', self.get_countries()),
            ('config', OrderedDict([
                ('location', self.raw_location),
                ('qualities', OrderedDict([
                    ('allowed', self.get_allowed_qualities()),
                    ('preferred', self.get_preferred_qualities()),
                ])),
                ('paused', bool(self.paused)),
                ('airByDate', bool(self.air_by_date)),
                ('subtitlesEnabled', bool(self.subtitles)),
                ('dvdOrder', bool(self.dvdorder)),
                ('flattenFolders', bool(self.flatten_folders)),
                ('scene', self.is_scene),
                ('defaultEpisodeStatus', statusStrings[self.default_ep_status]),
                ('aliases', self.exceptions or get_scene_exceptions(self.indexerid)),
                ('release', OrderedDict([
                    ('blacklist', bw_list.blacklist),
                    ('whitelist', bw_list.whitelist),
                    ('ignoredWords', [v for v in (self.rls_ignore_words or '').split(',') if v]),
                    ('requiredWords', [v for v in (self.rls_require_words or '').split(',') if v]),
                ])),
            ]))
        ])

        cache = image_cache.ImageCache()
        if 'rating' in self.imdb_info and 'votes' in self.imdb_info:
            result['rating']['imdb'] = OrderedDict([
                ('stars', self.imdb_info.get('rating')),
                ('votes', self.imdb_info.get('votes')),
            ])
        if os.path.isfile(cache.poster_path(self.indexerid)):
            result['cache']['poster'] = cache.poster_path(self.indexerid)
        if os.path.isfile(cache.banner_path(self.indexerid)):
            result['cache']['banner'] = cache.banner_path(self.indexerid)

        if detailed:
            result.update(OrderedDict([
                ('seasons', OrderedDict([]))
            ]))
            episodes = self.get_all_episodes()
            result['seasons'] = [list(v) for _, v in groupby([ep.to_json() for ep in episodes], lambda item: item['season'])]
            result['episodeCount'] = len(episodes)
            last_episode = episodes[-1] if episodes else None
            if self.status == 'Ended' and last_episode and last_episode.airdate:
                result['year']['end'] = last_episode.airdate.year

        return result

    def get_next_airdate(self):
        """Return next airdate."""
        return (
            sbdatetime.convert_to_setting(network_timezones.parse_date_time(self.nextaired, self.airs, self.network))
            if try_int(self.nextaired, 1) > MILLIS_YEAR_1900 else None
        )

    def get_genres(self):
        """Return genres list."""
        return list({v for v in (self.genre or '').split('|') if v} |
                    {v for v in self.imdb_info.get('genres', '').replace('Sci-Fi', 'Science-Fiction').split('|') if v})

    def get_akas(self):
        """Return genres akas dict."""
        akas = {}
        for x in [v for v in self.imdb_info.get('akas', '').split('|') if v]:
            if '::' in x:
                val, key = x.split('::')
                akas[key] = val
        return akas

    def get_countries(self):
        """Return country codes."""
        return [v for v in self.imdb_info.get('country_codes', '').split('|') if v]

    def get_allowed_qualities(self):
        """Return allowed qualities."""
        allowed = Quality.split_quality(self.quality)[0]

        return [Quality.qualityStrings[v] for v in allowed]

    def get_preferred_qualities(self):
        """Return preferred qualities."""
        preferred = Quality.split_quality(self.quality)[1]

        return [Quality.qualityStrings[v] for v in preferred]

    @staticmethod
    def __qualities_to_string(qualities=None):
        return ', '.join([Quality.qualityStrings[quality] for quality in qualities or []
                          if quality and quality in Quality.qualityStrings]) or 'None'

    def want_episode(self, season, episode, quality, forced_search=False, download_current_quality=False):
        """Whether or not the episode with the specified quality is wanted.

        :param season:
        :type season: int
        :param episode:
        :type episode: int
        :param quality:
        :type quality: int
        :param forced_search:
        :type forced_search: bool
        :param download_current_quality:
        :type download_current_quality: bool
        :return:
        :rtype: bool
        """
        # if the quality isn't one we want under any circumstances then just say no
        allowed_qualities, preferred_qualities = self.current_qualities
        logger.log(u'{id}: Allowed, Preferred = [ {allowed} ] [ {preferred} ] Found = [ {found} ]'.format
                   (id=self.indexerid, allowed=self.__qualities_to_string(allowed_qualities),
                    preferred=self.__qualities_to_string(preferred_qualities),
                    found=self.__qualities_to_string([quality])), logger.DEBUG)

        if not Quality.wanted_quality(quality, allowed_qualities, preferred_qualities):
            logger.log(u"{id}: Ignoring found result for '{show}' {ep} with unwanted quality '{quality}'".format
                       (id=self.indexerid, show=self.name, ep=episode_num(season, episode),
                        quality=Quality.qualityStrings[quality]), logger.DEBUG)
            return False

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(
            b'SELECT '
            b'  status, '
            b'  manually_searched '
            b'FROM '
            b'  tv_episodes '
            b'WHERE '
            b'  showid = ? '
            b'  AND season = ? '
            b'  AND episode = ?', [self.indexerid, season, episode])

        if not sql_results or not len(sql_results):
            logger.log(u'{id}: Unable to find a matching episode in database. '
                       u"Ignoring found result for '{show}' {ep} with quality '{quality}'".format
                       (id=self.indexerid, show=self.name, ep=episode_num(season, episode),
                        quality=Quality.qualityStrings[quality]), logger.DEBUG)
            return False

        ep_status = int(sql_results[0][b'status'])
        ep_status_text = statusStrings[ep_status]
        manually_searched = sql_results[0][b'manually_searched']
        _, cur_quality = Quality.split_composite_status(ep_status)

        # if it's one of these then we want it as long as it's in our allowed initial qualities
        if ep_status == WANTED:
            logger.log(u"{id}: '{show}' {ep} status is 'WANTED'. Accepting result with quality '{new_quality}'".format
                       (id=self.indexerid, status=ep_status_text, show=self.name, ep=episode_num(season, episode),
                        new_quality=Quality.qualityStrings[quality]), logger.DEBUG)
            return True

        should_replace, msg = Quality.should_replace(ep_status, cur_quality, quality, allowed_qualities,
                                                     preferred_qualities, download_current_quality,
                                                     forced_search, manually_searched)
        logger.log(u"{id}: '{show}' {ep} status is: '{status}'. {action} result with quality '{new_quality}'. "
                   u"Reason: {msg}".format
                   (id=self.indexerid, show=self.name, ep=episode_num(season, episode),
                    status=ep_status_text, action='Accepting' if should_replace else 'Ignoring',
                    new_quality=Quality.qualityStrings[quality], msg=msg), logger.DEBUG)
        return should_replace

    def get_overview(self, ep_status, backlog_mode=False, manually_searched=False):
        """Get the Overview status from the Episode status.

        :param ep_status: an Episode status
        :type ep_status: int
        :param backlog_mode: if we should return overview for backlogOverview
        :type backlog_mode: boolean
        :return: an Overview status
        :rtype: int
        """
        ep_status = try_int(ep_status) or UNKNOWN

        if backlog_mode:
            if ep_status == WANTED:
                return Overview.WANTED
            elif Quality.should_search(ep_status, self, manually_searched):
                return Overview.QUAL
            return Overview.GOOD

        if ep_status == WANTED:
            return Overview.WANTED
        elif ep_status in (UNAIRED, UNKNOWN):
            return Overview.UNAIRED
        elif ep_status in (SKIPPED, IGNORED):
            return Overview.SKIPPED
        elif ep_status in Quality.ARCHIVED:
            return Overview.GOOD
        elif ep_status in Quality.FAILED:
            return Overview.WANTED
        elif ep_status in Quality.SNATCHED:
            return Overview.SNATCHED
        elif ep_status in Quality.SNATCHED_PROPER:
            return Overview.SNATCHED_PROPER
        elif ep_status in Quality.SNATCHED_BEST:
            return Overview.SNATCHED_BEST
        elif ep_status in Quality.DOWNLOADED:
            if Quality.should_search(ep_status, self, manually_searched):
                return Overview.QUAL
            else:
                return Overview.GOOD
        else:
            logger.log(u'Could not parse episode status into a valid overview status: {status}'.format
                       (status=ep_status), logger.ERROR)

    def __getstate__(self):
        """Get threading lock state.

        :return:
        :rtype: dict(str -> threading.Lock)
        """
        d = dict(self.__dict__)
        del d['lock']
        return d

    def __setstate__(self, d):
        """Set threading lock state."""
        d['lock'] = threading.Lock()
        self.__dict__.update(d)


class TVEpisode(TVObject):
    """Represent a TV Show episode."""

    def __init__(self, show, season, episode, filepath=''):
        """Instantiate a TVEpisode with database information.

        :param show:
        :type show: TVShow
        :param season:
        :type season: int
        :param episode:
        :type episode: int
        :param filepath:
        :type filepath: str
        """
        super(TVEpisode, self).__init__(int(show.indexer) if show else 0, 0,
                                        {'show', 'scene_season', 'scene_episode', 'scene_absolute_number',
                                         'related_episodes', 'wanted_quality'})
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
        self.status = UNKNOWN
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
        """Return an TVEpisode for the given filepath.

        IMPORTANT: The filepath is not kept in the TVEpisode.location
        TVEpisode.location should only be set after it's post-processed and it's in the correct location.
        As of now, TVEpisode is also not cached in TVShow.episodes since this method is only used during postpone PP.
        Goal here is to slowly move to use this method to create TVEpisodes. New parameters might be introduced.

        :param filepath:
        :type filepath: str
        :return:
        :rtype: TVEpisode
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
            logger.log(u'Cannot create TVEpisode from path {path}'.format(path=filepath), logger.WARNING)

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
        logger.log(u'{id}: Setter sets location to {location}'.format
                   (id=self.show.indexerid, location=value), logger.DEBUG)
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
            logger.log(u'{id}: No changed subtitles for {show} {ep}. Current subtitles: {subs}'.format
                       (id=self.show.indexerid, show=self.show.name, ep=ep_num, subs=current_subtitles), logger.DEBUG)
        else:
            logger.log(u'{id}: Subtitle changes detected for this show {show} {ep}. Current subtitles: {subs}'.format
                       (id=self.show.indexerid, show=self.show.name, ep=ep_num, subs=current_subtitles), logger.DEBUG)
            self.subtitles = current_subtitles if current_subtitles else []
            logger.log(u'{id}: Saving subtitles changes to database'.format(id=self.show.indexerid), logger.DEBUG)
            self.save_to_db()

    def download_subtitles(self, lang=None):
        """Download subtitles.

        :param lang:
        :type lang: string
        """
        if not self.is_location_valid():
            logger.log(u"{id}: {show} {ep} file doesn't exist, can't download subtitles".format
                       (id=self.show.indexerid, show=self.show.name,
                        ep=(episode_num(self.season, self.episode) or episode_num(self.season, self.episode,
                                                                                  numbering='absolute'))),
                       logger.DEBUG)
            return

        new_subtitles = subtitles.download_subtitles(self, lang=lang)
        if new_subtitles:
            self.subtitles = subtitles.merge_subtitles(self.subtitles, new_subtitles)

        self.subtitles_searchcount += 1 if self.subtitles_searchcount else 1
        self.subtitles_lastsearch = datetime.datetime.now().strftime(dateTimeFormat)
        logger.log(u'{id}: Saving last subtitles search to database'.format(id=self.show.indexerid), logger.DEBUG)
        self.save_to_db()

        if new_subtitles:
            subtitle_list = ', '.join([subtitles.name_from_code(code) for code in new_subtitles])
            logger.log(u'{id}: Downloaded {subs} subtitles for {show} {ep}'.format
                       (id=self.show.indexerid, subs=subtitle_list, show=self.show.name,
                        ep=(episode_num(self.season, self.episode) or
                            episode_num(self.season, self.episode, numbering='absolute'))))

            notifiers.notify_subtitle_download(self.pretty_name(), subtitle_list)
        else:
            logger.log(u'{id}: No subtitles found for {show} {ep}'.format
                       (id=self.show.indexerid, show=self.show.name,
                        ep=(episode_num(self.season, self.episode) or
                            episode_num(self.season, self.episode, numbering='absolute'))))

        return new_subtitles

    def check_for_meta_files(self):
        """Whether metadata files has changed.

        :return:
        :rtype: bool
        """
        oldhasnfo = self.hasnfo
        oldhastbn = self.hastbn

        cur_nfo = False
        cur_tbn = False

        # check for nfo and tbn
        if self.is_location_valid():
            for cur_provider in app.metadata_provider_dict.values():
                if cur_provider.episode_metadata:
                    new_result = cur_provider.has_episode_metadata(self)
                else:
                    new_result = False
                cur_nfo = new_result or cur_nfo

                if cur_provider.episode_thumbnails:
                    new_result = cur_provider.has_episode_thumb(self)
                else:
                    new_result = False
                cur_tbn = new_result or cur_tbn

        self.hasnfo = cur_nfo
        self.hastbn = cur_tbn

        # if either setting has changed return true, if not return false
        return oldhasnfo != self.hasnfo or oldhastbn != self.hastbn

    def _specify_episode(self, season, episode):

        sql_results = self.load_from_db(season, episode)

        if not sql_results:
            # only load from NFO if we didn't load from DB
            if self.is_location_valid():
                try:
                    self.__load_from_nfo(self.location)
                except NoNFOException:
                    logger.log(u'{id}: There was an error loading the NFO for episode {show} {ep}'.format
                               (id=self.show.indexerid, show=self.show.name, ep=episode_num(season, episode)),
                               logger.ERROR)

                # if we tried loading it from NFO and didn't find the NFO, try the Indexers
                if not self.hasnfo:
                    try:
                        result = self.load_from_indexer(season, episode)
                    except EpisodeDeletedException:
                        result = False

                    # if we failed SQL *and* NFO, Indexers then fail
                    if not result:
                        raise EpisodeNotFoundException(u"{id}: Couldn't find episode {show} {ep}".format
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
            logger.log(u'{id}: {show} {ep} not found in the database'.format
                       (id=self.show.indexerid, show=self.show.name, ep=episode_num(self.season, self.episode)),
                       logger.DEBUG)
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

        indexer_lang = self.show.lang

        try:
            if cached_season:
                my_ep = cached_season[episode]
            else:
                if tvapi:
                    t = tvapi
                else:
                    indexer_api_params = indexerApi(self.indexer).api_params.copy()

                    indexer_api_params['cache'] = False

                    if indexer_lang:
                        indexer_api_params['language'] = indexer_lang

                    if self.show.dvdorder != 0:
                        indexer_api_params['dvdorder'] = True

                    t = indexerApi(self.indexer).indexer(**indexer_api_params)
                my_ep = t[self.show.indexerid][season][episode]

        except (IndexerError, IOError) as e:
            logger.log(u'{id}: {indexer} threw up an error: {error_msg}'.format
                       (id=self.show.indexerid, indexer=indexerApi(self.indexer).name, error_msg=ex(e)),
                       logger.WARNING)
            # if the episode is already valid just log it, if not throw it up
            if self.name:
                logger.log(
                    u'{id}: {indexer} timed out but we have enough info from other sources, allowing the error'.format
                    (id=self.show.indexerid, indexer=indexerApi(self.indexer).name), logger.DEBUG)
                return
            else:
                logger.log(u'{id}: {indexer} timed out, unable to create the episode'.format
                           (id=self.show.indexerid, indexer=indexerApi(self.indexer).name), logger.WARNING)
                return False
        except (IndexerEpisodeNotFound, IndexerSeasonNotFound):
            logger.log(u'{id}: Unable to find the episode on {indexer}. Deleting it from db'.format
                       (id=self.show.indexerid, indexer=indexerApi(self.indexer).name), logger.DEBUG)
            # if I'm no longer on the Indexers but I once was then delete myself from the DB
            if self.indexerid != -1:
                self.delete_episode()
            return

        if getattr(my_ep, 'episodename', None) is None:
            logger.log(u'{id}: {show} {ep} has no name on {indexer}. Setting to an empty string'.format
                       (id=self.show.indexerid, show=self.show.name, ep=episode_num(season, episode),
                        indexer=indexerApi(self.indexer).name))
            setattr(my_ep, 'episodename', '')

        if getattr(my_ep, 'absolute_number', None) is None:
            logger.log(u'{id}: {show} {ep} has no absolute number on {indexer}'.format
                       (id=self.show.indexerid, show=self.show.name, ep=episode_num(season, episode),
                        indexer=indexerApi(self.indexer).name), logger.DEBUG)
        else:
            logger.log(u'{id}: {show} {ep} has absolute number: {absolute} '.format
                       (id=self.show.indexerid, show=self.show.name, ep=episode_num(season, episode),
                        absolute=my_ep['absolute_number']),
                       logger.DEBUG)
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
            logger.log(u'{id}: Malformed air date of {aired} retrieved from {indexer} for {show} {ep}'.format
                       (id=self.show.indexerid, aired=firstaired, indexer=indexerApi(self.indexer).name,
                        show=self.show.name, ep=episode_num(season, episode)), logger.WARNING)
            # if I'm incomplete on the indexer but I once was complete then just delete myself from the DB for now
            if self.indexerid != -1:
                self.delete_episode()
            return False

        # early conversion to int so that episode doesn't get marked dirty
        self.indexerid = getattr(my_ep, 'id', None)
        if self.indexerid is None:
            logger.log(u'{id}: Failed to retrieve ID from {indexer}'.format
                       (id=self.show.indexerid, indexer=indexerApi(self.indexer).name), logger.ERROR)
            if self.indexerid != -1:
                self.delete_episode()
            return False

        # don't update show status if show dir is missing, unless it's missing on purpose
        if all([not self.show.is_location_valid(),
                not app.CREATE_MISSING_SHOW_DIRS,
                not app.ADD_SHOWS_WO_DIR]):
            logger.log(u"{id}: Show {show} location '{location}' is missing. Keeping current episode statuses"
                       .format(id=self.show.indexerid, show=self.show.name, location=self.show.raw_location),
                       logger.WARNING)
            return

        if self.location:
            logger.log(u"{id}: {show} {ep} has status '{status}' and location {location}".format
                       (id=self.show.indexerid, show=self.show.name, ep=episode_num(season, episode),
                        status=statusStrings[self.status].upper(), location=self.location), logger.DEBUG)

        if not os.path.isfile(self.location):
            if (self.airdate >= datetime.date.today() or self.airdate == datetime.date.fromordinal(1)) and \
                    self.status in (UNAIRED, UNKNOWN, WANTED):
                # Need to check if is UNAIRED otherwise code will step into second 'IF'
                # and make episode as default_ep_status
                # If is a leaked episode and user manually snatched, it will respect status
                # If is a fake (manually snatched), when user set as FAILED, status will be WANTED
                # and code below will make it UNAIRED again
                logger.log(u"{id}: {show} {ep} airs in the future or has no airdate, marking it '{status}'".format
                           (id=self.show.indexerid, show=self.show.name, ep=episode_num(season, episode),
                            status=statusStrings[UNAIRED].upper()), logger.DEBUG)
                self.status = UNAIRED
            elif self.status in (UNAIRED, UNKNOWN):
                # Only do UNAIRED/UNKNOWN, it could already be snatched/ignored/skipped,
                # or downloaded/archived to disconnected media
                new_status = self.show.default_ep_status if self.season > 0 else SKIPPED  # auto-skip specials
                logger.log(u"{id}: {show} {ep} has already aired, marking it '{status}'".format
                           (id=self.show.indexerid, show=self.show.name, ep=episode_num(season, episode),
                            status=statusStrings[new_status].upper()), logger.DEBUG)
                self.status = new_status
            else:
                logger.log(u"{id}: {show} {ep} status untouched: '{status}'".format
                           (id=self.show.indexerid, show=self.show.name,
                            ep=episode_num(season, episode), status=statusStrings[self.status].upper()), logger.DEBUG)

        # if we have a media file then it's downloaded
        elif helpers.is_media_file(self.location):
            # leave propers alone, you have to either post-process them or manually change them back
            if self.status not in Quality.SNATCHED_PROPER + Quality.DOWNLOADED + Quality.SNATCHED + Quality.ARCHIVED:
                old_status = self.status
                self.status = Quality.status_from_name(self.location, anime=self.show.is_anime)
                logger.log(u"{id}: {show} {ep} status changed from '{old_status}' to '{new_status}'".format
                           (id=self.show.indexerid, show=self.show.name, ep=episode_num(season, episode),
                            old_status=old_status, new_status=self.status), logger.DEBUG)

            else:
                logger.log(u"{id}: {show} {ep} status untouched: '{status}'".format
                           (id=self.show.indexerid, show=self.show.name,
                            ep=episode_num(season, episode), status=statusStrings[self.status].upper()), logger.DEBUG)

        # shouldn't get here probably
        else:
            logger.log(u"{id}: {show} {ep} status changed from '{old_status}' to 'UNKNOWN'".format
                       (id=self.show.indexerid, show=self.show.name, ep=episode_num(season, episode),
                        old_status=self.status), logger.WARNING)
            self.status = UNKNOWN

    def __load_from_nfo(self, location):

        if not self.show.is_location_valid():
            logger.log(u'{id}: The show location {location} is missing, unable to load metadata'.format
                       (id=self.show.indexerid, location=location), logger.WARNING)
            return

        logger.log(u'{id}: Loading episode details from the NFO file associated with {location}'.format
                   (id=self.show.indexerid, location=location), logger.DEBUG)

        self.location = location

        if self.location != '':

            if self.status == UNKNOWN and helpers.is_media_file(self.location):
                self.status = Quality.status_from_name(self.location, anime=self.show.is_anime)
                logger.log(u"{id}: {show} {ep} status changed from 'UNKNOWN' to '{new_status}'".format
                           (id=self.show.indexerid, show=self.show.name, ep=episode_num(self.season, self.episode),
                            new_status=self.status), logger.DEBUG)

            nfo_file = replace_extension(self.location, 'nfo')
            logger.log(u'{id}: Using NFO name {nfo}'.format(id=self.show.indexerid, nfo=nfo_file), logger.DEBUG)

            if os.path.isfile(nfo_file):
                try:
                    show_xml = ETree.ElementTree(file=nfo_file)
                except (SyntaxError, ValueError) as e:
                    logger.log(u'{id}: Error loading the NFO, backing up the NFO and skipping for now: '.format
                               (id=self.show.indexerid, error_msg=ex(e)), logger.ERROR)
                    try:
                        os.rename(nfo_file, nfo_file + '.old')
                    except Exception as e:
                        logger.log(u"{id}: Failed to rename your episode's NFO file. "
                                   u'You need to delete it or fix it: {error_msg}'.format
                                   (id=self.show.indexerid, error_msg=ex(e)), logger.WARNING)
                    raise NoNFOException('Error in NFO format')

                for ep_details in list(show_xml.iter('episodedetails')):
                    if (ep_details.findtext('season') is None or int(ep_details.findtext('season')) != self.season or
                            ep_details.findtext('episode') is None or
                            int(ep_details.findtext('episode')) != self.episode):
                        logger.log(u'{id}: NFO has an <episodedetails> block for a different episode - '
                                   u'wanted {ep_wanted} but got {ep_found}'.format
                                   (id=self.show.indexerid, ep_wanted=episode_num(self.season, self.episode),
                                    ep_found=episode_num(ep_details.findtext('season'),
                                                         ep_details.findtext('episode'))), logger.DEBUG)
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
        result = u''
        result += u'%r - %r - %r\n' % (self.show.name, episode_num(self.season, self.episode), self.name)
        result += u'location: %r\n' % self.location
        result += u'description: %r\n' % self.description
        result += u'subtitles: %r\n' % u','.join(self.subtitles)
        result += u'subtitles_searchcount: %r\n' % self.subtitles_searchcount
        result += u'subtitles_lastsearch: %r\n' % self.subtitles_lastsearch
        result += u'airdate: %r (%r)\n' % (self.airdate.toordinal(), self.airdate)
        result += u'hasnfo: %r\n' % self.hasnfo
        result += u'hastbn: %r\n' % self.hastbn
        result += u'status: %r\n' % self.status
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
            logger.log(u'{id}: The show dir is missing, unable to create metadata'.format
                       (id=self.show.indexerid), logger.WARNING)
            return

        self.__create_nfo()
        self.__create_thumbnail()

        if self.check_for_meta_files():
            logger.log(u'{id}: Saving metadata changes to database'.format(id=self.show.indexerid))
            self.save_to_db()

    def __create_nfo(self):

        result = False

        for cur_provider in app.metadata_provider_dict.values():
            result = cur_provider.create_episode_metadata(self) or result

        return result

    def __create_thumbnail(self):

        result = False

        for cur_provider in app.metadata_provider_dict.values():
            result = cur_provider.create_episode_thumb(self) or result

        return result

    def delete_episode(self):
        """Delete episode from database."""
        logger.log(u'{id}: Deleting {show} {ep} from the DB'.format
                   (id=self.show.indexerid, show=self.show.name,
                    ep=episode_num(self.season, self.episode)), logger.DEBUG)

        # remove myself from the show dictionary
        if self.show.get_episode(self.season, self.episode, no_create=True) == self:
            logger.log(u"{id}: Removing myself from my show's list".format
                       (id=self.show.indexerid), logger.DEBUG)
            del self.show.episodes[self.season][self.episode]

        # delete myself from the DB
        logger.log(u'{id}: Deleting myself from the database'.format
                   (id=self.show.indexerid), logger.DEBUG)
        main_db_con = db.DBConnection()
        sql = b'DELETE FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ?'
        main_db_con.action(sql, [self.show.indexerid, self.season, self.episode])

        # If there are now no more episodes in the db, also cleanup the indexer_update table. As we don't want
        # it to schedule updates for this season anymore.
        self.show.cleanup_season_updates(self.season)

        raise EpisodeDeletedException()

    def get_sql(self):
        """Create SQL queue for this episode if any of its data has been changed since the last save."""
        try:
            if not self.dirty:
                logger.log(u'{id}: Not creating SQL queue - record is not dirty'.format
                           (id=self.show.indexerid), logger.DEBUG)
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
            logger.log(u'{id}: Error while updating database: {error_msg}'.format
                       (id=self.show.indexerid, error_msg=repr(e)), logger.ERROR)

    def save_to_db(self):
        """Save this episode to the database if any of its data has been changed since the last save."""
        if not self.dirty:
            return

        new_value_dict = {'indexerid': self.indexerid,
                          'indexer': self.indexer,
                          'name': self.name,
                          'description': self.description,
                          'subtitles': ','.join(self.subtitles),
                          'subtitles_searchcount': self.subtitles_searchcount,
                          'subtitles_lastsearch': self.subtitles_lastsearch,
                          'airdate': self.airdate.toordinal(),
                          'hasnfo': self.hasnfo,
                          'hastbn': self.hastbn,
                          'status': self.status,
                          'location': self.location,
                          'file_size': self.file_size,
                          'release_name': self.release_name,
                          'is_proper': self.is_proper,
                          'absolute_number': self.absolute_number,
                          'version': self.version,
                          'release_group': self.release_group}

        control_value_dict = {'showid': self.show.indexerid,
                              'season': self.season,
                              'episode': self.episode}

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
                logger.log(u'Unable to parse release_group: {error_msg}'.format(error_msg=ex(e)), logger.DEBUG)
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
            logger.log(u'Found codec for {show} {ep}'.format(show=show_name, ep=ep_name), logger.DEBUG)

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
                logger.log(u'{id}: Episode has no release group, replacing it with {rg}'.format
                           (id=self.show.indexerid, rg=replace_map['%RG']), logger.DEBUG)
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

        logger.log(u'{id}: Formatting pattern: {pattern} -> {result_name}'.format
                   (id=self.show.indexerid, pattern=pattern, result_name=result_name), logger.DEBUG)

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
            logger.log(u"{id} Can't perform rename on {location} when it doesn't exist, skipping".format
                       (id=self.indexerid, location=self.location), logger.WARNING)
            return

        proper_path = self.proper_path()
        absolute_proper_path = os.path.join(self.show.location, proper_path)
        absolute_current_path_no_ext, file_ext = os.path.splitext(self.location)
        absolute_current_path_no_ext_length = len(absolute_current_path_no_ext)

        related_subs = []

        current_path = absolute_current_path_no_ext

        if absolute_current_path_no_ext.startswith(self.show.location):
            current_path = absolute_current_path_no_ext[len(self.show.location):]

        logger.log(u'{id}: Renaming/moving episode from the base path {location} to {new_location}'.format
                   (id=self.indexerid, location=self.location, new_location=absolute_proper_path), logger.DEBUG)

        # if it's already named correctly then don't do anything
        if proper_path == current_path:
            logger.log(u'{id}: File {location} is already named correctly, skipping'.format
                       (id=self.indexerid, location=self.location), logger.DEBUG)
            return

        related_files = post_processor.PostProcessor(self.location).list_associated_files(
            self.location, base_name_only=True, subfolders=True)

        # This is wrong. Cause of pp not moving subs.
        if self.show.subtitles and app.SUBTITLES_DIR != '':
            related_subs = post_processor.PostProcessor(
                self.location).list_associated_files(app.SUBTITLES_DIR, subtitles_only=True, subfolders=True)

        logger.log(u'{id} Files associated to {location}: {related_files}'.format
                   (id=self.indexerid, location=self.location, related_files=related_files), logger.DEBUG)

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
                logger.log(u'{id}: Unable to rename file {cur_file}'.format
                           (id=self.indexerid, cur_file=cur_related_file), logger.WARNING)

        for cur_related_sub in related_subs:
            absolute_proper_subs_path = os.path.join(app.SUBTITLES_DIR, self.formatted_filename())
            cur_result = helpers.rename_ep_file(cur_related_sub, absolute_proper_subs_path,
                                                absolute_current_path_no_ext_length)
            if not cur_result:
                logger.log(u'{id}: Unable to rename file {cur_file}'.format
                           (id=self.indexerid, cur_file=cur_related_sub), logger.WARNING)

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
                logger.log(u"{id}: About to modify date of '{location}' to show air date {air_date}".format
                           (id=self.show.indexerid, location=self.location,
                            air_date=time.strftime('%b %d,%Y (%H:%M)', airdatetime)), logger.DEBUG)
                try:
                    if helpers.touch_file(self.location, time.mktime(airdatetime)):
                        logger.log(u"{id}: Changed modify date of '{location}' to show air date {air_date}".format
                                   (id=self.show.indexerid, location=os.path.basename(self.location),
                                    air_date=time.strftime('%b %d,%Y (%H:%M)', airdatetime)))
                    else:
                        logger.log(u"{id}: Unable to modify date of '{location}' to show air date {air_date}".format
                                   (id=self.show.indexerid, location=os.path.basename(self.location),
                                    air_date=time.strftime('%b %d,%Y (%H:%M)', airdatetime)), logger.WARNING)
                except Exception:
                    logger.log(u"{id}: Failed to modify date of '{location}' to show air date {air_date}".format
                               (id=self.show.indexerid, location=os.path.basename(self.location),
                                air_date=time.strftime('%b %d,%Y (%H:%M)', airdatetime)), logger.WARNING)
        except Exception:
            logger.log(u"{id}: Failed to modify date of '{location}'".format
                       (id=self.show.indexerid, location=os.path.basename(self.location)), logger.WARNING)
