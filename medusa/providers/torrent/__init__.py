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
    freshontv,
    gftracker,
    hdspace,
    hdtorrents,
    horriblesubs,
    hounddawgs,
    iptorrents,
    limetorrents,
    morethantv,
    nebulance,
    newpct,
    pretome,
    scc,
    scenetime,
    sdbits,
    shanaproject,
    speedcd,
    thepiratebay,
    tntvillage,
    tokyotoshokan,
    torrent9,
    torrentbytes,
    torrentleech,
    torrentproject,
    tvchaosuk,
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
    t411,
    torrentday,
    xthor,
)

from medusa.providers.torrent.rss import (
    extratorrent,
    nyaa,
    rsstorrent,
    shazbat,
)

from medusa.providers.torrent.xml import (
    torrentz2,
)

__all__ = [
    'abnormal', 'alpharatio', 'animebytes', 'bithdtv', 'torrent9', 'danishbits', 'elitetorrent', 'extratorrent',
    'freshontv', 'gftracker', 'hdspace', 'hdtorrents', 'hounddawgs', 'iptorrents', 'limetorrents', 'morethantv',
    'newpct', 'pretome', 'sdbits', 'scc', 'scenetime', 'speedcd', 'thepiratebay', 'tntvillage', 'tokyotoshokan',
    'torrentbytes', 'torrentleech', 'nebulance', 'tvchaosuk', 'xthor', 'zooqle', 'bitcannon', 'btn', 'hd4free',
    'hdbits', 'norbits', 'rarbg', 't411', 'torrentday', 'torrentproject', 'nyaa', 'rsstorrent', 'shazbat',
    'torrentz2', 'animetorrents', 'horriblesubs', 'anidex', 'shanaproject'
]
