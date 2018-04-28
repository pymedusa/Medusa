# coding=utf-8

from __future__ import unicode_literals

import json
import os

from medusa.browser import list_folders
from medusa.helpers.utils import truth_to_bool
from medusa.server.web.core.base import WebRoot

from tornroutes import route


@route('/browser(/?.*)')
class WebFileBrowser(WebRoot):
    def __init__(self, *args, **kwargs):
        super(WebFileBrowser, self).__init__(*args, **kwargs)

    def index(self, path='', includeFiles=False, *args, **kwargs):
        # @TODO: Move all cache control headers to the whole API end point so nothing's cached
        self.set_header('Cache-Control', 'max-age=0,no-cache,no-store')
        self.set_header('Content-Type', 'application/json')
        return json.dumps(list_folders(path, True, truth_to_bool(includeFiles)))

    def complete(self, term, includeFiles=False, *args, **kwargs):
        self.set_header('Cache-Control', 'max-age=0,no-cache,no-store')
        self.set_header('Content-Type', 'application/json')
        paths = [entry['path'] for entry in
                 list_folders(os.path.dirname(term), include_files=truth_to_bool(includeFiles))
                 if 'path' in entry]

        return json.dumps(paths)
