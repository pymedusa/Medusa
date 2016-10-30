# coding=utf-8
"""Request handler for configuration."""
import medusa as app

from .base import BaseRequestHandler
from ....indexers import indexer_config
from ....show.show import Show


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

        arg_sort = self._get_sort(default='airDate')
        arg_sort_order = self._get_sort_order()
        arg_page = self._get_page()
        arg_limit = self._get_limit()

        tv_show = None
        if show_id is not None:
            tv_show = Show.find(app.showList, show_id, show_indexer)
        if not tv_show:
            return self.api_finish(status=404, error='Show not found')

        tv_episode = None
        if episode is None and absolute_episode is None and absolute_episode is None:
            tv_episodes = tv_show.get_all_episodes(season=season)
        else:
            tv_episode = self._find_tv_episode(tv_show=tv_show, season=season, episode=episode,
                                               absolute_episode=absolute_episode, air_date=air_date)
            if not tv_episode:
                return
            tv_episodes = [tv_episode]

        detailed = bool(tv_episode)
        headers = dict()
        data = []
        for item in tv_episodes:
            ep_data = item.to_json(detailed=detailed)
            # multiple results
            if not detailed:
                data.append(ep_data)
                continue

            # detailed single result
            if query:
                if query == 'metadata':
                    ep_data = item.metadata() if item.is_location_valid() else dict()
                elif query not in ep_data:
                    return self.api_finish(status=404, error='{key} not found'.format(key=query))
                else:
                    ep_data = ep_data[query]
            data = ep_data
            break

        if not detailed:
            count = len(data)
            data = self._paginate(data, arg_sort, arg_sort_order, arg_page, arg_limit)
            headers = {
                'X-Pagination-Count': count,
                'X-Pagination-Page': arg_page,
                'X-Pagination-Limit': arg_limit
            }

        self.api_finish(data=data, headers=headers)

    def _find_tv_episode(self, tv_show, season, episode, absolute_episode, air_date):
        """Find TVEpisode based on specified criteria.

        :param tv_show:
        :param season:
        :param episode:
        :param absolute_episode:
        :param air_date:
        :return:
        :rtype: medusa.tv.TVEpisode or tuple(int, string)
        """
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
