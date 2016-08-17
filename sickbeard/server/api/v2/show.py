# coding=utf-8
"""Request handler for shows."""

import sickbeard
from sickbeard import (
    helpers, network_timezones, sbdatetime
)
from sickbeard.server.api.v1.core import CMD_ShowCache, CMD_ShowSeasonList, _map_quality
from sickrage.helper.common import (
    dateFormat, timeFormat, try_int
)
from sickrage.helper.exceptions import (
    ShowDirectoryNotFoundException
)
from sickrage.helper.quality import get_quality_string
from sickrage.show.Show import Show
from .base import BaseRequestHandler


class ShowsHandler(BaseRequestHandler):
    """Shows request handler."""

    def get(self, query=''):
        """Query show information.

        :param query:
        :type query: str
        """
        show_id = query.split('/')[0]
        # This should be completely replaced with show_id
        indexerid = show_id

        if show_id:
            # get detailed information about a show
            show_obj = Show.find(sickbeard.showList, int(indexerid))
            if show_obj is None:
                self.api_finish({
                    'status': 404,
                    'error': 'Show not found'
                })

            # @TODO: Replace these with commands from here
            show_dict = {
                'season_list': CMD_ShowSeasonList((), {'indexerid': indexerid}).run()['data'],
                'cache': CMD_ShowCache((), {'indexerid': indexerid}).run()['data'],
                'ids': {}
            }

            genre_list = []
            if show_obj.genre:
                genre_list_tmp = show_obj.genre.split('|')
                for genre in genre_list_tmp:
                    if genre:
                        genre_list.append(genre)

            show_dict['genre'] = genre_list
            show_dict['quality'] = get_quality_string(show_obj.quality)

            any_qualities, best_qualities = _map_quality(show_obj.quality)
            show_dict['quality_details'] = {'initial': any_qualities, 'archive': best_qualities}

            try:
                show_dict['location'] = show_obj.location
            except ShowDirectoryNotFoundException:
                show_dict['location'] = ''

            show_dict['language'] = show_obj.lang
            show_dict['name'] = show_obj.name
            show_dict['paused'] = bool(show_obj.paused)
            show_dict['subtitles'] = bool(show_obj.subtitles)
            show_dict['air_by_date'] = bool(show_obj.air_by_date)
            show_dict['flatten_folders'] = bool(show_obj.flatten_folders)
            show_dict['sports'] = bool(show_obj.sports)
            show_dict['anime'] = bool(show_obj.anime)
            show_dict['airs'] = str(show_obj.airs).replace('am', ' AM').replace('pm', ' PM').replace('  ', ' ')
            show_dict['dvdorder'] = bool(show_obj.dvdorder)

            if show_obj.rls_require_words:
                show_dict['rls_require_words'] = show_obj.rls_require_words.split(', ')
            else:
                show_dict['rls_require_words'] = []

            if show_obj.rls_ignore_words:
                show_dict['rls_ignore_words'] = show_obj.rls_ignore_words.split(', ')
            else:
                show_dict['rls_ignore_words'] = []

            show_dict['scene'] = bool(show_obj.scene)

            show_dict['ids']['thetvdb'] = helpers.mapIndexersToShow(show_obj)[1]
            show_dict['ids']['imdb'] = show_obj.imdbid

            show_dict['network'] = show_obj.network
            if not show_dict['network']:
                show_dict['network'] = ''

            show_dict['status'] = show_obj.status

            if try_int(show_obj.nextaired, 1) > 693595:
                dt_episode_airs = sbdatetime.sbdatetime.convert_to_setting(
                    network_timezones.parse_date_time(show_obj.nextaired, show_dict['airs'], show_dict['network']))
                show_dict['airs'] = sbdatetime.sbdatetime.sbftime(dt_episode_airs, t_preset=timeFormat).lstrip('0').replace(' 0', ' ')
                show_dict['next_ep_airdate'] = sbdatetime.sbdatetime.sbfdate(dt_episode_airs, d_preset=dateFormat)
            else:
                show_dict['next_ep_airdate'] = ''
            self.api_finish(**{'show': show_dict})
        else:
            shows = {}
            for show in sickbeard.showList:
                # If self.get_argument('paused') is None: show all, 0: show un-paused, 1: show paused
                if self.get_argument('paused', default=None) is not None and self.get_argument('paused', default=None) != show.paused:
                    continue

                indexer_show = helpers.mapIndexersToShow(show)

                show_dict = {
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
                    'network': show.network,
                    'name': show.name,
                    'status': show.status,
                    'subtitles': bool(show.subtitles),
                    'cache': CMD_ShowCache((), {'indexerid': show.indexerid}).run()['data']
                }

                if try_int(show.nextaired, 1) > 693595:  # 1900
                    dt_episode_airs = sbdatetime.sbdatetime.convert_to_setting(
                        network_timezones.parse_date_time(show.nextaired, show.airs, show_dict['network'])
                    )
                    show_dict['next_ep_airdate'] = sbdatetime.sbdatetime.sbfdate(dt_episode_airs, d_preset=dateFormat)
                else:
                    show_dict['next_ep_airdate'] = ''

                if not show_dict['network']:
                    show_dict['network'] = ''
                if self.get_argument('sort', default='name') == 'name':
                    shows[show.name] = show_dict
                else:
                    shows[show.indexerid] = show_dict

            self.api_finish(**{'shows': shows})

    def put(self, item_id):
        """Update show information.

        :param item_id:
        :type item_id: int
        """
        # show update
        return self.finish({
        })

    def post(self):
        """Add a show."""
        # add show
        return self.finish({
        })

    def delete(self, item_id):
        """Delete a show.

        :param item_id:
        :type item_id: int
        """
        # delete show
        return self.finish({
        })
