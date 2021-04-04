# coding=utf-8
"""Request handler for series and episodes."""
from __future__ import unicode_literals

import logging

from medusa.logger.adapters.style import BraceAdapter
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
                data[section].append({
                    'airdate': coming_episode['airdate'],
                    'airs': coming_episode['airs'],
                    'ep_name': coming_episode['name'],
                    'ep_plot': coming_episode['description'],
                    'episode': coming_episode['episode'],
                    'indexerid': coming_episode['indexer_id'],
                    'network': coming_episode['network'],
                    'paused': coming_episode['paused'],
                    'quality': coming_episode['quality'],
                    'season': coming_episode['season'],
                    'show_name': coming_episode['show_name'],
                    'show_status': coming_episode['status'],
                    'tvdbid': coming_episode['tvdbid'],
                    'weekday': coming_episode['weekday']
                })

        return self._ok(data)
