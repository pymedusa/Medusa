# coding=utf-8
"""Request handler for shows."""

import datetime

import medusa as sickbeard
from .base import BaseRequestHandler
from .... import helpers, network_timezones, sbdatetime
from ....helper.common import dateFormat, try_int
from ....helper.quality import get_quality_string
from ....server.api.v1.core import CMD_ShowCache, CMD_ShowSeasonList, _map_quality
from ....show.Show import Show

MILLIS_YEAR_1900 = datetime.datetime(year=1900, month=1, day=1).toordinal()


class ShowHandler(BaseRequestHandler):
    """Shows request handler."""

    def get(self, show_id):
        """Query show information.

        :param show_id:
        :type show_id: str
        """
        # This should be completely replaced with show_id
        indexerid = show_id

        arg_paused = self.get_argument('paused', default=None)
        arg_sort = self.get_argument('sort', default='name')

        shows = {}
        show_list = sickbeard.showList if not show_id else [Show.find(sickbeard.showList, int(indexerid))]
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

            show_dict = {
                'name': show.name,
                'paused': bool(show.paused),
                'quality': get_quality_string(show.quality),
                'language': show.lang,
                'air_by_date': bool(show.air_by_date),
                'sports': bool(show.sports),
                'anime': bool(show.anime),
                'ids': {
                    'thetvdb': indexer_show[1],
                    'imdb': show.imdbid,
                },
                'network': show.network if show.network else '',
                'next_ep_airdate': sbdatetime.sbdatetime.sbfdate(dt_episode_airs, d_preset=dateFormat) if dt_episode_airs else '',
                'status': show.status,
                'subtitles': bool(show.subtitles),
                'cache': CMD_ShowCache((), {'indexerid': show.indexerid}).run()['data']
            }

            # Detailed information
            if show_id:
                any_qualities, best_qualities = _map_quality(show.quality)

                # @TODO: Replace these with commands from here
                detailed = {
                    'season_list': CMD_ShowSeasonList((), {'indexerid': indexerid}).run()['data'],
                    'genre': [genre for genre in show.genre.split('|') if genre] if show.genre else [],
                    'quality_details': {'initial': any_qualities, 'archive': best_qualities},
                    'location': show.raw_location,
                    'flatten_folders': bool(show.flatten_folders),
                    'airs': str(show.airs).replace('am', ' AM').replace('pm', ' PM').replace('  ', ' '),
                    'dvdorder': bool(show.dvdorder),
                    'rls_require_words': [w.strip() for w in show.rls_require_words.split(',')] if show.rls_require_words else [],
                    'rls_ignore_words': [w.strip() for w in show.rls_ignore_words.split(',')] if show.rls_ignore_words else [],
                    'scene': bool(show.scene),
                }
                show_dict.update(detailed)

                return self.api_finish(**{'show': show_dict})

            key = show.name if arg_sort == 'name' else show.indexerid
            shows[key] = show_dict

        self.api_finish(**{'shows': shows})

    def put(self, show_id):
        """Update show information.

        :param show_id:
        :type show_id: int
        """
        return self.finish({
        })

    def post(self):
        """Add a show."""
        return self.finish({
        })

    def delete(self, show_id):
        """Delete a show.

        :param show_id:
        :type show_id: int
        """
        return self.finish({
        })
