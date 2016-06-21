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

from __future__ import unicode_literals

import time
import datetime
import itertools
import traceback
import sickbeard
from sickbeard import db
from sickbeard import logger
from sickbeard.rssfeeds import getFeed
from sickbeard import show_name_helpers
from sickrage.helper.exceptions import AuthException, ex
from sickrage.show.Show import Show
from sickbeard.name_parser.parser import NameParser, InvalidNameException, InvalidShowException


class CacheDBConnection(db.DBConnection):
    def __init__(self, provider_id):
        db.DBConnection.__init__(self, 'cache.db')

        # Create the table if it's not already there
        try:
            if not self.hasTable(provider_id):
                logger.log('Creating cache table for provider {0}'.format(provider_id), logger.DEBUG)
                self.action(
                    b'CREATE TABLE [{provider_id}] (name TEXT, season NUMERIC, episodes TEXT, indexerid NUMERIC, '
                    b'url TEXT, time NUMERIC, quality NUMERIC, release_group TEXT)'.format(provider_id=provider_id))
            else:
                sql_results = self.select(b'SELECT url, COUNT(url) AS count FROM [{provider_id}] '
                                          b'GROUP BY url HAVING count > 1'.format(provider_id=provider_id))

                for cur_dupe in sql_results:
                    self.action(b'DELETE FROM [{provider_id}] WHERE url = ?'.format(provider_id=provider_id), [cur_dupe[b'url']])

            # remove wrong old index
            self.action(b'DROP INDEX IF EXISTS idx_url')

            # add unique index to prevent further dupes from happening if one does not exist
            logger.log('Creating UNIQUE URL index for {0}'.format(provider_id), logger.DEBUG)
            self.action(b'CREATE UNIQUE INDEX IF NOT EXISTS idx_url_{0}  ON [{1}] (url)'.
                        format(provider_id, provider_id))

            # add release_group column to table if missing
            if not self.hasColumn(provider_id, 'release_group'):
                self.addColumn(provider_id, 'release_group', 'TEXT', '')

            # add version column to table if missing
            if not self.hasColumn(provider_id, 'version'):
                self.addColumn(provider_id, 'version', 'NUMERIC', '-1')

            # add seeders column to table if missing
            if not self.hasColumn(provider_id, 'seeders'):
                self.addColumn(provider_id, 'seeders', 'NUMERIC', '-1')

            # add leechers column to table if missing
            if not self.hasColumn(provider_id, 'leechers'):
                self.addColumn(provider_id, 'leechers', 'NUMERIC', '-1')

            # add size column to table if missing
            if not self.hasColumn(provider_id, 'size'):
                self.addColumn(provider_id, 'size', 'NUMERIC', '-1')

            # add pubdate column to table if missing
            if not self.hasColumn(provider_id, 'pubdate'):
                self.addColumn(provider_id, 'pubdate', 'NUMERIC', '')

            # add hash column to table if missing
            if not self.hasColumn(provider_id, 'hash'):
                self.addColumn(provider_id, 'hash', 'NUMERIC', '')

        except Exception as e:
            if str(e) != 'table [{provider_id}] already exists'.format(provider_id=provider_id):
                raise

        # Create the table if it's not already there
        try:
            if not self.hasTable('lastUpdate'):
                self.action(b'CREATE TABLE lastUpdate (provider TEXT, time NUMERIC)')
        except Exception as e:
            logger.log('Error while searching {provider_id}, skipping: {e!r}'.
                       format(provider_id=self.provider.name, e=e), logger.DEBUG)
            logger.log(traceback.format_exc(), logger.DEBUG)
            if str(e) != 'table lastUpdate already exists':
                raise


