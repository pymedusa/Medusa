# coding=utf-8
"""Request handler for shows."""

import datetime
import os

import medusa as app

from .... import db, helpers, image_cache, network_timezones, sbdatetime
from ....common import Quality, statusStrings
from ....helper.common import dateFormat, try_int
from ....helper.quality import get_quality_string
from ....server.api.v1.core import _map_quality
from ....show.Show import Show
from .base import BaseRequestHandler

MILLIS_YEAR_1900 = datetime.datetime(year=1900, month=1, day=1).toordinal()


class ShowHandler(BaseRequestHandler):
    """Shows request handler."""

    def get(self, show_id):
        """Query show information.

        :param show_id:
        :type show_id: str
        """
        # @TODO: This should be completely replaced with show_id
        indexerid = show_id

        # @TODO: https://github.com/SiCKRAGETV/SiCKRAGE/pull/2558

        arg_paused = self.get_argument('paused', default=None)
        arg_sort = self.get_argument('sort', default='name')
        arg_page = self.get_argument('page', default=1)
        arg_limit = self.get_argument('limit', default=20)

        shows = []
        show_list = app.showList if not show_id else [Show.find(app.showList, int(indexerid))]
        for show in show_list:
            if show_id and show is None:
                return self.api_finish(status=404, error='Show not found')

            # If self.get_argument('paused') is None: show all, 0: show un-paused, 1: show paused
            if arg_paused is not None and try_int(arg_paused, -1) != show.paused:
                continue

            indexer_show = helpers.mapIndexersToShow(show)

            dt_episode_airs = (
                sbdatetime.sbdatetime.convert_to_setting(
                    network_timezones.parse_date_time(show.nextaired, show.airs, show.network)
                ) if try_int(show.nextaired, 1) > MILLIS_YEAR_1900 else None)

            cache_obj = image_cache.ImageCache()
            show_dict = {
                'name': show.name,
                'paused': bool(show.paused),
                'quality': get_quality_string(show.quality),
                'language': show.lang,
                'airByDate': bool(show.air_by_date),
                'sports': bool(show.sports),
                'anime': bool(show.anime),
                'queue': {
                    'raw': '',
                    'pretty': ''
                },
                'ids': {
                    'thetvdb': indexer_show[1],
                    'imdb': show.imdbid,
                },
                'network': show.network if show.network else '',
                'nextAirdate': sbdatetime.sbdatetime.sbfdate(dt_episode_airs, d_preset=dateFormat) if dt_episode_airs else '',
                'status': show.status,
                'subtitles': bool(show.subtitles),
                'cache': {
                    'poster': bool(os.path.isfile(cache_obj.poster_path(show.indexerid))),
                    'banner': bool(os.path.isfile(cache_obj.banner_path(show.indexerid)))
                },
                'startYear': show.imdb_info['year'] if show.imdb_info.get('year') else show.startyear,
                'runtime': show.imdb_info['runtimes'] if show.imdb_info.get('runtimes') else show.runtime,
                'countries': show.imdb_info['country_codes'].split('|') if 'country_codes' in show.imdb_info else []
            }

            if app.showQueueScheduler.action.isBeingAdded(show):
                show_dict.queue.raw = 'isBeingAdded'
                show_dict.queue.pretty = 'This show is in the process of being downloaded - the info below is incomplete.'

            elif app.showQueueScheduler.action.isBeingUpdated(show):
                show_dict.queue.raw = 'isBeingUpdated'
                show_dict.queue.pretty = 'The information on this page is in the process of being updated.'

            elif app.showQueueScheduler.action.isBeingRefreshed(show):
                show_dict.queue.raw = 'isBeingRefreshed'
                show_dict.queue.pretty = 'The episodes below are currently being refreshed from disk'

            elif app.showQueueScheduler.action.isBeingSubtitled(show):
                show_dict.queue.raw = 'isBeingSubtitled'
                show_dict.queue.pretty = 'Currently downloading subtitles for this show'

            elif app.showQueueScheduler.action.isInRefreshQueue(show):
                show_dict.queue.raw = 'isInRefreshQueue'
                show_dict.queue.pretty = 'This show is queued to be refreshed.'

            elif app.showQueueScheduler.action.isInUpdateQueue(show):
                show_dict.queue.raw = 'isInUpdateQueue'
                show_dict.queue.pretty = 'This show is queued and awaiting an update.'

            elif app.showQueueScheduler.action.isInSubtitleQueue(show):
                show_dict.queue.raw = 'isInSubtitleQueue'
                show_dict.queue.pretty = 'This show is queued and awaiting subtitles download.'

            # Detailed information
            if show_id:
                any_qualities, best_qualities = _map_quality(show.quality)

                # ------ START OF SEASONS ------
                main_db_con = db.DBConnection(row_type='dict')

                sql_results = main_db_con.select(
                    'SELECT name, episode, airdate, release_name, season, hasnfo, hastbn, location, absolute_number, file_size, subtitles, status FROM tv_episodes WHERE showid = ?',
                    [show_id])
                seasons = [{'episodes': [], 'seasonNumber': 0}]
                for row in sql_results:
                    status, quality = Quality.splitCompositeStatus(int(row['status']))
                    row['status'] = {
                        'raw': status,
                        'pretty': statusStrings[status]
                    }
                    row['quality'] = get_quality_string(quality)
                    row['hasnfo'] = bool(row['hasnfo'])
                    row['hastbn'] = bool(row['hastbn'])
                    row['seasonNumber'] = int(row['season'])
                    row['episodeNumber'] = int(row['episode'])
                    row['absoluteNumber'] = row['absolute_number']
                    row['fileSize'] = row['file_size']
                    row['releaseName'] = row['release_name']
                    row['subtitles'] = filter(None, (row['subtitles'] or '').split(','))
                    del row['season']
                    del row['episode']
                    del row['absolute_number']
                    del row['file_size']
                    del row['release_name']
                    if len(seasons) is not row['seasonNumber'] + 1:
                        seasons.append({'episodes': [], 'seasonNumber': row['seasonNumber']})
                    seasons[row['seasonNumber']]['episodes'].append(row)
                # ------ END OF SEASONS ------

                ratings = {}
                if show.imdb_info:
                    ratings.imdb = {
                        'stars': show.imdb_info['rating'],
                        'votes': show.imdb_info['votes']
                    }
                detailed = {
                    'seasons': seasons,
                    'genres': [genre for genre in show.genre.split('|') if genre] if show.genre else [],
                    'qualityDetails': {'initial': any_qualities, 'archive': best_qualities},
                    'location': show.raw_location,
                    'flattenFolders': bool(show.flatten_folders),
                    'airs': str(show.airs).replace('am', ' AM').replace('pm', ' PM').replace('  ', ' '),
                    'dvdOrder': bool(show.dvdorder),
                    'rlsRequireWords': [w.strip() for w in show.rls_require_words.split(',')] if show.rls_require_words else [],
                    'rlsIgnoreWords': [w.strip() for w in show.rls_ignore_words.split(',')] if show.rls_ignore_words else [],
                    'scene': bool(show.scene),
                    'ratings': ratings
                }
                show_dict.update(detailed)

                return self.api_finish(data={'shows': [show_dict]})
            shows.append(show_dict)

        self.api_finish(data={'shows': shows}, headers={
            'X-Pagination-Count': len(app.showList),
            'X-Pagination-Page': arg_page,
            'X-Pagination-Limit': arg_limit
        })

    def put(self, show_id):
        """Update show information.

        :param show_id:
        :type show_id: str
        """
        return self.api_finish()

    def post(self):
        """Add a show."""
        return self.api_finish()

    def delete(self, show_id):
        """Delete a show.

        :param show_id:
        :type show_id: str
        """
        error, show = Show.delete(indexer_id=show_id, remove_files=self.get_argument('remove_files', default=False))
        return self.api_finish(error=error, data=show)
