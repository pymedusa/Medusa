# coding=utf-8

"""Initialize all torrent providers."""
from __future__ import unicode_literals

import importlib
import os
import pkgutil


torrent_kinds = ['html', 'json', 'rss', 'torznab', 'xml']
dirname = os.path.dirname(__file__)
modules = [os.path.join(dirname, kind) for kind in torrent_kinds]

provider_names = []
for (module_loader, name, ispkg) in pkgutil.iter_modules(modules):
    base = os.path.basename(module_loader.path)
    module = importlib.import_module('.' + name, __package__ + '.' + base)
    if getattr(module, 'provider', None):
        provider_names.append(module.provider.name.lower())

__all__ = provider_names
