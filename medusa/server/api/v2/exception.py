# coding=utf-8
"""Request handler for scene/medusa exceptions."""
import logging
from six import iteritems

from .base import BaseRequestHandler
from .... import app
from ....scene_exceptions import get_all_scene_exceptions
from ....show.show import Show


logger = logging.getLogger(__name__)


class ExceptionHandler(BaseRequestHandler):
    """Scene/Medusa exception request handler."""

    def get(self, show_indexer, show_id):
        """Query scene/medusa exceptions.

        :param query:
        :type query: str
        """
        if Show.find(app.showList, show_id, show_indexer):
            # @TODO: This needs to take into account multiple indexers
            exceptions_list = get_all_scene_exceptions(show_id)
            data = {}
            for season, exception in iter(sorted(iteritems(exceptions_list))):
                data[season] = exception
            return self.api_finish(data=data)
        else:
            return self.api_finish(status=404, error='Show not found')

    def delete(self, query=None):
        """Delete all exceptions for a show/season.

        :param query:
        """
        self.api_finish()

    def post(self, query=None):
        """Create an exception.

        By definition this method is NOT idempotent.
        """
        self.api_finish()
