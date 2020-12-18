# coding=utf-8

"""All providers type init."""
from __future__ import unicode_literals

import importlib
import pkgutil
import sys
from builtins import next
from builtins import zip
from random import shuffle

from medusa import app


def import_providers(package_name):
    provider_names = []

    def import_submodules(subpackage_name):
        package = sys.modules[subpackage_name]

        results = {}
        for loader, name, is_pkg in pkgutil.iter_modules(package.__path__):
            full_name = subpackage_name + '.' + name
            module = importlib.import_module(full_name)
            if getattr(module, 'provider', None):
                provider_names.append(name)

            results[full_name] = module
            if is_pkg:
                valid_pkg = import_submodules(full_name)
                if valid_pkg:
                    results.update(valid_pkg)

        return results

    import_submodules(package_name)
    return provider_names


provider_names = import_providers(__name__)


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
    return [x.provider for x in (get_provider_module(y) for y in provider_names) if x]


def get_provider_module(name):
    name = name.lower()
    prefixes = [modname + '.' for importer, modname, ispkg in pkgutil.walk_packages(
        path=__path__, prefix=__name__ + '.', onerror=lambda x: None) if ispkg]

    for prefix in prefixes:
        if name in provider_names and prefix + name in sys.modules:
            return sys.modules[prefix + name]

    raise Exception("Can't find {prefix}{name} in Providers".format(prefix=prefix, name=name))


def get_provider_class(provider_id):
    provider_list = app.providerList + app.newznabProviderList + app.torrentRssProviderList + app.torznab_providers_list
    return next((provider for provider in provider_list if provider.get_id() == provider_id), None)
