# coding=utf-8

"""Initialize all torrent providers."""
from __future__ import unicode_literals

from medusa.providers.torrent.html import (
    abnormal,
    alpharatio,
    anidex,
    animebytes,
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
    horriblesubs,
    iptorrents,
    limetorrents,
    morethantv,
    nebulance,
    newpct,
    pretome,
    privatehd,
    scenetime,
    sdbits,
    shanaproject,
    speedcd,
    thepiratebay,
    tntvillage,
    tokyotoshokan,
    torrent9,
    torrentbytes,
    torrenting,
    tvchaosuk,
    yggtorrent,
    zooqle,
)
from medusa.providers.torrent.json import (
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
    'abnormal', 'alpharatio', 'animebytes', 'archetorrent', 'bithdtv', 'torrent9', 'danishbits',
    'hdspace', 'hdtorrents', 'iptorrents', 'limetorrents', 'morethantv', 'torznab',
    'newpct', 'pretome', 'sdbits', 'scenetime', 'speedcd', 'thepiratebay', 'tntvillage', 'tokyotoshokan',
    'torrentbytes', 'torrentleech', 'nebulance', 'tvchaosuk', 'xthor', 'zooqle', 'bitcannon', 'btn',
    'hdbits', 'norbits', 'rarbg', 'torrentday', 'nyaa', 'rsstorrent', 'shazbat', 'hebits',
    'torrentz2', 'animetorrents', 'horriblesubs', 'anidex', 'shanaproject', 'torrenting', 'yggtorrent',
    'elitetracker', 'privatehd', 'cinemaz', 'avistaz', 'bjshare'
]
