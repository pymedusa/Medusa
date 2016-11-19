# coding=utf-8
"""Request handler for assets."""
from .base import BaseRequestHandler
import mimetypes
import os
import medusa as app


class AssetHandler(BaseRequestHandler):
    """Asset request handler."""

    def get(self, asset_group=None, query=None, *args, **kwargs):
        """Get an asset.
        """
        if asset_group and query is not None:
            if asset_group == 'show':
                asset_type = self.get_argument('type', default='banner')
                path = os.path.join(app.CACHE_DIR, 'images/' + query + '.' + asset_type + '.jpg')
                mime_type, encoding = mimetypes.guess_type(path)
                self.set_status(200)
                self.set_header('Content-type', mime_type)
                try:
                    with open(path, 'rb') as f:
                        while 1:
                            data = f.read(16384)
                            if not data:
                                break
                            self.write(data)
                    self.finish()
                except IOError:
                    self.api_finish(status=404, error='Asset or Asset Type Does Not Exist')
