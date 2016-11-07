# coding=utf-8
"""Request handler for shows."""

import medusa as app

from .base import BaseRequestHandler
from ....indexers import indexer_config
from ....show.show import Show
from ....show_queue import ShowQueueActions


class EpisodeIdentifier(object):
    """Episode Identifier."""

    def __init__(self, season, episode, absolute_episode, air_date):
        """Default constructor."""
        self.season = season
        self.episode = episode
        self.absolute_episode = absolute_episode
        self.air_date = air_date

    def __bool__(self):
        """Boolean function."""
        return (self.season or self.episode or self.absolute_episode or self.air_date) is not None

    __nonzero__ = __bool__


class ShowHandler(BaseRequestHandler):
    """Shows request handler."""

    def get(self, show_indexer, show_id, season, episode, absolute_episode, air_date, query):
        """Query show information.

        :param show_indexer:
        :param show_id:
        :type show_id: str
        :param season:
        :param episode:
        :param absolute_episode:
        :param air_date:
        :param query:
        """
        # @TODO: This should be completely replaced with show_id
        show_indexer = indexer_config.mapping[show_indexer] if show_indexer else None
        indexerid = self._parse(show_id)
        season = self._parse(season)
        episode = self._parse(episode)
        absolute_episode = self._parse(absolute_episode)
        air_date = self._parse_date(air_date)

        # @TODO: https://github.com/SiCKRAGETV/SiCKRAGE/pull/2558

        arg_paused = self._parse(self.get_argument('paused', default=None))
        if show_id is not None:
            tv_show = Show.find(app.showList, indexerid, show_indexer)
            if not self._match(tv_show, arg_paused):
                return self.api_finish(status=404, error='Show not found')

            ep_id = EpisodeIdentifier(season, episode, absolute_episode, air_date)
            if ep_id or query == 'episodes':
                return self._handle_episode(tv_show, ep_id, query)

            return self._handle_detailed_show(tv_show, query)

        data = [s.to_json(detailed=False) for s in app.showList if self._match(s, arg_paused)]
        return self._paginate(data, 'title')

    @staticmethod
    def _match(tv_show, paused):
        return tv_show and (paused is None or tv_show.paused == paused)

    def _handle_detailed_show(self, tv_show, query):
        data = tv_show.to_json()
        if query:
            if query == 'queue':
                action, message = app.showQueueScheduler.action.get_queue_action(tv_show)
                data = {
                    'action': ShowQueueActions.names[action],
                    'message': message,
                } if action is not None else dict()
            elif query in data:
                data = data[query]
            else:
                return self.api_finish(status=400, error="Invalid resource path '{0}'".format(query))

        self.api_finish(data=data)

    def _handle_episode(self, tv_show, ep_id, query):
        if (ep_id.episode or ep_id.absolute_episode or ep_id.air_date) is not None:
            tv_episode = self._find_tv_episode(tv_show=tv_show, ep_id=ep_id)
            if not tv_episode:
                return self.api_finish(status=404, error='Episode not found')
            return self._handle_detailed_episode(tv_episode, query)

        tv_episodes = tv_show.get_all_episodes(season=ep_id.season)
        data = [e.to_json(detailed=False) for e in tv_episodes]

        return self._paginate(data, 'airDate')

    @staticmethod
    def _find_tv_episode(tv_show, ep_id):
        """Find TVEpisode based on specified criteria.

        :param tv_show:
        :param ep_id:
        :return:
        :rtype: medusa.tv.TVEpisode or tuple(int, string)
        """
        if ep_id.season is not None and ep_id.episode is not None:
            tv_episode = tv_show.get_episode(season=ep_id.season, episode=ep_id.episode, should_cache=False)
        elif ep_id.absolute_episode is not None:
            tv_episode = tv_show.get_episode(absolute_number=ep_id.absolute_episode, should_cache=False)
        elif ep_id.air_date:
            tv_episode = tv_show.get_episode(air_date=ep_id.air_date, should_cache=False)
        else:
            # if this happens then it's a bug!
            raise ValueError

        if tv_episode and tv_episode.loaded:
            return tv_episode

    def _handle_detailed_episode(self, tv_episode, query):
        data = tv_episode.to_json()
        if query:
            if query == 'metadata':
                data = tv_episode.metadata() if tv_episode.is_location_valid() else dict()
            elif query in data:
                data = data[query]
            else:
                return self.api_finish(status=400, error="Invalid resource path '{0}'".format(query))

        return self.api_finish(data=data)

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
