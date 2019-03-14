# coding=utf-8

"""Initialize all torrent providers."""
from __future__ import unicode_literals

from medusa.providers.torrent.html import (
    abnormal,
    alpharatio,
    anidex,
    animetorrents,
    archetorrent,
    avistaz,
    bithdtv,
    bjshare,
    cinemaz,
    elitetracker,
    hdspace,
    hdtorrents,
    hebits,
    iptorrents,
    limetorrents,
    morethantv,
    nebulance,
    nordicbits,
    pretome,
    privatehd,
    scenetime,
    sdbits,
    shanaproject,
    speedcd,
    thepiratebay,
    tntvillage,
    tokyotoshokan,
    torrentbytes,
    torrenting,
    tvchaosuk,
    yggtorrent,
    zooqle,
)
from medusa.providers.torrent.json import (
    animebytes,
    bitcannon,
    btn,
    danishbits,
    hdbits,
    norbits,
    rarbg,
    torrentday,
    torrentleech,
    xthor,
)
from medusa.providers.torrent.rss import (
    nyaa,
    rsstorrent,
    shazbat,
)
from medusa.providers.torrent.torznab import (
    torznab,
)
from medusa.providers.torrent.xml import (
    torrentz2,
)

__all__ = [
    'abnormal', 'alpharatio', 'animebytes', 'archetorrent', 'bithdtv', 'danishbits',
    'hdspace', 'hdtorrents', 'iptorrents', 'limetorrents', 'morethantv', 'torznab', 'nordicbits',
    'pretome', 'sdbits', 'scenetime', 'speedcd', 'thepiratebay', 'tntvillage', 'tokyotoshokan',
    'torrentbytes', 'torrentleech', 'nebulance', 'tvchaosuk', 'xthor', 'zooqle', 'bitcannon', 'btn',
    'hdbits', 'norbits', 'rarbg', 'torrentday', 'nyaa', 'rsstorrent', 'shazbat', 'hebits',
    'torrentz2', 'animetorrents', 'anidex', 'shanaproject', 'torrenting', 'yggtorrent',
    'elitetracker', 'privatehd', 'cinemaz', 'avistaz', 'bjshare'
]
