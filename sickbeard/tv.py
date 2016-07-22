# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
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
"""TVShow and TVEpisode classes."""

import os.path
import datetime
import threading
import re
import glob
import stat
import traceback
import shutil

from imdb import imdb
import shutil_custom
from six import text_type

import sickbeard
from sickbeard import (
    db, helpers, logger, image_cache, notifiers, postProcessor, subtitles, network_timezones,
)
from sickbeard.blackandwhitelist import BlackAndWhiteList
from sickbeard.common import (
    Quality, Overview, statusStrings,
    DOWNLOADED, SNATCHED, SNATCHED_PROPER, ARCHIVED, IGNORED, UNAIRED, WANTED, SKIPPED, UNKNOWN,
    NAMING_DUPLICATE, NAMING_EXTEND, NAMING_LIMITED_EXTEND, NAMING_SEPARATED_REPEAT, NAMING_LIMITED_EXTEND_E_PREFIXED,
)
from sickbeard.indexers.indexer_config import INDEXER_TVDB, INDEXER_TVRAGE
from sickbeard.name_parser.parser import NameParser, InvalidNameException, InvalidShowException
from sickbeard.scene_numbering import get_scene_absolute_numbering, get_scene_numbering, xem_refresh

from sickrage.helper.common import (
    dateTimeFormat, remove_extension, replace_extension, sanitize_filename, try_int, episode_num,
)
from sickrage.helper.encoding import ek
from sickrage.helper.exceptions import (
    EpisodeDeletedException, EpisodeNotFoundException, ex,
    MultipleEpisodesInDatabaseException, MultipleShowsInDatabaseException, MultipleShowObjectsException,
    NoNFOException, ShowDirectoryNotFoundException, ShowNotFoundException,
)
from sickrage.show.Show import Show


try:
    import xml.etree.cElementTree as ETree
except ImportError:
    import xml.etree.ElementTree as ETree

try:
    from send2trash import send2trash
except ImportError:
    pass


