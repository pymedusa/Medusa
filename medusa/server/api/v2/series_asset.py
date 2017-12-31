# coding=utf-8
"""Request handler for series assets."""

from medusa.server.api.v2.base import BaseRequestHandler
from medusa.server.api.v2.series import SeriesHandler
from medusa.tv.series import Series, SeriesIdentifier


class SeriesAssetHandler(BaseRequestHandler):
    """Series Asset request handler."""

    #: parent resource handler
    parent_handler = SeriesHandler
    #: resource name
    name = 'asset'
    #: identifier
    identifier = ('identifier', r'[a-zA-Z]+')
    #: allowed HTTP methods
    allowed_methods = ('GET', )

    def get(self, series_slug, identifier, *args, **kwargs):
        """Get an asset."""
        series_identifier = SeriesIdentifier.from_slug(series_slug)
        if not series_identifier:
            return self._bad_request('Invalid series slug')

        series = Series.find_by_identifier(series_identifier)
        if not series:
            return self._not_found('Series not found')

        asset_type = identifier or 'banner'
        asset = series.get_asset(asset_type)
        if not asset:
            return self._not_found('Asset not found')

        self._ok(stream=asset.media, content_type=asset.media_type)
