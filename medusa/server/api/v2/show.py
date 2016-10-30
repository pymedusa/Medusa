# coding=utf-8
"""Request handler for shows."""

import medusa as app

from .base import BaseRequestHandler
from ....helper.common import try_int
from ....indexers import indexer_config
from ....show.show import Show
from ....show_queue import ShowQueueActions


class ShowHandler(BaseRequestHandler):
    """Shows request handler."""

    def get(self, show_indexer, show_id, query):
        """Query show information.

        :param show_indexer:
        :param show_id:
        :type show_id: str
        """
        # @TODO: This should be completely replaced with show_id
        show_indexer = indexer_config.mapping[show_indexer] if show_indexer else None
        indexerid = self._parse(show_id)

        # @TODO: https://github.com/SiCKRAGETV/SiCKRAGE/pull/2558

        arg_paused = self.get_argument('paused', default=None)
        arg_sort = self._get_sort(default='title')
        arg_sort_order = self._get_sort_order()
        arg_page = self._get_page()
        arg_limit = self._get_limit()

        data = []
        headers = {}
        detailed = show_id is not None
        show_list = app.showList if not detailed else [Show.find(app.showList, indexerid, show_indexer)]
        for show in show_list:
            if show_id and show is None:
                return self.api_finish(status=404, error='Show not found')

            # If self.get_argument('paused') is None: show all, 0: show un-paused, 1: show paused
            if arg_paused is not None and try_int(arg_paused, -1) != show.paused:
                continue

            show_dict = show.to_json(detailed=detailed)
            if detailed:
                data = show_dict
                if query:
                    if query == 'queue':
                        action, message = app.showQueueScheduler.action.get_queue_action(show)
                        data = {
                            'action': ShowQueueActions.names[action],
                            'message': message,
                        } if action is not None else dict()
                    elif query in data:
                        data = data[query]
            else:
                data.append(show_dict)

        if not detailed:
            count = len(data)
            data = self._paginate(data, arg_sort, arg_sort_order, arg_page, arg_limit)
            headers = {
                'X-Pagination-Count': count,
                'X-Pagination-Page': arg_page,
                'X-Pagination-Limit': arg_limit
            }

        self.api_finish(data=data, headers=headers)

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
