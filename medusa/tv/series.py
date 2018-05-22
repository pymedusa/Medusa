# coding=utf-8

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
from builtins import map
from builtins import str
from collections import (
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
)
from medusa.black_and_white_list import BlackAndWhiteList
from medusa.common import (
    ARCHIVED,
    IGNORED,
    Overview,
    Quality,
    SKIPPED,
    UNAIRED,
    UNSET,
    WANTED,
    countryList,
    qualityPresets,
    statusStrings,
)
from medusa.helper.common import (
    episode_num,
    pretty_file_size,
    try_int,
)
from medusa.helper.exceptions import (
    CantRemoveShowException,
    EpisodeDeletedException,
    EpisodeNotFoundException,
    MultipleShowObjectsException,
    ShowDirectoryNotFoundException,
    ShowNotFoundException,
    ex,
)
from medusa.helper.mappings import NonEmptyDict
from medusa.helpers.anidb import get_release_groups_for_anime, short_group_names
from medusa.helpers.externals import get_externals, load_externals_from_db
from medusa.helpers.utils import safe_get
from medusa.indexers.indexer_api import indexerApi
from medusa.indexers.indexer_config import (
    INDEXER_TVRAGE,
    STATUS_MAP,
    indexerConfig
)
from medusa.indexers.indexer_exceptions import (
    IndexerAttributeNotFound,
    IndexerException,
    IndexerSeasonNotFound,
)
from medusa.indexers.tmdb.tmdb import Tmdb
from medusa.indexers.utils import (
    indexer_id_to_slug,
    mappings,
    reverse_mappings,
    slug_to_indexer_id
)
from medusa.logger.adapters.style import BraceAdapter
from medusa.media.banner import ShowBanner
from medusa.media.fan_art import ShowFanArt
from medusa.media.network_logo import ShowNetworkLogo
from medusa.media.poster import ShowPoster
from medusa.name_cache import build_name_cache
from medusa.name_parser.parser import (
    InvalidNameException,
    InvalidShowException,
    NameParser,
)
from medusa.sbdatetime import sbdatetime
from medusa.scene_exceptions import get_scene_exceptions, update_scene_exceptions
from medusa.show.show import Show
from medusa.subtitles import (
    code_from_code,
    from_country_code_to_name,
)
from medusa.tv.base import Identifier, TV
from medusa.tv.episode import Episode
from medusa.tv.indexer import Indexer

from six import iteritems, itervalues, string_types, text_type, viewitems

try:
    from send2trash import send2trash
except ImportError:
    app.TRASH_REMOVE_SHOW = 0


MILLIS_YEAR_1900 = datetime.datetime(year=1900, month=1, day=1).toordinal()

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class SeriesIdentifier(Identifier):
    """Series identifier with indexer and indexer id."""

    def __init__(self, indexer, identifier):
        """Constructor.

        :param indexer:
        :type indexer: Indexer or int
        :param identifier:
        :type identifier: int
        """
        self.indexer = indexer if isinstance(indexer, Indexer) else Indexer.from_id(indexer)
        self.id = identifier

    @classmethod
    def from_slug(cls, slug):
        """Create SeriesIdentifier from slug. E.g.: tvdb1234."""
        result = slug_to_indexer_id(slug)
        if result is not None:
            indexer, indexer_id = result
            if indexer is not None and indexer_id is not None:
                return SeriesIdentifier(Indexer(indexer), indexer_id)

    @classmethod
    def from_id(cls, indexer, indexer_id):
        """Create SeriesIdentifier from tuple (indexer, indexer_id)."""
        return SeriesIdentifier(indexer, indexer_id)

    @property
    def slug(self):
        """Slug."""
        return text_type(self)

    @property
    def api(self):
        """Api."""
        indexer_api = indexerApi(self.indexer.id)
        return indexer_api.indexer(**indexer_api.api_params)

    def __bool__(self):
        """Magic method."""
        return self.indexer is not None and self.id is not None

    def __repr__(self):
        """Magic method."""
        return '<SeriesIdentifier [{0!r} - {1}]>'.format(self.indexer, self.id)

    def __str__(self):
        """Magic method."""
        return '{0}{1}'.format(self.indexer, self.id)

    def __hash__(self):
        """Magic method."""
        return hash((self.indexer, self.id))

    def __eq__(self, other):
        """Magic method."""
        return isinstance(other, SeriesIdentifier) and self.indexer == other.indexer and self.id == other.id


