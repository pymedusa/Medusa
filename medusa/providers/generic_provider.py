# coding=utf-8

"""Provider code for Generic Provider."""

from __future__ import unicode_literals

import logging
import re
from builtins import map
from builtins import object
from builtins import str
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta
from itertools import chain
from os.path import join

from dateutil import parser, tz

from medusa import (
    app,
    config,
    scene_exceptions,
    tv,
    ui,
)
from medusa.classes import (
    SearchResult,
)
from medusa.common import (
    MULTI_EP_RESULT,
    Quality,
    SEASON_RESULT,
    USER_AGENT,
)
from medusa.db import DBConnection
from medusa.helper.common import (
    sanitize_filename,
)
from medusa.helpers import (
    download_file,
)
from medusa.indexers.indexer_config import INDEXER_TVDBV2
from medusa.logger.adapters.style import BraceAdapter
from medusa.name_parser.parser import (
    InvalidNameException,
    InvalidShowException,
    NameParser,
)
from medusa.search import PROPER_SEARCH
from medusa.session.core import MedusaSafeSession
from medusa.show.show import Show

from pytimeparse import parse

from requests.utils import add_dict_to_cookiejar, dict_from_cookiejar

from six import itervalues

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

# Keep a list of per provider of recent provider search results
recent_results = {}


