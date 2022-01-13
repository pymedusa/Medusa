# coding=utf-8
"""Request handler for series assets."""
from __future__ import unicode_literals

from medusa import app
from medusa.server.api.v2.base import BaseRequestHandler
from medusa.tv.series import Series, SeriesIdentifier

from tornado.escape import json_decode


class SeriesChangeIndexer(BaseRequestHandler):
    """Change shows indexer."""

    #: resource name
    name = 'changeindexer'
    #: identifier
    identifier = None
    #: allowed HTTP methods
    allowed_methods = ('POST', )

    def post(self):
        """Change an existing show's indexer to another."""
        data = json_decode(self.request.body)
        old_slug = data.get('oldSlug')
        new_slug = data.get('newSlug')

        identifier = SeriesIdentifier.from_slug(old_slug)
        series_obj = Series.find_by_identifier(identifier)
        if not series_obj:
            return self._not_found(f'Could not find a show to change indexer with slug {old_slug}')

        queue_item_obj = app.show_queue_scheduler.action.changeIndexer(old_slug, new_slug)

        return self._created(data=queue_item_obj.to_json)
