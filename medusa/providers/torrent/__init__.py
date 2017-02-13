# coding=utf-8
"""Initialize all torrent providers."""
from .html import (
    abnormal,
    alpharatio,
    animebytes,
    animetorrents,
    bithdtv,
    cpasbien,
    danishbits,
    elitetorrent,
    freshontv,
    gftracker,
    hdspace,
    hdtorrents,
    hounddawgs,
    iptorrents,
    limetorrents,
    morethantv,
    newpct,
    pretome,
    scc,
    scenetime,
    sdbits,
    speedcd,
    thepiratebay,
    tntvillage,
    tokyotoshokan,
    torrentbytes,
    torrentleech,
    torrentproject,
    transmitthenet,
    tvchaosuk,
    xthor,
    zooqle,
)

from .json import (
    bitcannon,
    btn,
    hd4free,
    hdbits,
    norbits,
    rarbg,
    t411,
    torrentday,
)

from .rss import (
    extratorrent,
    nyaatorrents,
    rsstorrent,
    shazbat,
)

from .xml import (
    bitsnoop,
    torrentz2,
)

__all__ = [
    'abnormal', 'alpharatio', 'animebytes', 'bithdtv', 'cpasbien', 'danishbits', 'elitetorrent', 'extratorrent',
    'freshontv', 'gftracker', 'hdspace', 'hdtorrents', 'hounddawgs', 'iptorrents', 'limetorrents', 'morethantv',
    'newpct', 'pretome', 'sdbits', 'scc', 'scenetime', 'speedcd', 'thepiratebay', 'tntvillage', 'tokyotoshokan',
    'torrentbytes', 'torrentleech', 'transmitthenet', 'tvchaosuk', 'xthor', 'zooqle', 'bitcannon', 'btn', 'hd4free',
    'hdbits', 'norbits', 'rarbg', 't411', 'torrentday', 'torrentproject', 'nyaatorrents', 'rsstorrent', 'shazbat',
    'bitsnoop', 'torrentz2', 'animetorrents'
]
