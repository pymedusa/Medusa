# coding=utf-8
"""Series and Episode classes."""

import datetime
import glob
import os.path
import re
import shutil
import stat
import traceback
import warnings
from collections import (
    OrderedDict,
    namedtuple,
)
from itertools import groupby

from imdb import imdb
from imdb._exceptions import (
    IMDbDataAccessError,
    IMDbParserError,
)

from medusa import (
    app,
    db,
    helpers,
    image_cache,
    logger,
    network_timezones,
    notifiers,
    post_processor,
    subtitles,
)
from medusa.black_and_white_list import BlackAndWhiteList
from medusa.common import (
    ARCHIVED,
    DOWNLOADED,
    IGNORED,
    Overview,
    Quality,
    SKIPPED,
    SNATCHED,
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
from medusa.helper.externals import get_externals
from medusa.indexers.indexer_api import indexerApi
from medusa.indexers.indexer_config import (
    INDEXER_TVRAGE,
    indexerConfig,
    mappings,
    reverse_mappings,
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
        super(Series, self).__init__(indexer, indexerid, {'episodes', 'nextaired', 'release_groups'})
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
            logger.log(
                u'{id}: Using language from show settings: {lang}'.format
                (id=self.indexerid, lang=self.lang), logger.DEBUG
            )

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
        # TODO: Fix for multi-indexer.
        # https://github.com/pymedusa/Medusa/issues/2073
        return self.indexerid in app.RECENTLY_DELETED

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

    @location.setter
    def location(self, value):
        logger.log(
            u'{indexer} {id}: Setting location: {location}'.format(
                indexer=self.indexer_api.name,
                id=self.indexerid,
                location=value
            ),
            logger.DEBUG
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

        return {int(x['season']): int(x['number_of_episodes']) for x in results}

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
            logger.log(u"{id}: Show dir doesn't exist, skipping NFO generation".format(id=self.indexerid),
                       logger.WARNING)
            return

        for metadata_provider in app.metadata_provider_dict.values():
            self.__get_images(metadata_provider)
            self.__write_show_nfo(metadata_provider)

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
        # You may only call .values() on metadata_provider_dict! As on values() call the indexer_api attribute
        # is reset. This will prevent errors, when using multiple indexers and caching.
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

            if cur_episode == 0:
                logger.log(u'{id}: Tried loading {show} {ep} from the DB. With an episode id set to 0.'
                           u' We dont support that. Skipping to next episode.'.
                           format(id=cur_show_id, show=cur_show_name,
                                  ep=episode_num(cur_season, cur_episode)), logger.WARNING)
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
        try:
            self.indexer_api = tvapi
            indexed_show = self.indexer_api[self.indexerid]
        except IndexerException as e:
            logger.log(
                u'{id}: {indexer} error, unable to update episodes.'
                u' Message: {ex}'.format(
                    id=self.indexerid,
                    indexer=indexerApi(self.indexer).name,
                    ex=e,
                ),
                logger.WARNING
            )
            raise

        logger.log(
            u'{id}: Loading all episodes from {indexer}{season_update}'.format(
                id=self.indexerid,
                indexer=indexerApi(self.indexer).name,
                season_update=u' on seasons {seasons}'.format(
                    seasons=seasons
                ) if seasons else u''
            ),
            logger.DEBUG
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
                    logger.log(u'{id}: {indexer} object for {ep} is incomplete, skipping this episode'.format
                               (id=self.indexerid, indexer=indexerApi(self.indexer).name,
                                ep=episode_num(season, episode)))
                    continue
                else:
                    try:
                        ep.load_from_indexer(tvapi=self.indexer_api)
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

    def make_ep_from_file(self, filepath):
        """Make a TVEpisode object from a media file.

        :param filepath:
        :type filepath: str
        :return:
        :rtype: Episode
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
            logger.log(u'{id}: Unable to find IMDb info'
                       u' in the database: {show}'.format
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
        self.runtime = getattr(indexed_show, 'runtime', '')

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

        self._save_externals_to_db()

    def load_imdb_info(self):
        """Load all required show information from IMDb with IMDbPY."""
        imdb_api = imdb.IMDb()

        try:
            if not self.imdb_id:
                # Somewhere title2imdbID started to return without 'tt'
                self.imdb_id = imdb_api.title2imdbID(self.name, kind='tv series')

            if not self.imdb_id:
                logger.log(u'{0}: Not loading show info from IMDb, '
                           u"because we don't know its ID".format(self.indexerid))
                return

            # Make sure we only use one ID, and sanitize the imdb to include the tt.
            self.imdb_id = self.imdb_id.split(',')[0]
            if 'tt' not in self.imdb_id:
                self.imdb_id = 'tt{imdb_id}'.format(imdb_id=self.imdb_id)

            logger.log(u'{0}: Loading show info from IMDb with ID: {1}'.format(
                self.indexerid, self.imdb_id), logger.DEBUG)

            # Remove first two chars from ID
            imdb_obj = imdb_api.get_movie(self.imdb_id[2:])

            # IMDb returned something we don't want
            if not imdb_obj.get('year'):
                logger.log(u'{0}: IMDb returned invalid info for {1}, skipping update.'.format(
                    self.indexerid, self.imdb_id), logger.DEBUG)
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
            'imdb_id': self.imdb_id,
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

        self.externals['imdb_id'] = self.imdb_id

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
                logger.log(u'{id}: No episode found... need to implement a show status'.format
                           (id=self.indexerid), logger.DEBUG)
                self.next_aired = u''
            else:
                logger.log(u'{id}: Found episode {ep}'.format
                           (id=self.indexerid, ep=episode_num(sql_results[0][b'season'], sql_results[0][b'episode'])),
                           logger.DEBUG)
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

        # Let's get some fresh indexer info, as we might need it later on.
        self.create_indexer()

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
                                        status=statusStrings[new_status].upper()), logger.DEBUG)
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

        # Clean up any empty season folders after deletion of associated files
        helpers.delete_empty_folders(self.location)

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
                          'dvdorder': self.dvd_order,
                          'startyear': self.start_year,
                          'lang': self.lang,
                          'imdb_id': self.imdb_id,
                          'last_update_indexer': self.last_update_indexer,
                          'rls_ignore_words': self.rls_ignore_words,
                          'rls_require_words': self.rls_require_words,
                          'default_ep_status': self.default_ep_status}

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
        indexer_name = indexerConfig[self.indexer]['identifier']
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
        ep_status_text = statusStrings[ep_status].upper()
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
            logger.log(u'Could not parse episode status into a valid overview status: {status}'.format
                       (status=ep_status), logger.ERROR)