class GenericProvider(object):
    """Generic provider."""

    NZB = 'nzb'
    TORRENT = 'torrent'

    def __init__(self, name):
        """Initialize the class."""
        self.name = name

        self.anime_only = False
        self.bt_cache_urls = [
            'http://reflektor.karmorra.info/torrent/{info_hash}.torrent',
            'https://torrent.cd/torrents/download/{info_hash}/.torrent',
            'https://asnet.pw/download/{info_hash}/',
            'http://p2pdl.com/download/{info_hash}',
            'http://itorrents.org/torrent/{info_hash}.torrent',
            'http://thetorrent.org/torrent/{info_hash}.torrent',
            'https://cache.torrentgalaxy.org/get/{info_hash}',
        ]
        self.cache = tv.Cache(self)
        self.enable_backlog = False
        self.enable_manualsearch = False
        self.enable_daily = False
        self.enabled = False
        self.headers = {'User-Agent': USER_AGENT}
        self.proper_strings = ['PROPER|REPACK|REAL|RERIP']
        self.provider_type = None
        self.public = False
        self.search_fallback = False
        self.search_mode = None
        self.session = MedusaSafeSession(cloudflare=True)
        self.session.headers.update(self.headers)
        self.series = None
        self.supports_absolute_numbering = False
        self.supports_backlog = True
        self.url = ''
        self.urls = {}

        # Ability to override the search separator. As for example anizb is using '*' instead of space.
        self.search_separator = ' '
        self.season_templates = (
            'S{season:0>2}',  # example: 'Series.Name.S03'
        )

        # Use and configure the attribute enable_cookies to show or hide the cookies input field per provider
        self.enable_cookies = False
        self.cookies = ''

        # Paramaters for reducting the daily search results parsing
        self.max_recent_items = 5
        self.stop_at = 3

        # Delay downloads
        self.enable_search_delay = False
        self.search_delay = 480  # minutes

    @classmethod
    def kind(cls):
        """Return the name of the current class."""
        return cls.__name__

    def download_result(self, result):
        """Download result from provider."""
        if not self.login():
            return False

        urls, filename = self._make_url(result)

        for url in urls:
            if 'NO_DOWNLOAD_NAME' in url:
                continue

            if url.startswith('http'):
                self.headers.update({
                    'Referer': '/'.join(url.split('/')[:3]) + '/'
                })

            log.info('Downloading {result} from {provider} at {url}',
                     {'result': result.name, 'provider': self.name, 'url': url})

            verify = False if self.public else None

            if download_file(url, filename, session=self.session, headers=self.headers,
                             verify=verify):

                if self._verify_download(filename):
                    log.info('Saved {result} to {location}',
                             {'result': result.name, 'location': filename})
                    return True

        log.warning('Failed to download any results for {result}',
                    {'result': result.name})

        return False

    def _make_url(self, result):
        """Return url if result is a magnet link."""
        urls = []
        filename = ''

        if not result or not result.url:
            return urls, filename

        urls = [result.url]
        result_name = sanitize_filename(result.name)

        # TODO: Remove this in future versions, kept for the warning
        # Some NZB providers (e.g. Jackett) can also download torrents
        # A similar check is performed for NZB splitting in medusa/search/core.py @ search_providers()
        if (result.url.endswith(GenericProvider.TORRENT) or
                result.url.startswith('magnet:')) and self.provider_type == GenericProvider.NZB:
            filename = join(app.TORRENT_DIR, result_name + '.torrent')
            log.warning('Using Jackett providers as Newznab providers is deprecated!'
                        ' Switch them to Jackett providers as soon as possible.')
        else:
            filename = join(self._get_storage_dir(), result_name + '.' + self.provider_type)

        return urls, filename

    def _verify_download(self, file_name=None):
        return True

    def get_content(self, url, params=None, timeout=30, **kwargs):
        """Retrieve the torrent/nzb content."""
        return self.session.get_content(url, params=params, timeout=timeout, **kwargs)

    def find_propers(self, proper_candidates):
        """Find propers in providers."""
        results = []

        for proper_candidate in proper_candidates:
            series_obj = Show.find_by_id(app.showList, proper_candidate[b'indexer'], proper_candidate[b'showid'])

            if series_obj:
                self.series = series_obj
                episode_obj = series_obj.get_episode(proper_candidate[b'season'], proper_candidate[b'episode'])

                for term in self.proper_strings:
                    search_strings = self._get_episode_search_strings(episode_obj, add_string=term)

                    for item in self.search(search_strings[0], ep_obj=episode_obj):
                        search_result = self.get_result()
                        results.append(search_result)

                        search_result.name, search_result.url = self._get_title_and_url(item)
                        search_result.seeders, search_result.leechers = self._get_result_info(item)
                        search_result.size = self._get_size(item)
                        search_result.pubdate = self._get_pubdate(item)

                        # This will be retrieved from the parser
                        search_result.proper_tags = ''

                        search_result.search_type = PROPER_SEARCH
                        search_result.date = datetime.today()
                        search_result.series = series_obj

        return results

    @staticmethod
    def remove_duplicate_mappings(items, pk='link'):
        """
        Remove duplicate items from an iterable of mappings.

        :param items: An iterable of mappings
        :param pk: Primary key for removing duplicates
        :return: An iterable of unique mappings
        """
        return list(
            itervalues(OrderedDict(
                (item[pk], item)
                for item in items
                )
            )
        )

    def find_search_results(self, series, episodes, search_mode, forced_search=False, download_current_quality=False,
                            manual_search=False, manual_search_type='episode'):
        """Search episodes based on param."""
        self._check_auth()
        self.series = series

        results = {}
        items_list = []

        for episode in episodes:
            if not manual_search:
                cache_result = self.cache.search_cache(episode, forced_search=forced_search,
                                                       down_cur_quality=download_current_quality)
                if cache_result:
                    if episode.episode not in results:
                        results[episode.episode] = cache_result
                    else:
                        results[episode.episode].extend(cache_result)

                    continue

            search_strings = []
            season_search = (len(episodes) > 1 or manual_search_type == 'season') and search_mode == 'sponly'
            if season_search:
                search_strings = self._get_season_search_strings(episode)
            elif search_mode == 'eponly':
                search_strings = self._get_episode_search_strings(episode)

            for search_string in search_strings:
                # Find results from the provider
                items_list += self.search(
                    search_string, ep_obj=episode, manual_search=manual_search
                )

            # In season search, we can't loop in episodes lists as we only need one episode to get the season string
            if search_mode == 'sponly':
                break

        if len(results) == len(episodes):
            return results

        # Remove duplicate items
        unique_items = self.remove_duplicate_mappings(items_list)
        log.debug('Found {0} unique items', len(unique_items))

        # categorize the items into lists by quality
        categorized_items = defaultdict(list)
        for item in unique_items:
            quality = self.get_quality(item, anime=series.is_anime)
            categorized_items[quality].append(item)

        # sort qualities in descending order
        sorted_qualities = sorted(categorized_items, reverse=True)
        log.debug('Found qualities: {0}', sorted_qualities)

        # chain items sorted by quality
        sorted_items = chain.from_iterable(
            categorized_items[quality]
            for quality in sorted_qualities
        )

        # unpack all of the quality lists into a single sorted list
        items_list = list(sorted_items)

        cl = []

        # Move through each item and parse it into a quality
        search_results = []
        for item in items_list:

            # Make sure we start with a TorrentSearchResult, NZBDataSearchResult or NZBSearchResult search result obj.
            search_result = self.get_result()
            search_results.append(search_result)
            search_result.item = item
            search_result.download_current_quality = download_current_quality
            # FIXME: Should be changed to search_result.search_type
            search_result.forced_search = forced_search

            (search_result.name, search_result.url) = self._get_title_and_url(item)
            (search_result.seeders, search_result.leechers) = self._get_result_info(item)

            search_result.size = self._get_size(item)
            search_result.pubdate = self._get_pubdate(item)

            search_result.result_wanted = True

            try:
                search_result.parsed_result = NameParser(parse_method=('normal', 'anime')[series.is_anime]
                                                         ).parse(search_result.name)
            except (InvalidNameException, InvalidShowException) as error:
                log.debug('Error during parsing of release name: {release_name}, with error: {error}',
                          {'release_name': search_result.name, 'error': error})
                search_result.add_cache_entry = False
                search_result.result_wanted = False
                continue

            # I don't know why i'm doing this. Maybe remove it later on all together, now i've added the parsed_result
            # to the search_result.
            search_result.series = search_result.parsed_result.series
            search_result.quality = search_result.parsed_result.quality
            search_result.release_group = search_result.parsed_result.release_group
            search_result.version = search_result.parsed_result.version
            search_result.actual_season = search_result.parsed_result.season_number
            search_result.actual_episodes = search_result.parsed_result.episode_numbers

            if not manual_search:
                if not (search_result.series.air_by_date or search_result.series.sports):
                    if search_mode == 'sponly':
                        if search_result.parsed_result.episode_numbers:
                            log.debug(
                                'This is supposed to be a season pack search but the result {0} is not a valid '
                                'season pack, skipping it', search_result.name
                            )
                            search_result.result_wanted = False
                            continue
                        elif not [ep for ep in episodes if
                                  search_result.parsed_result.season_number == (ep.season, ep.scene_season)
                                  [ep.series.is_scene]]:
                            log.debug(
                                'This season result {0} is for a season we are not searching for, '
                                'skipping it', search_result.name
                            )
                            search_result.result_wanted = False
                            continue
                    else:
                        # I'm going to split these up for better readability
                        # Check if at least got a season parsed.
                        if search_result.parsed_result.season_number is None:
                            log.debug(
                                "The result {0} doesn't seem to have a valid season that we are currently trying to "
                                "snatch, skipping it", search_result.name
                            )
                            search_result.result_wanted = False
                            continue

                        # Check if we at least got some episode numbers parsed.
                        if not search_result.parsed_result.episode_numbers:
                            log.debug(
                                "The result {0} doesn't seem to match an episode that we are currently trying to "
                                "snatch, skipping it", search_result.name
                            )
                            search_result.result_wanted = False
                            continue

                        # Compare the episodes and season from the result with what was searched.
                        if not [searched_episode for searched_episode in episodes
                                if searched_episode.season == search_result.parsed_result.season_number and
                                (searched_episode.episode, searched_episode.scene_episode)
                                [searched_episode.series.is_scene] in
                                search_result.parsed_result.episode_numbers]:
                            log.debug(
                                "The result {0} doesn't seem to match an episode that we are currently trying to "
                                "snatch, skipping it", search_result.name
                            )
                            search_result.result_wanted = False
                            continue

                    # We've performed some checks to decided if we want to continue with this result.
                    # If we've hit this, that means this is not an air_by_date and not a sports show. And it seems to be
                    # a valid result. Let's store the parsed season and episode number and continue.
                    search_result.actual_season = search_result.parsed_result.season_number
                    search_result.actual_episodes = search_result.parsed_result.episode_numbers
                else:
                    # air_by_date or sportshow.
                    search_result.same_day_special = False

                    if not search_result.parsed_result.is_air_by_date:
                        log.debug(
                            "This is supposed to be a date search but the result {0} didn't parse as one, "
                            "skipping it", search_result.name
                        )
                        search_result.result_wanted = False
                        continue
                    else:
                        # Use a query against the tv_episodes table, to match the parsed air_date against.
                        air_date = search_result.parsed_result.air_date.toordinal()
                        db = DBConnection()
                        sql_results = db.select(
                            'SELECT season, episode FROM tv_episodes WHERE indexer = ? AND showid = ? AND airdate = ?',
                            [search_result.series.indexer, search_result.series.series_id, air_date]
                        )

                        if len(sql_results) == 2:
                            if int(sql_results[0][b'season']) == 0 and int(sql_results[1][b'season']) != 0:
                                search_result.actual_season = int(sql_results[1][b'season'])
                                search_result.actual_episodes = [int(sql_results[1][b'episode'])]
                                search_result.same_day_special = True
                            elif int(sql_results[1][b'season']) == 0 and int(sql_results[0][b'season']) != 0:
                                search_result.actual_season = int(sql_results[0][b'season'])
                                search_result.actual_episodes = [int(sql_results[0][b'episode'])]
                                search_result.same_day_special = True
                        elif len(sql_results) != 1:
                            log.warning(
                                "Tried to look up the date for the episode {0} but the database didn't return proper "
                                "results, skipping it", search_result.name
                            )
                            search_result.result_wanted = False
                            continue

                        # @TODO: Need to verify and test this.
                        if search_result.result_wanted and not search_result.same_day_special:
                            search_result.actual_season = int(sql_results[0][b'season'])
                            search_result.actual_episodes = [int(sql_results[0][b'episode'])]

        # Iterate again over the search results, and see if there is anything we want.
        for search_result in search_results:

            # Try to cache the item if we want to.
            cache_result = search_result.add_result_to_cache(self.cache)
            if cache_result is not None:
                cl.append(cache_result)

            if not search_result.result_wanted:
                log.debug("We aren't interested in this result: {0} with url: {1}",
                          search_result.name, search_result.url)
                continue

            log.debug('Found result {0} at {1}', search_result.name, search_result.url)

            episode_object = search_result.create_episode_object()
            # result = self.get_result(episode_object, search_result)
            search_result.finish_search_result(self)

            if not episode_object:
                episode_number = SEASON_RESULT
                log.debug('Found season pack result {0} at {1}', search_result.name, search_result.url)
            elif len(episode_object) == 1:
                episode_number = episode_object[0].episode
                log.debug('Found single episode result {0} at {1}', search_result.name, search_result.url)
            else:
                episode_number = MULTI_EP_RESULT
                log.debug('Found multi-episode ({0}) result {1} at {2}',
                          ', '.join(map(str, search_result.parsed_result.episode_numbers)),
                          search_result.name,
                          search_result.url)
            if episode_number not in results:
                results[episode_number] = [search_result]
            else:
                results[episode_number].append(search_result)

        if cl:
            # Access to a protected member of a client class
            db = self.cache._get_db()
            db.mass_action(cl)

        return results

    def get_id(self):
        """Get ID of the provider."""
        return GenericProvider.make_id(self.name)

    def get_quality(self, item, anime=False):
        """Get quality of the result from its name."""
        (title, _) = self._get_title_and_url(item)
        quality = Quality.quality_from_name(title, anime)

        return quality

    def get_result(self, episodes=None):
        """Get result."""
        return self._get_result(episodes)

    def image_name(self):
        """Return provider image name."""
        return self.get_id() + '.png'

    def is_active(self):
        """Check if provider is active."""
        return False

    def is_enabled(self):
        """Check if provider is enabled."""
        return bool(self.enabled)

    @staticmethod
    def make_id(name):
        """Make ID of the provider."""
        if not name:
            return ''

        return re.sub(r'[^\w\d_]', '_', str(name).strip().lower())

    def search_rss(self, episodes):
        """Find cached needed episodes."""
        return self.cache.find_needed_episodes(episodes)

    def seed_ratio(self):
        """Return ratio."""
        return ''

    def _check_auth(self):
        """Check if we are autenticated."""
        return True

    def login(self):
        """Login to provider."""
        return True

    def search(self, search_strings, age=0, ep_obj=None, **kwargs):
        """Search the provider."""
        return []

    @staticmethod
    def parse_pubdate(pubdate, human_time=False, timezone=None, **kwargs):
        """
        Parse publishing date into a datetime object.

        :param pubdate: date and time string
        :param human_time: string uses human slang ("4 hours ago")
        :param timezone: use a different timezone ("US/Eastern")

        :keyword dayfirst: Interpret the first value as the day
        :keyword yearfirst: Interpret the first value as the year

        :returns: a datetime object or None
        """
        now_alias = ('right now', 'just now', 'now')

        df = kwargs.pop('dayfirst', False)
        yf = kwargs.pop('yearfirst', False)
        fromtimestamp = kwargs.pop('fromtimestamp', False)

        # This can happen from time to time
        if pubdate is None:
            log.debug('Skipping invalid publishing date.')
            return

        try:
            if human_time:
                if pubdate.lower() in now_alias:
                    seconds = 0
                else:
                    match = re.search(r'(?P<time>[\d.]+\W*)(?P<granularity>\w+)', pubdate)
                    matched_time = match.group('time')
                    matched_granularity = match.group('granularity')

                    # The parse method does not support decimals used with the month,
                    # months, year or years granularities.
                    if matched_granularity and matched_granularity in ('month', 'months', 'year', 'years'):
                        matched_time = int(round(float(matched_time.strip())))

                    seconds = parse('{0} {1}'.format(matched_time, matched_granularity))
                return datetime.now(tz.tzlocal()) - timedelta(seconds=seconds)

            if fromtimestamp:
                dt = datetime.fromtimestamp(int(pubdate), tz=tz.gettz('UTC'))
            else:
                dt = parser.parse(pubdate, dayfirst=df, yearfirst=yf, fuzzy=True)

            # Always make UTC aware if naive
            if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                dt = dt.replace(tzinfo=tz.gettz('UTC'))
            if timezone:
                dt = dt.astimezone(tz.gettz(timezone))

            return dt
        except (AttributeError, TypeError, ValueError):
            log.exception('Failed parsing publishing date: {0}', pubdate)

    def _get_result(self, episodes=None):
        """Get result."""
        return SearchResult(episodes)

    def _create_air_by_date_search_string(self, show_scene_name, episode, search_string, add_string=None):
        """Create a search string used for series that are indexed by air date."""
        episode_string = show_scene_name + self.search_separator
        episode_string += str(episode.airdate).replace('-', ' ')

        if add_string:
            episode_string += self.search_separator + add_string

        search_string['Episode'].append(episode_string.strip())

    def _create_sports_search_string(self, show_scene_name, episode, search_string, add_string=None):
        """Create a search string used for sport series."""
        episode_string = show_scene_name + self.search_separator

        episode_string += str(episode.airdate).replace('-', ' ')
        episode_string += ('|', ' ')[len(self.proper_strings) > 1]
        episode_string += episode.airdate.strftime('%b')

        if add_string:
            episode_string += self.search_separator + add_string

        search_string['Episode'].append(episode_string.strip())

    def _create_anime_search_string(self, show_scene_name, episode, search_string, add_string=None):
        """Create a search string used for as anime 'marked' shows."""
        episode_string = show_scene_name + self.search_separator

        # If the show name is a season scene exception, we want to use the indexer episode number.
        if (episode.scene_season > 1 and
                show_scene_name in scene_exceptions.get_season_scene_exceptions(episode.series, episode.scene_season)):
            # This is apparently a season exception, let's use the scene_episode instead of absolute
            ep = episode.scene_episode
        else:
            ep = episode.scene_absolute_number

        episode_string += '{episode:0>2}'.format(episode=ep)
        episode_string_fallback = episode_string + '{episode:0>3}'.format(episode=ep)

        if add_string:
            episode_string += self.search_separator + add_string
            episode_string_fallback += self.search_separator + add_string

        search_string['Episode'].append(episode_string.strip())

    def _create_default_search_string(self, show_scene_name, episode, search_string, add_string=None):
        """Create a default search string, used for standard type S01E01 tv series."""
        episode_string = show_scene_name + self.search_separator

        episode_string += config.naming_ep_type[2] % {
            'seasonnumber': episode.scene_season,
            'episodenumber': episode.scene_episode,
        }

        if add_string:
            episode_string += self.search_separator + add_string

        search_string['Episode'].append(episode_string.strip())

    def _get_episode_search_strings(self, episode, add_string=''):
        """Get episode search strings."""
        if not episode:
            return []

        search_string = {
            'Episode': []
        }

        all_possible_show_names = episode.series.get_all_possible_names()
        if episode.scene_season:
            all_possible_show_names = all_possible_show_names.union(
                episode.series.get_all_possible_names(season=episode.scene_season)
            )

        for show_name in all_possible_show_names:

            if episode.series.air_by_date:
                self._create_air_by_date_search_string(show_name, episode, search_string, add_string=add_string)
            elif episode.series.sports:
                self._create_sports_search_string(show_name, episode, search_string, add_string=add_string)
            elif episode.series.anime:
                self._create_anime_search_string(show_name, episode, search_string, add_string=add_string)
            else:
                self._create_default_search_string(show_name, episode, search_string, add_string=add_string)

        return [search_string]

    def _get_tvdb_id(self):
        """Return the tvdb id if the shows indexer is tvdb. If not, try to use the externals to get it."""
        if not self.series:
            return None

        return self.series.indexerid if self.series.indexer == INDEXER_TVDBV2 else self.series.externals.get('tvdb_id')

    def _get_season_search_strings(self, episode):
        search_string = {
            'Season': []
        }

        for show_name in episode.series.get_all_possible_names(season=episode.scene_season):
            episode_string = show_name + self.search_separator

            if episode.series.air_by_date or episode.series.sports:
                search_string['Season'].append(episode_string + str(episode.airdate).split('-')[0])
            elif episode.series.anime:
                search_string['Season'].append(episode_string + 'Season')
            else:
                for season_template in self.season_templates:
                    templated_episode_string = episode_string + season_template.format(season=episode.scene_season)
                    search_string['Season'].append(templated_episode_string.strip())

        return [search_string]

    def _get_size(self, item):
        """Return default size."""
        return -1

    def _get_storage_dir(self):
        """Return storage dir."""
        return ''

    def _get_result_info(self, item):
        """Return default seeders and leechers."""
        return -1, -1

    def _get_pubdate(self, item):
        """Return publish date of the item.

        If provider doesnt have _get_pubdate function this will be used
        """
        return None

    def _get_title_and_url(self, item):
        """Return title and url from result."""
        if not item:
            return '', ''

        title = item.get('title', '')
        url = item.get('link', '')

        if title:
            title = title.replace(' ', '.')
        else:
            title = ''

        if url:
            url = url.replace('&amp;', '&').replace('%26tr%3D', '&tr=')
        else:
            url = ''

        return title, url

    @property
    def recent_results(self):
        """Return recent RSS results from provier."""
        return recent_results.get(self.get_id(), [])

    @recent_results.setter
    def recent_results(self, items):
        """Set recent results from provider."""
        if not recent_results.get(self.get_id()):
            recent_results.update({self.get_id(): []})
        if items:
            add_to_list = []
            for item in items:
                if item['link'] not in {cache_item['link'] for cache_item in recent_results[self.get_id()]}:
                    add_to_list += [item]
            results = add_to_list + recent_results[self.get_id()]
            recent_results[self.get_id()] = results[:self.max_recent_items]

    def add_cookies_from_ui(self):
        """
        Add the cookies configured from UI to the providers requests session.

        :return: A dict with the the keys result as bool and message as string
        """
        # Added exception for rss torrent providers, as for them adding cookies initial should be optional.
        from medusa.providers.torrent.rss.rsstorrent import TorrentRssProvider
        if isinstance(self, TorrentRssProvider) and not self.cookies:
            return {'result': True,
                    'message': 'This is a TorrentRss provider without any cookies provided. '
                               'Cookies for this provider are considered optional.'}

        # This is the generic attribute used to manually add cookies for provider authentication
        if not self.enable_cookies:
            return {'result': False,
                    'message': 'Adding cookies is not supported for provider: {0}'.format(self.name)}

        if not self.cookies:
            return {'result': False,
                    'message': 'No Cookies added from ui for provider: {0}'.format(self.name)}

        cookie_validator = re.compile(r'^([\w%]+=[\w%]+)(;[\w%]+=[\w%]+)*$')
        if not cookie_validator.match(self.cookies):
            ui.notifications.message(
                'Failed to validate cookie for provider {provider}'.format(provider=self.name),
                'Cookie is not correctly formatted: {0}'.format(self.cookies))
            return {'result': False,
                    'message': 'Cookie is not correctly formatted: {0}'.format(self.cookies)}

        if not all(req_cookie in [x.rsplit('=', 1)[0] for x in self.cookies.split(';')]
                   for req_cookie in self.required_cookies):
            return {
                'result': False,
                'message': "You haven't configured the requied cookies. Please login at {provider_url}, "
                           "and make sure you have copied the following cookies: {required_cookies!r}"
                           .format(provider_url=self.name, required_cookies=self.required_cookies)
            }

        # cookie_validator got at least one cookie key/value pair, let's return success
        add_dict_to_cookiejar(self.session.cookies, dict(x.rsplit('=', 1) for x in self.cookies.split(';')))
        return {'result': True,
                'message': ''}

    def check_required_cookies(self):
        """
        Check if we have the required cookies in the requests sessions object.

        Meaning that we've already successfully authenticated once, and we don't need to go through this again.
        Note! This doesn't mean the cookies are correct!
        """
        if not hasattr(self, 'required_cookies'):
            # A reminder for the developer, implementing cookie based authentication.
            log.error(
                'You need to configure the required_cookies attribute, for the provider: {provider}',
                {'provider': self.name}
            )
            return False
        return all(dict_from_cookiejar(self.session.cookies).get(cookie) for cookie in self.required_cookies)

    def cookie_login(self, check_login_text, check_url=None):
        """
        Check the response for text that indicates a login prompt.

        In that case, the cookie authentication was not successful.
        :param check_login_text: A string that's visible when the authentication failed.
        :param check_url: The url to use to test the login with cookies. By default the providers home page is used.

        :return: False when authentication was not successful. True if successful.
        """
        check_url = check_url or self.url

        if self.check_required_cookies():
            # All required cookies have been found within the current session, we don't need to go through this again.
            return True

        if self.cookies:
            result = self.add_cookies_from_ui()
            if not result['result']:
                ui.notifications.message(result['message'])
                log.warning(result['message'])
                return False
        else:
            log.warning('Failed to login, you will need to add your cookies in the provider settings')
            ui.notifications.error('Failed to auth with {provider}'.format(provider=self.name),
                                   'You will need to add your cookies in the provider settings')
            return False

        response = self.session.get(check_url)
        if not response or any([not (response.text and response.status_code == 200),
                                check_login_text.lower() in response.text.lower()]):
            log.warning('Please configure the required cookies for this provider. Check your provider settings')
            ui.notifications.error('Wrong cookies for {provider}'.format(provider=self.name),
                                   'Check your provider settings')
            self.session.cookies.clear()
            return False
        else:
            return True

    def __str__(self):
        """Return provider name and provider type."""
        return '{provider_name} ({provider_type})'.format(provider_name=self.name, provider_type=self.provider_type)

    def __unicode__(self):
        """Return provider name and provider type."""
        return '{provider_name} ({provider_type})'.format(provider_name=self.name, provider_type=self.provider_type)