shutil.copyfile = shutil_custom.copyfile_custom


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
        """Return the tvdb_id

        :return:
        :rtype: int
        """
        return self.indexerid if self.indexerid and self.indexer == INDEXER_TVDB else None

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

    def __init__(self, indexer, indexerid, lang=''):
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
        self.quality = int(sickbeard.QUALITY_DEFAULT)
        self.flatten_folders = int(sickbeard.FLATTEN_FOLDERS_DEFAULT)
        self.status = 'Unknown'
        self.airs = ''
        self.startyear = 0
        self.paused = 0
        self.air_by_date = 0
        self.subtitles = int(sickbeard.SUBTITLES_DEFAULT)
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

        other_show = Show.find(sickbeard.showList, self.indexerid)
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
        return self.indexerid in sickbeard.RECENTLY_DELETED

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
        if sickbeard.CREATE_MISSING_SHOW_DIRS or self.is_location_valid():
            return self._location

        raise ShowDirectoryNotFoundException("Show folder doesn't exist, you shouldn't be using it")

    @location.setter
    def location(self, value):
        logger.log(u'Setter sets location to ' + value, logger.DEBUG)
        # Don't validate dir if user wants to add shows without creating a dir
        if sickbeard.ADD_SHOWS_WO_DIR or self.is_location_valid(value):
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
        return ek(os.path.isdir, location or self._location)

    def flush_episodes(self):
        """Delete references to anything that's not in the internal lists."""
        for cur_season in self.episodes:
            for cur_ep in self.episodes[cur_season]:
                my_ep = self.episodes[cur_season][cur_ep]
                self.episodes[cur_season][cur_ep] = None
                del my_ep

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
                    should_cache=True):
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
        :param should_cache:
        :type should_cache: bool
        :return:
        :rtype: TVEpisode
        """
        season = try_int(season, None)
        episode = try_int(episode, None)
        absolute_number = try_int(absolute_number, None)

        # if we get an anime get the real season and episode
        if self.is_anime and absolute_number and not season and not episode:
            main_db_con = db.DBConnection()
            sql = b'SELECT season, episode FROM tv_episodes WHERE showid = ? AND absolute_number = ? AND season != 0'
            sql_results = main_db_con.select(sql, [self.indexerid, absolute_number])

            if len(sql_results) == 1:
                episode = int(sql_results[0][b'episode'])
                season = int(sql_results[0][b'season'])
                logger.log(u'Found episode by absolute number {absolute} which is {ep}'.format
                           (absolute=absolute_number,
                            ep=episode_num(season, episode)), logger.DEBUG)
            elif len(sql_results) > 1:
                logger.log(u'Multiple entries for absolute number: {absolute} in show: {name} found '.format
                           (absolute=absolute_number, name=self.name), logger.ERROR)

                return None
            else:
                logger.log(
                    'No entries for absolute number: ' + str(absolute_number) + ' in show: ' + self.name + ' found.',
                    logger.DEBUG)
                return None

        if season not in self.episodes:
            self.episodes[season] = {}

        ep = None
        if episode not in self.episodes[season] or self.episodes[season][episode] is None:
            if no_create:
                return None

            if filepath:
                ep = TVEpisode(self, season, episode, filepath)
            else:
                ep = TVEpisode(self, season, episode)

        if ep is not None and should_cache:
            self.episodes[season][episode] = ep

        return ep

    def should_update(self, update_date=datetime.date.today()):
        """Whether the show information should be updated.

        :param update_date:
        :type update_date: datetime.date
        :return:
        :rtype: bool
        """
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

    def __write_show_nfo(self):

        result = False

        if not self.is_location_valid():
            logger.log(str(self.indexerid) + u": Show dir doesn't exist, skipping NFO generation")
            return False

        logger.log(str(self.indexerid) + u': Writing NFOs for show', logger.DEBUG)
        for cur_provider in sickbeard.metadata_provider_dict.values():
            result = cur_provider.create_show_metadata(self) or result

        return result

    def write_metadata(self, show_only=False):
        """Write show metadata files.

        :param show_only:
        :type show_only: bool
        """
        if not self.is_location_valid():
            logger.log(str(self.indexerid) + u": Show dir doesn't exist, skipping NFO generation")
            return

        self.__get_images()

        self.__write_show_nfo()

        if not show_only:
            self.__write_episode_nfos()

    def __write_episode_nfos(self):

        if not self.is_location_valid():
            logger.log(str(self.indexerid) + u": Show dir doesn't exist, skipping NFO generation")
            return

        logger.log(str(self.indexerid) + u': Writing NFOs for all episodes', logger.DEBUG)

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
            logger.log(str(self.indexerid) + u": Show dir doesn't exist, skipping NFO generation")
            return

        self.__update_show_nfo()

    def __update_show_nfo(self):

        result = False

        if not self.is_location_valid():
            logger.log(str(self.indexerid) + u": Show dir doesn't exist, skipping NFO generation")
            return False

        logger.log(str(self.indexerid) + u': Updating NFOs for show with new indexer info')
        for cur_provider in sickbeard.metadata_provider_dict.values():
            result = cur_provider.update_show_indexer_metadata(self) or result

        return result

    def load_episodes_from_dir(self):
        """Find all media files in the show folder and create episodes for as many as possible."""
        if not self.is_location_valid():
            logger.log(str(self.indexerid) + u": Show dir doesn't exist, not loading episodes from disk", logger.DEBUG)
            return

        logger.log(str(self.indexerid) + u': Loading all episodes from the show directory ' + self.location,
                   logger.DEBUG)

        # get file list
        media_files = helpers.listMediaFiles(self.location)
        logger.log(u'%s: Found files: %s' %
                   (self.indexerid, media_files), logger.DEBUG)

        # create TVEpisodes from each media file (if possible)
        sql_l = []
        for media_file in media_files:
            cur_episode = None

            logger.log(str(self.indexerid) + u': Creating episode from ' + media_file, logger.DEBUG)
            try:
                cur_episode = self.make_ep_from_file(ek(os.path.join, self.location, media_file))
            except (ShowNotFoundException, EpisodeNotFoundException) as e:
                logger.log(u'Episode ' + media_file + u' returned an exception: ' + ex(e), logger.ERROR)
                continue
            except EpisodeDeletedException:
                logger.log(u'The episode deleted itself when I tried making an object for it', logger.DEBUG)

            if cur_episode is None:
                continue

            # see if we should save the release name in the db
            ep_file_name = ek(os.path.basename, cur_episode.location)
            ep_file_name = ek(os.path.splitext, ep_file_name)[0]

            try:
                parse_result = NameParser(False, showObj=self, tryIndexers=True).parse(ep_file_name)
            except (InvalidNameException, InvalidShowException):
                parse_result = None

            if ' ' not in ep_file_name and parse_result and parse_result.release_group:
                logger.log(u'Name ' + ep_file_name + u' gave release group of ' + parse_result.release_group +
                           u', seems valid', logger.DEBUG)
                cur_episode.release_name = ep_file_name

            # store the reference in the show
            if cur_episode is not None:
                if self.subtitles:
                    try:
                        cur_episode.refresh_subtitles()
                    except Exception:
                        logger.log(u'%s: Could not refresh subtitles' % self.indexerid, logger.ERROR)
                        logger.log(traceback.format_exc(), logger.DEBUG)

                sql_l.append(cur_episode.get_sql())

        if sql_l:
            main_db_con = db.DBConnection()
            main_db_con.mass_action(sql_l)

    def load_episodes_from_db(self):
        """Load episodes from database.

        :return:
        :rtype: dict(int -> dict(int -> bool))
        """
        logger.log(u'Loading all episodes from the DB', logger.DEBUG)
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
                   b'  showid = indexer_id and showid = ?')
            sql_results = main_db_con.select(sql, [self.indexerid])
        except Exception as error:
            logger.log(u'Could not load episodes from the DB. Error: %s' % error, logger.ERROR)
            return scanned_eps

        indexer_api_params = sickbeard.indexerApi(self.indexer).api_params.copy()

        if self.lang:
            indexer_api_params[b'language'] = self.lang
            logger.log(u'Using language: ' + str(self.lang), logger.DEBUG)

        if self.dvdorder != 0:
            indexer_api_params[b'dvdorder'] = True

        t = sickbeard.indexerApi(self.indexer).indexer(**indexer_api_params)

        cached_show = t[self.indexerid]
        cached_seasons = {}
        cur_show_name = ''
        cur_show_id = ''

        for cur_result in sql_results:

            cur_season = int(cur_result[b'season'])
            cur_episode = int(cur_result[b'episode'])
            cur_show_id = int(cur_result[b'showid'])
            cur_show_name = text_type(cur_result[b'show_name'])

            logger.log(u'%s: Loading %s episodes from DB' % (cur_show_id, cur_show_name), logger.DEBUG)
            delete_ep = False

            if cur_season not in cached_seasons:
                try:
                    cached_seasons[cur_season] = cached_show[cur_season]
                except sickbeard.indexer_seasonnotfound as error:
                    logger.log(u'%s: %s (unaired/deleted) in the indexer %s for %s. '
                               u'Removing existing records from database' %
                               (cur_show_id, error.message, sickbeard.indexerApi(self.indexer).name, cur_show_name),
                               logger.DEBUG)
                    delete_ep = True

            if cur_season not in scanned_eps:
                logger.log(u'{id}: Not cur_season in scanned_eps'.format(id=cur_show_id), logger.DEBUG)
                scanned_eps[cur_season] = {}

            logger.log(u'{id}: Loading {show} {ep} from the DB'.format
                       (id=cur_show_id, show=cur_show_name, ep=episode_num(cur_season, cur_episode)),
                       logger.DEBUG)

            try:
                cur_ep = self.get_episode(cur_season, cur_episode)
                if not cur_ep:
                    raise EpisodeNotFoundException

                # if we found out that the ep is no longer on TVDB then delete it from our database too
                if delete_ep:
                    cur_ep.delete_episode()

                cur_ep.load_from_db(cur_season, cur_episode)
                cur_ep.load_from_indexer(tvapi=t, cached_season=cached_seasons[cur_season])
                scanned_eps[cur_season][cur_episode] = True
            except EpisodeDeletedException:
                logger.log(u'{id}: Tried loading {show} {ep} from the DB that should have been deleted, '
                           u'skipping it'.format(id=cur_show_id, show=cur_show_name,
                                                 ep=episode_num(cur_season, cur_episode)), logger.DEBUG)
                continue

        logger.log(u'{id}: Finished loading all episodes for {show} from the DB'.format
                   (show=cur_show_name, id=cur_show_id), logger.DEBUG)

        return scanned_eps

    def load_episodes_from_indexer(self, cache=True):
        """Load episodes from indexer.

        :param cache:
        :type cache: bool
        :return:
        :rtype: dict(int -> dict(int -> bool))
        """
        indexer_api_params = sickbeard.indexerApi(self.indexer).api_params.copy()

        if not cache:
            indexer_api_params['cache'] = False

        if self.lang:
            indexer_api_params['language'] = self.lang

        if self.dvdorder != 0:
            indexer_api_params['dvdorder'] = True

        try:
            t = sickbeard.indexerApi(self.indexer).indexer(**indexer_api_params)
            show_obj = t[self.indexerid]
        except sickbeard.indexer_error:
            logger.log(u'' + sickbeard.indexerApi(self.indexer).name +
                       u' timed out, unable to update episodes from ' +
                       sickbeard.indexerApi(self.indexer).name, logger.WARNING)
            return None

        logger.log(
            str(self.indexerid) + u': Loading all episodes from ' + sickbeard.indexerApi(self.indexer).name + u'..',
            logger.DEBUG)

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
                               (id=self.indexerid, indexer=sickbeard.indexerApi(self.indexer).name,
                                ep=episode_num(season, episode)))
                    continue
                else:
                    try:
                        ep.load_from_indexer(tvapi=t)
                    except EpisodeDeletedException:
                        logger.log(u'The episode was deleted, skipping the rest of the load')
                        continue

                with ep.lock:
                    ep.load_from_indexer(season, episode, tvapi=t)

                    sql_l.append(ep.get_sql())

                scanned_eps[season][episode] = True

        if sql_l:
            main_db_con = db.DBConnection()
            main_db_con.mass_action(sql_l)

        # Done updating save last update date
        self.last_update_indexer = datetime.date.today().toordinal()

        self.save_to_db()

        return scanned_eps

    def __get_images(self):
        fanart_result = poster_result = banner_result = False
        season_posters_result = season_banners_result = season_all_poster_result = season_all_banner_result = False

        for cur_provider in sickbeard.metadata_provider_dict.values():

            fanart_result = cur_provider.create_fanart(self) or fanart_result
            poster_result = cur_provider.create_poster(self) or poster_result
            banner_result = cur_provider.create_banner(self) or banner_result

            season_posters_result = cur_provider.create_season_posters(self) or season_posters_result
            season_banners_result = cur_provider.create_season_banners(self) or season_banners_result
            season_all_poster_result = cur_provider.create_season_all_poster(self) or season_all_poster_result
            season_all_banner_result = cur_provider.create_season_all_banner(self) or season_all_banner_result

        return fanart_result or poster_result or banner_result or season_posters_result or \
            season_banners_result or season_all_poster_result or season_all_banner_result

    def make_ep_from_file(self, filepath):
        """Make a TVEpisode object from a media file.

        :param filepath:
        :type filepath: str
        :return:
        :rtype: TVEpisode
        """
        if not ek(os.path.isfile, filepath):
            logger.log(u"{0}: That isn't even a real file dude... {1}".format
                       (self.indexerid, filepath))
            return None

        logger.log(u'{0}: Creating episode object from {1}'.format
                   (self.indexerid, filepath), logger.DEBUG)

        try:
            parse_result = NameParser(showObj=self, tryIndexers=True, parse_method=(
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
                if not cur_ep.location or ek(os.path.normpath, cur_ep.location) != ek(os.path.normpath, filepath):
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
                new_quality = Quality.nameQuality(filepath, self.is_anime)
                logger.log(u'{0}: Since this file has been renamed, I checked {1} and found quality {2}'.format
                           (self.indexerid, filepath, Quality.qualityStrings[new_quality]), logger.DEBUG)
                if new_quality != Quality.UNKNOWN:
                    with cur_ep.lock:
                        cur_ep.status = Quality.compositeStatus(DOWNLOADED, new_quality)

            # check for status/quality changes as long as it's a new file
            elif not same_file and sickbeard.helpers.isMediaFile(filepath) and (
                    cur_ep.status not in Quality.DOWNLOADED + Quality.ARCHIVED + [IGNORED]):
                old_status, old_quality = Quality.splitCompositeStatus(cur_ep.status)
                new_quality = Quality.nameQuality(filepath, self.is_anime)
                if new_quality == Quality.UNKNOWN:
                    new_quality = Quality.assumeQuality(filepath)

                new_status = None

                # if it was snatched and now exists then set the status correctly
                if old_status == SNATCHED and old_quality <= new_quality:
                    logger.log(u'{0}: This ep used to be snatched with quality {1} but a file exists with quality {2} '
                               u'so setting the status to DOWNLOADED'.format
                               (self.indexerid, Quality.qualityStrings[old_quality],
                                Quality.qualityStrings[new_quality]), logger.DEBUG)
                    new_status = DOWNLOADED

                # if it was snatched proper and we found a higher quality one then allow the status change
                elif old_status == SNATCHED_PROPER and old_quality < new_quality:
                    logger.log(u'{0}: This ep used to be snatched proper with quality {1} '
                               u'but a file exists with quality {2} so setting the status to DOWNLOADED'.format
                               (self.indexerid, Quality.qualityStrings[old_quality],
                                Quality.qualityStrings[new_quality]), logger.DEBUG)
                    new_status = DOWNLOADED

                elif old_status not in (SNATCHED, SNATCHED_PROPER):
                    new_status = DOWNLOADED

                if new_status is not None:
                    with cur_ep.lock:
                        logger.log(u'{0}: We have an associated file, '
                                   u'so setting the status from {1} to DOWNLOADED/{2}'.format
                                   (self.indexerid, cur_ep.status,
                                    Quality.statusFromName(filepath, anime=self.is_anime)), logger.DEBUG)
                        cur_ep.status = Quality.compositeStatus(new_status, new_quality)

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

        logger.log(str(self.indexerid) + u': Loading show info from database', logger.DEBUG)

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
            if self.airs is None:
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

        # Get IMDb_info from database
        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(b'SELECT * FROM imdb_info WHERE indexer_id = ?', [self.indexerid])

        if not sql_results:
            logger.log(u'{0}: Unable to find IMDb show info in the database'.format(self.indexerid))
            return
        else:
            self.imdb_info = dict(zip(sql_results[0].keys(), sql_results[0]))

        self.reset_dirty()
        return True

    def load_from_indexer(self, cache=True, tvapi=None):
        """Load show from indexer.

        :param cache:
        :type cache: bool
        :param tvapi:
        """
        if self.indexer == INDEXER_TVRAGE:
            return

        logger.log(u'{0}: Loading show info from {1}'.format(
            self.indexerid, sickbeard.indexerApi(self.indexer).name), logger.DEBUG)

        # There's gotta be a better way of doing this but we don't wanna
        # change the cache value elsewhere
        if tvapi:
            t = tvapi
        else:
            indexer_api_params = sickbeard.indexerApi(self.indexer).api_params.copy()

            if not cache:
                indexer_api_params['cache'] = False

            if self.lang:
                indexer_api_params['language'] = self.lang

            if self.dvdorder != 0:
                indexer_api_params['dvdorder'] = True

            t = sickbeard.indexerApi(self.indexer).indexer(**indexer_api_params)

        my_ep = t[self.indexerid]

        try:
            self.name = my_ep['seriesname'].strip()
        except AttributeError:
            raise sickbeard.indexer_attributenotfound(
                "Found %s, but attribute 'seriesname' was empty." % self.indexerid)

        self.classification = getattr(my_ep, 'classification', 'Scripted')
        self.genre = getattr(my_ep, 'genre', '')
        self.network = getattr(my_ep, 'network', '')
        self.runtime = getattr(my_ep, 'runtime', '')

        self.imdbid = getattr(my_ep, 'imdb_id', '')

        if getattr(my_ep, 'airs_dayofweek', None) is not None and getattr(my_ep, 'airs_time', None) is not None:
            self.airs = my_ep['airs_dayofweek'] + ' ' + my_ep['airs_time']

        if self.airs is None:
            self.airs = ''

        if getattr(my_ep, 'firstaired', None) is not None:
            self.startyear = int(str(my_ep['firstaired']).split('-')[0])

        self.status = getattr(my_ep, 'status', 'Unknown')

    def load_imdb_info(self):
        """Load all required show information from IMDb with IMDbPY."""
        imdb_api = imdb.IMDb()
        if not self.imdbid:
            self.imdbid = imdb_api.title2imdbID(self.name, kind='tv series')

        if not self.imdbid:
            logger.log(u'{0}: Not loading show info from IMDb, '
                       u"because we don't know its ID".format(self.indexerid))
            return

        # Make sure we only use one ID
        imdb_id = self.imdbid.split(',')[0]

        logger.log(u'{0}: Loading show info from IMDb with ID: {1}'.format(
                   self.indexerid, imdb_id), logger.DEBUG)

        # Remove first two chars from ID
        imdb_obj = imdb_api.get_movie(imdb_id[2:])

        self.imdb_info = {
            'imdb_id': imdb_id,
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

        action = ('delete', 'trash')[sickbeard.TRASH_REMOVE_SHOW]

        # remove self from show list
        sickbeard.showList = [x for x in sickbeard.showList if int(x.indexerid) != self.indexerid]

        # clear the cache
        image_cache_dir = ek(os.path.join, sickbeard.CACHE_DIR, 'images')
        for cache_file in ek(glob.glob, ek(os.path.join, image_cache_dir, str(self.indexerid) + '.*')):
            logger.log(u'Attempt to %s cache file %s' % (action, cache_file))
            try:
                if sickbeard.TRASH_REMOVE_SHOW:
                    send2trash(cache_file)
                else:
                    ek(os.remove, cache_file)

            except OSError as e:
                logger.log(u'Unable to %s %s: %s / %s' % (action, cache_file, repr(e), str(e)), logger.WARNING)

        # remove entire show folder
        if full:
            try:
                logger.log(u'Attempt to %s show folder %s' % (action, self.location))
                # check first the read-only attribute
                file_attribute = ek(os.stat, self.location)[0]
                if not file_attribute & stat.S_IWRITE:
                    # File is read-only, so make it writeable
                    logger.log(u'Attempting to make writeable the read only folder %s' % self.location, logger.DEBUG)
                    try:
                        ek(os.chmod, self.location, stat.S_IWRITE)
                    except Exception:
                        logger.log(u'Unable to change permissions of %s' % self.location, logger.WARNING)

                if sickbeard.TRASH_REMOVE_SHOW:
                    send2trash(self.location)
                else:
                    ek(shutil.rmtree, self.location)

                logger.log(u'%s show folder %s' % (('Deleted', 'Trashed')[sickbeard.TRASH_REMOVE_SHOW],
                                                   self.raw_location))

            except ShowDirectoryNotFoundException:
                logger.log(u'Show folder does not exist, no need to %s %s' % (action, self.raw_location),
                           logger.WARNING)
            except OSError as e:
                logger.log(u'Unable to %s %s: %s / %s' % (action, self.raw_location, repr(e), str(e)), logger.WARNING)

        if sickbeard.USE_TRAKT and sickbeard.TRAKT_SYNC_WATCHLIST:
            logger.log(u'Removing show: indexerid ' + str(self.indexerid) +
                       u', Title ' + str(self.name) + u' from Watchlist', logger.DEBUG)
            notifiers.trakt_notifier.update_watchlist(self, update='remove')

    def populate_cache(self):
        """Populate image caching."""
        cache_inst = image_cache.ImageCache()

        logger.log(u'Checking & filling cache for show ' + self.name, logger.DEBUG)
        cache_inst.fill_cache(self)

    def refresh_dir(self):
        """Refresh show using its location.

        :return:
        :rtype: bool
        """
        # make sure the show dir is where we think it is unless dirs are created on the fly
        if not sickbeard.CREATE_MISSING_SHOW_DIRS and not self.is_location_valid():
            return False

        # load from dir
        self.load_episodes_from_dir()

        # run through all locations from DB, check that they exist
        logger.log(str(self.indexerid) + u': Loading all episodes with a location from the database', logger.DEBUG)

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
            cur_loc = ek(os.path.normpath, ep[b'location'])
            season = int(ep[b'season'])
            episode = int(ep[b'episode'])

            try:
                cur_ep = self.get_episode(season, episode)
                if not cur_ep:
                    raise EpisodeDeletedException
            except EpisodeDeletedException:
                logger.log(u'The episode was deleted while we were refreshing it, moving on to the next one',
                           logger.DEBUG)
                continue

            # if the path doesn't exist or if it's not in our show dir
            if not ek(os.path.isfile, cur_loc) or not ek(os.path.normpath, cur_loc).startswith(
                    ek(os.path.normpath, self.location)):

                # check if downloaded files still exist, update our data if this has changed
                if not sickbeard.SKIP_REMOVED_FILES:
                    with cur_ep.lock:
                        # if it used to have a file associated with it and it doesn't anymore then
                        # set it to sickbeard.EP_DEFAULT_DELETED_STATUS
                        if cur_ep.location and cur_ep.status in Quality.DOWNLOADED:

                            if sickbeard.EP_DEFAULT_DELETED_STATUS == ARCHIVED:
                                _, old_quality = Quality.splitCompositeStatus(cur_ep.status)
                                new_status = Quality.compositeStatus(ARCHIVED, old_quality)
                            else:
                                new_status = sickbeard.EP_DEFAULT_DELETED_STATUS

                            logger.log(u"{id}: Location for {ep} doesn't exist, "
                                       u'removing it and changing our status to {status}'.format
                                       (id=self.indexerid, ep=episode_num(season, episode),
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

                    logger.log("Looking for hanging associates files for: {}".format(cur_loc))
                    related_files = postProcessor.PostProcessor(cur_loc).list_associated_files(
                                    cur_loc, base_name_only=False, subfolders=True)

                    if related_files:
                        logger.log(u"{id}: Found hanging associated files for {ep}, deleting: {files}".format(
                            id=self.indexerid, ep=episode_num(season, episode), files=related_files), logger.WARNING)
                        for related_file in related_files:
                            try:
                                os.remove(related_file)
                            except Exception as e:
                                logger.log(u"Could not delete associate file: {0}. Error: {1}".format(related_file, e),
                                           logger.WARNING)

        if sql_l:
            main_db_con = db.DBConnection()
            main_db_con.mass_action(sql_l)

    def download_subtitles(self, force=False):
        """Download subtitles.

        :param force:
        :type force: bool
        """
        if not self.is_location_valid():
            logger.log(u"{0}: Show dir doesn't exist, can't download subtitles".format(self.indexerid), logger.DEBUG)
            return

        logger.log(u'%s: Downloading subtitles' % self.indexerid, logger.DEBUG)

        try:
            episodes = self.get_all_episodes(has_location=True)
            if not episodes:
                logger.log(u'%s: No episodes to download subtitles for %s' % (self.indexerid, self.name), logger.DEBUG)
                return

            for episode in episodes:
                episode.download_subtitles(force=force)

        except Exception:
            logger.log(u'%s: Error occurred when downloading subtitles for %s' %
                       (self.indexerid, self.name), logger.DEBUG)
            logger.log(traceback.format_exc(), logger.ERROR)

    def save_to_db(self):
        """Save to database."""
        if not self.dirty:
            return

        logger.log(u'%i: Saving to database: %s' % (self.indexerid, self.name), logger.DEBUG)

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
        allowed_qualities, preferred_qualities = Quality.splitQuality(self.quality)
        logger.log(u'Any,Best = [ %s ] [ %s ] Found = [ %s ]' %
                   (self.__qualities_to_string(allowed_qualities),
                    self.__qualities_to_string(preferred_qualities),
                    self.__qualities_to_string([quality])), logger.DEBUG)

        if quality not in allowed_qualities + preferred_qualities or quality is UNKNOWN:
            logger.log(u"Don't want this quality, ignoring found result for {name} {ep} with quality {quality}".format
                       (name=self.name, ep=episode_num(season, episode), quality=Quality.qualityStrings[quality]),
                       logger.DEBUG)
            return False

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(
            b'SELECT '
            b'  status '
            b'FROM '
            b'  tv_episodes '
            b'WHERE '
            b'  showid = ? '
            b'  AND season = ? '
            b'  AND episode = ?', [self.indexerid, season, episode])

        if not sql_results or not len(sql_results):
            logger.log(u'Unable to find a matching episode in database, '
                       u'ignoring found result for {name} {ep} with quality {quality}'.format
                       (name=self.name, ep=episode_num(season, episode), quality=Quality.qualityStrings[quality]),
                       logger.DEBUG)
            return False

        ep_status = int(sql_results[0][b'status'])
        ep_status_text = statusStrings[ep_status]

        # if we know we don't want it then just say no
        if ep_status in Quality.ARCHIVED + [UNAIRED, SKIPPED, IGNORED] and not forced_search:
            logger.log(u"Existing episode status is '{status}', "
                       u'ignoring found result for {name} {ep} with quality {quality}'.format
                       (status=ep_status_text, name=self.name, ep=episode_num(season, episode),
                        quality=Quality.qualityStrings[quality]), logger.DEBUG)
            return False

        _, cur_quality = Quality.splitCompositeStatus(ep_status)

        # if it's one of these then we want it as long as it's in our allowed initial qualities
        if ep_status in (WANTED, SKIPPED, UNKNOWN):
            logger.log(u"Existing episode status is '{status}', "
                       u'getting found result for {name} {ep} with quality {quality}'.format
                       (status=ep_status_text, name=self.name, ep=episode_num(season, episode),
                        quality=Quality.qualityStrings[quality]), logger.DEBUG)
            return True
        elif forced_search:
            if (download_current_quality and quality >= cur_quality) or (
                    not download_current_quality and quality > cur_quality):
                logger.log(u'Usually ignoring found result, but forced search allows the quality,'
                           u' getting found result for {name} {ep} with quality {quality}'.format
                           (name=self.name, ep=episode_num(season, episode), quality=Quality.qualityStrings[quality]),
                           logger.DEBUG)
                return True

        # if we are re-downloading then we only want it if it's in our
        # preferred_qualities list and better than what we have, or we only have
        # one bestQuality and we do not have that quality yet
        if ep_status in Quality.DOWNLOADED + Quality.SNATCHED + Quality.SNATCHED_PROPER and \
                quality in preferred_qualities and (quality > cur_quality or cur_quality not in preferred_qualities):
            logger.log(u'Episode already exists with quality {existing_quality} but the found result'
                       u' quality {new_quality} is wanted more, getting found result for {name} {ep}'.format
                       (existing_quality=Quality.qualityStrings[cur_quality],
                        new_quality=Quality.qualityStrings[quality], name=self.name,
                        ep=episode_num(season, episode)), logger.DEBUG)
            return True
        elif cur_quality == Quality.UNKNOWN and forced_search:
            logger.log(u'Episode already exists but quality is Unknown, '
                       u'getting found result for {name} {ep} with quality {quality}'.format
                       (name=self.name, ep=episode_num(season, episode), quality=Quality.qualityStrings[quality]),
                       logger.DEBUG)
            return True
        else:
            logger.log(u'Episode already exists with quality {existing_quality} and the found result has '
                       u'same/lower quality, ignoring found result for {name} {ep} with quality {new_quality}'.format
                       (existing_quality=Quality.qualityStrings[cur_quality], name=self.name,
                        ep=episode_num(season, episode), new_quality=Quality.qualityStrings[quality]),
                       logger.DEBUG)
        return False

    def get_overview(self, ep_status):
        """Get the Overview status from the Episode status.

        :param ep_status: an Episode status
        :type ep_status: int
        :return: an Overview status
        :rtype: int
        """
        ep_status = try_int(ep_status) or UNKNOWN

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
            allowed_qualities, preferred_qualities = Quality.splitQuality(self.quality)
            ep_status, cur_quality = Quality.splitCompositeStatus(ep_status)

            if cur_quality not in allowed_qualities + preferred_qualities:
                return Overview.QUAL
            elif preferred_qualities and cur_quality not in preferred_qualities:
                return Overview.QUAL
            else:
                return Overview.GOOD
        else:
            logger.log(u'Could not parse episode status into a valid overview status: %s' % ep_status, logger.ERROR)

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
        self.related_episodes = []
        self.wanted_quality = []
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
            parse_result = NameParser(True, tryIndexers=True).parse(filepath, cache_result=True)
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
            logger.log(logger.INFO, u'Cannot create TVEpisode from path {path}'.format(path=filepath))


    @property
    def location(self):
        """Return the location.

        :return:
        :rtype: location
        """
        return self._location

    @location.setter
    def location(self, value):
        logger.log(u'Setter sets location to ' + value, logger.DEBUG)
        self._location = value
        self.file_size = ek(os.path.getsize, value) if value and self.is_location_valid(value) else 0

    def is_location_valid(self, location=None):
        """Whether the location is a valid file.

        :param location:
        :type location: str
        :return:
        :rtype: bool
        """
        return ek(os.path.isfile, location or self._location)

    def refresh_subtitles(self):
        """Look for subtitles files and refresh the subtitles property."""
        current_subtitles = subtitles.get_current_subtitles(self)
        ep_num = episode_num(self.season, self.episode) or \
            episode_num(self.season, self.episode, numbering='absolute')
        if self.subtitles == current_subtitles:
            logger.log(u'No changed subtitles for {0} {1}. Current subtitles: {2}'.format(
                self.show.name, ep_num, current_subtitles), logger.DEBUG)
        else:
            logger.log(u'Subtitle changes detected for this show {0} {1}. Current subtitles: {2}'.format(
                self.show.name, ep_num, current_subtitles), logger.DEBUG)
            self.subtitles = current_subtitles if current_subtitles else []
            self.save_to_db()

    def download_subtitles(self, force=False):
        """Download subtitles.

        :param force:
        :type force: bool
        """
        if not self.is_location_valid():
            logger.log(u"Episode file doesn't exist, can't download subtitles for {} {}".format
                       (self.show.name, episode_num(self.season, self.episode) or
                        episode_num(self.season, self.episode, numbering='absolute')), logger.DEBUG)
            return

        new_subtitles = subtitles.download_subtitles(self)
        if new_subtitles:
            self.subtitles = subtitles.merge_subtitles(self.subtitles, new_subtitles)

        self.subtitles_searchcount += 1 if self.subtitles_searchcount else 1
        self.subtitles_lastsearch = datetime.datetime.now().strftime(dateTimeFormat)
        self.save_to_db()

        if new_subtitles:
            subtitle_list = ', '.join([subtitles.name_from_code(code) for code in new_subtitles])
            logger.log(u'Downloaded {} subtitles for {} {}'.format
                       (subtitle_list, self.show.name, episode_num(self.season, self.episode) or
                        episode_num(self.season, self.episode, numbering='absolute')))

            notifiers.notify_subtitle_download(self.pretty_name(), subtitle_list)

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
            for cur_provider in sickbeard.metadata_provider_dict.values():
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
                    logger.log(u'{id}: There was an error loading the NFO for episode {ep}'.format
                               (id=self.show.indexerid, ep=episode_num(season, episode)), logger.ERROR)

                # if we tried loading it from NFO and didn't find the NFO, try the Indexers
                if not self.hasnfo:
                    try:
                        result = self.load_from_indexer(season, episode)
                    except EpisodeDeletedException:
                        result = False

                    # if we failed SQL *and* NFO, Indexers then fail
                    if not result:
                        raise EpisodeNotFoundException(
                            u"Couldn't find episode {ep}".format(ep=episode_num(season, episode)))

    def load_from_db(self, season, episode):
        """Load episode information from database.

        :param season:
        :type season: int
        :param episode:
        :type episode: int
        :return:
        :rtype: bool
        """
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
            logger.log(u'{id}: Episode {ep} not found in the database'.format
                       (id=self.show.indexerid, ep=episode_num(self.season, self.episode)),
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
                self.location = ek(os.path.normpath, sql_results[0][b'location'])
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

            self.reset_dirty()
            return True

    def load_from_indexer(self, season=None, episode=None, cache=True, tvapi=None, cached_season=None):
        """Load episode information from indexer.

        :param season:
        :type season: int
        :param episode:
        :type episode: int
        :param cache:
        :type cache: bool
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
                    indexer_api_params = sickbeard.indexerApi(self.indexer).api_params.copy()

                    if not cache:
                        indexer_api_params['cache'] = False

                    if indexer_lang:
                        indexer_api_params['language'] = indexer_lang

                    if self.show.dvdorder != 0:
                        indexer_api_params['dvdorder'] = True

                    t = sickbeard.indexerApi(self.indexer).indexer(**indexer_api_params)
                my_ep = t[self.show.indexerid][season][episode]

        except (sickbeard.indexer_error, IOError) as e:
            logger.log(u'' + sickbeard.indexerApi(self.indexer).name + u' threw up an error: ' + ex(e), logger.DEBUG)
            # if the episode is already valid just log it, if not throw it up
            if self.name:
                logger.log(u'' + sickbeard.indexerApi(self.indexer).name +
                           u' timed out but we have enough info from other sources, allowing the error', logger.DEBUG)
                return
            else:
                logger.log(u'' + sickbeard.indexerApi(self.indexer).name + u' timed out, unable to create the episode',
                           logger.ERROR)
                return False
        except (sickbeard.indexer_episodenotfound, sickbeard.indexer_seasonnotfound):
            logger.log(u'Unable to find the episode on ' + sickbeard.indexerApi(
                self.indexer).name + u'... has it been removed? Should I delete from db?', logger.DEBUG)
            # if I'm no longer on the Indexers but I once was then delete myself from the DB
            if self.indexerid != -1:
                self.delete_episode()
            return

        if getattr(my_ep, 'episodename', None) is None:
            logger.log(u'This episode {show} - {ep} has no name on {indexer}. Setting to an empty string'.format
                       (show=self.show.name, ep=episode_num(season, episode),
                        indexer=sickbeard.indexerApi(self.indexer).name))
            setattr(my_ep, 'episodename', '')

        if getattr(my_ep, 'absolute_number', None) is None:
            logger.log(u'{id}: This episode {show} - {ep} has no absolute number on {indexer}'.format
                       (id=self.show.indexerid, show=self.show.name, ep=episode_num(season, episode),
                        indexer=sickbeard.indexerApi(self.indexer).name), logger.DEBUG)
        else:
            logger.log(u'{id}: The absolute number for {ep} is: {absolute} '.format
                       (id=self.show.indexerid, ep=episode_num(season, episode), absolute=my_ep['absolute_number']),
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
            logger.log(u'Malformed air date of {aired} retrieved from {indexer} for ({show} - {ep})'.format
                       (aired=firstaired, indexer=sickbeard.indexerApi(self.indexer).name, show=self.show.name,
                        ep=episode_num(season, episode)), logger.WARNING)
            # if I'm incomplete on the indexer but I once was complete then just delete myself from the DB for now
            if self.indexerid != -1:
                self.delete_episode()
            return False

        # early conversion to int so that episode doesn't get marked dirty
        self.indexerid = getattr(my_ep, 'id', None)
        if self.indexerid is None:
            logger.log(u'Failed to retrieve ID from {indexer}'.format
                       (indexer=sickbeard.indexerApi(self.indexer).name), logger.ERROR)
            if self.indexerid != -1:
                self.delete_episode()
            return False

        # don't update show status if show dir is missing, unless it's missing on purpose
        if not self.show.is_location_valid() and \
                not sickbeard.CREATE_MISSING_SHOW_DIRS and not sickbeard.ADD_SHOWS_WO_DIR:
            logger.log(u'The show dir %s is missing, not bothering to change the episode statuses '
                       u"since it'd probably be invalid" % self.show.raw_location)
            return

        if self.location:
            logger.log(u'{id}: Setting status for {ep} based on status {status} and location {location}'.format
                       (id=self.show.indexerid, ep=episode_num(season, episode),
                        status=statusStrings[self.status], location=self.location), logger.DEBUG)

        if not ek(os.path.isfile, self.location):
            if (self.airdate >= datetime.date.today() or self.airdate == datetime.date.fromordinal(1)) and \
                    self.status in (UNAIRED, UNKNOWN, WANTED):
                # Need to check if is UNAIRED otherwise code will step into second 'IF'
                # and make episode as default_ep_status
                # If is a leaked episode and user manually snatched, it will respect status
                # If is a fake (manually snatched), when user set as FAILED, status will be WANTED
                # and code below will make it UNAIRED again
                logger.log(u'%s: Episode airs in the future or has no airdate, marking it %s' %
                           (self.show.indexerid, statusStrings[UNAIRED]), logger.DEBUG)
                self.status = UNAIRED
            elif self.status in (UNAIRED, UNKNOWN):
                # Only do UNAIRED/UNKNOWN, it could already be snatched/ignored/skipped,
                # or downloaded/archived to disconnected media
                logger.log(u'Episode has already aired, marking it %s' %
                           statusStrings[self.show.default_ep_status], logger.DEBUG)
                self.status = self.show.default_ep_status if self.season > 0 else SKIPPED  # auto-skip specials
            else:
                logger.log(u'Not touching status [ %s ] It could be skipped/ignored/snatched/archived' %
                           statusStrings[self.status], logger.DEBUG)

        # if we have a media file then it's downloaded
        elif sickbeard.helpers.isMediaFile(self.location):
            # leave propers alone, you have to either post-process them or manually change them back
            if self.status not in Quality.SNATCHED_PROPER + Quality.DOWNLOADED + Quality.SNATCHED + Quality.ARCHIVED:
                logger.log(
                    u'5 Status changes from ' + str(self.status) + u' to ' + str(Quality.statusFromName(self.location)),
                    logger.DEBUG)
                self.status = Quality.statusFromName(self.location, anime=self.show.is_anime)

        # shouldn't get here probably
        else:
            logger.log(u'6 Status changes from ' + str(self.status) + u' to ' + str(UNKNOWN), logger.DEBUG)
            self.status = UNKNOWN

    def __load_from_nfo(self, location):

        if not self.show.is_location_valid():
            logger.log(
                str(self.show.indexerid) + u': The show dir is missing, not bothering to try loading the episode NFO')
            return

        logger.log(
            str(self.show.indexerid) + u': Loading episode details from the NFO file associated with ' + location,
            logger.DEBUG)

        self.location = location

        if self.location != '':

            if self.status == UNKNOWN and sickbeard.helpers.isMediaFile(self.location):
                logger.log(u'7 Status changes from ' + str(self.status) + u' to ' + str(
                    Quality.statusFromName(self.location, anime=self.show.is_anime)), logger.DEBUG)
                self.status = Quality.statusFromName(self.location, anime=self.show.is_anime)

            nfo_file = replace_extension(self.location, 'nfo')
            logger.log(str(self.show.indexerid) + u': Using NFO name ' + nfo_file, logger.DEBUG)

            if ek(os.path.isfile, nfo_file):
                try:
                    show_xml = ETree.ElementTree(file=nfo_file)
                except (SyntaxError, ValueError) as e:
                    logger.log(u'Error loading the NFO, backing up the NFO and skipping for now: ' + ex(e),
                               logger.ERROR)
                    try:
                        ek(os.rename, nfo_file, nfo_file + '.old')
                    except Exception as e:
                        logger.log(u"Failed to rename your episode's NFO file - "
                                   u'you need to delete it or fix it: ' + ex(e), logger.ERROR)
                    raise NoNFOException('Error in NFO format')

                for ep_details in list(show_xml.iter('episodedetails')):
                    if ep_details.findtext('season') is None or int(ep_details.findtext('season')) != self.season or \
                       ep_details.findtext('episode') is None or int(ep_details.findtext('episode')) != self.episode:
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

            if ek(os.path.isfile, replace_extension(nfo_file, 'tbn')):
                self.hastbn = True
            else:
                self.hastbn = False

    def __str__(self):
        """String representation.

        :return:
        :rtype: unicode
        """
        result = u''
        result += u'%r - S%02rE%02r - %r\n' % (self.show.name, self.season, self.episode, self.name)
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

    def create_meta_files(self):
        """Create episode metadata files."""
        if not self.show.is_location_valid():
            logger.log(str(self.show.indexerid) + u': The show dir is missing, not bothering to try to create metadata')
            return

        self.__create_nfo()
        self.__create_thumbnail()

        if self.check_for_meta_files():
            self.save_to_db()

    def __create_nfo(self):

        result = False

        for cur_provider in sickbeard.metadata_provider_dict.values():
            result = cur_provider.create_episode_metadata(self) or result

        return result

    def __create_thumbnail(self):

        result = False

        for cur_provider in sickbeard.metadata_provider_dict.values():
            result = cur_provider.create_episode_thumb(self) or result

        return result

    def delete_episode(self):
        """Delete episode from database."""
        logger.log(u'Deleting {show} {ep} from the DB'.format
                   (show=self.show.name, ep=episode_num(self.season, self.episode)), logger.DEBUG)

        # remove myself from the show dictionary
        if self.show.get_episode(self.season, self.episode, no_create=True) == self:
            logger.log(u"Removing myself from my show's list", logger.DEBUG)
            del self.show.episodes[self.season][self.episode]

        # delete myself from the DB
        logger.log(u'Deleting myself from the database', logger.DEBUG)
        main_db_con = db.DBConnection()
        sql = b'DELETE FROM tv_episodes WHERE showid=' + str(self.show.indexerid) + b' AND season=' + str(
            self.season) + b' AND episode=' + str(self.episode)
        main_db_con.action(sql)

        raise EpisodeDeletedException()

    def get_sql(self):
        """Create SQL queue for this episode if any of its data has been changed since the last save."""
        try:
            if not self.dirty:
                logger.log(str(self.show.indexerid) + u': Not creating SQL queue - record is not dirty', logger.DEBUG)
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
                if sickbeard.SUBTITLES_MULTI or not rows[0][b'subtitles'] or not self.subtitles:
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
                        b'  release_group = ? '
                        b'WHERE '
                        b'  episode_id = ?',
                        [self.indexerid, self.indexer, self.name, self.description, ','.join(self.subtitles),
                         self.subtitles_searchcount, self.subtitles_lastsearch, self.airdate.toordinal(), self.hasnfo,
                         self.hastbn, self.status, self.location, self.file_size, self.release_name, self.is_proper,
                         self.show.indexerid, self.season, self.episode, self.absolute_number, self.version,
                         self.release_group, ep_id]]
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
                        b'  release_group = ? '
                        b'WHERE '
                        b'  episode_id = ?',
                        [self.indexerid, self.indexer, self.name, self.description,
                         self.subtitles_searchcount, self.subtitles_lastsearch, self.airdate.toordinal(), self.hasnfo,
                         self.hastbn, self.status, self.location, self.file_size, self.release_name, self.is_proper,
                         self.show.indexerid, self.season, self.episode, self.absolute_number, self.version,
                         self.release_group, ep_id]]
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
            logger.log(u'Error while updating database: %s' %
                       (repr(e)), logger.ERROR)

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

    def full_path(self):
        """Return episode full path.

        :return:
        :rtype: str
        """
        if self.location is None or self.location == '':
            return None
        else:
            return ek(os.path.join, self.show.location, self.location)

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
            return helpers.sanitizeSceneName(name)

        def us(name):
            return re.sub('[ -]', '_', name)

        def release_name(name):
            if name:
                name = helpers.remove_non_release_groups(remove_extension(name))
            return name

        def release_group(show, name):
            if name:
                name = helpers.remove_non_release_groups(remove_extension(name))
            else:
                return ''

            try:
                parse_result = NameParser(name, showObj=show, naming_pattern=True).parse(name)
            except (InvalidNameException, InvalidShowException) as e:
                logger.log(u'Unable to get parse release_group: {}'.format(e), logger.DEBUG)
                return ''

            if not parse_result.release_group:
                return ''
            return parse_result.release_group.strip('.- []{}')

        _, ep_qual = Quality.splitCompositeStatus(self.status)  # @UnusedVariable

        if sickbeard.NAMING_STRIP_YEAR:
            show_name = re.sub(r'\(\d+\)$', '', self.show.name).rstrip()
        else:
            show_name = self.show.name

        # try to get the release group
        rel_grp = {
            'SickRage': 'SickRage'
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
            relgrp = 'SickRage'

        # try to get the release encoder to comply with scene naming standards
        encoder = Quality.sceneQualityFromName(self.release_name.replace(rel_grp[relgrp], ''), ep_qual)
        if encoder:
            logger.log(u"Found codec for '" + show_name + u': ' + ep_name + u"'.", logger.DEBUG)

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
            pattern = sickbeard.NAMING_PATTERN

        if multi is None:
            multi = sickbeard.NAMING_MULTI_EP

        if sickbeard.NAMING_CUSTOM_ANIME:
            if anime_type is None:
                anime_type = sickbeard.NAMING_ANIME
        else:
            anime_type = 3

        replace_map = self.__replace_map()

        result_name = pattern

        # if there's no release group in the db, let the user know we replaced it
        if replace_map['%RG'] and replace_map['%RG'] != 'SickRage':
            if not hasattr(self, 'release_group'):
                logger.log(u"Episode has no release group, replacing it with '" +
                           replace_map['%RG'] + u"'", logger.DEBUG)
                self.release_group = replace_map['%RG']  # if release_group is not in the db, put it there
            elif not self.release_group:
                logger.log(u"Episode has no release group, replacing it with '" +
                           replace_map['%RG'] + u"'", logger.DEBUG)
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

        logger.log(u'formatting pattern: ' + pattern + u' -> ' + result_name, logger.DEBUG)

        return result_name

    def proper_path(self):
        """Figure out the path where this episode SHOULD be according to the renaming rules, relative from the show dir.

        :return:
        :rtype: str
        """
        anime_type = sickbeard.NAMING_ANIME
        if not self.show.is_anime:
            anime_type = 3

        result = self.formatted_filename(anime_type=anime_type)

        # if they want us to flatten it and we're allowed to flatten it then we will
        if self.show.flatten_folders and not sickbeard.NAMING_FORCE_FOLDERS:
            return result

        # if not we append the folder on and use that
        else:
            result = ek(os.path.join, self.formatted_dir(), result)

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
            if self.show.air_by_date and sickbeard.NAMING_CUSTOM_ABD and not self.related_episodes:
                pattern = sickbeard.NAMING_ABD_PATTERN
            elif self.show.sports and sickbeard.NAMING_CUSTOM_SPORTS and not self.related_episodes:
                pattern = sickbeard.NAMING_SPORTS_PATTERN
            elif self.show.anime and sickbeard.NAMING_CUSTOM_ANIME:
                pattern = sickbeard.NAMING_ANIME_PATTERN
            else:
                pattern = sickbeard.NAMING_PATTERN

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
            if self.show.air_by_date and sickbeard.NAMING_CUSTOM_ABD and not self.related_episodes:
                pattern = sickbeard.NAMING_ABD_PATTERN
            elif self.show.sports and sickbeard.NAMING_CUSTOM_SPORTS and not self.related_episodes:
                pattern = sickbeard.NAMING_SPORTS_PATTERN
            elif self.show.anime and sickbeard.NAMING_CUSTOM_ANIME:
                pattern = sickbeard.NAMING_ANIME_PATTERN
            else:
                pattern = sickbeard.NAMING_PATTERN

        # split off the dirs only, if they exist
        name_groups = re.split(r'[\\/]', pattern)

        return sanitize_filename(self._format_pattern(name_groups[-1], multi, anime_type))

    def rename(self):
        """Rename an episode file and all related files to the location and filename as specified in naming settings."""
        if not self.is_location_valid():
            logger.log(u"Can't perform rename on " + self.location + u" when it doesn't exist, skipping",
                       logger.WARNING)
            return

        proper_path = self.proper_path()
        absolute_proper_path = ek(os.path.join, self.show.location, proper_path)
        absolute_current_path_no_ext, file_ext = ek(os.path.splitext, self.location)
        absolute_current_path_no_ext_length = len(absolute_current_path_no_ext)

        related_subs = []

        current_path = absolute_current_path_no_ext

        if absolute_current_path_no_ext.startswith(self.show.location):
            current_path = absolute_current_path_no_ext[len(self.show.location):]

        logger.log(u'Renaming/moving episode from the base path ' + self.location + u' to ' + absolute_proper_path,
                   logger.DEBUG)

        # if it's already named correctly then don't do anything
        if proper_path == current_path:
            logger.log(str(self.indexerid) + u': File ' + self.location + u' is already named correctly, skipping',
                       logger.DEBUG)
            return

        related_files = postProcessor.PostProcessor(self.location).list_associated_files(
            self.location, base_name_only=True, subfolders=True)

        # This is wrong. Cause of pp not moving subs.
        if self.show.subtitles and sickbeard.SUBTITLES_DIR != '':
            related_subs = postProcessor.PostProcessor(
                self.location).list_associated_files(sickbeard.SUBTITLES_DIR, subtitles_only=True, subfolders=True)

        logger.log(u'Files associated to ' + self.location + u': ' + str(related_files), logger.DEBUG)

        # move the ep file
        result = helpers.rename_ep_file(self.location, absolute_proper_path, absolute_current_path_no_ext_length)

        # move related files
        for cur_related_file in related_files:
            # We need to fix something here because related files can be in subfolders
            # and the original code doesn't handle this (at all)
            cur_related_dir = ek(os.path.dirname, ek(os.path.abspath, cur_related_file))
            subfolder = cur_related_dir.replace(ek(os.path.dirname, ek(os.path.abspath, self.location)), '')
            # We now have a subfolder. We need to add that to the absolute_proper_path.
            # First get the absolute proper-path dir
            proper_related_dir = ek(os.path.dirname, ek(os.path.abspath, absolute_proper_path + file_ext))
            proper_related_path = absolute_proper_path.replace(proper_related_dir, proper_related_dir + subfolder)

            cur_result = helpers.rename_ep_file(cur_related_file, proper_related_path,
                                                absolute_current_path_no_ext_length + len(subfolder))
            if not cur_result:
                logger.log(str(self.indexerid) + u': Unable to rename file ' + cur_related_file, logger.ERROR)

        for cur_related_sub in related_subs:
            absolute_proper_subs_path = ek(os.path.join, sickbeard.SUBTITLES_DIR, self.formatted_filename())
            cur_result = helpers.rename_ep_file(cur_related_sub, absolute_proper_subs_path,
                                                absolute_current_path_no_ext_length)
            if not cur_result:
                logger.log(str(self.indexerid) + u': Unable to rename file ' + cur_related_sub, logger.ERROR)

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

        Note: Also called from postProcessor
        """
        if not all([sickbeard.AIRDATE_EPISODES, self.airdate, self.location,
                    self.show, self.show.airs, self.show.network]):
            return

        try:
            airdate_ordinal = self.airdate.toordinal()
            if airdate_ordinal < 1:
                return

            airdatetime = network_timezones.parse_date_time(airdate_ordinal, self.show.airs, self.show.network)

            if sickbeard.FILE_TIMESTAMP_TIMEZONE == 'local':
                airdatetime = airdatetime.astimezone(network_timezones.sb_timezone)

            filemtime = datetime.datetime.fromtimestamp(
                ek(os.path.getmtime, self.location)).replace(tzinfo=network_timezones.sb_timezone)

            if filemtime != airdatetime:
                import time

                airdatetime = airdatetime.timetuple()
                logger.log(u"{}: About to modify date of '{}' to show air date {}".format
                           (self.show.indexerid, self.location, time.strftime('%b %d,%Y (%H:%M)', airdatetime)),
                           logger.DEBUG)
                try:
                    if helpers.touchFile(self.location, time.mktime(airdatetime)):
                        logger.log(u"{}: Changed modify date of '{}' to show air date {}".format
                                   (self.show.indexerid, ek(os.path.basename, self.location),
                                    time.strftime('%b %d,%Y (%H:%M)', airdatetime)))
                    else:
                        logger.log(u"{}: Unable to modify date of '{}' to show air date {}".format
                                   (self.show.indexerid, ek(os.path.basename, self.location),
                                    time.strftime('%b %d,%Y (%H:%M)', airdatetime)), logger.WARNING)
                except Exception:
                    logger.log(u"{}: Failed to modify date of '{}' to show air date {}".format
                               (self.show.indexerid, ek(os.path.basename, self.location),
                                time.strftime('%b %d,%Y (%H:%M)', airdatetime)), logger.WARNING)
        except Exception:
            logger.log(u"{}: Failed to modify date of '{}'".format
                       (self.show.indexerid, ek(os.path.basename, self.location)), logger.WARNING)
