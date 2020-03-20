# coding=utf-8

"""Initialize all torrent providers."""
from __future__ import unicode_literals

import importlib
import os
import pkgutil
import sys


torrent_kinds = ['html', 'json', 'rss', 'torznab', 'xml']
dirname = os.path.dirname(__file__)
modules = [os.path.join(dirname, kind) for kind in torrent_kinds]

for (module_loader, name, ispkg) in pkgutil.iter_modules(modules):
    base = os.path.basename(module_loader.path)
    module = importlib.import_module('.' + name, __package__ + '.' + base)
    setattr(sys.modules[__name__], name, module)
