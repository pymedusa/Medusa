# coding=utf-8

import logging
import socket

from medusa import app
from medusa.logger.adapters.style import BraceAdapter
from medusa.notifiers import (
    boxcar2,
    emailnotify,
    emby,
    freemobile,
    growl,
    kodi,
    libnotify,
    nma,
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
nma_notifier = nma.Notifier()
pushalot_notifier = pushalot.Notifier()
pushbullet_notifier = pushbullet.Notifier()
freemobile_notifier = freemobile.Notifier()
telegram_notifier = telegram.Notifier()
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
    prowl_notifier,
    pushover_notifier,
    boxcar2_notifier,
    nma_notifier,
    pushalot_notifier,
    pushbullet_notifier,
    twitter_notifier,
    trakt_notifier,
    email_notifier,
    slack_notifier
]


def notify_download(ep_name):
    for n in notifiers:
        try:
            n.notify_download(ep_name)
        except (RequestException, socket.gaierror) as error:
            log.debug(u'Unable to send download notification. Error: {0}', error.message)


def notify_subtitle_download(ep_name, lang):
    for n in notifiers:
        try:
            n.notify_subtitle_download(ep_name, lang)
        except (RequestException, socket.gaierror) as error:
            log.debug(u'Unable to send download notification. Error: {0}', error.message)


def notify_snatch(ep_name, is_proper):
    for n in notifiers:
        try:
            n.notify_snatch(ep_name, is_proper)
        except (RequestException, socket.gaierror) as error:
            log.debug(u'Unable to send snatch notification. Error: {0}', error.message)


def notify_git_update(new_version=""):
    for n in notifiers:
        if app.NOTIFY_ON_UPDATE:
            try:
                n.notify_git_update(new_version)
            except (RequestException, socket.gaierror) as error:
                log.debug(u'Unable to send new update notification. Error: {0}', error.message)


def notify_login(ipaddress):
    for n in notifiers:
        if app.NOTIFY_ON_LOGIN:
            try:
                n.notify_login(ipaddress)
            except (RequestException, socket.gaierror) as error:
                log.debug(u'Unable to new login notification. Error: {0}', error.message)
