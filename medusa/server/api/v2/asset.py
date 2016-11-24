# coding=utf-8
"""Request handler for assets."""
import glob
import mimetypes
import os

import medusa as app

from .base import BaseRequestHandler


class AssetHandler(BaseRequestHandler):
    """Asset request handler."""

    def get(self, asset_group=None, query=None, *args, **kwargs):
        """Get an asset."""
        if asset_group and query:
            if asset_group == 'show':
                asset_type = self.get_argument('type', default='banner')
                return self._serve_asset(path=os.path.join(app.CACHE_DIR, 'images/'), filename=query + '.' + asset_type)
            if asset_group == 'network':
                return self._serve_asset(path=os.path.join(app.PROG_DIR, 'static/images/network/'), filename=query)

    def _serve_asset(self, path=None, filename=None):
        """Serve the asset from the provided path."""
        if path and filename:
            for infile in glob.glob(os.path.join(path, filename.lower() + '.*')):
                path = infile
            mime_type, _ = mimetypes.guess_type(path)
            if mime_type:
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
            else:
                self.api_finish(status=404, error='Asset or Asset Type Does Not Exist')
