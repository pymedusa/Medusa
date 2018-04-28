# coding=utf-8

"""tv_cache code."""

from __future__ import unicode_literals

import itertools
import logging
import traceback
from builtins import object
from builtins import str
from time import time

from medusa import (
    app,
    db,
)
from medusa.helper.common import episode_num
from medusa.helper.exceptions import AuthException
from medusa.logger.adapters.style import BraceAdapter
from medusa.name_parser.parser import (
    InvalidNameException,
    InvalidShowException,
    NameParser,
)
from medusa.rss_feeds import getFeed
from medusa.show import naming
from medusa.show.show import Show

from six import text_type

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class CacheDBConnection(db.DBConnection):
    """Cache database class."""

    def __init__(self, provider_id):
        """Initialize the class."""
        db.DBConnection.__init__(self, 'cache.db')

        # Create the table if it's not already there
        try:
            if not self.hasTable(provider_id):
                log.debug('Creating cache table for provider {0}', provider_id)
                self.action(
                    b'CREATE TABLE [{name}]'
                    b'   (name TEXT,'
                    b'    season NUMERIC,'
                    b'    episodes TEXT,'
                    b'    indexer NUMERIC,'
                    b'    indexerid NUMERIC,'
                    b'    url TEXT,'
                    b'    time NUMERIC,'
                    b'    quality NUMERIC,'
                    b'    release_group TEXT,'
                    b'    date_added NUMERIC)'.format(name=provider_id))
            else:
                sql_results = self.select(
                    b'SELECT url, COUNT(url) AS count '
                    b'FROM [{name}] '
                    b'GROUP BY url '
                    b'HAVING count > 1'.format(name=provider_id)
                )
                for duplicate in sql_results:
                    self.action(
                        b'DELETE FROM [{name}] '
                        b'WHERE url = ?'.format(name=provider_id),
                        [duplicate[b'url']]
                    )

            # remove wrong old index
            self.action(b'DROP INDEX IF EXISTS idx_url')

            # add unique index if one does not exist to prevent further dupes
            log.debug('Creating UNIQUE URL index for {0}', provider_id)
            self.action(
                b'CREATE UNIQUE INDEX '
                b'IF NOT EXISTS idx_url_{name} '
                b'ON [{name}] (url)'.format(name=provider_id)
            )

            # add release_group column to table if missing
            table = (
                ('release_group', 'TEXT', None),
                ('version', 'NUMERIC', -1),
                ('seeders', 'NUMERIC', -1),
                ('leechers', 'NUMERIC', -1),
                ('size', 'NUMERIC', -1),
                ('pubdate', 'NUMERIC', None),
                ('proper_tags', 'TEXT', None),
                ('date_added', 'NUMERIC', 0),
                ('indexer', 'NUMERIC', None),
            )
            for column, data_type, default in table:
                # add columns to table if missing
                if not self.hasColumn(provider_id, column):
                    self.addColumn(provider_id, column, data_type, default)

        except Exception as error:
            msg = 'table [{name}] already exists'.format(name=provider_id)
            if str(error) != msg:
                raise

        # Create the table if it's not already there
        try:
            if not self.hasTable('last_update'):
                self.action(
                    b'CREATE TABLE last_update'
                    b'   (provider TEXT, '
                    b'    time NUMERIC)'
                )
        except Exception as error:
            log.debug('Error while searching {provider_id}, skipping: {error!r}',
                      {'provider_id': provider_id, 'error': error})
            log.debug(traceback.format_exc())
            msg = 'table [{name}] already exists'.format(name='last_update')
            if str(error) != msg:
                raise


