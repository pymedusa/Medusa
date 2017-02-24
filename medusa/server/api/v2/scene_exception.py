# coding=utf-8
"""Request handler for scene_exceptions."""

from medusa.scene_exceptions import get_last_refresh, retrieve_exceptions
from .base import BaseRequestHandler


class SceneExceptionRetrieveHandler(BaseRequestHandler):
    """Scene Exception request handler."""

    def set_default_headers(self):
        """Set default CORS headers."""
        super(SceneExceptionRetrieveHandler, self).set_default_headers()
        self.set_header('Access-Control-Allow-Methods', 'GET POST')

    @staticmethod
    def get_last_updates():
        """Query the cache table for the last update for every scene exception source."""
        last_updates = {}
        for scene_exception_source in ['custom_exceptions', 'xem', 'anidb']:
            last_updates[scene_exception_source] = get_last_refresh(scene_exception_source)[0]['last_refreshed']
        return last_updates

    def get(self):
        """Return statistical information on the scene_exceptions table."""
        return self.api_finish(data={'last_update': self.get_last_updates()})

    def post(self):
        """Start fetch retrieving scene name exceptions."""
        retrieve_exceptions(force=True)
        return self.api_finish(data={'result': 'Updated scene exceptions',
                                     'last_update': self.get_last_updates()})
