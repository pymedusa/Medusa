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
"""Series classes."""

from __future__ import unicode_literals

import copy
import datetime
import glob
import logging
import os.path
import shutil
import stat
import traceback
import warnings
from collections import (
    OrderedDict,
    namedtuple,
)
from itertools import groupby

from imdbpie import imdbpie

from medusa import (
    app,
    db,
    helpers,
    image_cache,
    network_timezones,
    notifiers,
    post_processor,
    subtitles,
)
from medusa.black_and_white_list import BlackAndWhiteList
from medusa.common import (
    ARCHIVED,
    DOWNLOADED,
    FAILED,
    IGNORED,
    Overview,
    Quality,
    SKIPPED,
    SNATCHED,
    SNATCHED_BEST,
    SNATCHED_PROPER,
    UNAIRED,
    UNKNOWN,
    WANTED,
    qualityPresets,
    statusStrings,
)
from medusa.helper.common import (
    episode_num,
    pretty_file_size,
    try_int,
)
from medusa.helper.exceptions import (
    EpisodeDeletedException,
    EpisodeNotFoundException,
    MultipleShowObjectsException,
    MultipleShowsInDatabaseException,
    ShowDirectoryNotFoundException,
    ShowNotFoundException,
    ex,
)
from medusa.helpers.externals import get_externals
from medusa.indexers.indexer_api import indexerApi
from medusa.indexers.indexer_config import (
    INDEXER_TVRAGE,
    indexerConfig,
    indexer_id_to_slug,
    mappings,
    reverse_mappings
)
from medusa.indexers.indexer_exceptions import (
    IndexerAttributeNotFound,
    IndexerException,
    IndexerSeasonNotFound,
)
from medusa.name_parser.parser import (
    InvalidNameException,
    InvalidShowException,
    NameParser,
)
from medusa.sbdatetime import sbdatetime
from medusa.scene_exceptions import get_scene_exceptions
from medusa.show.show import Show
from medusa.tv.base import TV
from medusa.tv.episode import Episode

import shutil_custom

from six import text_type

try:
    from send2trash import send2trash
except ImportError:
    app.TRASH_REMOVE_SHOW = 0


shutil.copyfile = shutil_custom.copyfile_custom

MILLIS_YEAR_1900 = datetime.datetime(year=1900, month=1, day=1).toordinal()

logger = logging.getLogger(__name__)


