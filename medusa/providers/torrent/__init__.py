# coding=utf-8

"""Initialize all torrent providers."""

from medusa.providers.torrent.html import (
    abnormal,
    alpharatio,
    anidex,
    animebytes,
    animetorrents,
    archetorrent,
    bithdtv,
    elitetorrent,
    elitetracker,
    gftracker,
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
    torrentleech,
    tvchaosuk,
    yggtorrent,
    zooqle,
)
from medusa.providers.torrent.json import (
    bitcannon,
    btn,
    danishbits,
    hd4free,
    hdbits,
    norbits,
    rarbg,
    torrentday,
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
    'abnormal', 'alpharatio', 'animebytes', 'archetorrent', 'bithdtv', 'torrent9', 'danishbits', 'elitetorrent',
    'gftracker', 'hdspace', 'hdtorrents', 'iptorrents', 'limetorrents', 'morethantv',
    'newpct', 'pretome', 'sdbits', 'scenetime', 'speedcd', 'thepiratebay', 'tntvillage', 'tokyotoshokan',
    'torrentbytes', 'torrentleech', 'nebulance', 'tvchaosuk', 'xthor', 'zooqle', 'bitcannon', 'btn', 'hd4free',
    'hdbits', 'norbits', 'rarbg', 'torrentday', 'nyaa', 'rsstorrent', 'shazbat', 'hebits',
    'torrentz2', 'animetorrents', 'horriblesubs', 'anidex', 'shanaproject', 'torrenting', 'yggtorrent',
    'elitetracker', 'privatehd'
]