class TVCache(object):
    def __init__(self, provider, **kwargs):
        self.provider = provider
        self.provider_id = self.provider.get_id()
        self.provider_db = None
        self.minTime = kwargs.pop('min_time', 10)
        self.search_params = kwargs.pop('search_params', dict(RSS=['']))

    def _get_db(self):
        # init provider database if not done already
        if not self.provider_db:
            self.provider_db = CacheDBConnection(self.provider_id)

        return self.provider_db

    def _clearCache(self):
        """
        Performs requalar cache cleaning as required
        """
        # if cache trimming is enabled
        if sickbeard.CACHE_TRIMMING:
            # trim items older than MAX_CACHE_AGE days
            self.trim_cache(days=sickbeard.MAX_CACHE_AGE)

    def trim_cache(self, days=None):
        """
        Remove old items from cache

        :param days: Number of days to retain
        """
        if days:
            now = int(time.time())  # current timestamp
            retention_period = now - (days * 86400)
            logger.log('Removing cache entries older than {x} days from {provider}'.format
                       (x=days, provider=self.provider_id))
            cache_db_con = self._get_db()
            cache_db_con.action(
                b'DELETE FROM [{provider}] '
                b'WHERE time < ? '.format(provider=self.provider_id),
                [retention_period]
            )

    def _get_title_and_url(self, item):
        return self.provider._get_title_and_url(item)  # pylint:disable=protected-access

    def _get_result_info(self, item):
        return self.provider._get_result_info(item)

    def _get_size(self, item):
        return self.provider._get_size(item)

    def _get_pubdate(self, item):
        """
        Return publish date of the item. If provider doesnt
        have _get_pubdate function this will be used
        """
        return self.provider._get_pubdate(item)

    def _get_hash(self, item):
        """
        Return hash of the item. If provider doesnt
        have _get_hash function this will be used
        """
        return self.provider._get_hash(item)

    def _getRSSData(self):
        return {'entries': self.provider.search(self.search_params)} if self.search_params else None

    def _checkAuth(self, data):  # pylint:disable=unused-argument, no-self-use
        return True

    def _checkItemAuth(self, title, url):  # pylint:disable=unused-argument, no-self-use
        return True

    def updateCache(self):
        # check if we should update
        if not self.shouldUpdate():
            return

        try:
            data = self._getRSSData()
            if self._checkAuth(data):
                # clear cache
                self._clearCache()

                # set updated
                self.setLastUpdate()

                # get last 5 rss cache results
                recent_results = self.provider.recent_results
                found_recent_results = 0  # A counter that keeps track of the number of items that have been found in cache

                cl = []
                index = 0
                for index, item in enumerate(data['entries'] or []):
                    if item['link'] in {cache_item['link'] for cache_item in recent_results}:
                        found_recent_results += 1

                    if found_recent_results >= self.provider.stop_at:
                        logger.log('Hit the old cached items, not parsing any more for: {0}'.format
                                   (self.provider_id), logger.DEBUG)
                        break
                    try:
                        ci = self._parseItem(item)
                        if ci is not None:
                            cl.append(ci)
                    except UnicodeDecodeError as e:
                        logger.log('Unicode decoding error, missed parsing item from provider {0}: {1!r}'.format
                                   (self.provider.name, e), logger.WARNING)

                cache_db_con = self._get_db()
                if cl:
                    cache_db_con.mass_action(cl)

                # finished processing, let's save the newest x (index) items and store these in cache with a max of 5 
                # (overwritable per provider, throug hthe max_recent_items attribute.
                self.provider.recent_results = data['entries'][0:min(index, self.provider.max_recent_items)]

        except AuthException as e:
            logger.log('Authentication error: {0!r}'.format(e), logger.ERROR)
        except Exception as e:
            logger.log('Error while searching {0}, skipping: {1!r}'.format(self.provider.name, e), logger.DEBUG)

    def update_cache_manual_search(self, manual_data=None):

        try:
            cl = []
            for item in manual_data:
                logger.log('Adding to cache item found in manual search: {0}'.format(item.name), logger.DEBUG)
                ci = self._addCacheEntry(item.name, item.url, item.seeders, item.leechers, item.size, item.pubdate, item.hash)
                if ci is not None:
                    cl.append(ci)
        except Exception as e:
            logger.log('Error while adding to cache item found in manual seach for provider {0},'
                       ' skipping: {1!r}'.format(self.provider.name, e), logger.WARNING)

        results = []
        cache_db_con = self._get_db()
        if cl:
            logger.log('Mass updating cache table with manual results for provider: {0}'.
                       format(self.provider.name), logger.DEBUG)
            results = cache_db_con.mass_action(cl)

        return any(results)

    def getRSSFeed(self, url, params=None):
        if self.provider.login():
            return getFeed(url, params=params, request_hook=self.provider.get_url)
        return {'entries': []}

    @staticmethod
    def _translateTitle(title):
        return '{0}'.format(title.replace(' ', '.'))

    @staticmethod
    def _translateLinkURL(url):
        return url.replace('&amp;', '&')

    def _parseItem(self, item):
        title, url = self._get_title_and_url(item)
        seeders, leechers = self._get_result_info(item)
        size = self._get_size(item)
        pubdate = self._get_pubdate(item)
        torrent_hash = self._get_hash(item)

        self._checkItemAuth(title, url)

        if title and url:
            title = self._translateTitle(title)
            url = self._translateLinkURL(url)

            # logger.log('Attempting to add item to cache: ' + title, logger.DEBUG)
            return self._addCacheEntry(title, url, seeders, leechers, size, pubdate, torrent_hash)

        else:
            logger.log(
                'The data returned from the {0} feed is incomplete, this result is unusable'.format(self.provider.name),
                logger.DEBUG)

        return False

    def _getLastUpdate(self):
        cache_db_con = self._get_db()
        sql_results = cache_db_con.select(b'SELECT time FROM lastUpdate WHERE provider = ?', [self.provider_id])

        if sql_results:
            lastTime = int(sql_results[0][b'time'])
            if lastTime > int(time.mktime(datetime.datetime.today().timetuple())):
                lastTime = 0
        else:
            lastTime = 0

        return datetime.datetime.fromtimestamp(lastTime)

    def _getLastSearch(self):
        cache_db_con = self._get_db()
        sql_results = cache_db_con.select(b'SELECT time FROM lastSearch WHERE provider = ?', [self.provider_id])

        if sql_results:
            lastTime = int(sql_results[0][b'time'])
            if lastTime > int(time.mktime(datetime.datetime.today().timetuple())):
                lastTime = 0
        else:
            lastTime = 0

        return datetime.datetime.fromtimestamp(lastTime)

    def setLastUpdate(self, toDate=None):
        if not toDate:
            toDate = datetime.datetime.today()

        cache_db_con = self._get_db()
        cache_db_con.upsert(
            b'lastUpdate',
            {b'time': int(time.mktime(toDate.timetuple()))},
            {b'provider': self.provider_id}
        )

    def setLastSearch(self, toDate=None):
        if not toDate:
            toDate = datetime.datetime.today()

        cache_db_con = self._get_db()
        cache_db_con.upsert(
            b'lastSearch',
            {b'time': int(time.mktime(toDate.timetuple()))},
            {b'provider': self.provider_id}
        )

    lastUpdate = property(_getLastUpdate)
    lastSearch = property(_getLastSearch)

    def shouldUpdate(self):
        # if we've updated recently then skip the update
        if datetime.datetime.today() - self.lastUpdate < datetime.timedelta(minutes=self.minTime):
            logger.log('Last update was too soon, using old cache: {0}. '
                       'Updated less then {1} minutes ago'.format(self.lastUpdate, self.minTime), logger.DEBUG)
            return False

        return True

    def shouldClearCache(self):
        # # if daily search hasn't used our previous results yet then don't clear the cache
        # if self.lastUpdate > self.lastSearch:
        #     return False

        return False

    def _addCacheEntry(self, name, url, seeders, leechers, size, pubdate, torrent_hash):

        try:
            parse_result = NameParser().parse(name)
        except (InvalidNameException, InvalidShowException) as error:
            logger.log('{0}'.format(error), logger.DEBUG)
            return None

        if not parse_result or not parse_result.series_name:
            return None

        # if we made it this far then lets add the parsed result to cache for usager later on
        season = parse_result.season_number if parse_result.season_number is not None else 1
        episodes = parse_result.episode_numbers

        if season is not None and episodes is not None:
            # store episodes as a seperated string
            episodeText = '|{0}|'.format('|'.join({str(episode) for episode in episodes if episode}))

            # get the current timestamp
            cur_timestamp = int(time.mktime(datetime.datetime.today().timetuple()))

            # get quality of release
            quality = parse_result.quality

            assert isinstance(name, unicode)

            # get release group
            release_group = parse_result.release_group

            # get version
            version = parse_result.version

            logger.log('Added RSS item: [{0}] to cache: [{1}]'.format(name, self.provider_id), logger.DEBUG)

            return [
                b'INSERT OR REPLACE INTO [{provider_id}] (name, season, episodes, indexerid, url, time, quality, release_group, version, seeders, '
                b'leechers, size, pubdate, hash) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)'.format(provider_id=self.provider_id),
                [name, season, episodeText, parse_result.show.indexerid, url, cur_timestamp, quality,
                 release_group, version, seeders, leechers, size, pubdate, torrent_hash]]

    def searchCache(self, episode, forced_search=False, downCurQuality=False):
        needed_eps = self.findNeededEpisodes(episode, forced_search, downCurQuality)
        return needed_eps[episode] if episode in needed_eps else []

    def listPropers(self, date=None):
        cache_db_con = self._get_db()
        sql = b"SELECT * FROM [{provider_id}] WHERE name LIKE '%.PROPER.%' OR name LIKE '%.REPACK.%'".format(provider_id=self.provider_id)

        if date is not None:
            sql += b' AND time >= {0}'.format(int(time.mktime(date.timetuple())))

        propers_results = cache_db_con.select(sql)
        return [x for x in propers_results if x[b'indexerid']]

    def findNeededEpisodes(self, episode, forced_search=False, downCurQuality=False):  # pylint:disable=too-many-locals, too-many-branches
        needed_eps = {}
        cl = []

        cache_db_con = self._get_db()
        if not episode:
            sql_results = cache_db_con.select(b'SELECT * FROM [{provider_id}]'.format(provider_id=self.provider_id))
        elif not isinstance(episode, list):
            sql_results = cache_db_con.select(
                b'SELECT * FROM [{provider_id}] WHERE indexerid = ? AND season = ? AND episodes LIKE ?'.format(provider_id=self.provider_id),
                [episode.show.indexerid, episode.season, b'%|{0}|%'.format(episode.episode)])
        else:
            for ep_obj in episode:
                cl.append([
                    b'SELECT * FROM [{0}] WHERE indexerid = ? AND season = ? AND episodes LIKE ? AND quality IN ({1})'.
                    format(self.provider_id, ','.join([str(x) for x in ep_obj.wantedQuality])),
                    [ep_obj.show.indexerid, ep_obj.season, b'%|{0}|%'.format(ep_obj.episode)]])

            sql_results = cache_db_con.mass_action(cl, fetchall=True)
            sql_results = list(itertools.chain(*sql_results))

        # for each cache entry
        for cur_result in sql_results:
            # ignored/required words, and non-tv junk
            if not show_name_helpers.filterBadReleases(cur_result[b'name']):
                continue

            # get the show object, or if it's not one of our shows then ignore it
            show_obj = Show.find(sickbeard.showList, int(cur_result[b'indexerid']))
            if not show_obj:
                continue

            # skip if provider is anime only and show is not anime
            if self.provider.anime_only and not show_obj.is_anime:
                logger.log('{0} is not an anime, skiping'.format(show_obj.name), logger.DEBUG)
                continue

            # get season and ep data (ignoring multi-eps for now)
            cur_season = int(cur_result[b'season'])
            if cur_season == -1:
                continue

            cur_ep = cur_result[b'episodes'].split('|')[1]
            if not cur_ep:
                continue

            cur_ep = int(cur_ep)

            cur_quality = int(cur_result[b'quality'])
            cur_release_group = cur_result[b'release_group']
            cur_version = cur_result[b'version']

            # if the show says we want that episode then add it to the list
            if not show_obj.wantEpisode(cur_season, cur_ep, cur_quality, forced_search, downCurQuality):
                logger.log('Ignoring {0}'.format(cur_result[b'name']), logger.DEBUG)
                continue

            ep_obj = show_obj.getEpisode(cur_season, cur_ep)

            # build a result object
            title = cur_result[b'name']
            url = cur_result[b'url']

            logger.log('Found result {0} at {1}'.format(title, url))

            result = self.provider.get_result([ep_obj])
            result.show = show_obj
            result.url = url
            result.seeders = cur_result[b'seeders']
            result.leechers = cur_result[b'leechers']
            result.size = cur_result[b'size']
            result.pubdate = cur_result[b'pubdate']
            result.hash = cur_result[b'hash']
            result.name = title
            result.quality = cur_quality
            result.release_group = cur_release_group
            result.version = cur_version
            result.content = None

            # add it to the list
            if ep_obj not in needed_eps:
                needed_eps[ep_obj] = [result]
            else:
                needed_eps[ep_obj].append(result)

        # datetime stamp this search so cache gets cleared
        self.setLastSearch()

        return needed_eps
