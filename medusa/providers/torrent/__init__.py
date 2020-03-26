# coding=utf-8

"""Initialize all torrent providers."""
from __future__ import unicode_literals

import importlib
import pkgutil
import sys


def import_submodules(package_name):
    package = sys.modules[package_name]

    results = {}
    for loader, name, is_pkg in pkgutil.iter_modules(package.__path__):
        full_name = package_name + '.' + name
        module = importlib.import_module(full_name)
        setattr(sys.modules[__name__], name, module)

        results[full_name] = module
        if is_pkg:
            valid_pkg = import_submodules(full_name)
            if valid_pkg:
                results.update(valid_pkg)

    return results


import_submodules(__name__)