class Cache(object):
    """Cache class."""

    def __init__(self, provider, **kwargs):
        """Initialize class."""
        self.provider = provider
        self.provider_id = self.provider.get_id()
        self.provider_db = None
        self.minTime = kwargs.pop('min_time', 10)
        self.search_params = kwargs.pop('search_params', dict(RSS=['']))

    def _get_db(self):
        """Initialize provider database if not done already."""
        if not self.provider_db:
            self.provider_db = CacheDBConnection(self.provider_id)

        return self.provider_db

    def _clear_cache(self):
        """Perform regular cache cleaning as required."""
        # if cache trimming is enabled
        if app.CACHE_TRIMMING:
            # trim items older than MAX_CACHE_AGE days
            self.trim(days=app.MAX_CACHE_AGE)

    def trim(self, days=None):
        """
        Remove old items from cache.

        :param days: Number of days to retain
        """
        if days:
            now = int(time())  # current timestamp
            retention_period = now - (days * 86400)
            log.info('Removing cache entries older than {x} days from {provider}',
                     {'x': days, 'provider': self.provider_id})
            cache_db_con = self._get_db()
            cache_db_con.action(
                b'DELETE FROM [{provider}] '
                b'WHERE time < ? '.format(provider=self.provider_id),
                [retention_period]
            )

    def _get_title_and_url(self, item):
        """Return title and url from item."""
        return self.provider._get_title_and_url(item)

    def _get_result_info(self, item):
        """Return seeders and leechers from item."""
        return self.provider._get_result_info(item)

    def _get_size(self, item):
        """Return size of the item."""
        return self.provider._get_size(item)

    def _get_pubdate(self, item):
        """Return publish date of the item."""
        return self.provider._get_pubdate(item)

    def _get_rss_data(self):
        """Return rss data."""
        if self.search_params:
            return {'entries': self.provider.search(self.search_params)}

    def _check_auth(self, data):
        """Check if we are authenticated."""
        return True

    def _check_item_auth(self, title, url):
        """Check item auth."""
        return True

    def update_cache(self):
        """Update provider cache."""
        # check if we should update
        if not self.should_update():
            return

        try:
            data = self._get_rss_data()
            data['entries'] = self.provider.remove_duplicate_mappings(data['entries'])
            if self._check_auth(data):
                # clear cache
                self._clear_cache()

                # set updated
                self.updated = time()

                # get last 5 rss cache results
                recent_results = self.provider.recent_results

                # counter for number of items found in cache
                found_recent_results = 0

                results = []
                index = 0
                for index, item in enumerate(data['entries'] or []):
                    if item['link'] in {cache_item['link']
                                        for cache_item in recent_results}:
                        found_recent_results += 1

                    if found_recent_results >= self.provider.stop_at:
                        log.debug('Hit old cached items, not parsing any more for: {0}',
                                  self.provider_id)
                        break
                    try:
                        result = self._parse_item(item)
                        if result is not None:
                            results.append(result)
                    except UnicodeDecodeError as error:
                        log.warning('Unicode decoding error, missed parsing item'
                                    ' from provider {0}: {1!r}',
                                    self.provider.name, error)

                cache_db_con = self._get_db()
                if results:
                    cache_db_con.mass_action(results)

                # finished processing, let's save the newest x (index) items
                # and store up to max_recent_items in cache
                limit = min(index, self.provider.max_recent_items)
                self.provider.recent_results = data['entries'][0:limit]

        except AuthException as error:
            log.error('Authentication error: {0!r}', error)

    def update_cache_manual_search(self, manual_data=None):
        """Update cache using manual search results."""
        # clear cache
        self._clear_cache()

        results = []
        try:
            for item in manual_data:
                log.debug('Adding to cache item found in manual search: {0}',
                          item.name)
                result = self.add_cache_entry(
                    item.name, item.url, item.seeders,
                    item.leechers, item.size, item.pubdate
                )
                if result is not None:
                    results.append(result)
        except Exception as error:
            log.warning('Error while adding to cache item found in manual search'
                        ' for provider {0}, skipping: {1!r}',
                        self.provider.name, error)

        cache_db_con = self._get_db()
        if results:
            log.debug('Mass updating cache table with manual results'
                      ' for provider: {0}', self.provider.name)
            return bool(cache_db_con.mass_action(results))

    def get_rss_feed(self, url, params=None):
        """Get rss feed entries."""
        if self.provider.login():
            # TODO: Check the usage of get_url.
            return getFeed(url, params=params,
                           request_hook=self.provider.session.get)
        return {'entries': []}

    @staticmethod
    def _translate_title(title):
        """Sanitize title."""
        return '{0}'.format(title.replace(' ', '.'))

    @staticmethod
    def _translate_link_url(url):
        """Sanitize url."""
        return url.replace('&amp;', '&')

    def _parse_item(self, item):
        """Parse item to create cache entry."""
        title, url = self._get_title_and_url(item)
        seeders, leechers = self._get_result_info(item)
        size = self._get_size(item)
        pubdate = self._get_pubdate(item)

        self._check_item_auth(title, url)

        if title and url:
            title = self._translate_title(title)
            url = self._translate_link_url(url)

            return self.add_cache_entry(title, url, seeders,
                                        leechers, size, pubdate)

        else:
            log.debug('The data returned from the {0} feed is incomplete,'
                      ' this result is unusable', self.provider.name)
        return None

    @property
    def updated(self):
        """Timestamp of last update."""
        return self._get_time(b'last_update')

    @updated.setter
    def updated(self, value):
        self._set_time(b'last_update', value)

    @property
    def searched(self):
        """Timestamp of last search."""
        return self._get_time(b'lastSearch')

    @searched.setter
    def searched(self, value):
        self._set_time(b'lastSearch', value)

    def _get_time(self, table):
        """Get last provider update."""
        cache_db_con = self._get_db()
        sql_results = cache_db_con.select(
            b'SELECT time '
            b'FROM {name} '
            b'WHERE provider = ?'.format(name=table),
            [self.provider_id]
        )

        if sql_results:
            last_time = int(sql_results[0][b'time'])
            if last_time > int(time()):
                last_time = 0
        else:
            last_time = 0

        return last_time

    def _set_time(self, table, value):
        """Set provider last update."""
        cache_db_con = self._get_db()
        cache_db_con.upsert(
            table,
            {b'time': int(value or 0)},
            {b'provider': self.provider_id}
        )

    def should_update(self):
        """Check if we should update provider cache."""
        # if we've updated recently then skip the update
        if time() - self.updated < self.minTime * 60:
            log.debug('Last update was too soon, using old cache: {0}.'
                      ' Updated less than {1} minutes ago',
                      self.updated, self.minTime)
            return False
        log.debug('Updating providers cache')

        return True

    def add_cache_entry(self, name, url, seeders, leechers, size, pubdate, parsed_result=None):
        """Add item into cache database."""
        try:
            # Use the already passed parsed_result of possible.
            parse_result = parsed_result or NameParser().parse(name)
        except (InvalidNameException, InvalidShowException) as error:
            log.debug('{0}', error)
            return None

        if not parse_result or not parse_result.series_name:
            return None

        # add the parsed result to cache for usage later on
        season = 1
        if parse_result.season_number is not None:
            season = parse_result.season_number

        episodes = parse_result.episode_numbers

        if season is not None and episodes is not None:
            # store episodes as a separated string
            episode_text = '|{0}|'.format(
                '|'.join({str(episode) for episode in episodes if episode})
            )

            # get the current timestamp
            cur_timestamp = int(time())

            # get quality of release
            quality = parse_result.quality

            assert isinstance(name, text_type)

            # get release group
            release_group = parse_result.release_group

            # get version
            version = parse_result.version

            # Store proper_tags as proper1|proper2|proper3
            proper_tags = '|'.join(parse_result.proper_tags)

            if not self.item_in_cache(url):
                log.debug('Added RSS item: {0} to cache: {1} with url {2}', name, self.provider_id, url)
                return [
                    b'INSERT INTO [{name}] '
                    b'   (name, season, episodes, indexerid, url, time, quality, '
                    b'    release_group, version, seeders, leechers, size, pubdate, '
                    b'    proper_tags, date_added, indexer ) '
                    b'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'.format(
                        name=self.provider_id
                    ),
                    [name, season, episode_text, parse_result.series.series_id, url,
                     cur_timestamp, quality, release_group, version,
                     seeders, leechers, size, pubdate, proper_tags, cur_timestamp, parse_result.series.indexer]
                ]
            else:
                log.debug('Updating RSS item: {0} to cache: {1}', name, self.provider_id)
                return [
                    b'UPDATE [{name}] '
                    b'SET name=?, season=?, episodes=?, indexer=?, indexerid=?, '
                    b'    time=?, quality=?, release_group=?, version=?, '
                    b'    seeders=?, leechers=?, size=?, pubdate=?, proper_tags=? '
                    b'WHERE url=?'.format(
                        name=self.provider_id
                    ),
                    [name, season, episode_text, parse_result.series.indexer, parse_result.series.series_id,
                     cur_timestamp, quality, release_group, version,
                     seeders, leechers, size, pubdate, proper_tags, url]
                ]

    def search_cache(self, episode, forced_search=False,
                     down_cur_quality=False):
        """Search cache for needed episodes."""
        needed_eps = self.find_needed_episodes(episode, forced_search,
                                               down_cur_quality)
        return needed_eps[episode] if episode in needed_eps else []

    def item_in_cache(self, url):
        """Check if the url is already available for the specific provider."""
        cache_db_con = self._get_db()
        return cache_db_con.select(
            b'SELECT COUNT(url) '
            b'FROM [{provider}] '
            b'WHERE url=?'.format(provider=self.provider_id), [url]
        )[0][0]

    def find_needed_episodes(self, episode, forced_search=False,
                             down_cur_quality=False):
        """Find needed episodes."""
        needed_eps = {}
        results = []

        cache_db_con = self._get_db()
        if not episode:
            sql_results = cache_db_con.select(
                b'SELECT * FROM [{name}]'.format(name=self.provider_id))
        elif not isinstance(episode, list):
            sql_results = cache_db_con.select(
                b'SELECT * FROM [{name}] '
                b'WHERE indexer = ? AND'
                b'      indexerid = ? AND'
                b'      season = ? AND'
                b'      episodes LIKE ?'.format(name=self.provider_id),
                [episode.series.indexer, episode.series.series_id, episode.season,
                 b'%|{0}|%'.format(episode.episode)]
            )
        else:
            for ep_obj in episode:
                results.append([
                    b'SELECT * FROM [{name}] '
                    b'WHERE indexer = ? AND '
                    b'      indexerid = ? AND'
                    b'      season = ? AND'
                    b'      episodes LIKE ? AND '
                    b'      quality IN ({qualities})'.format(
                        name=self.provider_id,
                        qualities=','.join((str(x)
                                            for x in ep_obj.wanted_quality))
                    ),
                    [ep_obj.series.indexer, ep_obj.series.series_id, ep_obj.season,
                     b'%|{0}|%'.format(ep_obj.episode)]]
                )

            if results:
                # Only execute the query if we have results
                sql_results = cache_db_con.mass_action(results, fetchall=True)
                sql_results = list(itertools.chain(*sql_results))
            else:
                sql_results = []
                log.debug(
                    '{id}: No cached results in {provider} for series {show_name!r} episode {ep}', {
                        'id': episode[0].series.series_id,
                        'provider': self.provider.name,
                        'show_name': episode[0].series.name,
                        'ep': episode_num(episode[0].season, episode[0].episode),
                    }
                )

        # for each cache entry
        for cur_result in sql_results:
            if cur_result[b'indexer'] is None:
                log.debug('Ignoring result: {0}, missing indexer. This is probably a result added'
                          ' prior to medusa version 0.2.0', cur_result[b'name'])
                continue

            search_result = self.provider.get_result()

            # ignored/required words, and non-tv junk
            if not naming.filter_bad_releases(cur_result[b'name']):
                continue

            # get the show, or ignore if it's not one of our shows
            series_obj = Show.find_by_id(app.showList, int(cur_result[b'indexer']), int(cur_result[b'indexerid']))
            if not series_obj:
                continue

            # skip if provider is anime only and show is not anime
            if self.provider.anime_only and not series_obj.is_anime:
                log.debug('{0} is not an anime, skipping', series_obj.name)
                continue

            # get season and ep data (ignoring multi-eps for now)
            search_result.season = int(cur_result[b'season'])
            if search_result.season == -1:
                continue

            cur_ep = cur_result[b'episodes'].split('|')[1]
            if not cur_ep:
                continue

            cur_ep = int(cur_ep)

            search_result.quality = int(cur_result[b'quality'])
            search_result.release_group = cur_result[b'release_group']
            search_result.version = cur_result[b'version']

            # if the show says we want that episode then add it to the list
            if not series_obj.want_episode(search_result.season, cur_ep, search_result.quality,
                                           forced_search, down_cur_quality):
                log.debug('Ignoring {0}', cur_result[b'name'])
                continue

            search_result.episodes = [series_obj.get_episode(search_result.season, cur_ep)]

            search_result.actual_episodes = [search_result.episodes[0].episode]
            search_result.actual_season = search_result.season

            # build a result object
            search_result.name = cur_result[b'name']
            search_result.url = cur_result[b'url']

            log.debug(
                '{id}: Using cached results from {provider} for series {show_name!r} episode {ep}', {
                    'id': search_result.episodes[0].series.series_id,
                    'provider': self.provider.name,
                    'show_name': search_result.episodes[0].series.name,
                    'ep': episode_num(search_result.episodes[0].season, search_result.episodes[0].episode),
                }
            )

            # Map the remaining attributes
            search_result.series = series_obj
            search_result.seeders = cur_result[b'seeders']
            search_result.leechers = cur_result[b'leechers']
            search_result.size = cur_result[b'size']
            search_result.pubdate = cur_result[b'pubdate']
            search_result.proper_tags = cur_result[b'proper_tags'].split('|') if cur_result[b'proper_tags'] else ''
            search_result.content = None

            # FIXME: Should be changed to search_result.search_type
            search_result.forced_search = forced_search

            search_result.download_current_quality = down_cur_quality

            episode_object = search_result.episodes[0]
            # add it to the list
            if episode_object not in needed_eps:
                needed_eps[episode_object] = [search_result]
            else:
                needed_eps[episode_object].append(search_result)

        # datetime stamp this search so cache gets cleared
        self.searched = time()

        return needed_eps
