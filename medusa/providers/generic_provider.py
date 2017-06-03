# coding=utf-8

"""Provider code for Generic Provider."""

from __future__ import unicode_literals

import logging
import re

from base64 import b16encode, b32decode
from collections import defaultdict
from datetime import datetime, timedelta
from itertools import chain
from os.path import join
from random import shuffle

from dateutil import parser, tz

from medusa import (
    app,
    config,
    tv,
    ui,
)
from medusa.classes import (
    Proper,
    SearchResult,
)
from medusa.common import (
    MULTI_EP_RESULT,
    Quality,
    SEASON_RESULT,
    UA_POOL,
)
from medusa.db import DBConnection
from medusa.helper.common import (
    replace_extension,
    sanitize_filename,
)
from medusa.helpers import (
    download_file,
    get_url,
    make_session,
)
from medusa.indexers.indexer_config import INDEXER_TVDBV2
from medusa.logger.adapters.style import BraceAdapter
from medusa.name_parser.parser import (
    InvalidNameException,
    InvalidShowException,
    NameParser,
)
from medusa.scene_exceptions import get_scene_exceptions
from medusa.show.show import Show

from pytimeparse import parse

from requests.utils import add_dict_to_cookiejar

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
            'http://itorrents.org/torrent/{info_hash}.torrent',
            'https://torrentproject.se/torrent/{info_hash}.torrent',
            'http://torrasave.top/torrent/{info_hash}.torrent',
            'http://torra.pro/torrent/{info_hash}.torrent',
            'http://torra.click/torrent/{info_hash}.torrent',
            'http://reflektor.karmorra.info/torrent/{info_hash}.torrent',
            'http://torrasave.site/torrent/{info_hash}.torrent',
        ]
        self.cache = tv.Cache(self)
        self.enable_backlog = False
        self.enable_manualsearch = False
        self.enable_daily = False
        self.enabled = False
        self.headers = {'User-Agent': UA_POOL.random}
        self.proper_strings = ['PROPER|REPACK|REAL|RERIP']
        self.provider_type = None
        self.public = False
        self.search_fallback = False
        self.search_mode = None
        self.session = make_session()
        self.show = None
        self.supports_absolute_numbering = False
        self.supports_backlog = True
        self.url = ''
        self.urls = {}
        # Ability to override the search separator. As for example anizb is using '*' instead of space.
        self.search_separator = ' '

        # Use and configure the attribute enable_cookies to show or hide the cookies input field per provider
        self.enable_cookies = False
        self.cookies = ''

        # Paramaters for reducting the daily search results parsing
        self.max_recent_items = 5
        self.stop_at = 3

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

            if url.endswith(GenericProvider.TORRENT) and filename.endswith(GenericProvider.NZB):
                filename = replace_extension(filename, GenericProvider.TORRENT)

            verify = False if self.public else None

            if download_file(url, filename, session=self.session, headers=self.headers,
                             hooks={'response': self.get_url_hook}, verify=verify):

                if self._verify_download(filename):
                    log.info('Saved {result} to {location}',
                             {'result': result.name, 'location': filename})
                    return True

        if urls:
            log.warning('Failed to download any results for {result}',
                        {'result': result.name})

        return False

    def find_propers(self, proper_candidates):
        """Find propers in providers."""
        results = []

        for proper_candidate in proper_candidates:
            show_obj = Show.find(app.showList,
                                 int(proper_candidate[b'showid'])) if proper_candidate[b'showid'] else None
            if show_obj:
                self.show = show_obj
                episode_obj = show_obj.get_episode(proper_candidate[b'season'], proper_candidate[b'episode'])

                for term in self.proper_strings:
                    search_strings = self._get_episode_search_strings(episode_obj, add_string=term)

                    for item in self.search(search_strings[0], ep_obj=episode_obj):
                        title, url = self._get_title_and_url(item)
                        seeders, leechers = self._get_result_info(item)
                        size = self._get_size(item)
                        pubdate = self._get_pubdate(item)

                        # This will be retrived from the parser
                        proper_tags = ''

                        results.append(Proper(title, url, datetime.today(), show_obj, seeders, leechers, size, pubdate,
                                              proper_tags))

        return results

    def find_search_results(self, show, episodes, search_mode, forced_search=False, download_current_quality=False,
                            manual_search=False, manual_search_type='episode'):
        """Search episodes based on param."""
        self._check_auth()
        self.show = show

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
            if (len(episodes) > 1 or manual_search_type == 'season') and search_mode == 'sponly':
                search_strings = self._get_season_search_strings(episode)
            elif search_mode == 'eponly':
                search_strings = self._get_episode_search_strings(episode)

            for search_string in search_strings:
                # Find results from the provider
                items_list += self.search(search_string, ep_obj=episode)

            # In season search, we can't loop in episodes lists as we only need one episode to get the season string
            if search_mode == 'sponly':
                break

        if len(results) == len(episodes):
            return results

        if items_list:
            # categorize the items into lists by quality
            items = defaultdict(list)
            for item in items_list:
                items[self.get_quality(item, anime=show.is_anime)].append(item)

            # temporarily remove the list of items with unknown quality
            unknown_items = items.pop(Quality.UNKNOWN, [])

            # make a generator to sort the remaining items by descending quality
            items_list = (items[quality] for quality in sorted(items, reverse=True))

            # unpack all of the quality lists into a single sorted list
            items_list = list(chain(*items_list))

            # extend the list with the unknown qualities, now sorted at the bottom of the list
            items_list.extend(unknown_items)

        cl = []

        # Move through each item and parse it into a quality
        search_results = []
        for item in items_list:

            # Make sure we start with a TorrentSearchResult, NZBDataSearchResult or NZBSearchResult search result obj.
            search_result = self.get_result()
            search_results.append(search_result)
            search_result.item = item
            search_result.download_current_quality = download_current_quality
            search_result.forced_search = forced_search

            (search_result.name, search_result.url) = self._get_title_and_url(item)
            (search_result.seeders, search_result.leechers) = self._get_result_info(item)

            search_result.size = self._get_size(item)
            search_result.pubdate = self._get_pubdate(item)

            search_result.result_wanted = True

            try:
                search_result.parsed_result = NameParser(parse_method=('normal', 'anime')[show.is_anime]
                                                         ).parse(search_result.name)
            except (InvalidNameException, InvalidShowException) as error:
                log.debug(error.message)
                search_result.add_cache_entry = False
                search_result.result_wanted = False
                continue

            # I don't know why i'm doing this. Maybe remove it later on all together, now i've added the parsed_result
            # to the search_result.
            search_result.show = search_result.parsed_result.show
            search_result.quality = search_result.parsed_result.quality
            search_result.release_group = search_result.parsed_result.release_group
            search_result.version = search_result.parsed_result.version
            search_result.actual_season = search_result.parsed_result.season_number
            search_result.actual_episodes = search_result.parsed_result.episode_numbers

            if not manual_search:
                if not (search_result.show.air_by_date or search_result.show.sports):
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
                                  [ep.show.is_scene]]:
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
                            'SELECT season, episode FROM tv_episodes WHERE showid = ? AND airdate = ?',
                            [search_result.show.indexerid, air_date]
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
                log.debug('Separating full season result to check for later')
            elif len(episode_object) == 1:
                episode_number = episode_object[0].episode
                log.debug('Single episode result.')
            else:
                episode_number = MULTI_EP_RESULT
                log.debug('Separating multi-episode result to check for later - result contains episodes: {0}',
                          search_result.parsed_result.episode_numbers)

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
        """Get scene quality of the result."""
        (title, _) = self._get_title_and_url(item)
        quality = Quality.scene_quality(title, anime)

        return quality

    def get_result(self, episodes=None):
        """Get result."""
        return self._get_result(episodes)

    @staticmethod
    def get_url_hook(response, **kwargs):
        """Get URL hook."""
        log.debug('{0} URL: {1} [Status: {2}]', response.request.method, response.request.url, response.status_code)

        if response.request.method == 'POST':
            log.debug('With post data: {0}', response.request.body)

    def get_url(self, url, post_data=None, params=None, timeout=30, **kwargs):
        """Load the given URL."""
        kwargs['hooks'] = {'response': self.get_url_hook}
        return get_url(url, post_data, params, self.headers, timeout, self.session, **kwargs)

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

    def search(self, search_params, age=0, ep_obj=None):
        """Search the provider."""
        return []

    @staticmethod
    def parse_pubdate(pubdate, human_time=False, timezone=None):
        """
        Parse publishing date into a datetime object.

        :param pubdate: date and time string
        :param human_time: string uses human slang ("4 hours ago")
        :param timezone: use a different timezone ("US/Eastern")

        :returns: a datetime object or None
        """
        now_alias = ('right now', 'just now', 'now')

        # This can happen from time to time
        if pubdate is None:
            log.debug('Skipping invalid publishing date.')
            return

        try:
            if human_time:
                if pubdate.lower() in now_alias:
                    seconds = 0
                else:
                    match = re.search(r'(?P<time>\d+\W*\w+)', pubdate)
                    seconds = parse(match.group('time'))
                return datetime.now(tz.tzlocal()) - timedelta(seconds=seconds)

            dt = parser.parse(pubdate, fuzzy=True)
            # Always make UTC aware if naive
            if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                dt = dt.replace(tzinfo=tz.gettz('UTC'))
            if timezone:
                dt = dt.astimezone(tz.gettz(timezone))
            return dt

        except (AttributeError, ValueError):
            log.exception('Failed parsing publishing date: {0}', pubdate)

    def _get_result(self, episodes=None):
        """Get result."""
        return SearchResult(episodes)

    def _get_episode_search_strings(self, episode, add_string=''):
        """Get episode search strings."""
        if not episode:
            return []

        search_string = {
            'Episode': []
        }

        for show_name in episode.series.get_all_possible_names(season=episode.scene_season):
            episode_string = show_name + self.search_separator
            episode_string_fallback = None

            if episode.series.air_by_date:
                episode_string += str(episode.airdate).replace('-', ' ')
            elif episode.series.sports:
                episode_string += str(episode.airdate).replace('-', ' ')
                episode_string += ('|', ' ')[len(self.proper_strings) > 1]
                episode_string += episode.airdate.strftime('%b')
            elif episode.series.anime:
                # If the showname is a season scene exception, we want to use the indexer episode number.
                if (episode.scene_season > 1 and
                        show_name in get_scene_exceptions(episode.series.indexerid,
                                                          episode.series.indexer,
                                                          episode.scene_season)):
                    # This is apparently a season exception, let's use the scene_episode instead of absolute
                    ep = episode.scene_episode
                else:
                    ep = episode.scene_absolute_number
                episode_string_fallback = episode_string + '{episode:0>3}'.format(episode=ep)
                episode_string += '{episode:0>2}'.format(episode=ep)
            else:
                episode_string += config.naming_ep_type[2] % {
                    'seasonnumber': episode.scene_season,
                    'episodenumber': episode.scene_episode,
                }

            if add_string:
                episode_string += self.search_separator + add_string
                if episode_string_fallback:
                    episode_string_fallback += self.search_separator + add_string

            search_string['Episode'].append(episode_string.strip())
            if episode_string_fallback:
                search_string['Episode'].append(episode_string_fallback.strip())

        return [search_string]

    def _get_tvdb_id(self):
        """Return the tvdb id if the shows indexer is tvdb. If not, try to use the externals to get it."""
        return self.show.indexerid if self.show.indexer == INDEXER_TVDBV2 else self.show.externals.get('tvdb_id')

    def _get_season_search_strings(self, episode):
        search_string = {
            'Season': []
        }

        for show_name in episode.series.get_all_possible_names(season=episode.scene_season):
            episode_string = show_name + ' '

            if episode.series.air_by_date or episode.series.sports:
                episode_string += str(episode.airdate).split('-')[0]
            elif episode.series.anime:
                episode_string += 'Season'
            else:
                episode_string += 'S{season:0>2}'.format(season=episode.scene_season)

            search_string['Season'].append(episode_string.strip())

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

    def _make_url(self, result):
        """Return url if result is a magnet link."""
        if not result:
            return '', ''

        urls = []
        filename = ''

        if result.url.startswith('magnet'):
            try:
                info_hash = re.findall(r'urn:btih:([\w]{32,40})', result.url)[0].upper()

                try:
                    torrent_name = re.findall('dn=([^&]+)', result.url)[0]
                except Exception:
                    torrent_name = 'NO_DOWNLOAD_NAME'

                if len(info_hash) == 32:
                    info_hash = b16encode(b32decode(info_hash)).upper()

                if not info_hash:
                    log.error('Unable to extract torrent hash from magnet: {0}', result.url)
                    return urls, filename

                urls = [x.format(info_hash=info_hash, torrent_name=torrent_name) for x in self.bt_cache_urls]
                shuffle(urls)
            except Exception:
                log.error('Unable to extract torrent hash or name from magnet: {0}', result.url)
                return urls, filename
        else:
            urls = [result.url]

        filename = join(self._get_storage_dir(), sanitize_filename(result.name) + '.' + self.provider_type)

        return urls, filename

    def _verify_download(self, file_name=None):
        return True

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
        # This is the generic attribute used to manually add cookies for provider authentication
        if self.enable_cookies:
            if self.cookies:
                cookie_validator = re.compile(r'^(\w+=\w+)(;\w+=\w+)*$')
                if not cookie_validator.match(self.cookies):
                    ui.notifications.message(
                        'Failed to validate cookie for provider {provider}'.format(provider=self.name),
                        'Cookie is not correctly formatted: {0}'.format(self.cookies))
                    return {'result': False,
                            'message': 'Cookie is not correctly formatted: {0}'.format(self.cookies)}

                # cookie_validator got at least one cookie key/value pair, let's return success
                add_dict_to_cookiejar(self.session.cookies, dict(x.rsplit('=', 1) for x in self.cookies.split(';')))
                return {'result': True,
                        'message': ''}

            else:  # Cookies not set. Don't need to check cookies
                return {'result': True,
                        'message': 'No Cookies added from ui for provider: {0}'.format(self.name)}

        return {'result': False,
                'message': 'Adding cookies is not supported for provider: {0}'.format(self.name)}
