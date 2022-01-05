# coding=utf-8
"""Request handler for notifications data."""
from __future__ import unicode_literals


import logging
import re

from medusa import app, notifiers, ui
from medusa.logger.adapters.style import BraceAdapter
from medusa.server.api.v2.base import BaseRequestHandler
from medusa.tv.series import Series, SeriesIdentifier

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class NotificationsHandler(BaseRequestHandler):
    """Notifications data request handler."""

    #: resource name
    name = 'notifications'
    #: identifier
    identifier = ('resource', r'\w+')
    #: path param
    path_param = ('path_param', r'\w+')
    #: allowed HTTP methods
    allowed_methods = ('GET', 'POST')

    def post(self, resource, path_param=None):
        """Post Notifications actions for a specific external source.

        :param resource: a resource name
        :param path_param:
        :type path_param: str
        """
        if resource is None:
            return self._bad_request('You must provide a notifications resource name')

        available_resources = (
            'kodi', 'plexserver', 'plexhome', 'emby', 'nmj', 'nmjv2', 'trakt', 'plex'
        )

        if resource not in available_resources:
            return self._bad_request(f"Resource must be one of {', '.join(available_resources)}")

        # Convert 'camelCase' to 'resource_snake_case'
        resource_function_name = resource + '_' + re.sub('([A-Z]+)', r'_\1', path_param).lower()
        resource_function = getattr(self, resource_function_name, None)

        if resource_function is None:
            log.error('Unable to get function "{func}" for resource "{resource}"',
                      {'func': resource_function_name, 'resource': path_param})
            return self._bad_request('{key} is a invalid resource'.format(key=path_param))

        return resource_function()

    def kodi_update(self):
        """Update kodi's show library."""
        if app.KODI_UPDATE_ONLYFIRST:
            host = app.KODI_HOST[0].strip()
        else:
            host = ', '.join(app.KODI_HOST)

        if notifiers.kodi_notifier.update_library():
            ui.notifications.message(f'Library update command sent to KODI host(s): {host}')
        else:
            ui.notifications.error(f'Unable to contact one or more KODI host(s): {host}')

        return self._created()

    def emby_update(self):
        """Update emby's show library."""
        show_slug = self.get_argument('showslug', '')
        show = None

        if show_slug:
            show_identifier = SeriesIdentifier.from_slug(show_slug)
            if not show_identifier:
                return self._bad_request('Invalid show slug')

            show = Series.find_by_identifier(show_identifier)
            if not show:
                return self._not_found('Series not found')

        if notifiers.emby_notifier.update_library(show):
            ui.notifications.message(f'Library update command sent to Emby host: {app.EMBY_HOST}')
        else:
            ui.notifications.error(f'Unable to contact Emby host: {app.EMBY_HOST}')

        return self._created()

    def plex_update(self):
        """Update plex's show library."""
        if not notifiers.plex_notifier.update_library():
            ui.notifications.message(
                f"Library update command sent to Plex Media Server host: {', '.join(app.PLEX_SERVER_HOST)}")
        else:
            ui.notifications.error(f"Unable to contact Plex Media Server host: {', '.join(app.PLEX_SERVER_HOST)}")

        return self._created()
