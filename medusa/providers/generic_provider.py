# coding=utf-8
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
"""Provider code for Generic Provider."""
from __future__ import unicode_literals

import re
from base64 import b16encode, b32decode
from collections import defaultdict
from datetime import datetime
from itertools import chain
from os.path import join
from random import shuffle

from requests.utils import add_dict_to_cookiejar

from .. import app, config, logger, ui
from ..classes import Proper, SearchResult
from ..common import MULTI_EP_RESULT, Quality, SEASON_RESULT, UA_POOL
from ..db import DBConnection
from ..helper.common import replace_extension, sanitize_filename
from ..helper.exceptions import ex
from ..helpers import download_file, get_url, make_session
from ..indexers.indexer_config import INDEXER_TVDBV2
from ..name_parser.parser import InvalidNameException, InvalidShowException, NameParser
from ..show.show import Show
from ..show_name_helpers import allPossibleShowNames
from ..tv_cache import TVCache

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
        self.cache = TVCache(self)
        self.enable_backlog = False
        self.enable_manualsearch = False
        self.enable_daily = False
        self.enabled = False
        self.headers = {'User-Agent': UA_POOL.random}
        self.proper_strings = ['PROPER|REPACK|REAL']
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

            logger.log('Downloading {result} from {provider} at {url}'.format
                       (result=result.name, provider=self.name, url=url))

            if url.endswith(GenericProvider.TORRENT) and filename.endswith(GenericProvider.NZB):
                filename = replace_extension(filename, GenericProvider.TORRENT)

            verify = False if self.public else None

            if download_file(url, filename, session=self.session, headers=self.headers,
                             hooks={'response': self.get_url_hook}, verify=verify):

                if self._verify_download(filename):
                    logger.log('Saved {result} to {location}'.format(result=result.name, location=filename))
                    return True

        if urls:
            logger.log('Failed to download any results for {result}'.format(result=result.name), logger.WARNING)

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

        for item in items_list:
            (title, url) = self._get_title_and_url(item)
            (seeders, leechers) = self._get_result_info(item)
            size = self._get_size(item)
            pubdate = self._get_pubdate(item)

            try:
                parse_result = NameParser(parse_method=('normal', 'anime')[show.is_anime]).parse(title)
            except (InvalidNameException, InvalidShowException) as error:
                logger.log(u"{error}".format(error=error), logger.DEBUG)
                continue

            show_object = parse_result.show
            quality = parse_result.quality
            release_group = parse_result.release_group
            version = parse_result.version
            add_cache_entry = False

            if not manual_search:
                if not (show_object.air_by_date or show_object.sports):
                    if search_mode == 'sponly':
                        if parse_result.episode_numbers:
                            logger.log(
                                'This is supposed to be a season pack search but the result %s is not a valid '
                                'season pack, skipping it' % title, logger.DEBUG
                            )
                            add_cache_entry = True
                        elif not [ep for ep in episodes if
                                  parse_result.season_number == (ep.season, ep.scene_season)[ep.show.is_scene]]:
                            logger.log(
                                'This season result %s is for a season we are not searching for, skipping it' % title,
                                logger.DEBUG
                            )
                            add_cache_entry = True

                    else:
                        if not all([parse_result.season_number is not None,
                                    parse_result.episode_numbers,
                                    [ep for ep in episodes if (ep.season, ep.scene_season)[ep.show.is_scene] ==
                                     parse_result.season_number and
                                     (ep.episode, ep.scene_episode)[ep.show.is_scene] in
                                     parse_result.episode_numbers]]):
                            logger.log(
                                "The result %s doesn't seem to match an episode that we are currently trying to "
                                "snatch, skipping it" % title, logger.DEBUG
                            )
                            add_cache_entry = True

                    if not add_cache_entry:
                        actual_season = parse_result.season_number
                        actual_episodes = parse_result.episode_numbers
                else:
                    same_day_special = False

                    if not parse_result.is_air_by_date:
                        logger.log(
                            "This is supposed to be a date search but the result %s didn't parse as one, "
                            "skipping it" % title, logger.DEBUG
                        )
                        add_cache_entry = True
                    else:
                        air_date = parse_result.air_date.toordinal()
                        db = DBConnection()
                        sql_results = db.select(
                            'SELECT season, episode FROM tv_episodes WHERE showid = ? AND airdate = ?',
                            [show_object.indexerid, air_date]
                        )

                        if len(sql_results) == 2:
                            if int(sql_results[0][b'season']) == 0 and int(sql_results[1][b'season']) != 0:
                                actual_season = int(sql_results[1][b'season'])
                                actual_episodes = [int(sql_results[1][b'episode'])]
                                same_day_special = True
                            elif int(sql_results[1][b'season']) == 0 and int(sql_results[0][b'season']) != 0:
                                actual_season = int(sql_results[0][b'season'])
                                actual_episodes = [int(sql_results[0][b'episode'])]
                                same_day_special = True
                        elif len(sql_results) != 1:
                            logger.log(
                                "Tried to look up the date for the episode %s but the database didn't return proper "
                                "results, skipping it" % title, logger.WARNING
                            )
                            add_cache_entry = True

                    if not add_cache_entry and not same_day_special:
                        actual_season = int(sql_results[0][b'season'])
                        actual_episodes = [int(sql_results[0][b'episode'])]
            else:
                actual_season = parse_result.season_number
                actual_episodes = parse_result.episode_numbers

            if add_cache_entry:
                logger.log('Adding item from search to cache: %s' % title, logger.DEBUG)

                # Access to a protected member of a client class
                ci = self.cache.add_cache_entry(title, url, seeders, leechers, size, pubdate)

                if ci is not None:
                    cl.append(ci)

                continue

            episode_wanted = True

            if not manual_search:
                for episode_number in actual_episodes:
                    if not show_object.want_episode(actual_season, episode_number, quality, forced_search,
                                                    download_current_quality):
                        episode_wanted = False
                        break

                if not episode_wanted:
                    logger.log('Ignoring result %s.' % title, logger.DEBUG)
                    continue

            logger.log('Found result %s at %s' % (title, url), logger.DEBUG)

            episode_object = []
            for current_episode in actual_episodes:
                episode_object.append(show_object.get_episode(actual_season, current_episode))

            result = self.get_result(episode_object)
            result.show = show_object
            result.url = url
            result.seeders = seeders
            result.leechers = leechers
            result.name = title
            result.quality = quality
            result.release_group = release_group
            result.version = version
            result.content = None
            result.size = self._get_size(item)
            result.pubdate = self._get_pubdate(item)

            if not episode_object:
                episode_number = SEASON_RESULT
                logger.log('Separating full season result to check for later', logger.DEBUG)
            elif len(episode_object) == 1:
                episode_number = episode_object[0].episode
                logger.log('Single episode result.', logger.DEBUG)
            else:
                episode_number = MULTI_EP_RESULT
                logger.log('Separating multi-episode result to check for later - result contains episodes: {0}'.format
                           (parse_result.episode_numbers), logger.DEBUG)

            if episode_number not in results:
                results[episode_number] = [result]
            else:
                results[episode_number].append(result)

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

    def get_result(self, episodes):
        """Get result."""
        result = self._get_result(episodes)
        result.provider = self

        return result

    @staticmethod
    def get_url_hook(response, **kwargs):
        """Get URL hook."""
        logger.log('{} URL: {} [Status: {}]'.format
                   (response.request.method, response.request.url, response.status_code), logger.DEBUG)

        if response.request.method == 'POST':
            logger.log('With post data: {}'.format(response.request.body), logger.DEBUG)

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

    def _get_result(self, episodes):
        """Get result."""
        return SearchResult(episodes)

    def _get_episode_search_strings(self, episode, add_string=''):
        """Get episode search strings."""
        if not episode:
            return []

        search_string = {
            'Episode': []
        }

        for show_name in allPossibleShowNames(episode.show, season=episode.scene_season):
            episode_string = show_name + ' '

            if episode.show.air_by_date:
                episode_string += str(episode.airdate).replace('-', ' ')
            elif episode.show.sports:
                episode_string += str(episode.airdate).replace('-', ' ')
                episode_string += ('|', ' ')[len(self.proper_strings) > 1]
                episode_string += episode.airdate.strftime('%b')
            elif episode.show.anime:
                episode_string += '%02d' % int(episode.scene_absolute_number)
            else:
                episode_string += config.naming_ep_type[2] % {
                    'seasonnumber': episode.scene_season,
                    'episodenumber': episode.scene_episode,
                }

            if add_string:
                episode_string += ' ' + add_string

            search_string['Episode'].append(episode_string.strip())

        return [search_string]

    def _get_tvdb_id(self):
        """Return the tvdb id if the shows indexer is tvdb. If not, try to use the externals to get it."""
        return self.show.indexerid if self.show.indexer == INDEXER_TVDBV2 else self.show.externals.get('tvdb_id')

    def _get_season_search_strings(self, episode):
        search_string = {
            'Season': []
        }

        for show_name in allPossibleShowNames(episode.show, season=episode.season):
            episode_string = show_name + ' '

            if episode.show.air_by_date or episode.show.sports:
                episode_string += str(episode.airdate).split('-')[0]
            elif episode.show.anime:
                episode_string += 'Season'
            else:
                episode_string += 'S%02d' % int(episode.season)

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
                    logger.log('Unable to extract torrent hash from magnet: %s' % ex(result.url), logger.ERROR)
                    return urls, filename

                urls = [x.format(info_hash=info_hash, torrent_name=torrent_name) for x in self.bt_cache_urls]
                shuffle(urls)
            except Exception:
                logger.log('Unable to extract torrent hash or name from magnet: %s' % ex(result.url), logger.ERROR)
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

            else:  # Else is not needed, but placed it here for readability
                ui.notifications.message('Failed to validate cookie for provider {provider}'.format(provider=self.name),
                                         'No Cookies added from ui for provider: {0}'.format(self.name))
                return {'result': False,
                        'message': 'No Cookies added from ui for provider: {0}'.format(self.name)}

        return {'result': False,
                'message': 'Adding cookies is not supported for provider: {0}'.format(self.name)}
