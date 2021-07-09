# coding=utf-8

"""tv_cache code."""

from __future__ import unicode_literals

import itertools
import logging
import traceback
from builtins import object
from builtins import str
from collections import defaultdict
from time import time

from medusa import (
    app,
    db
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
from medusa.search import FORCED_SEARCH
from medusa.show import naming
from medusa.show.show import Show
from medusa.tv.series import SeriesIdentifier

from six import text_type, viewitems

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
                    'CREATE TABLE [{name}]'
                    '   (identifier TEXT,'
                    '    name TEXT,'
                    '    season NUMERIC,'
                    '    episodes TEXT,'
                    '    indexer NUMERIC,'
                    '    indexerid NUMERIC,'
                    '    url TEXT,'
                    '    time NUMERIC,'
                    '    quality NUMERIC,'
                    '    release_group TEXT,'
                    '    date_added NUMERIC)'.format(name=provider_id))
            else:
                sql_results = self.select(
                    'SELECT identifier, COUNT(identifier) AS count '
                    'FROM [{name}] '
                    'GROUP BY identifier '
                    'HAVING count > 1'.format(name=provider_id)
                )
                for duplicate in sql_results:
                    self.action(
                        'DELETE FROM [{name}] '
                        'WHERE identifier = ?'.format(name=provider_id),
                        [duplicate['identifier']]
                    )

            # remove wrong old index
            self.action('DROP INDEX IF EXISTS idx_url')

            # add unique index if one does not exist to prevent further dupes
            log.debug('Creating UNIQUE IDENTIFIER index for {0}', provider_id)
            self.action(
                'CREATE UNIQUE INDEX '
                'IF NOT EXISTS idx_identifier_{name} '
                'ON [{name}] (identifier)'.format(name=provider_id)
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
                    'CREATE TABLE last_update'
                    '   (provider TEXT, '
                    '    time NUMERIC)'
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

    def load_from_row(self, identifier):
        """Load cached result from a single row."""
        cache_db_con = self._get_db()
        cached_result = cache_db_con.action(
            'SELECT * '
            "FROM '{provider}' "
            'WHERE identifier = ?'.format(provider=self.provider_id),
            [identifier],
            fetchone=True
        )

        return cached_result

    def trim(self, days):
        """
        Remove old items from cache.

        :param days: Number of days to retain
        """
        now = int(time())  # current timestamp
        retention_period = now - (days * 86400)
        log.info('Removing cache entries older than {x} days from {provider}',
                 {'x': days, 'provider': self.provider_id})
        cache_db_con = self._get_db()
        cache_db_con.action(
            'DELETE FROM [{provider}] '
            'WHERE time < ? '.format(provider=self.provider_id),
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

    def _get_identifier(self, item):
        """
        Return the identifier for the item.

        By default this is the url. Providers can overwrite this, when needed.
        """
        return self.provider._get_identifier(item)

    def update_cache(self, search_start_time):
        """Update provider cache."""
        # check if we should update
        if not self.should_update(search_start_time):
            return

        try:
            data = self._get_rss_data()
            if self._check_auth(data):
                # clear cache
                self._clear_cache()

                # set updated start time
                self.updated = search_start_time

                # get last 5 daily cache results
                recent_results = self.provider.recent_results

                # counter for number of items found in cache
                found_recent_results = 0
                search_results = []
                query_results = []
                index = 0

                for index, item in enumerate(data['entries'] or []):
                    try:
                        parsed_result = NameParser().parse(item['title'])
                    except (InvalidNameException, InvalidShowException) as error:
                        log.debug('{0}', error)
                        continue

                    search_result = self.provider.get_result(series=parsed_result.series,
                                                             item=item)
                    if search_result in search_results:
                        continue

                    query_result = self._parse_item(search_result, parsed_result)
                    if query_result is not None:
                        query_results.append(query_result)
                        search_results.append(search_result)

                    if search_result in recent_results:
                        found_recent_results += 1

                    if found_recent_results >= self.provider.stop_at:
                        log.debug('Hit old cached items, not parsing any more for: {0}',
                                  self.provider_id)
                        break

                if query_results:
                    cache_db_con = self._get_db()
                    cache_db_con.mass_action(query_results)

                # finished processing, let's save the newest x (index) items
                # and store up to max_recent_items in cache
                limit = min(index, self.provider.max_recent_items)
                self.provider.recent_results = search_results[0:limit]

        except AuthException as error:
            log.error('Authentication error: {0!r}', error)

    def update_cache_manual_search(self, manual_data=None):
        """Update cache using manual search results."""
        # clear cache
        self._clear_cache()

        results = []
        try:
            for search_result in manual_data:
                log.debug('Adding to cache item found in manual search: {0}',
                          search_result.name)
                result = self.add_cache_entry(search_result)
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

    def _parse_item(self, result, parsed_result):
        """Parse search result to create cache entry."""
        title, url = self._get_title_and_url(result.item)
        self._check_item_auth(title, url)

        if title and url:
            result.title = self._translate_title(title)
            result.url = self._translate_link_url(url)
            return self.add_cache_entry(result, parsed_result)
        else:
            log.debug('The data returned from the {0} feed is incomplete,'
                      ' this result is unusable', self.provider.name)

    @property
    def updated(self):
        """Timestamp of last update."""
        return self._get_time('last_update')

    @updated.setter
    def updated(self, value):
        self._set_time('last_update', value)

    @property
    def searched(self):
        """Timestamp of last search."""
        return self._get_time('lastSearch')

    @searched.setter
    def searched(self, value):
        self._set_time('lastSearch', value)

    def _get_time(self, table):
        """Get last provider update."""
        cache_db_con = self._get_db()
        sql_results = cache_db_con.select(
            'SELECT time '
            'FROM {name} '
            'WHERE provider = ?'.format(name=table),
            [self.provider_id]
        )

        if sql_results:
            last_time = int(sql_results[0]['time'])
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
            {'time': int(value or 0)},
            {'provider': self.provider_id}
        )

    def should_update(self, scheduler_start_time):
        """Check if we should update provider cache."""
        # if we've updated recently then skip the update
        if scheduler_start_time - self.updated < self.minTime * 60:
            log.debug('Last update was too soon, using old cache.'
                      ' Last update ran {0} seconds ago.'
                      ' Updated less than {1} minutes ago.',
                      scheduler_start_time - self.updated, self.minTime)
            return False
        log.debug('Updating providers cache')

        return True

    def add_cache_entry(self, search_result, parsed_result=None):
        """Add item into cache database."""
        if parsed_result is None:
            try:
                parsed_result = NameParser().parse(search_result.name)
            except (InvalidNameException, InvalidShowException) as error:
                log.debug('{0}', error)
                return None

        if not parsed_result or not parsed_result.series_name:
            return None

        # add the parsed result to cache for usage later on
        season = 1
        if parsed_result.season_number is not None:
            season = parsed_result.season_number

        episodes = parsed_result.episode_numbers

        if season is not None and episodes is not None:
            # store episodes as a separated string
            episode_text = '|{0}|'.format(
                '|'.join({str(episode) for episode in episodes if episode})
            )

            # get the current timestamp
            cur_timestamp = int(time())

            # get quality of release
            quality = parsed_result.quality

            name = search_result.name
            assert isinstance(name, text_type)

            # get release group
            release_group = parsed_result.release_group

            # get version
            version = parsed_result.version

            # Store proper_tags as proper1|proper2|proper3
            proper_tags = '|'.join(parsed_result.proper_tags)

            identifier = self._get_identifier(search_result)
            url = search_result.url
            seeders = search_result.seeders
            leechers = search_result.leechers
            size = search_result.size
            pubdate = search_result.pubdate

            if not self.item_in_cache(identifier):
                log.debug('Added item: {0} to cache: {1} with url: {2}', name, self.provider_id, url)
                return [
                    'INSERT INTO [{name}] '
                    '   (identifier, name, season, episodes, indexerid, url, time, quality, '
                    '    release_group, version, seeders, leechers, size, pubdate, '
                    '    proper_tags, date_added, indexer ) '
                    'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'.format(
                        name=self.provider_id
                    ),
                    [identifier, name, season, episode_text, parsed_result.series.series_id, url,
                     cur_timestamp, quality, release_group, version,
                     seeders, leechers, size, pubdate, proper_tags, cur_timestamp, parsed_result.series.indexer]
                ]
            else:
                log.debug('Updating item: {0} to cache: {1}', name, self.provider_id)
                return [
                    'UPDATE [{name}] '
                    'SET name=?, url=?, season=?, episodes=?, indexer=?, indexerid=?, '
                    '    time=?, quality=?, release_group=?, version=?, '
                    '    seeders=?, leechers=?, size=?, pubdate=?, proper_tags=? '
                    'WHERE identifier=?'.format(
                        name=self.provider_id
                    ),
                    [name, url, season, episode_text, parsed_result.series.indexer, parsed_result.series.series_id,
                     cur_timestamp, quality, release_group, version,
                     seeders, leechers, size, pubdate, proper_tags, identifier]
                ]

    def item_in_cache(self, identifier):
        """Check if the url is already available for the specific provider."""
        cache_db_con = self._get_db()
        return cache_db_con.select(
            'SELECT COUNT(url) as count '
            'FROM [{provider}] '
            'WHERE identifier=?'.format(provider=self.provider_id), [identifier]
        )[0]['count']

    def find_needed_episodes(self, episodes, forced_search=False, down_cur_quality=False):
        """
        Search cache for needed episodes.

        NOTE: This is currently only used by the Daily Search.
        The following checks are performed on the cache results:
        * Use the episodes current quality / wanted quality to decide if we want it
        * Filtered on ignored/required words, and non-tv junk
        * Filter out non-anime results on Anime only providers
        * Check if the series is still in our library

        :param episodes: Single or list of episode object(s)
        :param forced_search: Flag to mark that this is searched through a forced search
        :param down_cur_quality: Flag to mark that we want to include the episode(s) current quality

        :return dict(episode: [list of SearchResult objects]).
        """
        results = defaultdict(list)
        cache_results = self.find_episodes(episodes)

        for episode_number, search_results in viewitems(cache_results):
            for search_result in search_results:

                # ignored/required words, and non-tv junk
                if not naming.filter_bad_releases(search_result.name):
                    continue

                wanted_episodes = search_result.series.want_episodes(
                    search_result.actual_season,
                    search_result.actual_episodes,
                    search_result.quality,
                    download_current_quality=search_result.download_current_quality,
                    search_type=search_result.search_type)

                if not wanted_episodes:
                    continue

                log.debug(
                    '{id}: Using cached results from {provider} for series {show_name!r} episode {ep}', {
                        'id': search_result.series.series_id,
                        'provider': self.provider.name,
                        'show_name': search_result.series.name,
                        'ep': episode_num(search_result.episodes[0].season, search_result.episodes[0].episode),
                    }
                )

                if forced_search:
                    search_result.search_type = FORCED_SEARCH
                search_result.download_current_quality = down_cur_quality

                # add it to the list
                results[episode_number].append(search_result)

        return results

    def find_episodes(self, episodes):
        """
        Search cache for episodes.

        NOTE: This is currently only used by the Backlog/Forced Search. As we determine the candidates there.
        The following checks are performed on the cache results:
        * Filter out non-anime results on Anime only providers
        * Check if the series is still in our library
        :param episodes: Single or list of episode object(s)

        :return list of SearchResult objects.
        """
        cache_results = defaultdict(list)
        results = []

        cache_db_con = self._get_db()
        if not episodes:
            sql_results = cache_db_con.select(
                'SELECT * FROM [{name}]'.format(name=self.provider_id))
        elif not isinstance(episodes, list):
            sql_results = cache_db_con.select(
                'SELECT * FROM [{name}] '
                'WHERE indexer = ? AND '
                'indexerid = ? AND '
                'season = ? AND '
                'episodes LIKE ?'.format(name=self.provider_id),
                [episodes.series.indexer, episodes.series.series_id, episodes.season,
                 '%|{0}|%'.format(episodes.episode)]
            )
        else:
            for ep_obj in episodes:
                results.append([
                    'SELECT * FROM [{name}] '
                    'WHERE indexer = ? AND '
                    'indexerid = ? AND '
                    'season = ? AND '
                    'episodes LIKE ?'.format(
                        name=self.provider_id
                    ),
                    [ep_obj.series.indexer, ep_obj.series.series_id, ep_obj.season,
                     '%|{0}|%'.format(ep_obj.episode)]]
                )

            if len(episodes) > 1:
                results.append([
                    'SELECT * FROM [{name}] '
                    'WHERE indexer = ? AND '
                    'indexerid = ? AND '
                    'season = ? AND '
                    'episodes == "||"'.format(
                        name=self.provider_id
                    ),
                    [ep_obj.series.indexer, ep_obj.series.series_id, ep_obj.season]
                ])

            if results:
                # Only execute the query if we have results
                sql_results = cache_db_con.mass_action(results, fetchall=True)
                sql_results = list(itertools.chain(*sql_results))
            else:
                sql_results = []
                log.debug(
                    '{id}: No cached results in {provider} for series {show_name!r} episode {ep}', {
                        'id': episodes[0].series.series_id,
                        'provider': self.provider.name,
                        'show_name': episodes[0].series.name,
                        'ep': episode_num(episodes[0].season, episodes[0].episode),
                    }
                )

        # for each cache entry
        for cur_result in sql_results:
            if cur_result['indexer'] is None:
                log.debug('Ignoring result: {0}, missing indexer. This is probably a result added'
                          ' prior to medusa version 0.2.0', cur_result['name'])
                continue

            # get the show, or ignore if it's not one of our shows
            series_obj = Show.find_by_id(app.showList, int(cur_result['indexer']), int(cur_result['indexerid']))
            if not series_obj:
                continue

            # skip if provider is anime only and show is not anime
            if self.provider.anime_only and not series_obj.is_anime:
                log.debug('{0} is not an anime, skipping', series_obj.name)
                continue

            search_result = self.provider.get_result(series=series_obj, cache=cur_result)
            if search_result in cache_results[search_result.episode_number]:
                continue
            # add it to the list
            cache_results[search_result.episode_number].append(search_result)

        # datetime stamp this search so cache gets cleared
        self.searched = time()

        return cache_results

    def get_results(self, show_slug=None, season=None, episode=None):
        """Get cached results for this provider."""
        cache_db_con = self._get_db()

        param = []
        where = []

        if show_slug:
            show = SeriesIdentifier.from_slug(show_slug)
            where += ['indexer', 'indexerid']
            param += [show.indexer.id, show.id]

        if season:
            where += ['season']
            param += [season]

        if episode:
            where += ['episodes']
            param += ['|{0}|'.format(episode)]

        base_sql = 'SELECT * FROM [{name}]'.format(name=self.provider_id)
        base_params = []

        if where and param:
            base_sql += ' WHERE '
            base_sql += ' AND '.join([item + ' = ? ' for item in where])
            base_params += param

        results = cache_db_con.select(
            base_sql,
            base_params
        )

        return results
