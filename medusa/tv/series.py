# coding=utf-8

"""Series classes."""
from __future__ import unicode_literals

import copy
import datetime
import glob
import json
import logging
import os.path
import shutil
import stat
import traceback
import warnings
from builtins import map
from builtins import str
from collections import (
    OrderedDict, namedtuple
)
from itertools import chain, groupby

from medusa import (
    app,
    db,
    helpers,
    image_cache,
    network_timezones,
    notifiers,
    post_processor,
    ui,
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
    UNSET,
    WANTED,
    countryList,
    qualityPresets,
    statusStrings,
)
from medusa.helper.common import episode_num, pretty_file_size, sanitize_filename, try_int
from medusa.helper.exceptions import (
    CantRefreshShowException,
    CantRemoveShowException,
    EpisodeDeletedException,
    EpisodeNotFoundException,
    MultipleShowObjectsException,
    ShowDirectoryNotFoundException,
    ShowNotFoundException,
    ex,
)
from medusa.helpers import make_dir
from medusa.helpers.anidb import short_group_names
from medusa.helpers.externals import check_existing_shows, get_externals, load_externals_from_db
from medusa.helpers.utils import dict_to_array, safe_get, to_camel_case
from medusa.imdb import Imdb
from medusa.indexers.api import indexerApi
from medusa.indexers.config import (
    INDEXER_TVRAGE,
    STATUS_MAP,
    indexerConfig
)
from medusa.indexers.exceptions import (
    IndexerAttributeNotFound, IndexerException, IndexerSeasonNotFound, IndexerShowAlreadyInLibrary
)
from medusa.indexers.tmdb.api import Tmdb
from medusa.indexers.utils import (
    indexer_id_to_slug,
    mappings,
    reverse_mappings,
    slug_to_indexer_id
)
from medusa.logger.adapters.style import CustomBraceAdapter
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
from medusa.scene_exceptions import get_all_scene_exceptions, get_scene_exceptions, update_scene_exceptions
from medusa.scene_numbering import (
    get_scene_absolute_numbering_for_show, get_scene_numbering_for_show,
    get_xem_absolute_numbering_for_show, get_xem_numbering_for_show,
    numbering_tuple_to_dict, xem_refresh
)
from medusa.search import FORCED_SEARCH
from medusa.show.show import Show
from medusa.subtitles import (
    code_from_code,
    from_country_code_to_name,
)
from medusa.tv.base import Identifier, TV
from medusa.tv.episode import Episode
from medusa.tv.indexer import Indexer

from six import ensure_text, iteritems, itervalues, string_types, text_type, viewitems

import ttl_cache

try:
    from send2trash import send2trash
except ImportError:
    app.TRASH_REMOVE_SHOW = 0


MILLIS_YEAR_1900 = datetime.datetime(year=1900, month=1, day=1).toordinal()

log = CustomBraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class SaveSeriesException(Exception):
    """Generic exception used for adding a new series."""


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

    def get_indexer_api(self, options=None):
        """Return an indexer api for this show."""
        indexer_api = indexerApi(self.indexer.id)
        indexer_api_params = indexer_api.api_params.copy()

        if options and options.get('language') is not None:
            indexer_api_params['language'] = options['language']

        log.debug('{indexer_name}: {indexer_params!r}', {
            'indexer_name': indexerApi(self.indexer.id).name,
            'indexer_params': indexer_api_params
        })

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
        self.show_id = None
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
        # Amount of hours we want to start searching early (-1) or late (1) for new episodes
        self.airdate_offset = 0
        self.start_year = 0
        self.paused = 0
        self.air_by_date = 0
        self.subtitles = enabled_subtitles or int(app.SUBTITLES_DEFAULT)
        self.notify_list = {}
        self.dvd_order = 0
        self.lang = lang
        self._last_update_indexer = 1
        self.sports = 0
        self.anime = 0
        self.scene = 0
        self.rls_ignore_words = ''
        self.rls_require_words = ''
        self.rls_ignore_exclude = 0
        self.rls_require_exclude = 0
        self.default_ep_status = SKIPPED
        self._location = ''
        self.episodes = {}
        self._prev_aired = 0
        self._next_aired = 0
        self.release_groups = None
        self.exceptions = set()
        self.externals = {}
        self._cached_indexer_api = None
        self.plot = None
        self._show_lists = None

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

    @property
    def identifier(self):
        """Return a series identifier object."""
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
            params['language'] = self.lang
            log.debug(u'{id}: Using language from show settings: {lang}',
                      {'id': self.series_id, 'lang': self.lang})

        if self.dvd_order != 0 or dvd_order:
            params['dvdorder'] = True

        params['actors'] = actors

        params['banners'] = banners

        params['episodes'] = episodes

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
        def sanitize_network_names(str):
            dict = ({
                    u'\u010C': 'C',  # Č
                    u'\u00E1': 'a',  # á
                    u'\u00E9': 'e',  # é
                    u'\u00F1': 'n',  # ñ
                    u'\u00C9': 'e',  # É
                    u'\u05E7': 'q',  # ק
                    u'\u05E9': 's',  # ש
                    u'\u05EA': 't',  # ת
                    ' ': '-'})
            for key in dict:
                str = str.replace(key, dict[key])
            return str.lower()

        return sanitize_network_names(self.network)

    @property
    def validate_location(self):
        """Legacy call to location with a validation when ADD_SHOWS_WO_DIR is set."""
        if app.CREATE_MISSING_SHOW_DIRS or self.is_location_valid():
            return self._location
        raise ShowDirectoryNotFoundException(u'Show folder does not exist.')

    @property
    def location(self):
        """Get the show location."""
        return self._location

    @location.setter
    def location(self, value):
        old_location = os.path.normpath(self._location)
        new_location = os.path.normpath(value)

        log.debug(
            u'{indexer} {id}: Setting location: {location}', {
                'indexer': indexerApi(self.indexer).name,
                'id': self.series_id,
                'location': new_location,
            }
        )

        if new_location == old_location:
            return

        # Don't validate directory if user wants to add shows without creating a dir
        if app.ADD_SHOWS_WO_DIR or self.is_location_valid(value):
            self._location = new_location
            return

        changed_location = True
        log.info('Changing show location to: {new}', {'new': new_location})
        if not os.path.isdir(new_location):
            if app.CREATE_MISSING_SHOW_DIRS:
                log.info(u"Show directory doesn't exist, creating it")
                try:
                    os.mkdir(new_location)
                except OSError as error:
                    changed_location = False
                    log.warning(u"Unable to create the show directory '{location}'. Error: {msg}",
                                {'location': new_location, 'msg': error})
                else:
                    log.info(u'New show directory created')
                    helpers.chmod_as_parent(new_location)
            else:
                changed_location = False
                log.warning("New location '{location}' does not exist. "
                            "Enable setting '(Config - Postprocessing) Create missing show dirs'", {'location': new_location})

        # Save new location only if we changed it
        if changed_location:
            self._location = new_location

        if changed_location and os.path.isdir(new_location):
            try:
                app.show_queue_scheduler.action.refreshShow(self)
            except CantRefreshShowException as error:
                log.warning("Unable to refresh show '{show}'. Error: {error}",
                            {'show': self.name, 'error': error})

    @property
    def indexer_name(self):
        """Return the indexer name identifier. Example: tvdb."""
        return indexerConfig[self.indexer].get('identifier')

    @property
    def indexer_slug(self):
        """Return the slug name of the series. Example: tvdb1234."""
        return indexer_id_to_slug(self.indexer, self.series_id)

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
        return helpers.get_size(self.location)

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
        for x in [v for v in (self.imdb_info.get('akas') or '').split('|') if v]:
            if '::' in x:
                val, key = x.split('::')
                akas[key] = val
        return akas

    @property
    def imdb_countries(self):
        """Return country codes."""
        return [v for v in (self.imdb_info.get('country_codes') or '').split('|') if v]

    @property
    def imdb_plot(self):
        """Return series plot."""
        return self.imdb_info.get('plot') or ''

    @property
    def imdb_genres(self):
        """Return series genres."""
        return self.imdb_info.get('genres') or ''

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
    def last_update_indexer(self):
        """Return last indexer update as epoch."""
        update_date = datetime.date.fromordinal(self._last_update_indexer)
        epoch_date = update_date - datetime.date.fromtimestamp(0)
        return int(epoch_date.total_seconds())

    @property
    def prev_aired(self):
        """Return last aired episode ordinal."""
        self._prev_aired = self.prev_episode()
        return self._prev_aired

    @property
    def next_aired(self):
        """Return next aired episode ordinal."""
        today = datetime.date.today().toordinal()
        if not self._next_aired or self._next_aired < today:
            self._next_aired = self.next_episode()
        return self._next_aired

    @property
    @ttl_cache(43200.0)
    def prev_airdate(self):
        """Return last aired episode airdate."""
        return (
            sbdatetime.convert_to_setting(network_timezones.parse_date_time(self.prev_aired, self.airs, self.network))
            if self.prev_aired > MILLIS_YEAR_1900 else None
        )

    @property
    @ttl_cache(43200.0)
    def next_airdate(self):
        """Return next aired episode airdate."""
        return (
            sbdatetime.convert_to_setting(network_timezones.parse_date_time(self.next_aired, self.airs, self.network))
            if self.next_aired > MILLIS_YEAR_1900 else None
        )

    @property
    def countries(self):
        """Return countries."""
        return [v for v in (self.imdb_info.get('countries') or '').split('|') if v]

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
        img_type = image_cache.BANNER
        return image_cache.get_artwork(img_type, self)

    @property
    def aliases(self):
        """Return series aliases."""
        if self.exceptions:
            return self.exceptions

        return set(chain(*itervalues(get_all_scene_exceptions(self))))

    @aliases.setter
    def aliases(self, exceptions):
        """Set the series aliases."""
        update_scene_exceptions(self, exceptions)
        self.exceptions = set(chain(*itervalues(get_all_scene_exceptions(self))))
        build_name_cache(self)

    @property
    def aliases_to_json(self):
        """Return aliases as a dict."""
        return [{
            'season': alias.season,
            'title': alias.title,
            'custom': alias.custom
        } for alias in self.aliases]

    @property
    @ttl_cache(25200.0)  # Caching as this is requested for the /home page.
    def xem_numbering(self):
        """Return series episode xem numbering."""
        return get_xem_numbering_for_show(self, refresh_data=False)

    @property
    def xem_absolute_numbering(self):
        """Return series xem absolute numbering."""
        return get_xem_absolute_numbering_for_show(self)

    @property
    def scene_absolute_numbering(self):
        """Return series scene absolute numbering."""
        return get_scene_absolute_numbering_for_show(self)

    @property
    def scene_numbering(self):
        """Return series scene numbering."""
        return get_scene_numbering_for_show(self)

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
    def blacklist(self, group_names):
        """
        Set the anime's blacklisted release groups.

        :param group_names: A list of blacklist release group names.
        """
        self.release_groups.set_black_keywords(short_group_names(group_names))

    @property
    def whitelist(self):
        """Return the anime's whitelisted release groups."""
        bw_list = self.release_groups or BlackAndWhiteList(self)
        return bw_list.whitelist

    @whitelist.setter
    def whitelist(self, group_names):
        """
        Set the anime's whitelisted release groups.

        :param group_names: A list of whitelist release group names.
        """
        self.release_groups.set_white_keywords(short_group_names(group_names))

    @staticmethod
    def normalize_status(status):
        """Return a normalized status given current indexer status."""
        for medusa_status, indexer_mappings in viewitems(STATUS_MAP):
            if status.lower() in indexer_mappings:
                return medusa_status

        return 'Unknown'

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
        sql_selection = 'SELECT season, {0} AS number_of_episodes FROM tv_episodes ' \
                        'WHERE showid = ? GROUP BY season'.format('count(*)' if not last_airdate else 'max(airdate)')
        main_db_con = db.DBConnection()
        results = main_db_con.select(sql_selection, [self.series_id])

        return {int(x['season']): int(x['number_of_episodes']) for x in results}

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
        sql_selection = ('SELECT season, episode, (SELECT '
                         '  COUNT (*) '
                         'FROM '
                         '  tv_episodes '
                         'WHERE '
                         '  indexer = tve.indexer AND showid = tve.showid '
                         '  AND season = tve.season '
                         "  AND location != '' "
                         '  AND location = tve.location '
                         '  AND episode != tve.episode) AS share_location '
                         'FROM tv_episodes tve WHERE indexer = ? AND showid = ?'
                         )
        sql_args = [self.indexer, self.series_id]

        if season is not None:
            season = helpers.ensure_list(season)
            sql_selection += ' AND season IN (?)'
            sql_args.append(','.join(map(text_type, season)))

        if has_location:
            sql_selection += " AND location != ''"

        # need ORDER episode ASC to rename multi-episodes in order S01E01-02
        sql_selection += ' ORDER BY season ASC, episode ASC'

        main_db_con = db.DBConnection()
        results = main_db_con.select(sql_selection, sql_args)

        ep_list = []
        for cur_result in results:
            cur_ep = self.get_episode(cur_result['season'], cur_result['episode'])
            if not cur_ep:
                continue

            cur_ep.related_episodes = []
            if cur_ep.location:
                # if there is a location, check if it's a multi-episode (share_location > 0)
                # and put them in related_episodes
                if cur_result['share_location'] > 0:
                    related_eps_result = main_db_con.select(
                        'SELECT '
                        '  season, episode '
                        'FROM '
                        '  tv_episodes '
                        'WHERE '
                        '  showid = ? '
                        '  AND season = ? '
                        '  AND location = ? '
                        '  AND episode != ? '
                        'ORDER BY episode ASC',
                        [self.series_id, cur_ep.season, cur_ep.location, cur_ep.episode])
                    for cur_related_ep in related_eps_result:
                        related_ep = self.get_episode(cur_related_ep['season'], cur_related_ep['episode'])
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
                sql = (
                    'SELECT season, episode '
                    'FROM tv_episodes '
                    'WHERE indexer = ? '
                    'AND showid = ? '
                    'AND absolute_number = ? '
                    'AND season != 0'
                )
                sql_args = [self.indexer, self.series_id, absolute_number]
                log.debug(u'{id}: Season and episode lookup for {show} using absolute number {absolute}',
                          {'id': self.series_id, 'absolute': absolute_number, 'show': self.name})
            elif air_date:
                sql = (
                    'SELECT season, episode '
                    'FROM tv_episodes '
                    'WHERE indexer = ? '
                    'AND showid = ? '
                    'AND airdate = ?'
                )
                sql_args = [self.indexer, self.series_id, air_date.toordinal()]
                log.debug(u'{id}: Season and episode lookup for {show} using air date {air_date}',
                          {'id': self.series_id, 'air_date': air_date, 'show': self.name})

            sql_results = main_db_con.select(sql, sql_args) if sql else []
            if len(sql_results) == 1:
                episode = int(sql_results[0]['episode'])
                season = int(sql_results[0]['season'])
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
        if not self.rls_ignore_exclude:
            final_ignore = show_ignore + [i for i in global_ignore if i.lower() not in [r.lower() for r in show_require]]
        else:
            final_ignore = [i for i in global_ignore if i.lower() not in [r.lower() for r in show_require] and
                            i.lower() not in [sh_i.lower() for sh_i in show_ignore]]
        # If word is in global require and also in show ignore, then remove it from global requires
        # Join new global required with show require
        if not self.rls_require_exclude:
            final_require = show_require + [i for i in global_require if i.lower() not in [r.lower() for r in show_ignore]]
        else:
            final_require = [gl_r for gl_r in global_require if gl_r.lower() not in [r.lower() for r in show_ignore] and
                             gl_r.lower() not in [sh_r.lower() for sh_r in show_require]]

        ignored_words = list(OrderedDict.fromkeys(final_ignore))
        required_words = list(OrderedDict.fromkeys(final_require))

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
        if not app.CREATE_MISSING_SHOW_DIRS and not self.is_location_valid():
            log.warning("{id}: Show directory doesn't exist, skipping NFO generation",
                        {'id': self.series_id})
            return

        for metadata_provider in itervalues(app.metadata_provider_dict):
            self.__get_images(metadata_provider)
            self.__write_show_nfo(metadata_provider)

        if not show_only:
            self.__write_episode_nfos()

    def __write_episode_nfos(self):

        log.debug(u'{id}: Writing NFOs for all episodes',
                  {'id': self.series_id})

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(
            'SELECT '
            '  season, '
            '  episode '
            'FROM '
            '  tv_episodes '
            'WHERE '
            '  showid = ? '
            "  AND location != ''", [self.series_id])

        for ep_result in sql_results:
            log.debug(
                u'{id}: Retrieving/creating episode {ep}', {
                    'id': self.series_id,
                    'ep': episode_num(ep_result['season'], ep_result['episode'])
                }
            )
            cur_ep = self.get_episode(ep_result['season'], ep_result['episode'])
            if not cur_ep:
                continue

            cur_ep.create_meta_files()

    def update_metadata(self):
        """Update show metadata files."""
        if not app.CREATE_MISSING_SHOW_DIRS and not self.is_location_valid():
            log.warning(u"{id}: Show directory doesn't exist, skipping NFO update",
                        {'id': self.series_id})
            return

        self.__update_show_nfo()

    def __update_show_nfo(self):

        result = False

        log.info(u'{id}: Updating NFOs for show with new indexer info',
                 {'id': self.series_id})
        # You may only call .values() on metadata_provider_dict! As on values() call the indexer_api attribute
        # is reset. This will prevent errors, when using multiple indexers and caching.
        for cur_provider in itervalues(app.metadata_provider_dict):
            result = cur_provider.update_show_indexer_metadata(self) or result

        return result

    def load_episodes_from_dir(self):
        """Find all media files in the show folder and create episodes for as many as possible."""
        if not app.CREATE_MISSING_SHOW_DIRS and not self.is_location_valid():
            log.warning(u"{id}: Show directory doesn't exist, not loading episodes from disk",
                        {'id': self.series_id})
            return

        log.debug(u'{id}: Loading all episodes from the show directory: {location}',
                  {'id': self.series_id, 'location': self.location})

        # get file list
        media_files = helpers.list_media_files(self.location)
        log.debug(u'{id}: Found files: {media_files}',
                  {'id': self.series_id, 'media_files': media_files})

        # create TVEpisodes from each media file (if possible)
        sql_l = []
        for media_file in media_files:
            cur_episode = None

            log.debug(u'{id}: Creating episode from: {location}',
                      {'id': self.series_id, 'location': media_file})
            try:
                cur_episode = self.make_ep_from_file(os.path.join(self.location, media_file))
            except (ShowNotFoundException, EpisodeNotFoundException) as error:
                log.warning(
                    u'{id}: Episode {location} returned an exception {error_msg}', {
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
            sql = ('SELECT '
                   '  season, episode, showid, show_name, tv_shows.show_id, tv_shows.indexer '
                   'FROM '
                   '  tv_episodes '
                   'JOIN '
                   '  tv_shows '
                   'WHERE '
                   '  tv_episodes.showid = tv_shows.indexer_id'
                   '  AND tv_episodes.indexer = tv_shows.indexer'
                   '  AND tv_shows.indexer = ? AND tv_shows.indexer_id = ?')
            if seasons:
                sql += ' AND season IN (%s)' % ','.join('?' * len(seasons))
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

            cur_season = int(cur_result['season'])
            cur_episode = int(cur_result['episode'])
            cur_indexer = int(cur_result['indexer'])
            cur_show_id = int(cur_result['showid'])
            cur_show_name = text_type(cur_result['show_name'])

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
                        u'{id}: {error_msg!r} (unaired/deleted) in the indexer {indexer} for {show}.'
                        u' Removing existing records from database', {
                            'id': cur_show_id,
                            'error_msg': error,
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
        self._last_update_indexer = datetime.date.today().toordinal()
        log.debug(u'{id}: Saving indexer changes to database',
                  {'id': self.series_id})
        self.save_to_db()

        return scanned_eps

    def _save_externals_to_db(self):
        """Save the indexers external id's to the db."""
        sql_l = []

        for external in self.externals:
            if external in reverse_mappings and self.externals[external]:
                sql_l.append(['INSERT OR IGNORE '
                              'INTO indexer_mapping (indexer_id, indexer, mindexer_id, mindexer) '
                              'VALUES (?,?,?,?)',
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
            log.debug(u'{indexer_id}: {error}',
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
                cur_ep.update_status_quality(filepath)

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
            'SELECT *'
            ' FROM tv_shows'
            ' WHERE indexer = ?'
            ' AND indexer_id = ?',
            [self.indexer, self.series_id]
        )

        if not sql_results:
            log.info(u'{id}: Unable to find the show in the database',
                     {'id': self.series_id})
            return
        else:
            self.show_id = int(sql_results[0]['show_id'] or 0)
            self.indexer = int(sql_results[0]['indexer'] or 0)

            if not self.name:
                self.name = sql_results[0]['show_name']
            if not self.network:
                self.network = sql_results[0]['network']
            if not self.genre:
                self.genre = sql_results[0]['genre']
            if not self.classification:
                self.classification = sql_results[0]['classification']

            self.runtime = sql_results[0]['runtime']

            self.status = sql_results[0]['status']
            if self.status is None:
                self.status = 'Unknown'

            self.airs = sql_results[0]['airs']
            if self.airs is None or not network_timezones.test_timeformat(self.airs):
                self.airs = ''

            self.start_year = int(sql_results[0]['startyear'] or 0)
            self.air_by_date = int(sql_results[0]['air_by_date'] or 0)
            self.anime = int(sql_results[0]['anime'] or 0)
            self.sports = int(sql_results[0]['sports'] or 0)
            self.scene = int(sql_results[0]['scene'] or 0)
            self.subtitles = int(sql_results[0]['subtitles'] or 0)
            self.notify_list = json.loads(sql_results[0]['notify_list'] or '{}')
            self.dvd_order = int(sql_results[0]['dvdorder'] or 0)
            self.quality = int(sql_results[0]['quality'] or Quality.NA)
            self.season_folders = int(not (sql_results[0]['flatten_folders'] or 0))  # TODO: Rename this in the DB
            self.paused = int(sql_results[0]['paused'] or 0)
            self._location = sql_results[0]['location']  # skip location validation

            if not self.lang:
                self.lang = sql_results[0]['lang']

            self._last_update_indexer = sql_results[0]['last_update_indexer']

            self.rls_ignore_words = sql_results[0]['rls_ignore_words']
            self.rls_require_words = sql_results[0]['rls_require_words']
            self.rls_ignore_exclude = sql_results[0]['rls_ignore_exclude']
            self.rls_require_exclude = sql_results[0]['rls_require_exclude']

            self.default_ep_status = int(sql_results[0]['default_ep_status'] or SKIPPED)

            if not self.imdb_id:
                self.imdb_id = sql_results[0]['imdb_id']

            self.plot = sql_results[0]['plot']
            self.airdate_offset = int(sql_results[0]['airdate_offset'] or 0)

            self.release_groups = BlackAndWhiteList(self)

            # Load external id's from indexer_mappings table.
            self.externals = load_externals_from_db(self.indexer, self.series_id)

            self._show_lists = sql_results[0]['show_lists']

        # Get IMDb_info from database
        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(
            'SELECT * '
            'FROM imdb_info'
            ' WHERE indexer = ?'
            ' AND indexer_id = ?',
            [self.indexer, self.series_id]
        )

        if not sql_results:
            log.info(u'{id}: Unable to find IMDb info in the database: {show}',
                     {'id': self.series_id, 'show': self.name})
            return
        else:
            self.imdb_info = sql_results[0]

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
        imdb_api = Imdb()

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
            try:
                country_codes = Tmdb().get_show_country_codes(tmdb_id)
            except IndexerException as error:
                log.info(u'Unable to get country codes from TMDB. Error: {error}',
                         {'error': error})
                country_codes = None

            if country_codes:
                countries = (from_country_code_to_name(country) for country in country_codes)
                self.imdb_info['countries'] = '|'.join([_f for _f in countries if _f])
                self.imdb_info['country_codes'] = '|'.join(country_codes).lower()

        # Make sure these always have a value
        self.imdb_info['countries'] = self.imdb_info.get('countries') or ''
        self.imdb_info['country_codes'] = self.imdb_info.get('country_codes') or ''

        try:
            imdb_info = imdb_api.get_title(self.imdb_id)
        except LookupError as error:
            log.warning(u'{id}: IMDbPie error while loading show info: {error}',
                        {'id': self.series_id, 'error': error})
            imdb_info = None

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

    def check_existing(self):
        """Check if we can already find this show in our current showList."""
        try:
            check_existing_shows(self.identifier.get_indexer_api(), self.identifier.indexer.id)
        except IndexerShowAlreadyInLibrary as error:
            log.warning(
                'Could not add the show {series}, as it already is in your library.'
                'Error: {error}',
                {'series': self.name, 'error': error}
            )
            ui.notifications.error(
                'Unable to add show',
                'reason: {0}'.format(error)
            )
            raise SaveSeriesException(
                'Unable to add show',
                'reason: {0}'.format(error)
            )

    def configure(self, queue_item):
        """Configure series."""
        # Let's try to create the show Dir if it's not provided. This way we force the show dir
        # to build using the Indexers provided series name
        options = queue_item.options
        show_dir = queue_item.show_dir
        root_dir = queue_item.root_dir or app.ROOT_DIRS[int(app.ROOT_DIRS[0]) + 1] if len(app.ROOT_DIRS) > 0 else None

        if not show_dir and root_dir:
            # I don't think we need to check this. We just create the folder after we already queried the indexer.
            # show_name = get_showname_from_indexer(self.indexer, self.indexer_id, self.lang)
            if self.name:
                show_dir = os.path.join(root_dir, sanitize_filename(self.name))

                # don't create show dir if config says not to
                if app.ADD_SHOWS_WO_DIR:
                    log.info('Skipping initial creation of {path} due to config.ini setting',
                             {'path': show_dir})
                else:
                    dir_exists = make_dir(show_dir)
                    if not dir_exists:
                        log.error("Unable to create the folder {0}, can't add the show", show_dir)
                        ui.notifications.error(
                            'Unable to create folder',
                            'folder: {0}'.format(show_dir)
                        )
                        return

                    helpers.chmod_as_parent(show_dir)
            else:
                log.error("Unable to get a show {0}, can't add the show", show_dir)
                return

        if show_dir:
            self.location = ensure_text(show_dir)

        self.subtitles = options['subtitles'] if options.get('subtitles') is not None else app.SUBTITLES_DEFAULT

        if options.get('quality'):
            self.qualities_allowed = options['quality']['allowed']
            self.qualities_preferred = options['quality']['preferred']
        else:
            self.qualities_allowed, self.qualities_preferred = Quality.split_quality(int(app.QUALITY_DEFAULT))

        self.season_folders = options['season_folders'] if options.get('season_folders') is not None \
            else app.SEASON_FOLDERS_DEFAULT
        self.anime = options['anime'] if options.get('anime') is not None else app.ANIME_DEFAULT
        self.scene = options['scene'] if options.get('scene') is not None else app.SCENE_DEFAULT
        self.paused = options['paused'] if options.get('paused') is not None else False
        self.lang = options['language'] if options.get('language') is not None else app.INDEXER_DEFAULT_LANGUAGE
        self.show_lists = options['show_lists'] if options.get('show_lists') is not None else app.SHOWLISTS_DEFAULT

        if options.get('default_status') is not None:
            # set up default new/missing episode status
            log.info(
                'Setting all previously aired episodes to the specified status: {status}',
                {'status': statusStrings[options['default_status']]}
            )
            self.default_ep_status = options['default_status']
        else:
            self.default_ep_status = app.STATUS_DEFAULT

        if self.anime:
            self.release_groups = BlackAndWhiteList(self)
            if options.get('release') is not None:
                if options['release']['blacklist']:
                    self.release_groups.set_black_keywords(options['release']['blacklist'])
                if options['release']['whitelist']:
                    self.release_groups.set_white_keywords(options['release']['whitelist'])

    def prev_episode(self):
        """Return the last aired episode air date.

        :return:
        :rtype: datetime.date
        """
        log.debug(u'{id}: Finding the episode which aired last', {'id': self.series_id})

        today = datetime.date.today().toordinal()
        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(
            'SELECT '
            '  airdate,'
            '  season,'
            '  episode '
            'FROM '
            '  tv_episodes '
            'WHERE '
            '  indexer = ?'
            '  AND showid = ? '
            '  AND airdate < ? '
            '  AND status <> ? '
            'ORDER BY'
            '  airdate '
            'DESC LIMIT 1',
            [self.indexer, self.series_id, today, UNAIRED])

        if sql_results is None or len(sql_results) == 0:
            log.debug(u'{id}: Could not find a previous aired episode', {'id': self.series_id})
        else:
            log.debug(
                u'{id}: Found previous aired episode number {ep}', {
                    'id': self.series_id,
                    'ep': episode_num(sql_results[0]['season'], sql_results[0]['episode'])
                }
            )
            self._prev_aired = sql_results[0]['airdate']

        return self._prev_aired

    def next_episode(self):
        """Return the next episode air date.

        :return:
        :rtype: datetime.date
        """
        log.debug(u'{id}: Finding the episode which airs next', {'id': self.series_id})

        today = datetime.date.today().toordinal()
        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(
            'SELECT '
            '  airdate,'
            '  season,'
            '  episode '
            'FROM '
            '  tv_episodes '
            'WHERE '
            '  indexer = ?'
            '  AND showid = ? '
            '  AND airdate >= ? '
            'ORDER BY'
            '  airdate '
            'ASC LIMIT 1',
            [self.indexer, self.series_id, today])

        if sql_results is None or len(sql_results) == 0:
            log.debug(u'{id}: Could not find a next episode', {'id': self.series_id})
        else:
            log.debug(
                u'{id}: Found episode {ep}', {
                    'id': self.series_id,
                    'ep': episode_num(sql_results[0]['season'], sql_results[0]['episode']),
                }
            )
            self._next_aired = sql_results[0]['airdate']

        return self._next_aired

    def delete_show(self, full=False):
        """Delete the tv show from the database.

        :param full:
        :type full: bool
        """
        sql_l = [['DELETE FROM tv_episodes WHERE indexer = ? AND showid = ?', [self.indexer, self.series_id]],
                 ['DELETE FROM tv_shows WHERE indexer = ? AND indexer_id = ?', [self.indexer, self.series_id]],
                 ['DELETE FROM imdb_info WHERE indexer = ? AND indexer_id = ?', [self.indexer, self.series_id]],
                 ['DELETE FROM xem_refresh WHERE indexer = ? AND indexer_id = ?', [self.indexer, self.series_id]],
                 ['DELETE FROM scene_numbering WHERE indexer = ? AND indexer_id = ?', [self.indexer, self.series_id]]]

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
                self.validate_location  # Let's get the exception out of the way asap.
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
                         {'id': self.series_id, 'action': action, 'location': self.location})

            except ShowDirectoryNotFoundException:
                log.warning(u'{id}: Show folder {location} does not exist. No need to {action}',
                            {'id': self.series_id, 'action': action, 'location': self.location})
            except OSError as error:
                log.warning(
                    u'{id}: Unable to {action} {location}. Error: {error_msg}', {
                        'id': self.series_id,
                        'action': action,
                        'location': self.location,
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

    def sync_trakt(self):
        """Sync trakt episodes if trakt is enabled."""
        if app.USE_TRAKT:
            # if there are specific episodes that need to be added by trakt
            app.trakt_checker_scheduler.action.manage_new_show(self)

            # add show to trakt.tv library
            if app.TRAKT_SYNC:
                app.trakt_checker_scheduler.action.add_show_trakt_library(self)

            if app.TRAKT_SYNC_WATCHLIST:
                log.info('updating trakt watchlist')
                notifiers.trakt_notifier.update_watchlist(show_obj=self)

    def add_scene_numbering(self):
        """
        Add XEM data to DB for show.

        Warn the user if an episode number mapping is available on thexem.
        Only use this method, through show_queue.QueueItemAdd().
        """
        xem_refresh(self, force=True)

        # check if show has XEM mapping so we can determine if searches
        # should go by scene numbering or indexer numbering. Warn the user.
        if not self.scene and get_xem_numbering_for_show(self):
            log.warning(
                '{id}: while adding the show {title} we noticed thexem.de has an episode mapping available'
                '\nyou might want to consider enabling the scene option for this show.',
                {'id': self.series_id, 'title': self.name}
            )
            ui.notifications.message(
                'consider enabling scene for this show',
                'for show {title} you might want to consider enabling the scene option'
                .format(title=self.name)
            )

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
            'SELECT '
            '  season, episode, location '
            'FROM '
            '  tv_episodes '
            'WHERE '
            '  indexer = ?'
            '  AND showid = ? '
            "  AND location != ''", [self.indexer, self.series_id])

        sql_l = []
        for ep in sql_results:
            cur_loc = os.path.normpath(ep['location'])
            season = int(ep['season'])
            episode = int(ep['episode'])

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
                        if cur_ep.location and cur_ep.status in [ARCHIVED, DOWNLOADED, IGNORED, SKIPPED]:

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
                        cur_ep.release_group = ''
                        cur_ep.is_proper = False
                        cur_ep.version = 0
                        cur_ep.manually_searched = False

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

    @property
    def show_queue_status(self):
        """Return a status the show checking the queue scheduler if there is currently an action queued or active."""
        return [
            {'action': 'isBeingAdded',
             'active': app.show_queue_scheduler.action.isBeingAdded(self),
             'message': 'This show is in the process of being downloaded - the info below is incomplete'},
            {'action': 'isBeingUpdated',
             'active': app.show_queue_scheduler.action.isBeingUpdated(self),
             'message': 'The information on this page is in the process of being updated'},
            {'action': 'isBeingRefreshed',
             'active': app.show_queue_scheduler.action.isBeingRefreshed(self),
             'message': 'The episodes below are currently being refreshed from disk'},
            {'action': 'isBeingSubtitled',
             'active': app.show_queue_scheduler.action.isBeingSubtitled(self),
             'message': 'Currently downloading subtitles for this show'},
            {'action': 'isInRefreshQueue',
             'active': app.show_queue_scheduler.action.isInRefreshQueue(self),
             'message': 'This show is queued to be refreshed'},
            {'action': 'isInUpdateQueue',
             'active': app.show_queue_scheduler.action.isInUpdateQueue(self),
             'message': 'This show is queued and awaiting an update'},
            {'action': 'isInSubtitleQueue',
             'active': app.show_queue_scheduler.action.isInSubtitleQueue(self),
             'message': 'This show is queued and awaiting subtitles download'},
        ]

    def save_to_db(self):
        """Save to database."""
        if not self.dirty:
            return

        log.debug(u'{id}: Saving to database: {show}',
                  {'id': self.series_id, 'show': self.name})

        control_value_dict = {'indexer': self.indexer, 'indexer_id': self.series_id}
        new_value_dict = {'show_name': self.name,
                          'location': self.location,  # skip location validation
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
                          'notify_list': json.dumps(self.notify_list),
                          'dvdorder': self.dvd_order,
                          'startyear': self.start_year,
                          'lang': self.lang,
                          'imdb_id': self.imdb_id,
                          'last_update_indexer': self._last_update_indexer,
                          'rls_ignore_words': self.rls_ignore_words,
                          'rls_require_words': self.rls_require_words,
                          'rls_ignore_exclude': self.rls_ignore_exclude,
                          'rls_require_exclude': self.rls_require_exclude,
                          'default_ep_status': self.default_ep_status,
                          'plot': self.plot,
                          'airdate_offset': self.airdate_offset,
                          'show_lists': self._show_lists}

        main_db_con = db.DBConnection()
        main_db_con.upsert('tv_shows', new_value_dict, control_value_dict)

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
        to_return += 'location: ' + self.location + '\n'  # skip location validation
        if self.network:
            to_return += 'network: ' + self.network + '\n'
        if self.airs:
            to_return += 'airs: ' + self.airs + '\n'
        if self.airdate_offset != 0:
            to_return += 'airdate_offset: ' + str(self.airdate_offset) + '\n'
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
        to_return += u'location: {0}\n'.format(self.location)  # skip location validation
        if self.network:
            to_return += u'network: {0}\n'.format(self.network)
        if self.airs:
            to_return += u'airs: {0}\n'.format(self.airs)
        if self.airdate_offset != 0:
            to_return += 'airdate_offset: {0}\n'.format(self.airdate_offset)
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

    def to_json(self, detailed=False, episodes=False):
        """
        Return JSON representation.

        :param detailed: Append seasons & episodes data as well
        """
        data = {}
        data['id'] = {}
        data['id'][self.indexer_name] = self.series_id
        data['id']['imdb'] = text_type(self.imdb_id)
        data['id']['slug'] = self.identifier.slug
        data['id']['trakt'] = self.externals.get('trakt_id')
        data['title'] = self.name
        data['indexer'] = self.indexer_name  # e.g. tvdb
        data['network'] = self.network  # e.g. CBS
        data['type'] = self.classification  # e.g. Scripted
        data['status'] = self.status  # e.g. Continuing
        data['airs'] = self.airs  # e.g. Thursday 8:00 PM
        data['airsFormatValid'] = network_timezones.test_timeformat(self.airs)
        data['language'] = self.lang
        data['showType'] = self.show_type  # e.g. anime, sport, series
        data['imdbInfo'] = {to_camel_case(k): v for k, v in viewitems(self.imdb_info)}
        data['year'] = {}
        data['year']['start'] = self.imdb_year or self.start_year
        data['prevAirDate'] = self.prev_airdate.isoformat() if self.prev_airdate else None
        data['nextAirDate'] = self.next_airdate.isoformat() if self.next_airdate else None
        data['lastUpdate'] = datetime.date.fromordinal(self._last_update_indexer).isoformat()
        data['runtime'] = self.imdb_runtime or self.runtime
        data['genres'] = self.genres
        data['rating'] = {}
        if self.imdb_rating and self.imdb_votes:
            data['rating']['imdb'] = {}
            data['rating']['imdb']['rating'] = self.imdb_rating
            data['rating']['imdb']['votes'] = self.imdb_votes

        data['classification'] = self.imdb_certificates
        data['cache'] = {}
        data['cache']['poster'] = self.poster
        data['cache']['banner'] = self.banner
        data['countries'] = self.countries  # e.g. ['ITALY', 'FRANCE']
        data['countryCodes'] = self.imdb_countries  # e.g. ['it', 'fr']
        data['plot'] = self.plot or self.imdb_plot
        data['config'] = {}
        data['config']['location'] = self.location
        data['config']['locationValid'] = self.is_location_valid()
        data['config']['qualities'] = {}
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
        data['config']['aliases'] = self.aliases_to_json
        data['config']['release'] = {}
        data['config']['release']['ignoredWords'] = self.release_ignore_words
        data['config']['release']['requiredWords'] = self.release_required_words
        data['config']['release']['ignoredWordsExclude'] = bool(self.rls_ignore_exclude)
        data['config']['release']['requiredWordsExclude'] = bool(self.rls_require_exclude)
        data['config']['airdateOffset'] = self.airdate_offset
        data['config']['showLists'] = self.show_lists

        # Moved from detailed, as the home page, needs it to display the Xem icon.
        data['xemNumbering'] = numbering_tuple_to_dict(self.xem_numbering)

        # These are for now considered anime-only options
        if self.is_anime:
            bw_list = self.release_groups or BlackAndWhiteList(self)
            data['config']['release']['blacklist'] = bw_list.blacklist
            data['config']['release']['whitelist'] = bw_list.whitelist

        # Make sure these are at least defined
        data['sceneAbsoluteNumbering'] = []
        data['xemAbsoluteNumbering'] = []
        data['sceneNumbering'] = []

        if detailed:
            data['size'] = self.size
            data['showQueueStatus'] = self.show_queue_status
            data['sceneAbsoluteNumbering'] = dict_to_array(self.scene_absolute_numbering, key='absolute', value='sceneAbsolute')
            if self.is_scene:
                data['xemAbsoluteNumbering'] = dict_to_array(self.xem_absolute_numbering, key='absolute', value='sceneAbsolute')
                data['sceneNumbering'] = numbering_tuple_to_dict(self.scene_numbering)
            data['seasonCount'] = dict_to_array(self.get_all_seasons(), key='season', value='episodeCount')

        if episodes:
            all_episodes = self.get_all_episodes()
            data['episodeCount'] = len(all_episodes)
            last_episode = all_episodes[-1] if all_episodes else None
            if self.status == 'Ended' and last_episode and last_episode.airdate:
                data['year']['end'] = last_episode.airdate.year

            data['seasons'] = [{'episodes': list(v), 'season': season}
                               for season, v in
                               groupby([ep.to_json() for ep in all_episodes], lambda item: item['season'])]

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

    @property
    def show_lists(self):
        """
        Return series show lists.

        :returns: A list of show categories.
        """
        return self._show_lists.split(',') if self._show_lists else ['series']

    @show_lists.setter
    def show_lists(self, show_lists):
        """
        Configure the show lists, for this show.

        self._show_lists is stored as a comma separated string.
        :param show_lists: A list of show categories.
        """
        self._show_lists = ','.join(show_lists) if show_lists else 'series'

    def get_all_possible_names(self, season=-1):
        """Get every possible variation of the name for a particular show.

        Includes indexer name, and any scene exception names, and country code
        at the end of the name (e.g. "Show Name (AU)".

        show: a Series object that we should get the names of
        :returns: all possible show names
        """
        show_names = {exception.title for exception in get_scene_exceptions(self, season)}
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

    def want_episode(self, season, episode, quality,
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
        forced_search = True if search_type == FORCED_SEARCH else False

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
            'SELECT '
            '  status, quality, '
            '  manually_searched '
            'FROM '
            '  tv_episodes '
            'WHERE '
            '  indexer = ? '
            '  AND showid = ? '
            '  AND season = ? '
            '  AND episode = ?', [self.indexer, self.series_id, season, episode])

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

        cur_status, cur_quality = int(sql_results[0]['status'] or UNSET), int(sql_results[0]['quality'] or Quality.NA)
        ep_status_text = statusStrings[cur_status]
        manually_searched = sql_results[0]['manually_searched']

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
            u' Reason: {reason}', {
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

    def want_episodes(self, season, episodes, quality,
                      download_current_quality=False, search_type=None):
        """Whether one or more episodes are wanted based on their quality and status.

        Args:
            season (int): Season number of the episode(s)
            episodes (int): Episode number(s)
            quality (int): Quality of the episode(s)
            download_current_quality (bool, optional): Accept the same quality. Defaults to False.
            search_type (SearchType, optional): The type used to search. Defaults to None.

        Returns:
            bool: Whether the episode(s) are wanted.

        """
        wanted_episodes = [
            self.want_episode(season, episode, quality,
                              download_current_quality=download_current_quality,
                              search_type=search_type)
            for episode in episodes
        ]

        if all(wanted_episodes):
            log.info('Episodes {eps} of season {sea} are needed with this quality for {show}',
                     {'eps': episodes, 'sea': season, 'show': self.name})
            return True

        elif not any(wanted_episodes):
            log.debug('No episodes {eps} of season {sea} are needed with this quality for {show}',
                      {'eps': episodes, 'sea': season, 'show': self.name})
            return False
        else:
            # If there are 2 candidates and only one is wanted it
            # is likely a single episode released as multi episode
            if len(wanted_episodes) == 2:
                log.info('Only 1 of episodes {eps} of season {sea} are needed with this quality for {show}',
                         {'eps': episodes, 'sea': season, 'show': self.name})
                return True
            else:
                log.debug(u'Only some episodes {eps} of season {sea} are needed with this quality for {show}',
                          {'eps': episodes, 'sea': season, 'show': self.name})
                return False

    def get_overview(self, ep_status, ep_quality, backlog_mode=False, manually_searched=False):
        """Get the Overview status from the Episode status.

        :param ep_status: an Episode status
        :type ep_status: int
        :param ep_quality: an Episode quality
        :type ep_quality: int
        :param backlog_mode: if we should return overview for backlogOverview
        :type backlog_mode: boolean
        :param manually_searched: if episode was manually searched
        :type manually_searched: boolean
        :return: an Overview status
        :rtype: int
        """
        ep_status = int(ep_status)
        ep_quality = int(ep_quality)

        if backlog_mode:
            if ep_status == WANTED:
                return Overview.WANTED
            elif Quality.should_search(ep_status, ep_quality, self, manually_searched)[0]:
                return Overview.QUAL
            return Overview.GOOD

        if ep_status in (UNSET, UNAIRED):
            return Overview.UNAIRED
        elif ep_status in (SKIPPED, IGNORED):
            return Overview.SKIPPED
        elif ep_status == WANTED:
            return Overview.WANTED
        elif ep_status == ARCHIVED:
            return Overview.GOOD
        elif ep_status == FAILED:
            return Overview.WANTED
        elif ep_status == SNATCHED:
            return Overview.SNATCHED
        elif ep_status == SNATCHED_PROPER:
            return Overview.SNATCHED_PROPER
        elif ep_status == SNATCHED_BEST:
            return Overview.SNATCHED_BEST
        elif ep_status == DOWNLOADED:
            if Quality.should_search(ep_status, ep_quality, self, manually_searched)[0]:
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
                if Quality.should_search(ep_obj.status, ep_obj.quality, show_obj, ep_obj.manually_searched)[0]:
                    new_backlogged += 1
                if Quality.should_search(ep_obj.status, ep_obj.quality, self, ep_obj.manually_searched)[0]:
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
                if ep_obj.status == DOWNLOADED:
                    if final_status_only and Quality.should_search(ep_obj.status, ep_obj.quality, self,
                                                                   ep_obj.manually_searched)[0]:
                        continue
                    ep_obj.status = ARCHIVED
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

    def get_wanted_segments(self, from_date=None):
        """Get episodes that should be backlog searched."""
        wanted = {}
        if self.paused:
            log.debug(u'Skipping backlog for {0} because the show is paused', self.name)
            return wanted

        log.debug(u'Seeing if we need anything from {0}', self.name)

        from_date = from_date or datetime.date.fromordinal(1)

        con = db.DBConnection()
        sql_results = con.select(
            'SELECT status, quality, season, episode, manually_searched '
            'FROM tv_episodes '
            'WHERE airdate > ?'
            ' AND indexer = ? '
            ' AND showid = ?',
            [from_date.toordinal(), self.indexer, self.series_id]
        )

        # check through the list of statuses to see if we want any
        for episode in sql_results:
            cur_status, cur_quality = int(episode['status'] or UNSET), int(episode['quality'] or Quality.NA)
            should_search, should_search_reason = Quality.should_search(
                cur_status, cur_quality, self, episode['manually_searched']
            )
            if not should_search:
                continue
            log.debug(
                u'Found needed backlog episodes for: {show} {ep}. Reason: {reason}', {
                    'show': self.name,
                    'ep': episode_num(episode['season'], episode['episode']),
                    'reason': should_search_reason,
                }
            )
            ep_obj = self.get_episode(episode['season'], episode['episode'])

            if ep_obj.season not in wanted:
                wanted[ep_obj.season] = [ep_obj]
            else:
                wanted[ep_obj.season].append(ep_obj)

        return wanted

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

    def get_asset(self, asset_type, fallback=True):
        """Get the specified asset for this series."""
        asset_type = asset_type.lower()
        media_format = ('normal', 'thumb')[asset_type in ('bannerthumb', 'posterthumb', 'small')]

        if asset_type.startswith('banner'):
            return ShowBanner(self, media_format, fallback)
        elif asset_type.startswith('fanart'):
            return ShowFanArt(self, media_format, fallback)
        elif asset_type.startswith('poster'):
            return ShowPoster(self, media_format, fallback)
        elif asset_type.startswith('network'):
            return ShowNetworkLogo(self, media_format, fallback)
