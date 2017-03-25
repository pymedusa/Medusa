# coding=utf-8

# Author: Dustyn Gibson <miigotu@gmail.com>

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
import logging
import socket

from medusa import app
from medusa.notifiers import boxcar2, emailnotify, emby, freemobile, growl, kodi, libnotify, nma, nmj, nmjv2, plex, prowl, pushalot, pushbullet, pushover, \
    pytivo, synoindex, synology_notifier, telegram, trakt, tweet

from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

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
]


def notify_download(ep_name):
    for n in notifiers:
        try:
            n.notify_download(ep_name)
        except (RequestException, socket.gaierror) as e:
            logger.debug(u'Unable to send download notification. Error: {error}', error=e.message)


def notify_subtitle_download(ep_name, lang):
    for n in notifiers:
        try:
            n.notify_subtitle_download(ep_name, lang)
        except (RequestException, socket.gaierror) as e:
            logger.debug(u'Unable to send download notification. Error: {error}', error=e.message)


def notify_snatch(ep_name, is_proper):
    for n in notifiers:
        try:
            n.notify_snatch(ep_name, is_proper)
        except (RequestException, socket.gaierror) as e:
            logger.debug(u'Unable to send snatch notification. Error: {error}', error=e.message)


def notify_git_update(new_version=""):
    for n in notifiers:
        if app.NOTIFY_ON_UPDATE:
            try:
                n.notify_git_update(new_version)
            except (RequestException, socket.gaierror) as e:
                logger.debug(u'Unable to send new update notification. Error: {error}', error=e.message)


def notify_login(ipaddress):
    for n in notifiers:
        if app.NOTIFY_ON_LOGIN:
            try:
                n.notify_login(ipaddress)
            except (RequestException, socket.gaierror) as e:
                logger.debug(u'Unable to new login notification. Error: {error}', error=e.message)
