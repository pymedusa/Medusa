# coding=utf-8
"""Request handler for configuration."""
import os

import knowit
import medusa as app

from .base import BaseRequestHandler
from ....indexers import indexer_config
from ....show.Show import Show


class EpisodeHandler(BaseRequestHandler):
    """Episode request handler."""

    def get(self, show_indexer, show_id, season, episode, absolute_episode, air_date, query=None):
        """Find and return TVEpisode information.

        :param show_indexer:
        :param show_id:
        :param season:
        :param episode:
        :param absolute_episode:
        :param air_date:
        :param query:
        :return:
        """
        show_indexer = indexer_config.mapping[show_indexer]
        show_id = self._parse(show_id)
        season = self._parse(season)
        episode = self._parse(episode)
        absolute_episode = self._parse(absolute_episode)
        air_date = self._parse_date(air_date)

        tv_episode = self._find_tv_episode(show_indexer=show_indexer, show_id=show_id, season=season,
                                           episode=episode, absolute_episode=absolute_episode, air_date=air_date)

        if tv_episode:
            data = tv_episode.to_json()
            if query:
                if query == 'metadata':
                    if not tv_episode.location or not os.path.isfile(tv_episode.location):
                        return self.api_finish(status=404, error='Episode video file not found')
                    data = knowit.know(tv_episode.location)
                elif query not in data:
                    return self.api_finish(status=404, error='{key} not found'.format(key=query))
                else:
                    data = data[query]

            self.api_finish(data=data)

    def _find_tv_episode(self, show_indexer, show_id, season, episode, absolute_episode, air_date):
        """Find a TVEpisode based on specified numbering.

        :param show_indexer:
        :param show_id:
        :param season:
        :param episode:
        :param absolute_episode:
        :param air_date:
        :return:
        :rtype: medusa.tv.TVEpisode
        """
        tv_show = None
        if show_id is not None:
            tv_show = Show.find(app.showList, show_id, show_indexer)
        if not tv_show:
            return self.api_finish(status=404, error='Show not found')

        if season is not None and episode is not None:
            tv_episode = tv_show.get_episode(season=season, episode=episode, should_cache=False)
        elif absolute_episode is not None and tv_show.is_anime:
            tv_episode = tv_show.get_episode(absolute_episode=absolute_episode, should_cache=False)
        elif air_date:
            tv_episode = tv_show.get_episode(air_date=air_date, should_cache=False)
        else:
            return self.api_finish(status=400, error='Bad Request')

        if not tv_episode:
            return self.api_finish(status=404, error='Episode not found')

        return tv_episode