class Series(TV):
    """Represent a TV Show."""

    def __init__(self, indexer, indexerid, lang='', quality=None,
                 flatten_folders=None, enabled_subtitles=None):
        """Instantiate a Series with database information based on indexerid.

        :param indexer:
        :type indexer: int
        :param indexerid:
        :type indexerid: int
        :param lang:
        :type lang: str
        """
        super(Series, self).__init__(indexer, indexerid, {'episodes', 'next_aired', 'release_groups', 'exceptions',
                                                          'external', 'imdb_info'})
        self.name = ''
        self.imdb_id = ''
        self.network = ''
        self.genre = ''
        self.classification = ''
        self.runtime = 0
        self.imdb_info = {}
        self.quality = quality or int(app.QUALITY_DEFAULT)
        self.flatten_folders = flatten_folders or int(app.FLATTEN_FOLDERS_DEFAULT)
        self.status = 'Unknown'
        self.airs = ''
        self.start_year = 0
        self.paused = 0
        self.air_by_date = 0
        self.subtitles = enabled_subtitles or int(app.SUBTITLES_DEFAULT)
        self.dvd_order = 0
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
        self.next_aired = ''
        self.release_groups = None
        self.exceptions = set()
        self.externals = {}
        self._cached_indexer_api = None
        self.plot = None

        other_show = Show.find(app.showList, self.indexerid)
        if other_show is not None:
            raise MultipleShowObjectsException("Can't create a show if it already exists")

        self._load_from_db()

    @property
    def indexer_api(self):
        """Get an Indexer API instance."""
        if not self._cached_indexer_api:
            self.create_indexer()
        return self._cached_indexer_api

    @indexer_api.setter
    def indexer_api(self, value):
        """Set an Indexer API instance."""
        self._cached_indexer_api = value

    def create_indexer(self, banners=False, actors=False, dvd_order=False, episodes=True, ):
        """Force the creation of a new Indexer API."""
        api = indexerApi(self.indexer)
        params = api.api_params.copy()

        if self.lang:
            params[b'language'] = self.lang
            logger.debug(u'{id}: Using language from show settings: {lang}', id=self.indexerid, lang=self.lang)

        if self.dvd_order != 0 or dvd_order:
            params[b'dvdorder'] = True

        params[b'actors'] = actors

        params[b'banners'] = banners

        params[b'episodes'] = episodes

        self._cached_indexer_api = api.indexer(**params)

    @property
    def is_anime(self):
        """Check if the show is Anime."""
        return bool(self.anime)

    def is_location_valid(self, location=None):
        """
        Check if the location is valid.

        :param location: Path to check
        :return: True if the given path is a directory
        """
        return os.path.isdir(location or self._location)

    @property
    def is_recently_deleted(self):
        """
        Check if the show was recently deleted.

        Can be used to suppress error messages such as attempting to use the
        show object just after being removed.
        """
        return self.indexer_slug in app.RECENTLY_DELETED

    @property
    def is_scene(self):
        """Check if this ia a scene show."""
        return bool(self.scene)

    @property
    def is_sports(self):
        """Check if this is a sport show."""
        return bool(self.sports)

    @property
    def network_logo_name(self):
        """The network logo name."""
        return self.network.replace(u'\u00C9', 'e').replace(u'\u00E9', 'e').lower()

    @property
    def raw_location(self):
        """The raw show location, unvalidated."""
        return self._location

    @property
    def location(self):
        """The show location."""
        # no dir check needed if missing
        # show dirs are created during post-processing
        if app.CREATE_MISSING_SHOW_DIRS or self.is_location_valid():
            return self._location
        raise ShowDirectoryNotFoundException(u'Show folder does not exist.')

    @property
    def indexer_name(self):
        """Return the indexer name identifier. Example: tvdb."""
        return indexerConfig[self.indexer].get('identifier')

    @property
    def indexer_slug(self):
        """Return the slug name of the show. Example: tvdb1234."""
        return indexer_id_to_slug(self.indexer, self.indexerid)

    @location.setter
    def location(self, value):
        logger.debug(
            u'{indexer} {id}: Setting location: {location}',
            indexer=indexerApi(self.indexer).name,
            id=self.indexerid,
            location=value
        )
        # Don't validate dir if user wants to add shows without creating a dir
        if app.ADD_SHOWS_WO_DIR or self.is_location_valid(value):
            self._location = value
        else:
            raise ShowDirectoryNotFoundException(u'Invalid show folder!')

    @property
    def current_qualities(self):
        """
        The show qualities.

        :returns: A tuple of allowed and preferred qualities
        """
        return Quality.split_quality(int(self.quality))

    @property
    def using_preset_quality(self):
        """Check if a preset is used."""
        return self.quality in qualityPresets

    @property
    def default_ep_status_name(self):
        """Default episode status name."""
        return statusStrings[self.default_ep_status]

    @property
    def size(self):
        """Size of the show on disk."""
        return helpers.get_size(self.raw_location)

    def show_size(self, pretty=False):
        """
        Deprecated method to get the size of the show on disk.

        :param pretty: True if you want a pretty size. (e.g. 3 GB)
        :return:  Size of the show on disk.
        """
        warnings.warn(
            u'Method show_size is deprecated.  Use size property instead.',
            DeprecationWarning,
        )
        return pretty_file_size(self.size) if pretty else self.size

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

        return {int(x[b'season']): int(x[b'number_of_episodes']) for x in results}

    def get_all_episodes(self, season=None, has_location=False):
        """Retrieve all episodes for this show given the specified filter.

        :param season:
        :type season: int
        :param has_location:
        :type has_location: bool
        :return:
        :rtype: list of Episode
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
        :rtype: Episode
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
                logger.debug(u'{id}: Season and episode lookup for {show} using absolute number {absolute}',
                             id=self.indexerid, absolute=absolute_number, show=self.name)
            elif air_date:
                sql = b'SELECT season, episode FROM tv_episodes WHERE showid = ? AND airdate = ?'
                sql_args = [self.indexerid, air_date.toordinal()]
                logger.debug(u'{id}: Season and episode lookup for {show} using air date {air_date}',
                             id=self.indexerid, air_date=air_date, show=self.name)

            sql_results = main_db_con.select(sql, sql_args) if sql else []
            if len(sql_results) == 1:
                episode = int(sql_results[0][b'episode'])
                season = int(sql_results[0][b'season'])
                logger.debug(u'{id}: Found season and episode which is {show} {ep}',
                             id=self.indexerid, show=self.name, ep=episode_num(season, episode))
            elif len(sql_results) > 1:
                logger.error(u'{id}: Multiple entries found in show: {show} ', id=self.indexerid, show=self.name)

                return None
            else:
                logger.debug(u'{id}: No entries found in show: {show}', id=self.indexerid, show=self.name)
                return None

        if season not in self.episodes:
            self.episodes[season] = {}

        if episode in self.episodes[season] and self.episodes[season][episode] is not None:
            return self.episodes[season][episode]
        elif no_create:
            return None

        if filepath:
            ep = Episode(self, season, episode, filepath)
        else:
            ep = Episode(self, season, episode)

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
        # if show is 'paused' do not update_date
        if self.paused:
            logger.info(u'{id}: Show {show} is paused. Update skipped',
                        id=self.indexerid, show=self.name)
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

    def __write_show_nfo(self, metadata_provider):

        result = False
        result = metadata_provider.create_show_metadata(self) or result

        return result

    def write_metadata(self, show_only=False):
        """Write show metadata files.

        :param show_only:
        :type show_only: bool
        """
        if not self.is_location_valid():
            logger.warning(u"{id}: Show dir doesn't exist, skipping NFO generation", id=self.indexerid)
            return

        for metadata_provider in app.metadata_provider_dict.values():
            self.__get_images(metadata_provider)
            self.__write_show_nfo(metadata_provider)

        if not show_only:
            self.__write_episode_nfos()

    def __write_episode_nfos(self):

        logger.debug(u"{id}: Writing NFOs for all episodes", id=self.indexerid)

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
            logger.debug(u'{id}: Retrieving/creating episode {ep}',
                         id=self.indexerid, ep=episode_num(ep_result[b'season'], ep_result[b'episode']))
            cur_ep = self.get_episode(ep_result[b'season'], ep_result[b'episode'])
            if not cur_ep:
                continue

            cur_ep.create_meta_files()

    def update_metadata(self):
        """Update show metadata files."""
        if not self.is_location_valid():
            logger.warning(u"{id}: Show dir doesn't exist, skipping NFO generation", id=self.indexerid)
            return

        self.__update_show_nfo()

    def __update_show_nfo(self):

        result = False

        logger.info(u"{id}: Updating NFOs for show with new indexer info", id=self.indexerid)
        # You may only call .values() on metadata_provider_dict! As on values() call the indexer_api attribute
        # is reset. This will prevent errors, when using multiple indexers and caching.
        for cur_provider in app.metadata_provider_dict.values():
            result = cur_provider.update_show_indexer_metadata(self) or result

        return result

    def load_episodes_from_dir(self):
        """Find all media files in the show folder and create episodes for as many as possible."""
        if not self.is_location_valid():
            logger.warning(u"{id}: Show dir doesn't exist, not loading episodes from disk", id=self.indexerid)
            return

        logger.debug(u"{id}: Loading all episodes from the show directory: {location}",
                     id=self.indexerid, location=self.location)

        # get file list
        media_files = helpers.list_media_files(self.location)
        logger.debug(u'{id}: Found files: {media_files}', id=self.indexerid, media_files=media_files)

        # create TVEpisodes from each media file (if possible)
        sql_l = []
        for media_file in media_files:
            cur_episode = None

            logger.debug(u"{id}: Creating episode from: {location}", id=self.indexerid, location=media_file)
            try:
                cur_episode = self.make_ep_from_file(os.path.join(self.location, media_file))
            except (ShowNotFoundException, EpisodeNotFoundException) as e:
                logger.warning(u"{id}: Episode {location} returned an exception {error_msg}",
                               id=self.indexerid, location=media_file, error_msg=ex(e))
                continue
            except EpisodeDeletedException:
                logger.debug(u'{id}: The episode deleted itself when I tried making an object for it',
                             id=self.indexerid)

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
                logger.debug(u'{id}: Filename {file_name} gave release group of {rg}, seems valid',
                             id=self.indexerid, file_name=ep_file_name, rg=parse_result.release_group)
                cur_episode.release_name = ep_file_name

            # store the reference in the show
            if cur_episode is not None:
                if self.subtitles:
                    try:
                        cur_episode.refresh_subtitles()
                    except Exception:
                        logger.info(u'{id}: Could not refresh subtitles', id=self.indexerid)
                        logger.debug(traceback.format_exc())

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
                logger.debug(u'{id}: Loading all episodes of season(s) {seasons} from the DB',
                             id=self.indexerid, seasons=seasons)
            else:
                sql_results = main_db_con.select(sql, [self.indexerid])
                logger.debug(u'{id}: Loading all episodes of all seasons from the DB', id=self.indexerid)
        except Exception as error:
            logger.error(u'{id}: Could not load episodes from the DB. Error: {error_msg}',
                         id=self.indexerid, error_msg=error)
            return scanned_eps

        cached_show = self.indexer_api[self.indexerid]

        cached_seasons = {}
        cur_show_name = ''
        cur_show_id = ''

        for cur_result in sql_results:

            cur_season = int(cur_result[b'season'])
            cur_episode = int(cur_result[b'episode'])
            cur_show_id = int(cur_result[b'showid'])
            cur_show_name = text_type(cur_result[b'show_name'])

            delete_ep = False

            logger.debug(u'{id}: Loading {show} {ep} from the DB',
                         id=cur_show_id, show=cur_show_name, ep=episode_num(cur_season, cur_episode))

            if cur_season not in cached_seasons:
                try:
                    cached_seasons[cur_season] = cached_show[cur_season]
                except IndexerSeasonNotFound as error:
                    logger.debug(u'{id}: {error_msg} (unaired/deleted) in the indexer {indexer} for {show}. '
                                 u'Removing existing records from database',
                                 id=cur_show_id, error_msg=error.message, indexer=indexerApi(self.indexer).name,
                                 show=cur_show_name)
                    delete_ep = True

            if cur_season not in scanned_eps:
                scanned_eps[cur_season] = {}

            if cur_episode == 0:
                logger.warning(u'{id}: Tried loading {show} {ep} from the DB. With an episode id set to 0.'
                               u' We dont support that. Skipping to next episode.',
                               id=cur_show_id, show=cur_show_name, ep=episode_num(cur_season, cur_episode))
                continue

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
                logger.debug(u'{id}: Tried loading {show} {ep} from the DB that should have been deleted, '
                             u'skipping it', id=cur_show_id, show=cur_show_name,
                             ep=episode_num(cur_season, cur_episode))
                continue

        logger.debug(u'{id}: Finished loading all episodes for {show} from the DB', show=cur_show_name, id=cur_show_id)

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
        try:
            self.indexer_api = tvapi
            indexed_show = self.indexer_api[self.indexerid]
        except IndexerException as e:
            logger.warning(
                u'{id}: {indexer} error, unable to update episodes.'
                u' Message: {ex}',
                id=self.indexerid,
                indexer=indexerApi(self.indexer).name,
                ex=e
            )
            raise

        logger.debug(
            u'{id}: Loading all episodes from {indexer}{season_update}',
            id=self.indexerid,
            indexer=indexerApi(self.indexer).name,
            season_update=u' on seasons {seasons}'.format(seasons=seasons) if seasons else u''
        )

        scanned_eps = {}

        sql_l = []
        for season in indexed_show:
            # Only index episodes for seasons that are currently being updated.
            if seasons and season not in seasons:
                continue

            scanned_eps[season] = {}
            for episode in indexed_show[season]:
                # need some examples of wtf episode 0 means to decide if we want it or not
                if episode == 0:
                    continue
                try:
                    ep = self.get_episode(season, episode)
                    if not ep:
                        raise EpisodeNotFoundException
                except EpisodeNotFoundException:
                    logger.info(u'{id}: {indexer} object for {ep} is incomplete, skipping this episode',
                                id=self.indexerid, indexer=indexerApi(self.indexer).name,
                                ep=episode_num(season, episode))
                    continue
                else:
                    try:
                        ep.load_from_indexer(tvapi=self.indexer_api)
                    except EpisodeDeletedException:
                        logger.debug(u'{id}: The episode {ep} was deleted, skipping the rest of the load',
                                     id=self.indexerid, ep=episode_num(season, episode))
                        continue

                with ep.lock:
                    sql_l.append(ep.get_sql())

                scanned_eps[season][episode] = True

        if sql_l:
            main_db_con = db.DBConnection()
            main_db_con.mass_action(sql_l)

        # Done updating save last update date
        self.last_update_indexer = datetime.date.today().toordinal()
        logger.debug(u'{id}: Saving indexer changes to database', id=self.indexerid)
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
            try:
                if result[b'indexer'] == self.indexer:
                    self.externals[mappings[result[b'mindexer']]] = result[b'mindexer_id']
                else:
                    self.externals[mappings[result[b'indexer']]] = result[b'indexer_id']
            except KeyError as e:
                logger.error(u'Indexer not supported in current mappings: {id}', id=e.message)

        return self.externals

    def _save_externals_to_db(self):
        """Save the indexers external id's to the db."""
        sql_l = []

        for external in self.externals:
            if external in reverse_mappings and self.externals[external]:
                sql_l.append([b'INSERT OR IGNORE '
                              b'INTO indexer_mapping (indexer_id, indexer, mindexer_id, mindexer) '
                              b'VALUES (?,?,?,?)',
                              [self.indexerid,
                               self.indexer,
                               self.externals[external],
                               int(reverse_mappings[external])
                               ]])

        if sql_l:
            main_db_con = db.DBConnection()
            main_db_con.mass_action(sql_l)

    def __get_images(self, metadata_provider):
        fanart_result = poster_result = banner_result = False
        season_posters_result = season_banners_result = season_all_poster_result = season_all_banner_result = False

        fanart_result = metadata_provider.create_fanart(self) or fanart_result
        poster_result = metadata_provider.create_poster(self) or poster_result
        banner_result = metadata_provider.create_banner(self) or banner_result

        season_posters_result = metadata_provider.create_season_posters(self) or season_posters_result
        season_banners_result = metadata_provider.create_season_banners(self) or season_banners_result
        season_all_poster_result = metadata_provider.create_season_all_poster(self) or season_all_poster_result
        season_all_banner_result = metadata_provider.create_season_all_banner(self) or season_all_banner_result

        return (fanart_result or poster_result or banner_result or season_posters_result or
                season_banners_result or season_all_poster_result or season_all_banner_result)

    @staticmethod
    def should_refresh_file(cur_status, same_file, check_quality_again, anime, filepath):
        """Check if we should use the dectect file to change status.

        This method only refreshes when there is a existing file in show folder
        For SNATCHED status without existing file (first snatch), it won't use this method
        For SNATCHED BEST status, there is a existing file in `location` in DB, so it MUST stop in `same_file` rule
        so user doesn't lose this SNATCHED_BEST status
        """
        if same_file:
            return False, 'New file is the same as current file'
        if not helpers.is_media_file(filepath):
            return False, 'New file is not a valid media file'

        new_quality = Quality.name_quality(filepath, anime)

        if check_quality_again:
            if new_quality != Quality.UNKNOWN:
                return True, 'New file has different name from the database but has valid quality.'
            else:
                return False, 'New file has UNKNOWN quality'

        #  Reach here to check for status/quality changes as long as it's a new/different file
        if cur_status in Quality.DOWNLOADED + Quality.ARCHIVED + [IGNORED]:
            return False, 'Existing status is {0} and its not allowed'.format(statusStrings[cur_status])

        if cur_status in [FAILED, SKIPPED, WANTED, UNKNOWN, UNAIRED]:
            return True, 'Existing status is {0} and its allowed'.format(statusStrings[cur_status])

        old_status, old_quality = Quality.split_composite_status(cur_status)

        if old_status == SNATCHED or old_status == SNATCHED_BEST:
            #  Only use new file if is same|higher quality
            if old_quality <= new_quality:
                return True, 'Existing status is {0} and new quality is same|higher'.format(statusStrings[cur_status])
            else:
                return False, 'Existing status is {0} and new quality is lower'.format(statusStrings[cur_status])

        if old_status == SNATCHED_PROPER:
            #  Only use new file if is a higher quality (not necessary a PROPER)
            if old_quality < new_quality:
                return True, 'Existing status is {0} and new quality is higher'.format(statusStrings[cur_status])
            else:
                return False, 'Existing status is {0} and new quality is same|lower'.format(statusStrings[cur_status])

        return False, 'There is no rule set to allow this file'

    def make_ep_from_file(self, filepath):
        """Make a TVEpisode object from a media file.

        :param filepath:
        :type filepath: str
        :return:
        :rtype: Episode
        """
        if not os.path.isfile(filepath):
            logger.info(u"{indexer_id}: That isn't even a real file dude... {filepath}",
                        indexer_id=self.indexerid, filepath=filepath)
            return None

        logger.debug(u'{indexer_id}: Creating episode object from {filepath}',
                     indexer_id=self.indexerid, filepath=filepath)

        try:
            parse_result = NameParser(show=self, try_indexers=True, parse_method=(
                'normal', 'anime')[self.is_anime]).parse(filepath)
        except (InvalidNameException, InvalidShowException) as error:
            logger.debug(u'{indexerid}: {error}', indexer_id=self.indexerid, error=error)
            return None

        episodes = [ep for ep in parse_result.episode_numbers if ep is not None]
        if not episodes:
            logger.debug(u'{indexerid}: parse_result: {parse_result}',
                         indexerid=self.indexerid, parse_result=parse_result)
            logger.debug(u'{indexerid}: No episode number found in {filepath}, ignoring it',
                         indexerid=self.indexerid, filepath=filepath)
            return None

        # for now lets assume that any episode in the show dir belongs to that show
        season = parse_result.season_number if parse_result.season_number is not None else 1
        root_ep = None

        sql_l = []
        for current_ep in episodes:
            logger.debug(u'{id}: {filepath} parsed to {series_name} {ep_num}',
                         id=self.indexerid, filepath=filepath, series_name=self.name,
                         ep_num=episode_num(season, current_ep))

            check_quality_again = False
            same_file = False

            cur_ep = self.get_episode(season, current_ep)
            if not cur_ep:
                try:
                    cur_ep = self.get_episode(season, current_ep, filepath)
                    if not cur_ep:
                        raise EpisodeNotFoundException
                except EpisodeNotFoundException:
                    logger.log(u'{indexerid}: Unable to figure out what this file is, skipping {filepath}',
                               indexerid=self.indexerid, filepath=filepath)
                    continue

            else:
                # if there is a new file associated with this ep then re-check the quality
                if not cur_ep.location or os.path.normpath(cur_ep.location) != os.path.normpath(filepath):
                    logger.debug(
                        u'{indexerid}: The old episode had a different file associated with it, '
                        u're-checking the quality using the new filename {filepath}',
                        indexerid=self.indexerid, filepath=filepath
                    )
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
            should_refresh, should_refresh_reason = self.should_refresh_file(cur_ep.status, same_file,
                                                                             check_quality_again, self.is_anime,
                                                                             filepath)
            if should_refresh:
                with cur_ep.lock:
                    old_ep_status = cur_ep.status
                    new_quality = Quality.name_quality(filepath, self.is_anime)
                    cur_ep.status = Quality.composite_status(DOWNLOADED, new_quality)
                    logger.debug(u"{id}: Setting the status from '{status_old}' to '{status_cur}' "
                                 u"based on file: {filepath}. Reason: {reason}",
                                 id=self.indexerid, status_old=statusStrings[old_ep_status],
                                 status_cur=statusStrings[cur_ep.status],
                                 filepath=filepath, reason=should_refresh_reason)
            else:
                logger.debug(u"{id}: Not changing current status '{status_string}' based on file: {filepath}. "
                             u'Reason: {should_refresh}', id=self.indexerid, status_string=statusStrings[cur_ep.status],
                             filepath=filepath, should_refresh=should_refresh_reason)
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

        logger.debug(u'{id}: Loading show info from database', id=self.indexerid)

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(b'SELECT * FROM tv_shows WHERE indexer_id = ?', [self.indexerid])

        if len(sql_results) > 1:
            raise MultipleShowsInDatabaseException()
        elif not sql_results:
            logger.info(u'{indexerid}: Unable to find the show in the database', indexerid=self.indexerid)
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

            self.airs = sql_results[0][b'airs']
            if self.airs is None or not network_timezones.test_timeformat(self.airs):
                self.airs = ''

            self.start_year = int(sql_results[0][b'startyear'] or 0)
            self.air_by_date = int(sql_results[0][b'air_by_date'] or 0)
            self.anime = int(sql_results[0][b'anime'] or 0)
            self.sports = int(sql_results[0][b'sports'] or 0)
            self.scene = int(sql_results[0][b'scene'] or 0)
            self.subtitles = int(sql_results[0][b'subtitles'] or 0)
            self.dvd_order = int(sql_results[0][b'dvdorder'] or 0)
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

            if not self.imdb_id:
                self.imdb_id = sql_results[0][b'imdb_id']

            if self.is_anime:
                self.release_groups = BlackAndWhiteList(self.indexerid)

            self.plot = sql_results[0][b'plot']

            # Load external id's from indexer_mappings table.
            self._load_externals_from_db()

        # Get IMDb_info from database
        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(
            b'SELECT * '
            b'FROM imdb_info '
            b'WHERE indexer_id = ?',
            [self.indexerid]
        )

        if not sql_results:
            logger.info(u'{id}: Unable to find IMDb info'
                        u' in the database: {show}', id=self.indexerid, show=self.name)
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

        logger.debug(u'{id}: Loading show info from {indexer_name}',
                     id=self.indexerid, indexer_name=indexerApi(self.indexer).name)

        self.indexer_api = tvapi
        indexed_show = self.indexer_api[self.indexerid]

        try:
            self.name = indexed_show['seriesname'].strip()
        except AttributeError:
            raise IndexerAttributeNotFound(
                "Found {id}, but attribute 'seriesname' was empty.".format(id=self.indexerid))

        self.classification = getattr(indexed_show, 'classification', 'Scripted')
        self.genre = getattr(indexed_show, 'genre', '')
        self.network = getattr(indexed_show, 'network', '')
        self.runtime = int(getattr(indexed_show, 'runtime', 0))

        # set the externals, using the result from the indexer.
        self.externals = {k: v for k, v in getattr(indexed_show, 'externals', {}).items() if v}

        # Add myself (indexer) as an external
        self.externals[mappings[self.indexer]] = self.indexerid

        # Enrich the externals, using reverse lookup.
        self.externals.update(get_externals(self))

        self.imdb_id = self.externals.get('imdb_id') or getattr(indexed_show, 'imdb_id', '')

        if getattr(indexed_show, 'airs_dayofweek', '') and getattr(indexed_show, 'airs_time', ''):
            self.airs = '{airs_day_of_week} {airs_time}'.format(airs_day_of_week=indexed_show['airs_dayofweek'],
                                                                airs_time=indexed_show['airs_time'])

        if getattr(indexed_show, 'firstaired', ''):
            self.start_year = int(str(indexed_show['firstaired']).split('-')[0])

        self.status = getattr(indexed_show, 'status', 'Unknown')

        self.plot = getattr(indexed_show, 'overview', '') or self.get_plot()

        self._save_externals_to_db()

    def load_imdb_info(self):
        """Load all required show information from IMDb with ImdbPie."""
        imdb_api = imdbpie.Imdb()

        if not self.imdb_id:
            self.imdb_id = helpers.title_to_imdb(self.name, self.start_year, imdb_api)

            if not self.imdb_id:
                logger.info(u"{indexerid}: Not loading show info from IMDb, "
                            u"because we don't know its ID.", indexerid=self.indexerid)
                return

        # Make sure we only use the first ID
        self.imdb_id = self.imdb_id.split(',')[0]

        logger.debug(u'{id}: Loading show info from IMDb with ID: {imdb_id}',
                     id=self.indexerid, imdb_id=self.imdb_id)

        imdb_obj = imdb_api.get_title_by_id(self.imdb_id)

        # If the show has no year, IMDb returned something we don't want
        if not imdb_obj.year:
            logger.debug(u'{id}: IMDb returned invalid info for {imdb_id}, skipping update.',
                         id=self.indexerid, imdb_id=self.imdbid)
            return

        self.imdb_info = {
            'imdb_id': imdb_obj.imdb_id,
            'title': imdb_obj.title,
            'year': imdb_obj.year,
            'akas': '',
            'genres': '|'.join(imdb_obj.genres or ''),
            'countries': '',
            'country_codes': '',
            'rating': str(imdb_obj.rating) or '',
            'votes': imdb_obj.votes or '',
            'runtimes': int(imdb_obj.runtime / 60) if imdb_obj.runtime else '',  # Time is returned in seconds
            'certificates': imdb_obj.certification or '',
            'plot': imdb_obj.plots[0] if imdb_obj.plots else imdb_obj.plot_outline or '',
            'last_update': datetime.date.today().toordinal(),
        }

        self.externals['imdb_id'] = self.imdb_id

        logger.debug(u'{id}: Obtained info from IMDb: {imdb_info}',
                     id=self.indexerid, imdb_info=self.imdb_info)

    def next_episode(self):
        """Return the next episode air date.

        :return:
        :rtype: datetime.date
        """
        logger.debug(u'{id}: Finding the episode which airs next', id=self.indexerid)

        cur_date = datetime.date.today().toordinal()
        if not self.next_aired or self.next_aired and cur_date > self.next_aired:
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
                logger.debug(u'{id}: No episode found... need to implement a show status', id=self.indexerid)
                self.next_aired = u''
            else:
                logger.debug(u'{id}: Found episode {ep}',
                             id=self.indexerid, ep=episode_num(sql_results[0][b'season'], sql_results[0][b'episode']))
                self.next_aired = sql_results[0][b'airdate']

        return self.next_aired

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

        action = ('delete', 'trash')[app.TRASH_REMOVE_SHOW]

        # remove self from show list
        app.showList = [x for x in app.showList if int(x.indexerid) != self.indexerid]

        # clear the cache
        image_cache_dir = os.path.join(app.CACHE_DIR, 'images')
        for cache_file in glob.glob(os.path.join(image_cache_dir, str(self.indexerid) + '.*')):
            logger.info(u'{id}: Attempt to {action} cache file {cache_file}',
                        id=self.indexerid, action=action, cache_file=cache_file)
            try:
                if app.TRASH_REMOVE_SHOW:
                    send2trash(cache_file)
                else:
                    os.remove(cache_file)

            except OSError as e:
                logger.warning(u'{id}: Unable to {action} {cache_file}: {error_msg}',
                               id=self.indexerid, action=action, cache_file=cache_file, error_msg=ex(e))

        # remove entire show folder
        if full:
            try:
                logger.info(u'{id}: Attempt to {action} show folder {location}',
                            id=self.indexerid, action=action, location=self.location)
                # check first the read-only attribute
                file_attribute = os.stat(self.location)[0]
                if not file_attribute & stat.S_IWRITE:
                    # File is read-only, so make it writeable
                    logger.debug(u'{id}: Attempting to make writeable the read only folder {location}',
                                 id=self.indexerid, location=self.location)
                    try:
                        os.chmod(self.location, stat.S_IWRITE)
                    except OSError:
                        logger.warning(u'{id}: Unable to change permissions of {location}',
                                       id=self.indexerid, location=self.location)

                if app.TRASH_REMOVE_SHOW:
                    send2trash(self.location)
                else:
                    shutil.rmtree(self.location)

                logger.info(u'{id}: {action} show folder {location}',
                            id=self.indexerid, action=action, location=self.raw_location)

            except ShowDirectoryNotFoundException:
                logger.warning(u'{id}: Show folder {location} does not exist. No need to {action}',
                               id=self.indexerid, location=self.raw_location, action=action)
            except OSError as e:
                logger.warning(u'{id}: Unable to {action} {location}. Error: {error_msg}',
                               id=self.indexerid, action=action, location=self.raw_location, error_msg=ex(e))

        if app.USE_TRAKT and app.TRAKT_SYNC_WATCHLIST:
            logger.debug(u'{id}: Removing show {show} from Trakt watchlist',
                         id=self.indexerid, show=self.name)
            notifiers.trakt_notifier.update_watchlist(self, update='remove')

    def populate_cache(self):
        """Populate image caching."""
        cache_inst = image_cache.ImageCache()

        logger.debug(u'{id}: Checking & filling cache for show {show}',
                     id=self.indexerid, show=self.name)
        cache_inst.fill_cache(self)

    def refresh_dir(self):
        """Refresh show using its location.

        :return:
        :rtype: bool
        """
        # make sure the show dir is where we think it is unless dirs are created on the fly
        if not app.CREATE_MISSING_SHOW_DIRS and not self.is_location_valid():
            return False

        # Let's get some fresh indexer info, as we might need it later on.
        # self.create_indexer()

        # load from dir
        self.load_episodes_from_dir()

        # run through all locations from DB, check that they exist
        logger.debug(u'{id}: Loading all episodes from {show} with a location from the database',
                     id=self.indexerid, show=self.name)

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
                logger.debug(u'{id:} Episode {show} {ep} was deleted while we were refreshing it, '
                             u'moving on to the next one',
                             id=self.indexerid, show=self.name, ep=episode_num(season, episode))
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

                            logger.debug(u"{id}: Location for {show} {ep} doesn't exist and status is {old_status}, "
                                         u"removing it and changing our status to '{status}'",
                                         id=self.indexerid, show=self.name, ep=episode_num(season, episode),
                                         old_status=statusStrings[cur_ep.status].upper(),
                                         status=statusStrings[new_status].upper())

                            cur_ep.status = new_status
                            cur_ep.subtitles = ''
                            cur_ep.subtitles_searchcount = 0
                            cur_ep.subtitles_lastsearch = ''
                        cur_ep.location = ''
                        cur_ep.hasnfo = False
                        cur_ep.hastbn = False
                        cur_ep.release_name = ''

                        sql_l.append(cur_ep.get_sql())

                    logger.info(u'{id}: Looking for hanging associated files for: {show} {ep} in: {location}',
                                id=self.indexerid, show=self.name, ep=episode_num(season, episode), location=cur_loc)
                    related_files = post_processor.PostProcessor(cur_loc).list_associated_files(
                        cur_loc, base_name_only=False, subfolders=True)

                    if related_files:
                        logger.warning(u'{id}: Found hanging associated files for {show} {ep}, deleting: {files}',
                                       id=self.indexerid, show=self.name, ep=episode_num(season, episode),
                                       files=related_files)
                        for related_file in related_files:
                            try:
                                os.remove(related_file)
                            except Exception as e:
                                logger.warning(
                                    u'{id}: Could not delete associated file: {related_file}. Error: {error_msg}',
                                    id=self.indexerid, related_file=related_file, error_msg=e
                                )

        # Clean up any empty season folders after deletion of associated files
        helpers.delete_empty_folders(self.location)

        if sql_l:
            main_db_con = db.DBConnection()
            main_db_con.mass_action(sql_l)

    def download_subtitles(self):
        """Download subtitles."""
        if not self.is_location_valid():
            logger.warning(u"{id}: Show {show} location doesn't exist, can't download subtitles",
                           id=self.indexerid, show=self.name)
            return

        logger.debug(u'{id}: Downloading subtitles for {show}', id=self.indexerid, show=self.name)

        try:
            episodes = self.get_all_episodes(has_location=True)
            if not episodes:
                logger.debug(u'{id}: No episodes to download subtitles for {show}',
                             id=self.indexerid, show=self.name)
                return

            for episode in episodes:
                episode.download_subtitles()

        # TODO: Change into a non catch all exception.
        except Exception:
            logger.warning(u'{id}: Error occurred when downloading subtitles for show {show}',
                           id=self.indexerid, show=self.name)
            logger.error(traceback.format_exc())

    def save_to_db(self):
        """Save to database."""
        if not self.dirty:
            return

        logger.debug(u'{id}: Saving to database: {show}', id=self.indexerid, show=self.name)

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
                          'dvdorder': self.dvd_order,
                          'startyear': self.start_year,
                          'lang': self.lang,
                          'imdb_id': self.imdb_id,
                          'last_update_indexer': self.last_update_indexer,
                          'rls_ignore_words': self.rls_ignore_words,
                          'rls_require_words': self.rls_require_words,
                          'default_ep_status': self.default_ep_status,
                          'plot': self.plot}

        main_db_con = db.DBConnection()
        main_db_con.upsert('tv_shows', new_value_dict, control_value_dict)

        helpers.update_anime_support()

        if self.imdb_id and self.imdb_info.get('year'):
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
        to_return += 'start_year: ' + str(self.start_year) + '\n'
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
        to_return += u'start_year: {0}\n'.format(self.start_year)
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
        indexer_name = self.indexer_slug
        bw_list = self.release_groups or BlackAndWhiteList(self.indexerid)
        result = OrderedDict([
            ('id', OrderedDict([
                (indexer_name, self.indexerid),
                ('imdb', str(self.imdb_id))
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
                ('start', self.imdb_info.get('year') or self.start_year),
            ])),
            ('nextAirDate', self.get_next_airdate()),
            ('runtime', self.imdb_info.get('runtimes') or self.runtime),
            ('genres', self.get_genres()),
            ('rating', OrderedDict([])),
            ('classification', self.imdb_info.get('certificates')),
            ('cache', OrderedDict([])),
            ('countries', self.get_countries()),
            ('plot', self.get_plot()),
            ('config', OrderedDict([
                ('location', self.raw_location),
                ('qualities', OrderedDict([
                    ('allowed', self.get_allowed_qualities()),
                    ('preferred', self.get_preferred_qualities()),
                ])),
                ('paused', bool(self.paused)),
                ('airByDate', bool(self.air_by_date)),
                ('subtitlesEnabled', bool(self.subtitles)),
                ('dvdOrder', bool(self.dvd_order)),
                ('flattenFolders', bool(self.flatten_folders)),
                ('scene', self.is_scene),
                ('defaultEpisodeStatus', statusStrings[self.default_ep_status]),
                ('aliases', self.exceptions or get_scene_exceptions(self.indexerid, self.indexer)),
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
            sbdatetime.convert_to_setting(network_timezones.parse_date_time(self.next_aired, self.airs, self.network))
            if try_int(self.next_aired, 1) > MILLIS_YEAR_1900 else None
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

    def get_plot(self):
        """Return show plot."""
        return self.imdb_info.get('plot', '')

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
        logger.debug(u'{id}: Allowed, Preferred = [ {allowed} ] [ {preferred} ] Found = [ {found} ]',
                     id=self.indexerid, allowed=self.__qualities_to_string(allowed_qualities),
                     preferred=self.__qualities_to_string(preferred_qualities),
                     found=self.__qualities_to_string([quality]))

        if not Quality.wanted_quality(quality, allowed_qualities, preferred_qualities):
            logger.debug(u"{id}: Ignoring found result for '{show}' {ep} with unwanted quality '{quality}'",
                         id=self.indexerid, show=self.name, ep=episode_num(season, episode),
                         quality=Quality.qualityStrings[quality])
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
            logger.debug(u'{id}: Unable to find a matching episode in database. '
                         u"Ignoring found result for '{show}' {ep} with quality '{quality}'",
                         id=self.indexerid, show=self.name, ep=episode_num(season, episode),
                         quality=Quality.qualityStrings[quality])
            return False

        ep_status = int(sql_results[0][b'status'])
        ep_status_text = statusStrings[ep_status].upper()
        manually_searched = sql_results[0][b'manually_searched']
        _, cur_quality = Quality.split_composite_status(ep_status)

        # if it's one of these then we want it as long as it's in our allowed initial qualities
        if ep_status == WANTED:
            logger.debug(u"{id}: '{show}' {ep} status is 'WANTED'. Accepting result with quality '{new_quality}'",
                         id=self.indexerid, status=ep_status_text, show=self.name, ep=episode_num(season, episode),
                         new_quality=Quality.qualityStrings[quality])
            return True

        should_replace, reason = Quality.should_replace(ep_status, cur_quality, quality, allowed_qualities,
                                                        preferred_qualities, download_current_quality,
                                                        forced_search, manually_searched)
        logger.debug(u"{id}: '{show}' {ep} status is: '{status}'. {action} result with quality '{new_quality}'. "
                     u"Reason: {reason}", id=self.indexerid, show=self.name, ep=episode_num(season, episode),
                     status=ep_status_text, action='Accepting' if should_replace else 'Ignoring',
                     new_quality=Quality.qualityStrings[quality], reason=reason)
        return should_replace

    def get_overview(self, ep_status, backlog_mode=False, manually_searched=False):
        """Get the Overview status from the Episode status.

        :param ep_status: an Episode status
        :type ep_status: int
        :param backlog_mode: if we should return overview for backlogOverview
        :type backlog_mode: boolean
        :param manually_searched: if episode was manually searched
        :type manually_searched: boolean
        :return: an Overview status
        :rtype: int
        """
        ep_status = try_int(ep_status) or UNKNOWN

        if backlog_mode:
            if ep_status == WANTED:
                return Overview.WANTED
            elif Quality.should_search(ep_status, self, manually_searched)[0]:
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
            if Quality.should_search(ep_status, self, manually_searched)[0]:
                return Overview.QUAL
            else:
                return Overview.GOOD
        else:
            logger.error(u'Could not parse episode status into a valid overview status: {status}', status=ep_status)

    def get_backlogged_episodes(self, allowed_qualities, preferred_qualities, include_wanted=False):
        """Check how many episodes will be backlogged when changing qualities."""
        BackloggedEpisodes = namedtuple('backlogged_episodes', ['new_backlogged', 'existing_backlogged'])
        new_backlogged = 0
        existing_backlogged = 0
        if allowed_qualities + preferred_qualities:
            # We need to change show qualities without save it
            show_obj = copy.copy(self)

            show_obj.quality = Quality.combine_qualities(allowed_qualities, preferred_qualities)
            ep_list = self.get_all_episodes()
            for ep_obj in ep_list:
                if not include_wanted and ep_obj.status == WANTED:
                    continue
                if Quality.should_search(ep_obj.status, show_obj, ep_obj.manually_searched)[0]:
                    new_backlogged += 1
                if Quality.should_search(ep_obj.status, self, ep_obj.manually_searched)[0]:
                    existing_backlogged += 1
        else:
            new_backlogged = existing_backlogged = -1
        return BackloggedEpisodes(new_backlogged, existing_backlogged)

    def set_all_episodes_archived(self, final_status_only=False):
        """Set all episodes with final `downloaded` status to `archived`.

        :param final_status_only: archive only episode with final status
        :type final_status_only: boolean
        :return: True if we archived at least one episode
        :rtype: boolean
        """
        ep_list = self.get_all_episodes()
        sql_list = []
        for ep_obj in ep_list:
            with ep_obj.lock:
                if ep_obj.status in Quality.DOWNLOADED:
                    if final_status_only and Quality.should_search(ep_obj.status, self,
                                                                   ep_obj.manually_searched)[0]:
                        continue
                    _, old_quality = Quality.split_composite_status(ep_obj.status)
                    ep_obj.status = Quality.composite_status(ARCHIVED, old_quality)
                    sql_list.append(ep_obj.get_sql())
        if sql_list:
            main_db_con = db.DBConnection()
            main_db_con.mass_action(sql_list)
            logger.debug(u'Change all DOWNLOADED episodes to ARCHIVED '
                         u'for show ID: {show}', show=self.name)
            return True
        else:
            logger.debug(u'No DOWNLOADED episodes for show ID: {show}', show=self.name)
            return False
