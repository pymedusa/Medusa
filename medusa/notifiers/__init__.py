# coding=utf-8

from __future__ import unicode_literals

import logging
import socket

from medusa import app
from medusa.common import (
    NOTIFY_SNATCH,
    NOTIFY_SNATCH_PROPER,
    notifyStrings,
)
from medusa.logger.adapters.style import BraceAdapter
from medusa.notifiers import (
    boxcar2,
    discord,
    emailnotify,
    emby,
    freemobile,
    growl,
    join,
    kodi,
    libnotify,
    nmj,
    nmjv2,
    plex,
    prowl,
    pushalot,
    pushbullet,
    pushover,
    pytivo,
    slack,
    synoindex,
    synology_notifier,
    telegram,
    trakt,
    tweet,
)

from requests.exceptions import RequestException

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

# home theater / nas
kodi_notifier = kodi.Notifier()
plex_notifier = plex.Notifier()
emby_notifier = emby.Notifier()
nmj_notifier = nmj.Notifier()
nmjv2_notifier = nmjv2.Notifier()
synoindex_notifier = synoindex.Notifier()
synology_notifier = synology_notifier.Notifier()
pytivo_notifier = pytivo.Notifier()

# devices
growl_notifier = growl.Notifier()
prowl_notifier = prowl.Notifier()
libnotify_notifier = libnotify.Notifier()
pushover_notifier = pushover.Notifier()
boxcar2_notifier = boxcar2.Notifier()
pushalot_notifier = pushalot.Notifier()
pushbullet_notifier = pushbullet.Notifier()
join_notifier = join.Notifier()
freemobile_notifier = freemobile.Notifier()
telegram_notifier = telegram.Notifier()
discord_notifier = discord.Notifier()
# social
twitter_notifier = tweet.Notifier()
trakt_notifier = trakt.Notifier()
email_notifier = emailnotify.Notifier()
slack_notifier = slack.Notifier()

notifiers = [
    libnotify_notifier,  # Libnotify notifier goes first because it doesn't involve blocking on network activity.
    kodi_notifier,
    plex_notifier,
    nmj_notifier,
    nmjv2_notifier,
    synoindex_notifier,
    synology_notifier,
    pytivo_notifier,
    growl_notifier,
    freemobile_notifier,
    telegram_notifier,
    discord_notifier,
    prowl_notifier,
    pushover_notifier,
    boxcar2_notifier,
    pushalot_notifier,
    pushbullet_notifier,
    join_notifier,
    twitter_notifier,
    trakt_notifier,
    email_notifier,
    slack_notifier
]


def notify_download(ep_obj):
    for n in notifiers:
        try:
            n.notify_download(ep_obj)
        except (RequestException, socket.gaierror, socket.timeout) as error:
            log.debug(u'Unable to send download notification. Error: {0!r}', error)


def notify_subtitle_download(ep_obj, lang):
    for n in notifiers:
        try:
            n.notify_subtitle_download(ep_obj, lang)
        except (RequestException, socket.gaierror, socket.timeout) as error:
            log.debug(u'Unable to send subtitle download notification. Error: {0!r}', error)


def notify_snatch(ep_obj, result):
    ep_name = ep_obj.pretty_name_with_quality()
    is_proper = bool(result.proper_tags)
    title = notifyStrings[(NOTIFY_SNATCH, NOTIFY_SNATCH_PROPER)[is_proper]]

    has_peers = result.seeders not in (-1, None) and result.leechers not in (-1, None)
    if app.SEEDERS_LEECHERS_IN_NOTIFY and has_peers:
        message = u'{0} with {1} seeders and {2} leechers from {3}'.format(
            ep_name, result.seeders, result.leechers, result.provider.name)
    else:
        message = u'{0} from {1}'.format(ep_name, result.provider.name)

    for n in notifiers:
        try:
            n.notify_snatch(title, message)
        except (RequestException, socket.gaierror, socket.timeout) as error:
            log.debug(u'Unable to send snatch notification. Error: {0!r}', error)


def notify_git_update(new_version=''):
    for n in notifiers:
        if app.NOTIFY_ON_UPDATE:
            try:
                n.notify_git_update(new_version)
            except (RequestException, socket.gaierror, socket.timeout) as error:
                log.debug(u'Unable to send new update notification. Error: {0!r}', error)


def notify_login(ipaddress):
    for n in notifiers:
        if app.NOTIFY_ON_LOGIN:
            try:
                n.notify_login(ipaddress)
            except (RequestException, socket.gaierror, socket.timeout) as error:
                log.debug(u'Unable to new login notification. Error: {0!r}', error)
