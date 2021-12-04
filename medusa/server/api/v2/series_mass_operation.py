# coding=utf-8
"""Request handler for series assets."""
from __future__ import unicode_literals

from collections import defaultdict
from itertools import chain

from medusa import app, image_cache, ui
from medusa.helper.exceptions import (
    CantRefreshShowException,
    CantUpdateShowException,
)
from medusa.server.api.v2.base import BaseRequestHandler
from medusa.tv.series import Series, SeriesIdentifier

from tornado.escape import json_decode


class SeriesMassOperation(BaseRequestHandler):
    """Series mass update operation request handler."""

    #: resource name
    name = 'massupdate'
    #: identifier
    identifier = None
    #: allowed HTTP methods
    allowed_methods = ('POST', )

    def post(self):
        """Perform a mass update action."""
        data = json_decode(self.request.body)
        update = data.get('update', [])
        rescan = data.get('rescan', [])
        rename = data.get('rename', [])
        subtitle = data.get('subtitle', [])
        delete = data.get('delete', [])
        remove = data.get('remove', [])
        image = data.get('image', [])

        result = {
            'shows': defaultdict(list),
            'totals': {
                'update': 0,
                'rescan': 0,
                'rename': 0,
                'subtitle': 0,
                'delete': 0,
                'remove': 0,
                'image': 0
            }
        }

        for slug in set(update + rescan + rename + subtitle + delete + remove + image):
            identifier = SeriesIdentifier.from_slug(slug)
            series_obj = Series.find_by_identifier(identifier)

            if not series_obj:
                result['shows'][slug].append('Unable to locate show: {show}'.format(show=slug))
                continue

            if slug in delete + remove:
                app.show_queue_scheduler.action.removeShow(series_obj, slug in delete)
                if slug in delete:
                    result['totals']['delete'] += 1
                if slug in remove:
                    result['totals']['remove'] += 1
                continue  # don't do anything else if it's being deleted or removed

            if slug in update:
                try:
                    app.show_queue_scheduler.action.updateShow(series_obj)
                    result['totals']['update'] += 1
                except CantUpdateShowException as msg:
                    result['shows'][slug].append('Unable to update show: {error}'.format(error=msg))

            elif slug in rescan:  # don't bother refreshing shows that were updated
                try:
                    app.show_queue_scheduler.action.refreshShow(series_obj)
                    result['totals']['rescan'] += 1
                except CantRefreshShowException as msg:
                    result['shows'][slug].append(
                        'Unable to refresh show {show.name}: {error}'.format(show=series_obj, error=msg)
                    )

            if slug in rename:
                app.show_queue_scheduler.action.renameShowEpisodes(series_obj)
                result['totals']['rename'] += 1

            if slug in subtitle:
                app.show_queue_scheduler.action.download_subtitles(series_obj)
                result['totals']['subtitle'] += 1

            if slug in image:
                image_cache.replace_images(series_obj)
                result['totals']['image'] += 1

        if result['shows']:
            ui.notifications.error('Errors encountered', '<br />\n'.join(chain(*result['shows'].values())))

        return self._created(data=result)
