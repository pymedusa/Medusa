# coding=utf-8

"""Initialize all torrent providers."""

from medusa.providers.torrent.html import (
    abnormal,
    alpharatio,
    anidex,
    animebytes,
    animetorrents,
    bithdtv,
    elitetorrent,
    gftracker,
    hdspace,
    hdtorrents,
    hebits,
    horriblesubs,
    hounddawgs,
    iptorrents,
    limetorrents,
    morethantv,
    nebulance,
    newpct,
    pretome,
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
    torrentproject,
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

from medusa.providers.torrent.xml import (
    torrentz2,
)

__all__ = [
    'abnormal', 'alpharatio', 'animebytes', 'bithdtv', 'torrent9', 'danishbits', 'elitetorrent',
    'gftracker', 'hdspace', 'hdtorrents', 'hounddawgs', 'iptorrents', 'limetorrents', 'morethantv',
    'newpct', 'pretome', 'sdbits', 'scenetime', 'speedcd', 'thepiratebay', 'tntvillage', 'tokyotoshokan',
    'torrentbytes', 'torrentleech', 'nebulance', 'tvchaosuk', 'xthor', 'zooqle', 'bitcannon', 'btn', 'hd4free',
    'hdbits', 'norbits', 'rarbg', 'torrentday', 'torrentproject', 'nyaa', 'rsstorrent', 'shazbat', 'hebits',
    'torrentz2', 'animetorrents', 'horriblesubs', 'anidex', 'shanaproject', 'torrenting', 'yggtorrent'
]
