# coding=utf-8

"""All providers type init."""
from __future__ import unicode_literals

import importlib
import os
import pkgutil
from builtins import next
from builtins import zip
from os import sys
from random import shuffle

from medusa import app


torrent_kinds = ['html', 'json', 'rss', 'torznab', 'xml']
dirname = os.path.dirname(__file__)
modules = [os.path.join(dirname, 'torrent', kind) for kind in torrent_kinds] + [os.path.join(dirname, 'nzb')]

provider_names = []
for (module_loader, name, ispkg) in pkgutil.iter_modules(modules):
    base = os.path.basename(module_loader.path)
    if base != 'nzb':
        base = os.path.basename(os.path.dirname(module_loader.path)) + '.' + base
    module = importlib.import_module('.' + name, __package__ + '.' + base)
    if getattr(module, 'provider', None):
        provider_names.append(module.provider.name.lower())

__all__ = provider_names


def sorted_provider_list(randomize=False):
    initial_list = app.providerList + app.newznabProviderList + app.torrentRssProviderList + app.torznab_providers_list
    provider_dict = dict(list(zip([x.get_id() for x in initial_list], initial_list)))

    new_list = []

    # add all modules in the priority list, in order
    for cur_module in app.PROVIDER_ORDER:
        if cur_module in provider_dict:
            new_list.append(provider_dict[cur_module])

    # add all enabled providers first
    for cur_module in provider_dict:
        if provider_dict[cur_module] not in new_list and provider_dict[cur_module].is_enabled():
            new_list.append(provider_dict[cur_module])

    # add any modules that are missing from that list
    for cur_module in provider_dict:
        if provider_dict[cur_module] not in new_list:
            new_list.append(provider_dict[cur_module])

    if randomize:
        shuffle(new_list)

    return new_list


def make_provider_list():
    return [x.provider for x in (get_provider_module(y) for y in __all__) if x]


def get_provider_module(name):
    name = name.lower()
    prefixes = [modname + '.' for importer, modname, ispkg in pkgutil.walk_packages(
        path=__path__, prefix=__name__ + '.', onerror=lambda x: None) if ispkg]

    for prefix in prefixes:
        if name in __all__ and prefix + name in sys.modules:
            return sys.modules[prefix + name]

    raise Exception("Can't find {prefix}{name} in Providers".format(prefix=prefix, name=name))


def get_provider_class(provider_id):
    provider_list = app.providerList + app.newznabProviderList + app.torrentRssProviderList + app.torznab_providers_list
    return next((provider for provider in provider_list if provider.get_id() == provider_id), None)
