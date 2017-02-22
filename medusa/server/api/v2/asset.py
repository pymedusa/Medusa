# coding=utf-8
"""Request handler for assets."""

from .base import BaseRequestHandler
from ....media.banner import ShowBanner
from ....media.fan_art import ShowFanArt
from ....media.network_logo import ShowNetworkLogo
from ....media.poster import ShowPoster
from ....media.trakt import ShowTrakt


class AssetHandler(BaseRequestHandler):
    """Asset request handler."""

    def get(self, asset_group=None, query=None, *args, **kwargs):
        """Get an asset."""
        if asset_group == 'show':
            # http://localhost:8081/api/v2/asset/show/295519?api_key=xxx&type=banner
            asset_type = self.get_argument('type', default='banner')
            show_id = query
            media = None
            media_format = ('normal', 'thumb')[asset_type in ('bannerThumb', 'posterThumb', 'small')]

            if asset_type.lower().startswith('banner'):
                media = ShowBanner(show_id, media_format)
            elif asset_type.lower().startswith('fanart'):
                media = ShowFanArt(show_id, media_format)
            elif asset_type.lower().startswith('poster'):
                media = ShowPoster(show_id, media_format)
            elif asset_type.lower().startswith('network'):
                media = ShowNetworkLogo(show_id, media_format)
            elif asset_type.lower().startswith('trakt'):
                media = ShowTrakt(show_id, media_format)

            if media is not None:
                self.set_header('Content-Type', media.get_media_type())
                self.api_finish(stream=media.get_media())
        else:
            self.api_finish(status=404, error='Asset or Asset Type Does Not Exist')
