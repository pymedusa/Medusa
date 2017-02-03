# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
#
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.
"""All providers type init."""
import pkgutil
from os import sys
from random import shuffle

from .nzb import (
    anizb, binsearch,
)
from .torrent import (
    abnormal, alpharatio, animebytes, animetorrents, bitcannon, bithdtv, bitsnoop, btn, cpasbien, danishbits,
    elitetorrent, extratorrent, freshontv, gftracker, hd4free, hdbits, hdspace, hdtorrents, hounddawgs, iptorrents,
    limetorrents, morethantv, newpct, norbits, nyaatorrents, pretome, rarbg, scc, scenetime, sdbits, shazbat,
    speedcd, t411, thepiratebay, tntvillage, tokyotoshokan, torrentbytes, torrentday, torrentleech, torrentproject,
    torrentz2, transmitthenet, tvchaosuk, xthor, zooqle
)
from .. import app

__all__ = [
    'btn', 'thepiratebay', 'torrentleech', 'scc', 'hdtorrents', 'torrentday', 'hdbits', 'hounddawgs', 'iptorrents',
    'speedcd', 'nyaatorrents', 'torrentbytes', 'freshontv', 'cpasbien', 'morethantv', 't411', 'tokyotoshokan',
    'alpharatio', 'sdbits', 'shazbat', 'rarbg', 'tntvillage', 'binsearch', 'xthor', 'abnormal', 'scenetime',
    'transmitthenet', 'tvchaosuk', 'torrentproject', 'extratorrent', 'bitcannon', 'torrentz2', 'pretome', 'gftracker',
    'hdspace', 'newpct', 'elitetorrent', 'bitsnoop', 'danishbits', 'hd4free', 'limetorrents', 'norbits', 'anizb',
    'bithdtv', 'zooqle', 'animebytes', 'animetorrents'
]


def sorted_provider_list(randomize=False):
    initial_list = app.providerList + app.newznabProviderList + app.torrentRssProviderList
    provider_dict = dict(zip([x.get_id() for x in initial_list], initial_list))

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

    raise Exception("Can't find " + prefix + name + " in " + "Providers")


def get_provider_class(provider_id):
    provider_list = app.providerList + app.newznabProviderList + app.torrentRssProviderList
    return next((provider for provider in provider_list if provider.get_id() == provider_id), None)
