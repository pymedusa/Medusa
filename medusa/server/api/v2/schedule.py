# coding=utf-8
"""Request handler for series and episodes."""
from __future__ import unicode_literals

import logging
from datetime import datetime

from medusa.logger.adapters.style import BraceAdapter
from medusa.network_timezones import parse_date_time
from medusa.server.api.v2.base import BaseRequestHandler
from medusa.show.coming_episodes import ComingEpisodes


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class ScheduleHandler(BaseRequestHandler):
    """Coming episodes request handler."""

    #: resource name
    name = 'schedule'
    #: identifier
    identifier = None
    #: allowed HTTP methods
    allowed_methods = ('GET',)

    def get(self):
        """Query episode's history information."""
        sort = self.get_argument('sort', default='desc')
        categories = self.get_arguments('category[]') or ['missed']
        paused = self.get_argument('paused', default=False)

        grouped_coming_episodes = ComingEpisodes.get_coming_episodes(categories, sort, True, paused)
        data = {section: [] for section in grouped_coming_episodes}

        for section, coming_episodes in grouped_coming_episodes.items():
            for coming_episode in coming_episodes:
                airs_time = ' '.join(coming_episode['airs'].split(' ')[-2:])
                airdate_oridinal = datetime.strptime(coming_episode['airdate'], '%Y-%m-%d').date().toordinal()
                show_air_time = parse_date_time(airdate_oridinal, airs_time)

                data[section].append({
                    'airdate': coming_episode['airdate'],
                    'airs': coming_episode['airs'],
                    'localAirTime': show_air_time.replace(microsecond=0).isoformat(),
                    'epName': coming_episode['name'],
                    'epPlot': coming_episode['description'],
                    'season': coming_episode['season'],
                    'episode': coming_episode['episode'],
                    'episodeSlug': 's{season:02d}e{episode:02d}'.format(
                        season=coming_episode['season'], episode=coming_episode['episode']
                    ),
                    'indexerId': coming_episode['indexer_id'],
                    'indexer': coming_episode['indexer'],
                    'network': coming_episode['network'],
                    'paused': coming_episode['paused'],
                    'quality': coming_episode['qualityValue'],
                    'showSlug': coming_episode['series_slug'],
                    'showName': coming_episode['show_name'],
                    'showStatus': coming_episode['status'],
                    'tvdbid': coming_episode['tvdbid'],
                    'weekday': coming_episode['weekday'],
                    'runtime': coming_episode['runtime'],
                    'externals': coming_episode['externals']
                })

        return self._ok(data)
