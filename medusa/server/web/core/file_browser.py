# coding=utf-8

from __future__ import unicode_literals

import json
import os

from tornado.routes import route
from .base import WebRoot
from ....browser import list_folders


@route('/browser(/?.*)')
class WebFileBrowser(WebRoot):
    def __init__(self, *args, **kwargs):
        super(WebFileBrowser, self).__init__(*args, **kwargs)

    def index(self, path='', includeFiles=False, *args, **kwargs):
        self.set_header('Cache-Control', 'max-age=0,no-cache,no-store')
        self.set_header('Content-Type', 'application/json')
        return json.dumps(list_folders(path, True, bool(int(includeFiles))))

    def complete(self, term, includeFiles=0, *args, **kwargs):
        self.set_header('Cache-Control', 'max-age=0,no-cache,no-store')
        self.set_header('Content-Type', 'application/json')
        paths = [entry['path'] for entry in list_folders(os.path.dirname(term), include_files=bool(int(includeFiles)))
                 if 'path' in entry]

        return json.dumps(paths)
