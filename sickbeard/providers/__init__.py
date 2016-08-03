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

from os import sys
from random import shuffle

import sickbeard
from sickbeard.providers.nzb import (
    anizb, binsearch, omgwtfnzbs, womble,
)
from sickbeard.providers.torrent import (
    abnormal, alpharatio, animebytes, bitcannon, bithdtv, bitsnoop, bluetigers, btdigg, btn, cpasbien, danishbits,
    elitetorrent, extratorrent, freshontv, gftracker, hd4free, hdbits, hdspace, hdtorrents, hounddawgs, ilovetorrents,
    iptorrents, kat, limetorrents, morethantv, newpct, norbits, nyaatorrents, pretome, rarbg, scc, scenetime, shazbat,
    speedcd, t411, thepiratebay, tntvillage, tokyotoshokan, torrentbytes, torrentday, torrentleech, torrentproject,
    torrentshack, torrentz, transmitthenet, tvchaosuk, xthor, zooqle,
)

from .nzb.newznab import NewznabProvider
from .torrent.rss.rsstorrent import TorrentRssProvider

__all__ = [
    'womble', 'btn', 'thepiratebay', 'kat', 'torrentleech', 'scc', 'hdtorrents',
    'torrentday', 'hdbits', 'hounddawgs', 'iptorrents', 'omgwtfnzbs',
    'speedcd', 'nyaatorrents', 'torrentbytes', 'freshontv', 'cpasbien',
    'morethantv', 't411', 'tokyotoshokan', 'alpharatio',
    'shazbat', 'rarbg', 'tntvillage', 'binsearch', 'bluetigers',
    'xthor', 'abnormal', 'scenetime', 'btdigg', 'transmitthenet', 'tvchaosuk',
    'torrentproject', 'extratorrent', 'bitcannon', 'torrentz', 'pretome', 'gftracker',
    'hdspace', 'newpct', 'elitetorrent', 'bitsnoop', 'danishbits', 'hd4free', 'limetorrents',
    'norbits', 'ilovetorrents', 'anizb', 'bithdtv', 'zooqle', 'animebytes', 'torrentshack'
]


def sortedProviderList(randomize=False):
    initial_list = sickbeard.providerList + sickbeard.newznabProviderList + sickbeard.torrentRssProviderList
    provider_dict = dict(zip([x.get_id() for x in initial_list], initial_list))

    new_list = []

    # add all modules in the priority list, in order
    for cur_module in sickbeard.PROVIDER_ORDER:
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


def makeProviderList():
    return [x.provider for x in (getProviderModule(y) for y in __all__) if x]


def getProviderModule(name):
    name = name.lower()
    prefixes = [
        "sickbeard.providers.nzb.",
        "sickbeard.providers.torrent.html.",
        "sickbeard.providers.torrent.json.",
        "sickbeard.providers.torrent.rss.",
        "sickbeard.providers.torrent.xml.",
    ]

    for prefix in prefixes:
        if name in __all__ and prefix + name in sys.modules:
            return sys.modules[prefix + name]

    raise Exception("Can't find " + prefix + name + " in " + "Providers")


def getProviderClass(provider_id):
    provider_list = sickbeard.providerList + sickbeard.newznabProviderList + sickbeard.torrentRssProviderList
    return next((provider for provider in provider_list if provider.get_id() == provider_id), None)