class Series(TV):
    """Represent a TV Show."""

    def __init__(self, indexer, indexerid, lang='', quality=None,
                 season_folders=None, enabled_subtitles=None):
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
        self.season_folders = season_folders or int(app.SEASON_FOLDERS_DEFAULT)
        self.status = 'Unknown'
        self._airs = ''
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

        other_show = Show.find_by_id(app.showList, self.indexer, self.series_id)
        if other_show is not None:
            raise MultipleShowObjectsException("Can't create a show if it already exists")

        self._load_from_db()

    @classmethod
    def find_series(cls, predicate=None):
        """Find series based on given predicate."""
        return [s for s in app.showList if s and (not predicate or predicate(s))]

    @classmethod
    def find_by_identifier(cls, identifier, predicate=None):
        """Find series by its identifier and predicate.

        :param identifier:
        :type identifier: medusa.tv.series.SeriesIdentifier
        :param predicate:
        :type predicate: callable
        :return:
        :rtype:
        """
        result = Show.find_by_id(app.showList, identifier.indexer.id, identifier.id)
        if result and (not predicate or predicate(result)):
            return result

    @classmethod
    def from_identifier(cls, identifier):
        """Create a series object from its identifier."""
        return Series(identifier.indexer.id, identifier.id)

    # TODO: Make this the single entry to add new series
    @classmethod
    def save_series(cls, series):
        """Save the specified series to medusa."""
        try:
            api = series.identifier.api
            series.load_from_indexer(tvapi=api)
            series.load_imdb_info()
            app.showList.append(series)
            series.save_to_db()
            series.load_episodes_from_indexer(tvapi=api)
            return series
        except IndexerException as error:
            log.warning('Unable to load series from indexer: {0!r}'.format(error))

    @property
    def identifier(self):
        """Identifier."""
        return SeriesIdentifier(self.indexer, self.series_id)

    @property
    def slug(self):
        """Slug."""
        return self.identifier.slug

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

    def create_indexer(self, banners=False, actors=False, dvd_order=False, episodes=True):
        """Force the creation of a new Indexer API."""
        api = indexerApi(self.indexer)
        params = api.api_params.copy()

        if self.lang:
            params[b'language'] = self.lang
            log.debug(u'{id}: Using language from show settings: {lang}',
                      {'id': self.series_id, 'lang': self.lang})

        if self.dvd_order != 0 or dvd_order:
            params[b'dvdorder'] = True

        params[b'actors'] = actors

        params[b'banners'] = banners

        params[b'episodes'] = episodes

        self.indexer_api = api.indexer(**params)

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
        """Get the network logo name."""
        return self.network.replace(u'\u00C9', 'e').replace(u'\u00E9', 'e').lower()

    @property
    def raw_location(self):
        """Get the raw show location, unvalidated."""
        return self._location

    @property
    def location(self):
        """Get the show location."""
        # no directory check needed if missing
        # show directories are created during post-processing
        if app.CREATE_MISSING_SHOW_DIRS or self.is_location_valid():
            return self._location
        raise ShowDirectoryNotFoundException(u'Show folder does not exist.')

    @property
    def indexer_name(self):
        """Return the indexer name identifier. Example: tvdb."""
        return indexerConfig[self.indexer].get('identifier')

    @property
    def indexer_slug(self):
        """Return the slug name of the series. Example: tvdb1234."""
        return indexer_id_to_slug(self.indexer, self.series_id)

    @location.setter
    def location(self, value):
        log.debug(
            u'{indexer} {id}: Setting location: {location}', {
                'indexer': indexerApi(self.indexer).name,
                'id': self.series_id,
                'location': value,
            }
        )
        # Don't validate directory if user wants to add shows without creating a dir
        if app.ADD_SHOWS_WO_DIR or self.is_location_valid(value):
            self._location = value
        else:
            raise ShowDirectoryNotFoundException(u'Invalid show folder!')

    @property
    def current_qualities(self):
        """
        Get the show qualities.

        :returns: A tuple of allowed and preferred qualities
        """
        return Quality.split_quality(int(self.quality))

    @property
    def using_preset_quality(self):
        """Check if a preset is used."""
        return self.quality in qualityPresets

    @property
    def default_ep_status_name(self):
        """Get the default episode status name."""
        return statusStrings[self.default_ep_status]

    @default_ep_status_name.setter
    def default_ep_status_name(self, status_name):
        """Set the default episode status using its name."""
        self.default_ep_status = next((status for status, name in iteritems(statusStrings)
                                       if name.lower() == status_name.lower()),
                                      self.default_ep_status)

    @property
    def size(self):
        """Size of the show on disk."""
        return helpers.get_size(self.raw_location)

    def show_size(self, pretty=False):
        """
        Get the size of the show on disk (deprecated).

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
        return code_from_code(self.lang) if self.lang else ''

    @property
    def show_type(self):
        """Return show type."""
        return 'sports' if self.is_sports else ('anime' if self.is_anime else 'series')

    @property
    def imdb_year(self):
        """Return series year."""
        return self.imdb_info.get('year')

    @property
    def imdb_runtime(self):
        """Return series runtime."""
        return self.imdb_info.get('runtimes')

    @property
    def imdb_akas(self):
        """Return genres akas dict."""
        akas = {}
        for x in [v for v in self.imdb_info.get('akas', '').split('|') if v]:
            if '::' in x:
                val, key = x.split('::')
                akas[key] = val
        return akas

    @property
    def imdb_countries(self):
        """Return country codes."""
        return [v for v in self.imdb_info.get('country_codes', '').split('|') if v]

    @property
    def imdb_plot(self):
        """Return series plot."""
        return self.imdb_info.get('plot', '')

    @property
    def imdb_genres(self):
        """Return series genres."""
        return self.imdb_info.get('genres', '')

    @property
    def imdb_votes(self):
        """Return series votes."""
        return self.imdb_info.get('votes')

    @property
    def imdb_rating(self):
        """Return series rating."""
        return self.imdb_info.get('rating')

    @property
    def imdb_certificates(self):
        """Return series certificates."""
        return self.imdb_info.get('certificates')

    @property
    def next_airdate(self):
        """Return next airdate."""
        return (
            sbdatetime.convert_to_setting(network_timezones.parse_date_time(self.next_aired, self.airs, self.network))
            if try_int(self.next_aired, 1) > MILLIS_YEAR_1900 else None
        )

    @property
    def countries(self):
        """Return countries."""
        return [v for v in self.imdb_info.get('countries', '').split('|') if v]

    @property
    def genres(self):
        """Return genres list."""
        return list({i for i in (self.genre or '').split('|') if i} |
                    {i for i in self.imdb_genres.replace('Sci-Fi', 'Science-Fiction').split('|') if i})

    @property
    def airs(self):
        """Return episode time that series usually airs."""
        return self._airs

    @airs.setter
    def airs(self, value):
        """Set episode time that series usually airs."""
        self._airs = text_type(value).replace('am', ' AM').replace('pm', ' PM').replace('  ', ' ').strip()

    @property
    def poster(self):
        """Return poster path."""
        img_type = image_cache.POSTER
        return image_cache.get_artwork(img_type, self)

    @property
    def banner(self):
        """Return banner path."""
        img_type = image_cache.POSTER
        return image_cache.get_artwork(img_type, self)

    @property
    def aliases(self):
        """Return series aliases."""
        return self.exceptions or get_scene_exceptions(self)

    @aliases.setter
    def aliases(self, exceptions):
        """Set the series aliases."""
        self.exceptions = exceptions
        update_scene_exceptions(self, exceptions)
        build_name_cache(self)

    @property
    def release_ignore_words(self):
        """Return release ignore words."""
        return [v for v in (self.rls_ignore_words or '').split(',') if v]

    @release_ignore_words.setter
    def release_ignore_words(self, value):
        self.rls_ignore_words = value if isinstance(value, string_types) else ','.join(value)

    @property
    def release_required_words(self):
        """Return release ignore words."""
        return [v for v in (self.rls_require_words or '').split(',') if v]

    @release_required_words.setter
    def release_required_words(self, value):
        self.rls_require_words = value if isinstance(value, string_types) else ','.join(value)

    @property
    def blacklist(self):
        """Return the anime's blacklisted release groups."""
        bw_list = self.release_groups or BlackAndWhiteList(self)
        return bw_list.blacklist

    @blacklist.setter
    def blacklist(self, value):
        """
        Set the anime's blacklisted release groups.

        :param value: A list of blacklist release groups.
        """
        self.release_groups.set_black_keywords(short_group_names([v['name'] for v in value]))

    @property
    def whitelist(self):
        """Return the anime's whitelisted release groups."""
        bw_list = self.release_groups or BlackAndWhiteList(self)
        return bw_list.whitelist

    @whitelist.setter
    def whitelist(self, value):
        """
        Set the anime's whitelisted release groups.

        :param value: A list of whitelist release groups.
        """
        self.release_groups.set_white_keywords(short_group_names([v['name'] for v in value]))

    @staticmethod
    def normalize_status(series_status):
        """Return a normalized status given current indexer status."""
        default_status = 'Unknown'
        return STATUS_MAP.get(series_status.lower(), default_status) if series_status else default_status

    def flush_episodes(self):
        """Delete references to anything that's not in the internal lists."""
        for cur_season in self.episodes:
            for cur_ep in self.episodes[cur_season]:
                my_ep = self.episodes[cur_season][cur_ep]
                self.episodes[cur_season][cur_ep] = None
                del my_ep

    def erase_cached_parse(self):
        """Erase parsed cached results."""
        NameParser().erase_cached_parse(self.indexer, self.series_id)

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
        results = main_db_con.select(sql_selection, [self.series_id])

        return {int(x[b'season']): int(x[b'number_of_episodes']) for x in results}

    def get_all_episodes(self, season=None, has_location=False):
        """Retrieve all episodes for this show given the specified filter.

        :param season:
        :type season: int or list of int
        :param has_location:
        :type has_location: bool
        :return:
        :rtype: list of Episode
        """
        # subselection to detect multi-episodes early, share_location > 0
        # If a multi-episode release has been downloaded. For example my.show.S01E1E2.1080p.WEBDL.mkv, you'll find the same location
        # in the database for those episodes (S01E01 and S01E02). The query is to mark that the location for each episode is shared with another episode.
        sql_selection = (b'SELECT season, episode, (SELECT '
                         b'  COUNT (*) '
                         b'FROM '
                         b'  tv_episodes '
                         b'WHERE '
                         b'  indexer = tve.indexer AND showid = tve.showid '
                         b'  AND season = tve.season '
                         b"  AND location != '' "
                         b'  AND location = tve.location '
                         b'  AND episode != tve.episode) AS share_location '
                         b'FROM tv_episodes tve WHERE indexer = ? AND showid = ?'
                         )
        sql_args = [self.indexer, self.series_id]

        if season is not None:
            season = helpers.ensure_list(season)
            sql_selection += b' AND season IN (?)'
            sql_args.append(','.join(map(text_type, season)))

        if has_location:
            sql_selection += b" AND location != ''"

        # need ORDER episode ASC to rename multi-episodes in order S01E01-02
        sql_selection += b' ORDER BY season ASC, episode ASC'

        main_db_con = db.DBConnection()
        results = main_db_con.select(sql_selection, sql_args)

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
                        [self.series_id, cur_ep.season, cur_ep.location, cur_ep.episode])
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
                sql_args = [self.series_id, absolute_number]
                log.debug(u'{id}: Season and episode lookup for {show} using absolute number {absolute}',
                          {'id': self.series_id, 'absolute': absolute_number, 'show': self.name})
            elif air_date:
                sql = b'SELECT season, episode FROM tv_episodes WHERE showid = ? AND airdate = ?'
                sql_args = [self.series_id, air_date.toordinal()]
                log.debug(u'{id}: Season and episode lookup for {show} using air date {air_date}',
                          {'id': self.series_id, 'air_date': air_date, 'show': self.name})

            sql_results = main_db_con.select(sql, sql_args) if sql else []
            if len(sql_results) == 1:
                episode = int(sql_results[0][b'episode'])
                season = int(sql_results[0][b'season'])
                log.debug(
                    u'{id}: Found season and episode which is {show} {ep}', {
                        'id': self.series_id,
                        'show': self.name,
                        'ep': episode_num(season, episode)
                    }
                )
            elif len(sql_results) > 1:
                log.error(u'{id}: Multiple entries found in show: {show} ',
                          {'id': self.series_id, 'show': self.name})
                return None
            else:
                log.debug(u'{id}: No entries found in show: {show}',
                          {'id': self.series_id, 'show': self.name})
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

        if ep is not None and ep.loaded and should_cache:
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
            log.info(u'{id}: Show {show} is paused. Update skipped',
                     {'id': self.series_id, 'show': self.name})
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
            [self.series_id])

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
            [self.series_id])

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

        preferred_words = app.PREFERRED_WORDS
        undesired_words = app.UNDESIRED_WORDS

        global_ignore = app.IGNORE_WORDS
        global_require = app.REQUIRE_WORDS
        show_ignore = self.rls_ignore_words.split(',') if self.rls_ignore_words else []
        show_require = self.rls_require_words.split(',') if self.rls_require_words else []

        # If word is in global ignore and also in show require, then remove it from global ignore
        # Join new global ignore with show ignore
        final_ignore = show_ignore + [i for i in global_ignore if i.lower() not in [r.lower() for r in show_require]]
        # If word is in global require and also in show ignore, then remove it from global require
        # Join new global required with show require
        final_require = show_require + [i for i in global_require if i.lower() not in [r.lower() for r in show_ignore]]

        ignored_words = final_ignore
        required_words = final_require

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
            log.warning("{id}: Show directory doesn't exist, skipping NFO generation",
                        {'id': self.series_id})
            return

        for metadata_provider in itervalues(app.metadata_provider_dict):
            self.__get_images(metadata_provider)
            self.__write_show_nfo(metadata_provider)

        if not show_only:
            self.__write_episode_nfos()

    def __write_episode_nfos(self):

        log.debug(u"{id}: Writing NFOs for all episodes",
                  {'id': self.series_id})

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(
            b'SELECT '
            b'  season, '
            b'  episode '
            b'FROM '
            b'  tv_episodes '
            b'WHERE '
            b'  showid = ? '
            b"  AND location != ''", [self.series_id])

        for ep_result in sql_results:
            log.debug(
                u'{id}: Retrieving/creating episode {ep}', {
                    'id': self.series_id,
                    'ep': episode_num(ep_result[b'season'], ep_result[b'episode'])
                }
            )
            cur_ep = self.get_episode(ep_result[b'season'], ep_result[b'episode'])
            if not cur_ep:
                continue

            cur_ep.create_meta_files()

    def update_metadata(self):
        """Update show metadata files."""
        if not self.is_location_valid():
            log.warning(u"{id}: Show directory doesn't exist, skipping NFO generation",
                        {'id': self.series_id})
            return

        self.__update_show_nfo()

    def __update_show_nfo(self):

        result = False

        log.info(u"{id}: Updating NFOs for show with new indexer info",
                 {'id': self.series_id})
        # You may only call .values() on metadata_provider_dict! As on values() call the indexer_api attribute
        # is reset. This will prevent errors, when using multiple indexers and caching.
        for cur_provider in itervalues(app.metadata_provider_dict):
            result = cur_provider.update_show_indexer_metadata(self) or result

        return result

    def load_episodes_from_dir(self):
        """Find all media files in the show folder and create episodes for as many as possible."""
        if not self.is_location_valid():
            log.warning(u"{id}: Show directory doesn't exist, not loading episodes from disk",
                        {'id': self.series_id})
            return

        log.debug(u"{id}: Loading all episodes from the show directory: {location}",
                  {'id': self.series_id, 'location': self.location})

        # get file list
        media_files = helpers.list_media_files(self.location)
        log.debug(u'{id}: Found files: {media_files}',
                  {'id': self.series_id, 'media_files': media_files})

        # create TVEpisodes from each media file (if possible)
        sql_l = []
        for media_file in media_files:
            cur_episode = None

            log.debug(u"{id}: Creating episode from: {location}",
                      {'id': self.series_id, 'location': media_file})
            try:
                cur_episode = self.make_ep_from_file(os.path.join(self.location, media_file))
            except (ShowNotFoundException, EpisodeNotFoundException) as error:
                log.warning(
                    u"{id}: Episode {location} returned an exception {error_msg}", {
                        'id': self.series_id,
                        'location': media_file,
                        'error_msg': ex(error),
                    }
                )
                continue
            except EpisodeDeletedException:
                log.debug(u'{id}: The episode deleted itself when I tried making an object for it',
                          {'id': self.series_id})
            if cur_episode is None:
                continue

            # see if we should save the release name in the db
            ep_file_name = os.path.basename(cur_episode.location)
            ep_file_name = os.path.splitext(ep_file_name)[0]

            try:
                parse_result = NameParser(series=self, try_indexers=True).parse(ep_file_name)
            except (InvalidNameException, InvalidShowException):
                parse_result = None

            if ' ' not in ep_file_name and parse_result and parse_result.release_group:
                log.debug(
                    u'{id}: Filename {file_name} gave release group of {rg}, seems valid', {
                        'id': self.series_id,
                        'file_name': ep_file_name,
                        'rg': parse_result.release_group,
                    }
                )
                cur_episode.release_name = ep_file_name

            # store the reference in the show
            if cur_episode is not None:
                if self.subtitles:
                    try:
                        cur_episode.refresh_subtitles()
                    except OSError:
                        log.info(u'{id}: Could not refresh subtitles',
                                 {'id': self.series_id})
                        log.debug(traceback.format_exc())

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
                   b'  season, episode, showid, show_name, tv_shows.show_id, tv_shows.indexer '
                   b'FROM '
                   b'  tv_episodes '
                   b'JOIN '
                   b'  tv_shows '
                   b'WHERE '
                   b'  tv_episodes.showid = tv_shows.indexer_id'
                   b'  AND tv_episodes.indexer = tv_shows.indexer'
                   b'  AND tv_shows.indexer = ? AND tv_shows.indexer_id = ?')
            if seasons:
                sql += b' AND season IN (%s)' % ','.join('?' * len(seasons))
                sql_results = main_db_con.select(sql, [self.indexer, self.series_id] + seasons)
                log.debug(u'{id}: Loading all episodes of season(s) {seasons} from the DB',
                          {'id': self.series_id, 'seasons': seasons})
            else:
                sql_results = main_db_con.select(sql, [self.indexer, self.series_id])
                log.debug(u'{id}: Loading all episodes of all seasons from the DB',
                          {'id': self.series_id})
        except Exception as error:
            log.error(u'{id}: Could not load episodes from the DB. Error: {error_msg}',
                      {'id': self.series_id, 'error_msg': error})
            return scanned_eps

        cached_show = self.indexer_api[self.series_id]

        cached_seasons = {}
        cur_show_name = ''
        cur_show_id = ''

        for cur_result in sql_results:

            cur_season = int(cur_result[b'season'])
            cur_episode = int(cur_result[b'episode'])
            cur_indexer = int(cur_result[b'indexer'])
            cur_show_id = int(cur_result[b'showid'])
            cur_show_name = text_type(cur_result[b'show_name'])

            delete_ep = False

            log.debug(
                u'{id}: Loading {show} with indexer {indexer} and ep {ep} from the DB', {
                    'id': cur_show_id,
                    'show': cur_show_name,
                    'indexer': cur_indexer,
                    'ep': episode_num(cur_season, cur_episode),
                }
            )

            if cur_season not in cached_seasons:
                try:
                    cached_seasons[cur_season] = cached_show[cur_season]
                except IndexerSeasonNotFound as error:
                    log.debug(
                        u'{id}: {error_msg} (unaired/deleted) in the indexer {indexer} for {show}.'
                        u' Removing existing records from database', {
                            'id': cur_show_id,
                            'error_msg': error.message,
                            'indexer': indexerApi(self.indexer).name,
                            'show': cur_show_name,
                        }
                    )
                    delete_ep = True

            if cur_season not in scanned_eps:
                scanned_eps[cur_season] = {}

            if cur_episode == 0:
                log.warning(
                    u'{id}: Tried loading {show} {ep} from the database with an episode id set to 0.'
                    u' We do not support that. Skipping to next episode.', {
                        'id': cur_show_id,
                        'show': cur_show_name,
                        'ep': episode_num(cur_season, cur_episode),
                    }
                )
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
                log.debug(
                    u'{id}: Tried loading {show} {ep} from the DB that should have been deleted,'
                    u' skipping it', {
                        'id': cur_show_id,
                        'show': cur_show_name,
                        'ep': episode_num(cur_season, cur_episode),
                    }
                )
                continue

        log.debug(u'{id}: Finished loading all episodes for {show} from the DB',
                  {'show': cur_show_name, 'id': cur_show_id})

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
            indexed_show = self.indexer_api[self.series_id]
        except IndexerException as error:
            log.warning(
                u'{id}: {indexer} error, unable to update episodes.'
                u' Message: {ex}', {
                    'id': self.series_id,
                    'indexer': indexerApi(self.indexer).name,
                    'ex': error,
                }
            )
            raise

        log.debug(
            u'{id}: Loading all episodes from {indexer}{season_update}', {
                'id': self.series_id,
                'indexer': indexerApi(self.indexer).name,
                'season_update': u' on seasons {seasons}'.format(seasons=seasons) if seasons else u''
            }
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
                    log.info(
                        u'{id}: {indexer} object for {ep} is incomplete, skipping this episode', {
                            'id': self.series_id,
                            'indexer': indexerApi(self.indexer).name,
                            'ep': episode_num(season, episode),
                        }
                    )
                    continue
                else:
                    try:
                        ep.load_from_indexer(tvapi=self.indexer_api)
                    except EpisodeDeletedException:
                        log.debug(u'{id}: The episode {ep} was deleted, skipping the rest of the load',
                                  {'id': self.series_id, 'ep': episode_num(season, episode)})
                        continue

                with ep.lock:
                    sql_l.append(ep.get_sql())

                scanned_eps[season][episode] = True

        if sql_l:
            main_db_con = db.DBConnection()
            main_db_con.mass_action(sql_l)

        # Done updating save last update date
        self.last_update_indexer = datetime.date.today().toordinal()
        log.debug(u'{id}: Saving indexer changes to database',
                  {'id': self.series_id})
        self.save_to_db()

        return scanned_eps

    def _save_externals_to_db(self):
        """Save the indexers external id's to the db."""
        sql_l = []

        for external in self.externals:
            if external in reverse_mappings and self.externals[external]:
                sql_l.append([b'INSERT OR IGNORE '
                              b'INTO indexer_mapping (indexer_id, indexer, mindexer_id, mindexer) '
                              b'VALUES (?,?,?,?)',
                              [self.series_id,
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
        if not (os.path.isfile(filepath) and helpers.is_media_file(filepath)):
            log.info(u"{indexer_id}: This isn't a valid media file: {filepath}",
                     {'indexer_id': self.series_id, 'filepath': filepath})
            return None

        log.debug(u'{indexer_id}: Creating episode object from {filepath}',
                  {'indexer_id': self.series_id, 'filepath': filepath})

        try:
            parse_result = NameParser(series=self, try_indexers=True, parse_method=(
                'normal', 'anime')[self.is_anime]).parse(filepath)
        except (InvalidNameException, InvalidShowException) as error:
            log.debug(u'{indexerid}: {error}',
                      {'indexer_id': self.series_id, 'error': error})
            return None

        episodes = [ep for ep in parse_result.episode_numbers if ep is not None]
        if not episodes:
            log.debug(u'{indexerid}: parse_result: {parse_result}',
                      {'indexerid': self.series_id, 'parse_result': parse_result})
            log.debug(u'{indexerid}: No episode number found in {filepath}, ignoring it',
                      {'indexerid': self.series_id, 'filepath': filepath})
            return None

        # for now lets assume that any episode in the show directory belongs to that show
        season = parse_result.season_number if parse_result.season_number is not None else 1
        root_ep = None

        sql_l = []
        for current_ep in episodes:
            log.debug(
                u'{id}: {filepath} parsed to {series_name} {ep_num}', {
                    'id': self.series_id,
                    'filepath': filepath,
                    'series_name': self.name,
                    'ep_num': episode_num(season, current_ep)
                }
            )

            cur_ep = self.get_episode(season, current_ep)
            if not cur_ep:
                try:
                    cur_ep = self.get_episode(season, current_ep, filepath)
                    if not cur_ep:
                        raise EpisodeNotFoundException
                except EpisodeNotFoundException:
                    log.warning(u'{indexerid}: Unable to figure out what this file is, skipping {filepath}',
                                {'indexerid': self.series_id, 'filepath': filepath})
                    continue

            else:
                cur_ep.update_status(filepath)

                with cur_ep.lock:
                    cur_ep.check_for_meta_files()

            if root_ep is None:
                root_ep = cur_ep
            else:
                if cur_ep not in root_ep.related_episodes:
                    with root_ep.lock:
                        root_ep.related_episodes.append(cur_ep)

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

        log.debug(u'{id}: Loading show info from database',
                  {'id': self.series_id})

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(
            b'SELECT *'
            b' FROM tv_shows'
            b' WHERE indexer = ?'
            b' AND indexer_id = ?',
            [self.indexer, self.series_id]
        )

        if not sql_results:
            log.info(u'{id}: Unable to find the show in the database',
                     {'id': self.series_id})
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
            self.quality = int(sql_results[0][b'quality'] or UNSET)
            self.season_folders = int(not (sql_results[0][b'flatten_folders'] or 0))  # TODO: Rename this in the DB
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

            self.release_groups = BlackAndWhiteList(self)

            self.plot = sql_results[0][b'plot']

            # Load external id's from indexer_mappings table.
            self.externals = load_externals_from_db(self.indexer, self.series_id)

        # Get IMDb_info from database
        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(
            b'SELECT * '
            b'FROM imdb_info'
            b' WHERE indexer = ?'
            b' AND indexer_id = ?',
            [self.indexer, self.series_id]
        )

        if not sql_results:
            log.info(u'{id}: Unable to find IMDb info in the database: {show}',
                     {'id': self.series_id, 'show': self.name})
            return
        else:
            self.imdb_info = dict(sql_results[0])

        self.reset_dirty()
        return True

    def load_from_indexer(self, tvapi=None):
        """Load show from indexer.

        :param tvapi:
        """
        if self.indexer == INDEXER_TVRAGE:
            return

        log.debug(
            u'{id}: Loading show info from {indexer_name}', {
                'id': self.series_id,
                'indexer_name': indexerApi(self.indexer).name,
            }
        )

        self.indexer_api = tvapi
        indexed_show = self.indexer_api[self.series_id]

        try:
            self.name = indexed_show['seriesname'].strip()
        except AttributeError:
            raise IndexerAttributeNotFound(
                "Found {id}, but attribute 'seriesname' was empty.".format(id=self.series_id))

        self.classification = getattr(indexed_show, 'classification', 'Scripted')
        self.genre = getattr(indexed_show, 'genre', '')
        self.network = getattr(indexed_show, 'network', '')
        self.runtime = int(getattr(indexed_show, 'runtime', 0) or 0)

        # set the externals, using the result from the indexer.
        self.externals = {k: v for k, v in viewitems(getattr(indexed_show, 'externals', {})) if v}

        # Add myself (indexer) as an external
        self.externals[mappings[self.indexer]] = self.series_id

        # Enrich the externals, using reverse lookup.
        self.externals.update(get_externals(self))

        self.imdb_id = self.externals.get('imdb_id') or getattr(indexed_show, 'imdb_id', '')

        if getattr(indexed_show, 'airs_dayofweek', '') and getattr(indexed_show, 'airs_time', ''):
            self.airs = '{airs_day_of_week} {airs_time}'.format(airs_day_of_week=indexed_show['airs_dayofweek'],
                                                                airs_time=indexed_show['airs_time'])

        if getattr(indexed_show, 'firstaired', ''):
            self.start_year = int(str(indexed_show['firstaired']).split('-')[0])

        self.status = self.normalize_status(getattr(indexed_show, 'status', None))

        self.plot = getattr(indexed_show, 'overview', '') or self.imdb_plot

        self._save_externals_to_db()

    def load_imdb_info(self):
        """Load all required show information from IMDb with ImdbPie."""
        imdb_api = imdbpie.Imdb()

        if not self.imdb_id:
            self.imdb_id = helpers.title_to_imdb(self.name, self.start_year, imdb_api)

            if not self.imdb_id:
                log.info(u"{id}: Not loading show info from IMDb, because we don't know its ID.",
                         {'id': self.series_id})
                return

        # Make sure we only use the first ID
        self.imdb_id = self.imdb_id.split(',')[0]

        # Set retrieved IMDb ID as imdb_id for externals
        self.externals['imdb_id'] = self.imdb_id

        log.debug(u'{id}: Loading show info from IMDb with ID: {imdb_id}',
                  {'id': self.series_id, 'imdb_id': self.imdb_id})

        tmdb_id = self.externals.get('tmdb_id')
        if tmdb_id:
            # Country codes and countries obtained from TMDB's API. Not IMDb info.
            country_codes = Tmdb().get_show_country_codes(tmdb_id)
            if country_codes:
                countries = (from_country_code_to_name(country) for country in country_codes)
                self.imdb_info['countries'] = '|'.join([_f for _f in countries if _f])
                self.imdb_info['country_codes'] = '|'.join(country_codes).lower()

        # Make sure these always have a value
        self.imdb_info['countries'] = self.imdb_info.get('countries', '')
        self.imdb_info['country_codes'] = self.imdb_info.get('country_codes', '')

        imdb_info = imdb_api.get_title(self.imdb_id)
        if not imdb_info:
            log.debug(u"{id}: IMDb didn't return any info for {imdb_id}, skipping update.",
                      {'id': self.series_id, 'imdb_id': self.imdb_id})
            return

        # Additional query needed to get genres
        imdb_genres = imdb_api.get_title_genres(self.imdb_id)

        self.imdb_info.update({
            'imdb_id': self.imdb_id,
            'title': safe_get(imdb_info, ('base', 'title')),
            'year': safe_get(imdb_info, ('base', 'year')),
            'akas': '',
            'genres': '|'.join(safe_get(imdb_genres, ('genres',))),
            'rating': text_type(safe_get(imdb_info, ('ratings', 'rating'))),
            'votes': safe_get(imdb_info, ('ratings', 'ratingCount')),
            'runtimes': safe_get(imdb_info, ('base', 'runningTimeInMinutes')),
            'certificates': '',
            'plot': safe_get(imdb_info, ('plot', 'outline', 'text')),
            'last_update': datetime.date.today().toordinal(),
        })

        log.debug(u'{id}: Obtained info from IMDb: {imdb_info}',
                  {'id': self.series_id, 'imdb_info': self.imdb_info})

    def next_episode(self):
        """Return the next episode air date.

        :return:
        :rtype: datetime.date
        """
        log.debug(u'{id}: Finding the episode which airs next',
                  {'id': self.series_id})

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
                b'  indexer = ?'
                b'  AND showid = ? '
                b'  AND airdate >= ? '
                b'  AND status IN (?,?) '
                b'ORDER BY'
                b'  airdate '
                b'ASC LIMIT 1',
                [self.indexer, self.series_id, datetime.date.today().toordinal(), UNAIRED, WANTED])

            if sql_results is None or len(sql_results) == 0:
                log.debug(u'{id}: No episode found... need to implement a show status',
                          {'id': self.series_id})
                self.next_aired = u''
            else:
                log.debug(
                    u'{id}: Found episode {ep}', {
                        'id': self.series_id,
                        'ep': episode_num(sql_results[0][b'season'],
                                          sql_results[0][b'episode']),
                    }
                )
                self.next_aired = sql_results[0][b'airdate']

        return self.next_aired

    def delete_show(self, full=False):
        """Delete the tv show from the database.

        :param full:
        :type full: bool
        """
        sql_l = [[b'DELETE FROM tv_episodes WHERE indexer = ? AND showid = ?', [self.indexer, self.series_id]],
                 [b'DELETE FROM tv_shows WHERE indexer = ? AND indexer_id = ?', [self.indexer, self.series_id]],
                 [b'DELETE FROM imdb_info WHERE indexer = ? AND indexer_id = ?', [self.indexer, self.series_id]],
                 [b'DELETE FROM xem_refresh WHERE indexer = ? AND indexer_id = ?', [self.indexer, self.series_id]],
                 [b'DELETE FROM scene_numbering WHERE indexer = ? AND indexer_id = ?', [self.indexer, self.series_id]]]

        main_db_con = db.DBConnection()
        main_db_con.mass_action(sql_l)

        action = ('delete', 'trash')[app.TRASH_REMOVE_SHOW]

        # remove self from show list
        app.showList = [x for x in app.showList if x.identifier != self.identifier]

        # clear the cache
        image_cache_dir = os.path.join(app.CACHE_DIR, 'images')
        for cache_file in glob.glob(os.path.join(image_cache_dir, str(self.series_id) + '.*')):
            log.info(u'{id}: Attempt to {action} cache file {cache_file}',
                     {'id': self.series_id, 'action': action, 'cache_file': cache_file})
            try:
                if app.TRASH_REMOVE_SHOW:
                    send2trash(cache_file)
                else:
                    os.remove(cache_file)

            except OSError as error:
                log.warning(
                    u'{id}: Unable to {action} {cache_file}: {error_msg}', {
                        'id': self.series_id,
                        'action': action,
                        'cache_file': cache_file,
                        'error_msg': ex(error),
                    }
                )

        # remove entire show folder
        if full:
            try:
                log.info(u'{id}: Attempt to {action} show folder {location}',
                         {'id': self.series_id, 'action': action, 'location': self.location})
                # check first the read-only attribute
                file_attribute = os.stat(self.location)[0]
                if not file_attribute & stat.S_IWRITE:
                    # File is read-only, so make it writeable
                    log.debug(u'{id}: Attempting to make writeable the read only folder {location}',
                              {'id': self.series_id, 'location': self.location})
                    try:
                        os.chmod(self.location, stat.S_IWRITE)
                    except OSError:
                        log.warning(u'{id}: Unable to change permissions of {location}',
                                    {'id': self.series_id, 'location': self.location})

                if app.TRASH_REMOVE_SHOW:
                    send2trash(self.location)
                else:
                    shutil.rmtree(self.location)

                log.info(u'{id}: {action} show folder {location}',
                         {'id': self.series_id, 'action': action, 'location': self.raw_location})

            except ShowDirectoryNotFoundException:
                log.warning(u'{id}: Show folder {location} does not exist. No need to {action}',
                            {'id': self.series_id, 'action': action, 'location': self.raw_location})
            except OSError as error:
                log.warning(
                    u'{id}: Unable to {action} {location}. Error: {error_msg}', {
                        'id': self.series_id,
                        'action': action,
                        'location': self.raw_location,
                        'error_msg': ex(error),
                    }
                )

        if app.USE_TRAKT and app.TRAKT_SYNC_WATCHLIST:
            log.debug(u'{id}: Removing show {show} from Trakt watchlist',
                      {'id': self.series_id, 'show': self.name})
            notifiers.trakt_notifier.update_watchlist(self, update='remove')

    def populate_cache(self):
        """Populate image caching."""
        log.debug(u'{id}: Checking & filling cache for show {show}',
                  {'id': self.series_id, 'show': self.name})
        image_cache.fill_cache(self)

    def refresh_dir(self):
        """Refresh show using its location.

        :return:
        :rtype: bool
        """
        # make sure the show directory is where we think it is unless directories are created on the fly
        if not app.CREATE_MISSING_SHOW_DIRS and not self.is_location_valid():
            return False

        # load from dir
        self.load_episodes_from_dir()

        # run through all locations from DB, check that they exist
        log.debug(u"{id}: Loading all episodes from '{show}' with a location from the database",
                  {'id': self.series_id, 'show': self.name})

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(
            b'SELECT '
            b'  season, episode, location '
            b'FROM '
            b'  tv_episodes '
            b'WHERE '
            b'  indexer = ?'
            b'  AND showid = ? '
            b"  AND location != ''", [self.indexer, self.series_id])

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
                log.debug(
                    u"{id:} Episode '{show}' {ep} was deleted while we were refreshing it,"
                    u' moving on to the next one', {
                        'id': self.series_id,
                        'show': self.name,
                        'ep': episode_num(season, episode)
                    }
                )
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

                            log.debug(
                                u"{id}: Location for '{show}' {ep} doesn't exist and current status is '{old_status}',"
                                u" removing it and changing status to '{status}'", {
                                    'id': self.series_id,
                                    'show': self.name,
                                    'ep': episode_num(season, episode),
                                    'old_status': statusStrings[cur_ep.status],
                                    'status': statusStrings[new_status],
                                }
                            )

                            cur_ep.status = new_status
                            cur_ep.subtitles = ''
                            cur_ep.subtitles_searchcount = 0
                            cur_ep.subtitles_lastsearch = ''
                        cur_ep.location = ''
                        cur_ep.hasnfo = False
                        cur_ep.hastbn = False
                        cur_ep.release_name = ''

                        sql_l.append(cur_ep.get_sql())

                    log.info(
                        u"{id}: Looking for hanging associated files for: '{show}' {ep} in: {location}", {
                            'id': self.series_id,
                            'show': self.name,
                            'ep': episode_num(season, episode),
                            'location': cur_loc,
                        }
                    )
                    related_files = post_processor.PostProcessor(cur_loc).list_associated_files(
                        cur_loc, subfolders=True)

                    if related_files:
                        log.info(
                            u"{id}: Found hanging associated files for '{show}' {ep}, deleting: '{files}'", {
                                'id': self.series_id, 'show': self.name,
                                'ep': episode_num(season, episode),
                                'files': ', '.join(related_files)
                            }
                        )
                        for related_file in related_files:
                            try:
                                os.remove(related_file)
                            except OSError as error:
                                log.warning(
                                    u'id}: Could not delete associated file: {related_file}. Error: {error_msg}', {
                                        'id': self.series_id,
                                        'related_file': related_file,
                                        'error_msg': error,
                                    }
                                )

        # Clean up any empty season folders after deletion of associated files
        helpers.delete_empty_folders(self.location)

        if sql_l:
            main_db_con = db.DBConnection()
            main_db_con.mass_action(sql_l)

    def download_subtitles(self):
        """Download subtitles."""
        if not self.is_location_valid():
            log.warning(
                u"{id}: Show {show} location doesn't exist, can't download subtitles",
                {'id': self.series_id, 'show': self.name}
            )
            return

        log.debug(u'{id}: Downloading subtitles for {show}', id=self.series_id, show=self.name)

        episodes = self.get_all_episodes(has_location=True)
        if not episodes:
            log.debug(u'{id}: No episodes to download subtitles for {show}',
                      {'id': self.series_id, 'show': self.name})
            return

        for episode in episodes:
            episode.download_subtitles()

    def save_to_db(self):
        """Save to database."""
        if not self.dirty:
            return

        log.debug(u'{id}: Saving to database: {show}',
                  {'id': self.series_id, 'show': self.name})

        control_value_dict = {'indexer': self.indexer, 'indexer_id': self.series_id}
        new_value_dict = {'show_name': self.name,
                          'location': self.raw_location,  # skip location validation
                          'network': self.network,
                          'genre': self.genre,
                          'classification': self.classification,
                          'runtime': self.runtime,
                          'quality': self.quality,
                          'airs': self.airs,
                          'status': self.status,
                          'flatten_folders': not self.season_folders,  # TODO: Remove negation after DB change
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
            control_value_dict = {'indexer': self.indexer, 'indexer_id': self.series_id}
            new_value_dict = self.imdb_info

            main_db_con = db.DBConnection()
            main_db_con.upsert('imdb_info', new_value_dict, control_value_dict)

        self.reset_dirty()

    def __str__(self):
        """Represent a string.

        :return:
        :rtype: str
        """
        to_return = ''
        to_return += 'indexerid: ' + str(self.series_id) + '\n'
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
        to_return += u'indexerid: {0}\n'.format(self.series_id)
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
        bw_list = self.release_groups or BlackAndWhiteList(self)

        data = NonEmptyDict()
        data['id'] = NonEmptyDict()
        data['id'][self.indexer_name] = self.series_id
        data['id']['imdb'] = text_type(self.imdb_id)
        data['id']['slug'] = self.identifier.slug
        data['title'] = self.name
        data['indexer'] = self.indexer_name  # e.g. tvdb
        data['network'] = self.network  # e.g. CBS
        data['type'] = self.classification  # e.g. Scripted
        data['status'] = self.status  # e.g. Continuing
        data['airs'] = self.airs  # e.g. Thursday 8:00 PM
        data['language'] = self.lang
        data['showType'] = self.show_type  # e.g. anime, sport, series
        data['akas'] = self.imdb_akas
        data['year'] = NonEmptyDict()
        data['year']['start'] = self.imdb_year or self.start_year
        data['nextAirDate'] = self.next_airdate
        data['runtime'] = self.imdb_runtime or self.runtime
        data['genres'] = self.genres
        data['rating'] = NonEmptyDict()
        if self.imdb_rating and self.imdb_votes:
            data['rating']['imdb'] = NonEmptyDict()
            data['rating']['imdb']['rating'] = self.imdb_rating
            data['rating']['imdb']['votes'] = self.imdb_votes

        data['classification'] = self.imdb_certificates
        data['cache'] = NonEmptyDict()
        data['cache']['poster'] = self.poster
        data['cache']['banner'] = self.banner
        data['countries'] = self.countries  # e.g. ['ITALY', 'FRANCE']
        data['country_codes'] = self.imdb_countries  # e.g. ['it', 'fr']
        data['plot'] = self.imdb_plot or self.plot
        data['config'] = NonEmptyDict()
        data['config']['location'] = self.raw_location
        data['config']['qualities'] = NonEmptyDict()
        data['config']['qualities']['allowed'] = self.qualities_allowed
        data['config']['qualities']['preferred'] = self.qualities_preferred
        data['config']['paused'] = bool(self.paused)
        data['config']['airByDate'] = bool(self.air_by_date)
        data['config']['subtitlesEnabled'] = bool(self.subtitles)
        data['config']['dvdOrder'] = bool(self.dvd_order)
        data['config']['seasonFolders'] = bool(self.season_folders)
        data['config']['anime'] = self.is_anime
        data['config']['scene'] = self.is_scene
        data['config']['sports'] = self.is_sports
        data['config']['paused'] = bool(self.paused)
        data['config']['defaultEpisodeStatus'] = self.default_ep_status_name
        data['config']['aliases'] = self.aliases
        data['config']['release'] = NonEmptyDict()
        # These are for now considered anime-only options, as they query anidb for available release groups.
        if self.is_anime:
            data['config']['release']['blacklist'] = bw_list.blacklist
            data['config']['release']['whitelist'] = bw_list.whitelist
            data['config']['release']['allgroups'] = get_release_groups_for_anime(self.name)
        data['config']['release']['ignoredWords'] = self.release_ignore_words
        data['config']['release']['requiredWords'] = self.release_required_words

        if detailed:
            episodes = self.get_all_episodes()
            data['seasons'] = [list(v) for _, v in
                               groupby([ep.to_json() for ep in episodes], lambda item: item['season'])]
            data['episodeCount'] = len(episodes)
            last_episode = episodes[-1] if episodes else None
            if self.status == 'Ended' and last_episode and last_episode.airdate:
                data['year']['end'] = last_episode.airdate.year

        return data

    def get_allowed_qualities(self):
        """Return allowed qualities descriptions."""
        allowed = Quality.split_quality(self.quality)[0]

        return [Quality.qualityStrings[v] for v in allowed]

    def get_preferred_qualities(self):
        """Return preferred qualities descriptions."""
        preferred = Quality.split_quality(self.quality)[1]

        return [Quality.qualityStrings[v] for v in preferred]

    @property
    def qualities_allowed(self):
        """Return allowed qualities."""
        return Quality.split_quality(self.quality)[0]

    @property
    def qualities_preferred(self):
        """Return preferred qualities."""
        return Quality.split_quality(self.quality)[1]

    @qualities_allowed.setter
    def qualities_allowed(self, qualities_allowed):
        """Configure qualities (combined) by adding the allowed qualities to it."""
        self.quality = Quality.combine_qualities(qualities_allowed, self.qualities_preferred)

    @qualities_preferred.setter
    def qualities_preferred(self, qualities_preferred):
        """Configure qualities (combined) by adding the preferred qualities to it."""
        self.quality = Quality.combine_qualities(self.qualities_allowed, qualities_preferred)

    def get_all_possible_names(self, season=-1):
        """Get every possible variation of the name for a particular show.

        Includes indexer name, and any scene exception names, and country code
        at the end of the name (e.g. "Show Name (AU)".

        show: a Series object that we should get the names of
        Returns: all possible show names
        """
        show_names = get_scene_exceptions(self, season)
        show_names.add(self.name)

        new_show_names = set()

        if not self.is_anime:
            country_list = {}
            # add the country list
            country_list.update(countryList)
            # add the reversed mapping of the country list
            country_list.update({v: k for k, v in viewitems(countryList)})

            for name in show_names:
                if not name:
                    continue

                # if we have "Show Name Australia" or "Show Name (Australia)"
                # this will add "Show Name (AU)" for any countries defined in
                # common.countryList (and vice versa)
                for country in country_list:
                    pattern_1 = ' {0}'.format(country)
                    pattern_2 = ' ({0})'.format(country)
                    replacement = ' ({0})'.format(country_list[country])
                    if name.endswith(pattern_1):
                        new_show_names.add(name.replace(pattern_1, replacement))
                    elif name.endswith(pattern_2):
                        new_show_names.add(name.replace(pattern_2, replacement))

        return show_names.union(new_show_names)

    @staticmethod
    def __qualities_to_string(qualities=None):
        return ', '.join([Quality.qualityStrings[quality] for quality in qualities or []
                          if quality and quality in Quality.qualityStrings]) or 'None'

    def want_episode(self, season, episode, quality, forced_search=False,
                     download_current_quality=False, search_type=None):
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
        :param search_type:
        :type search_type: int
        :return:
        :rtype: bool
        """
        # if the quality isn't one we want under any circumstances then just say no
        allowed_qualities, preferred_qualities = self.current_qualities
        log.debug(
            u'{id}: Allowed, Preferred = [ {allowed} ] [ {preferred} ] Found = [ {found} ]', {
                'id': self.series_id,
                'allowed': self.__qualities_to_string(allowed_qualities),
                'preferred': self.__qualities_to_string(preferred_qualities),
                'found': self.__qualities_to_string([quality]),
            }
        )

        if not Quality.wanted_quality(quality, allowed_qualities, preferred_qualities):
            log.debug(
                u"{id}: Ignoring found result for '{show}' {ep} with unwanted quality '{quality}'", {
                    'id': self.series_id,
                    'show': self.name,
                    'ep': episode_num(season, episode),
                    'quality': Quality.qualityStrings[quality],
                }
            )
            return False

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(
            b'SELECT '
            b'  status, '
            b'  manually_searched '
            b'FROM '
            b'  tv_episodes '
            b'WHERE '
            b'  indexer = ? '
            b'  AND showid = ? '
            b'  AND season = ? '
            b'  AND episode = ?', [self.indexer, self.series_id, season, episode])

        if not sql_results or not len(sql_results):
            log.debug(
                u'{id}: Unable to find a matching episode in database.'
                u' Ignoring found result for {show} {ep} with quality {quality}', {
                    'id': self.series_id,
                    'show': self.name,
                    'ep': episode_num(season, episode),
                    'quality': Quality.qualityStrings[quality],
                }
            )
            return False

        cur_status, cur_quality = Quality.split_composite_status(int(sql_results[0][b'status']))
        ep_status_text = statusStrings[cur_status]
        manually_searched = sql_results[0][b'manually_searched']

        # if it's one of these then we want it as long as it's in our allowed initial qualities
        if cur_status == WANTED:
            should_replace, reason = (
                True, u"Current status is 'WANTED'. Accepting result with quality '{new_quality}'".format(
                    new_quality=Quality.qualityStrings[quality]
                )
            )
        else:
            should_replace, reason = Quality.should_replace(cur_status, cur_quality, quality, allowed_qualities,
                                                            preferred_qualities, download_current_quality,
                                                            forced_search, manually_searched, search_type)

        log.debug(
            u"{id}: '{show}' {ep} status is: '{status}'."
            u" {action} result with quality '{new_quality}'."
            u" Reason: {reason}", {
                'id': self.series_id,
                'show': self.name,
                'ep': episode_num(season, episode),
                'status': ep_status_text,
                'action': 'Accepting' if should_replace else 'Ignoring',
                'new_quality': Quality.qualityStrings[quality],
                'reason': reason,
            }
        )
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
        ep_status = try_int(ep_status) or UNSET

        if backlog_mode:
            if ep_status == WANTED:
                return Overview.WANTED
            elif Quality.should_search(ep_status, self, manually_searched)[0]:
                return Overview.QUAL
            return Overview.GOOD

        if ep_status in (UNSET, UNAIRED):
            return Overview.UNAIRED
        elif ep_status in (SKIPPED, IGNORED):
            return Overview.SKIPPED
        elif ep_status in Quality.WANTED:
            return Overview.WANTED
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
            log.error(u'Could not parse episode status into a valid overview status: {status}',
                      {'status': ep_status})

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
            log.debug(u'Change all DOWNLOADED episodes to ARCHIVED for show ID: {show}',
                      {'show': self.name})
            return True
        else:
            log.debug(u'No DOWNLOADED episodes for show ID: {show}',
                      {'show': self.name})
            return False

    def pause(self):
        """Pause the series."""
        self.paused = True
        self.save_to_db()

    def unpause(self):
        """Unpause the series."""
        self.paused = False
        self.save_to_db()

    def delete(self, remove_files):
        """Delete the series."""
        try:
            app.show_queue_scheduler.action.removeShow(self, bool(remove_files))
            return True
        except CantRemoveShowException:
            pass

    def remove_images(self):
        """Remove images from cache."""
        image_cache.remove_images(self)

    def get_asset(self, asset_type):
        """Get the specified asset for this series."""
        asset_type = asset_type.lower()
        media_format = ('normal', 'thumb')[asset_type in ('bannerthumb', 'posterthumb', 'small')]

        if asset_type.startswith('banner'):
            return ShowBanner(self, media_format)
        elif asset_type.startswith('fanart'):
            return ShowFanArt(self, media_format)
        elif asset_type.startswith('poster'):
            return ShowPoster(self, media_format)
        elif asset_type.startswith('network'):
            return ShowNetworkLogo(self, media_format)
