# coding=utf-8
"""Request handler for show assets."""
from __future__ import unicode_literals

from medusa.server.api.v2.base import BaseRequestHandler
from medusa.server.api.v2.show import ShowHandler
from medusa.tv.show import Show, ShowIdentifier


class ShowAssetHandler(BaseRequestHandler):
    """Show Asset request handler."""

    #: parent resource handler
    parent_handler = ShowHandler
    #: resource name
    name = 'asset'
    #: identifier
    identifier = ('identifier', r'[a-zA-Z]+')
    #: allowed HTTP methods
    allowed_methods = ('GET', )

    def get(self, show_slug, identifier, *args, **kwargs):
        """Get an asset."""
        show_identifier = ShowIdentifier.from_slug(show_slug)
        if not show_identifier:
            return self._bad_request('Invalid show slug')

        show = Show.find_by_identifier(show_identifier)
        if not show:
            return self._not_found('Show not found')

        asset_type = identifier or 'banner'
        asset = show.get_asset(asset_type)
        if not asset:
            return self._not_found('Asset not found')

        self._ok(stream=asset.media, content_type=asset.media_type)
